#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PsyLens 公开数据审计脚本（PSYLENS-AUDIT-001 / Phase 0）。

设计约束（严格遵守）：
  1. 不进行任何网络调用。
  2. 不调用任何模型 / API。
  3. 不读取环境变量中的任何密钥 / cookie / token。
  4. 只读取仓库内的公开文件，不修改任何被审计的历史数据文件。
  5. 相同输入产生相同结果（确定性）。
  6. 若存在阻断性（BLOCKED）数据错误，进程返回非零退出码。

仅依赖 Python 标准库（csv / json / re / difflib / unicodedata / html / zipfile
/ xml / hashlib / argparse / pathlib / collections），不依赖 pandas、python-docx。

用法：
    python tools/audit_public_data.py
    python tools/audit_public_data.py --json-out <path>
    python tools/audit_public_data.py --csv-out <path>          # 证据单元逐行关联表
    python tools/audit_public_data.py --mismatch-out <path>      # ID 不匹配报告
"""
from __future__ import annotations

import argparse
import csv
import html
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from pathlib import Path
from urllib.parse import urlparse

# ---------------------------------------------------------------------------
# 路径与常量
# ---------------------------------------------------------------------------
TOOLS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TOOLS_DIR.parent
FILES_DIR = REPO_ROOT / "docs" / "files"

CLEAN_CSV = FILES_DIR / "input_feedback_phase2_multiplatform_clean.csv"
EVIDENCE_CSV = FILES_DIR / "final_evidence_table.csv"
INSIGHTS_JSONL = FILES_DIR / "04_validated_insights.jsonl"
ACTION_JSON = FILES_DIR / "05_action_matrix.json"

# v2 数据底座（Phase 1A）
V2_DIR = REPO_ROOT / "data" / "v2"
V2_SAMPLES = V2_DIR / "samples_v2.csv"
V2_EVIDENCE = V2_DIR / "evidence_v2.csv"
V2_AMBIGUOUS = V2_DIR / "ambiguous_evidence_queue.csv"
V2_BILI_QUEUE = V2_DIR / "bili_evidence_queue.csv"
V2_MIGRATION = V2_DIR / "id_migration.csv"
V2_MANIFEST = V2_DIR / "v2_manifest.json"

SAMPLE_ID_RE = re.compile(r"^(BILI|NGA|TIEBA)_\d{4}$")
EVIDENCE_ID_RE = re.compile(r"^(BILI|NGA|TIEBA)_\d{4}_U\d{2}$")
EXPECTED_MIGRATED_EVIDENCE = 695
EXPECTED_AMBIGUOUS = 2
EXPECTED_V2_CSV_NAMES = ["samples_v2.csv", "evidence_v2.csv", "ambiguous_evidence_queue.csv",
                         "bili_evidence_queue.csv", "id_migration.csv"]
# 当前冻结 v2 快照的权威来源提交与来源文件（用于精确校验，非仅格式）
EXPECTED_V2_SOURCE_DATA_COMMIT = "371d245a0ce82ed5d980472147b49568525e2986"
EXPECTED_V2_SOURCE_FILES = {
    "clean_csv": "docs/files/input_feedback_phase2_multiplatform_clean.csv",
    "evidence_csv": "docs/files/final_evidence_table.csv",
}
# legacy evidence id 的 _uN 后缀解析
LEGACY_UNIT_RE = re.compile(r"_u(\d+)$")

# 合法取值集合（依据 METHODOLOGY.md §3 与 run_pipeline.py 的 allowed labels）
ALLOWED_SURFACE_TOPIC = {
    "rewards", "matchmaking", "progression", "balance", "new_player_onboarding",
    "community_conflict", "communication_transparency", "event_design", "other_uncertain",
}
ALLOWED_MECHANISM = {
    "competence_frustration", "fairness_threat", "trust_communication_gap",
    "belonging_drop", "norm_safety_risk", "uncertain",
}
ALLOWED_CONFIDENCE = {"high", "medium", "low"}
ALLOWED_THEME_BUCKET = {
    "balance_mechanic", "hero_experience", "team_interaction",
    "fairness_attribution", "off_topic",
}

EXPECTED_CLEAN_ROWS = 360
EXPECTED_EVIDENCE_ROWS = 697
EXPECTED_INSIGHTS = 19

# 相似度阈值（文档化，供报告引用）
HIGH_SIM_RATIO = 0.85       # SequenceMatcher.ratio() >= 此值 -> high_similarity
HIGH_NGRAM_OVERLAP = 0.80   # 字符 3-gram overlap 系数 >= 此值 -> high_similarity
PARTIAL_SIM_RATIO = 0.40
PARTIAL_NGRAM_OVERLAP = 0.50
DUP_TEXT_SIM = 0.90         # 整洁样本高相似文本阈值


# ---------------------------------------------------------------------------
# 文本归一化
# ---------------------------------------------------------------------------
_PUNCT_MAP = {
    "，": ",", "。": ".", "！": "!", "？": "?", "；": ";", "：": ":",
    "“": '"', "”": '"', "‘": "'", "’": "'", "（": "(", "）": ")",
    "、": ",", "《": "<", "》": ">", "【": "[", "】": "]", "—": "-",
    "～": "~", "…": ".", "·": ".",
}


def normalize_text(text: str) -> str:
    """文本归一化：HTML 转义、全半角(NFKC)、大小写、中英文标点、空白、连续重复标点。"""
    if text is None:
        return ""
    t = html.unescape(str(text))
    t = unicodedata.normalize("NFKC", t)  # 全角->半角等
    t = t.lower()
    t = "".join(_PUNCT_MAP.get(ch, ch) for ch in t)
    t = re.sub(r"\s+", "", t)              # 移除所有空白，便于子串匹配
    t = re.sub(r"([^\w\u4e00-\u9fff])\1+", r"\1", t)  # 连续重复标点折叠为一个
    return t


def char_ngrams(s: str, n: int = 3):
    if len(s) < n:
        return {s} if s else set()
    return {s[i:i + n] for i in range(len(s) - n + 1)}


def ngram_overlap(a: str, b: str, n: int = 3) -> float:
    """overlap 系数 = |A∩B| / min(|A|,|B|)。"""
    ga, gb = char_ngrams(a, n), char_ngrams(b, n)
    if not ga or not gb:
        return 0.0
    inter = len(ga & gb)
    return inter / min(len(ga), len(gb))


# ---------------------------------------------------------------------------
# 文件读取
# ---------------------------------------------------------------------------
def read_bytes(path: Path) -> bytes:
    return path.read_bytes() if path.exists() else b""


def detect_encoding_report(path: Path) -> dict:
    raw = read_bytes(path)
    has_bom = raw.startswith(b"\xef\xbb\xbf")
    has_crlf = b"\r\n" in raw
    has_lone_lf = b"\n" in raw.replace(b"\r\n", b"")
    utf8_ok = True
    try:
        raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        utf8_ok = False
    return {
        "exists": path.exists(),
        "size_bytes": len(raw),
        "has_utf8_bom": has_bom,
        "has_crlf": has_crlf,
        "has_lone_lf": has_lone_lf,
        "utf8_decodable": utf8_ok,
    }


def read_csv_rows(path: Path):
    """用 utf-8-sig 读取 CSV（去 BOM），返回 (fieldnames, list[dict])。"""
    if not path.exists():
        return [], []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fields = reader.fieldnames or []
    return fields, rows


def read_jsonl(path: Path):
    """返回 (list[(lineno, ok, obj_or_errstr, raw)])。"""
    results = []
    if not path.exists():
        return results
    with path.open("r", encoding="utf-8-sig") as f:
        for i, line in enumerate(f, 1):
            raw = line.rstrip("\n")
            if raw.strip() == "":
                continue
            try:
                results.append((i, True, json.loads(raw), raw))
            except json.JSONDecodeError as e:
                results.append((i, False, str(e), raw))
    return results


# ---------------------------------------------------------------------------
# 隐私 / PII 启发式扫描（仅报告，不判定违规）
# ---------------------------------------------------------------------------
PII_PATTERNS = {
    "email": re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}"),
    "phone_cn": re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)"),
    "qq": re.compile(r"(?:q{1,2}|扣扣|企鹅)[\s:：号]*(\d{5,12})", re.I),
    "wechat": re.compile(r"(?:微信|weixin|vx|wx)[\s:：号]*([A-Za-z][-_A-Za-z0-9]{5,19})", re.I),
    "at_mention": re.compile(r"@[\w\u4e00-\u9fff\-]{2,20}"),
    "bvid": re.compile(r"BV[0-9A-Za-z]{8,12}"),
    "tieba_pid": re.compile(r"tieba\.baidu\.com/p/\d+"),
    "uid_param": re.compile(r"\b(?:uid|mid|space)\b[=/:]\s*\d{4,}", re.I),
    "url_userpage": re.compile(r"(?:space\.bilibili\.com|home\.php\?mod=space)", re.I),
}


def scan_pii(text: str) -> dict:
    hits = {}
    for name, pat in PII_PATTERNS.items():
        found = pat.findall(text or "")
        if found:
            hits[name] = len(found)
    return hits


# ---------------------------------------------------------------------------
# 阶段一：整洁样本审计
# ---------------------------------------------------------------------------
def audit_clean(clean_rows):
    n = len(clean_rows)
    ids = [r.get("id", "") for r in clean_rows]
    id_nonempty = [i for i in ids if str(i).strip() != ""]
    id_empty = n - len(id_nonempty)
    id_dupes = [k for k, v in Counter(id_nonempty).items() if v > 1]
    non_int_ids = [i for i in id_nonempty if not re.fullmatch(r"\d+", str(i).strip())]

    platform_dist = Counter(r.get("platform_source", "") for r in clean_rows)
    window_dist = Counter(r.get("window_tag", "") for r in clean_rows)
    theme_dist = Counter(r.get("theme_bucket", "") for r in clean_rows)
    reply_dist = Counter(r.get("reply_type", "") for r in clean_rows)

    raw_empty = sum(1 for r in clean_rows if str(r.get("raw_text", "")).strip() == "")
    url_empty = sum(1 for r in clean_rows if str(r.get("url", "")).strip() == "")
    date_empty = sum(1 for r in clean_rows if str(r.get("date", "")).strip() == "")

    domain_dist = Counter()
    for r in clean_rows:
        u = str(r.get("url", "")).strip()
        if u:
            try:
                netloc = urlparse(u).netloc or "(unparsable)"
            except ValueError:
                netloc = "(unparsable)"
            domain_dist[netloc] += 1

    # 重复文本 / 高相似文本
    norm_map = {}
    for r in clean_rows:
        norm_map[str(r.get("id"))] = normalize_text(r.get("raw_text", ""))
    exact_dupe_groups = defaultdict(list)
    for rid, nt in norm_map.items():
        if nt:
            exact_dupe_groups[nt].append(rid)
    exact_dupes = {k: v for k, v in exact_dupe_groups.items() if len(v) > 1}

    high_sim_pairs = []
    items = [(rid, nt) for rid, nt in norm_map.items() if len(nt) >= 10]
    for a in range(len(items)):
        ida, ta = items[a]
        for b in range(a + 1, len(items)):
            idb, tb = items[b]
            if ta == tb:
                continue  # 已在精确重复
            # 长度差异过大跳过，降低开销
            if min(len(ta), len(tb)) / max(len(ta), len(tb)) < 0.6:
                continue
            ratio = SequenceMatcher(None, ta, tb).ratio()
            if ratio >= DUP_TEXT_SIM:
                high_sim_pairs.append({"id_a": ida, "id_b": idb, "ratio": round(ratio, 4)})

    # PII 扫描
    pii_summary = Counter()
    pii_rows = []
    for r in clean_rows:
        combined = " ".join(str(r.get(c, "")) for c in ("raw_text", "url", "thread_or_video_title"))
        hits = scan_pii(combined)
        if hits:
            for k, v in hits.items():
                pii_summary[k] += v
            pii_rows.append({"id": r.get("id"), "hits": hits})

    # 粗口 / 攻击性（启发式，仅提示）
    profanity_terms = ["傻逼", "sb", "垃圾", "废物", "脑残", "智障", "nmsl", "操你", "草你", "狗屎", "煞笔", "弱智"]
    profanity_rows = []
    for r in clean_rows:
        txt = str(r.get("raw_text", ""))
        low = txt.lower()
        hit = [t for t in profanity_terms if t in low]
        if hit:
            profanity_rows.append({"id": r.get("id"), "terms": sorted(set(hit))})

    return {
        "total_rows": n,
        "id_unique": len(id_dupes) == 0 and id_empty == 0,
        "id_empty_count": id_empty,
        "id_duplicate_values": id_dupes,
        "id_non_integer_values": non_int_ids,
        "platform_distribution": dict(platform_dist),
        "window_distribution": dict(window_dist),
        "theme_bucket_distribution": dict(theme_dist),
        "reply_type_distribution": dict(reply_dist),
        "raw_text_empty_count": raw_empty,
        "url_empty_count": url_empty,
        "date_empty_count": date_empty,
        "url_domain_distribution": dict(domain_dist),
        "exact_duplicate_text_groups": len(exact_dupes),
        "exact_duplicate_examples": {k[:30]: v for k, v in list(exact_dupes.items())[:10]},
        "high_similarity_pair_count": len(high_sim_pairs),
        "high_similarity_examples": high_sim_pairs[:20],
        "pii_hit_summary": dict(pii_summary),
        "pii_hit_row_count": len(pii_rows),
        "pii_hit_rows_sample": pii_rows[:30],
        "profanity_hit_row_count": len(profanity_rows),
        "profanity_hit_rows_sample": profanity_rows[:30],
    }


# ---------------------------------------------------------------------------
# 阶段二：证据单元审计（含 linkage_status）
# ---------------------------------------------------------------------------
def classify_linkage(unit_text, parent_raw, parent_exists):
    if not parent_exists:
        return "missing_parent", None, None
    if str(unit_text).strip() == "":
        return "empty_text", None, None
    if str(unit_text) in str(parent_raw):
        return "exact_substring", 1.0, 1.0
    nu, npar = normalize_text(unit_text), normalize_text(parent_raw)
    if nu and nu in npar:
        return "normalized_substring", 1.0, 1.0
    ratio = SequenceMatcher(None, nu, npar).ratio() if nu and npar else 0.0
    ov = ngram_overlap(nu, npar) if nu and npar else 0.0
    if ratio >= HIGH_SIM_RATIO or ov >= HIGH_NGRAM_OVERLAP:
        return "high_similarity", round(ratio, 4), round(ov, 4)
    if ratio >= PARTIAL_SIM_RATIO or ov >= PARTIAL_NGRAM_OVERLAP:
        return "partial_overlap", round(ratio, 4), round(ov, 4)
    return "no_match", round(ratio, 4), round(ov, 4)


def audit_evidence(evidence_rows, clean_rows):
    clean_by_id = {str(r.get("id")): r for r in clean_rows}
    # 全域归一化索引：unit_text 是否能在 *任意* 整洁样本中定位（用于诊断 id 错位）
    clean_norm = {str(r.get("id")): normalize_text(r.get("raw_text", "")) for r in clean_rows}
    n = len(evidence_rows)
    ids = [r.get("id", "") for r in evidence_rows]
    id_dupes = [k for k, v in Counter(ids).items() if v > 1]

    parent_empty = sum(1 for r in evidence_rows if str(r.get("parent_id", "")).strip() == "")
    unit_empty = sum(1 for r in evidence_rows if str(r.get("unit_text", "")).strip() == "")

    bad_mechanism = Counter()
    bad_topic = Counter()
    bad_conf = Counter()
    ev_rawtext_nonempty = 0

    surface_dist = Counter()
    mechanism_dist = Counter()
    confidence_dist = Counter()

    linkage_rows = []
    status_counter = Counter()
    phrase_in_unit = 0
    phrase_total_nonempty = 0
    phrase_norm_only = 0
    parent_missing_ids = []

    # 全域匹配诊断计数（多候选感知）
    # 分类：found_in_declared_parent / unique_match_in_other_id
    #      / ambiguous_match_in_other_ids / not_found_anywhere
    global_counter = Counter()
    offset_examples = []            # 仅收集 *唯一命中* 的偏移示例
    ambiguous_examples = []         # 歧义命中示例（多候选）
    unique_offset_hist = Counter()  # 仅唯一命中参与偏移直方图
    parent_ids_int = []
    parent_reference_exists = 0     # parent_id 值能找到同编号 clean 行
    parent_semantic_linkage = 0     # unit_text 匹配声明 parent raw_text
    actual_platform_dist = Counter()  # 仅唯一命中计入平台分布
    evidence_actual_source = {}       # evidence_id -> {actual_clean_id, actual_platform, actual_window}（仅唯一命中）

    for r in evidence_rows:
        eid = str(r.get("id"))
        pid = str(r.get("parent_id", "")).strip()
        unit = r.get("unit_text", "") or ""
        mech = (r.get("mechanism_label", "") or "").strip()
        topic = (r.get("surface_topic", "") or "").strip()
        conf = (r.get("confidence", "") or "").strip()
        phrase = (r.get("evidence_phrase", "") or "").strip()
        ev_raw = (r.get("raw_text", "") or "").strip()

        surface_dist[topic] += 1
        mechanism_dist[mech] += 1
        confidence_dist[conf] += 1

        if mech not in ALLOWED_MECHANISM:
            bad_mechanism[mech] += 1
        if topic not in ALLOWED_SURFACE_TOPIC:
            bad_topic[topic] += 1
        if conf not in ALLOWED_CONFIDENCE:
            bad_conf[conf] += 1
        if ev_raw != "":
            ev_rawtext_nonempty += 1

        parent = clean_by_id.get(pid)
        parent_exists = parent is not None
        if parent_exists:
            parent_reference_exists += 1
        if not parent_exists and pid != "":
            parent_missing_ids.append({"evidence_id": eid, "parent_id": pid})
        parent_raw = parent.get("raw_text", "") if parent else ""

        status, ratio, ov = classify_linkage(unit, parent_raw, parent_exists)
        status_counter[status] += 1
        # 语义关联：unit_text 精确/归一化匹配声明 parent 原文
        if status in ("exact_substring", "normalized_substring", "high_similarity"):
            parent_semantic_linkage += 1

        # 全域诊断（多候选）：收集 *所有* 包含 unit_text 的 clean id
        nu = normalize_text(unit)
        candidate_ids = []
        if nu:
            candidate_ids = [cid for cid, cn in clean_norm.items() if nu in cn]
        candidate_count = len(candidate_ids)

        global_match_id = None       # 仅当唯一命中时才确定
        if candidate_count == 0:
            global_status = "not_found_anywhere"
        elif parent_exists and pid in candidate_ids and candidate_count == 1:
            global_status = "found_in_declared_parent"
            global_match_id = pid
        elif candidate_count == 1:
            global_status = "unique_match_in_other_id"
            global_match_id = candidate_ids[0]
        else:
            global_status = "ambiguous_match_in_other_ids"
        global_counter[global_status] += 1

        if re.fullmatch(r"\d+", pid or ""):
            parent_ids_int.append(int(pid))

        # 仅唯一命中：计入平台分布、offset、实际出处
        if global_match_id is not None:
            gm_row = clean_by_id.get(global_match_id, {})
            actual_platform_dist[gm_row.get("platform_source", "")] += 1
            evidence_actual_source[eid] = {
                "actual_clean_id": global_match_id,
                "actual_platform": gm_row.get("platform_source", ""),
                "actual_window": gm_row.get("window_tag", ""),
            }
            if global_status == "unique_match_in_other_id":
                try:
                    off = int(global_match_id) - int(pid)
                except (ValueError, TypeError):
                    off = None
                unique_offset_hist[off] += 1
                if len(offset_examples) < 60:
                    offset_examples.append({
                        "evidence_id": eid, "declared_parent_id": pid,
                        "actual_clean_id": global_match_id, "offset": off,
                        "declared_platform": (clean_by_id.get(pid, {}).get("platform_source")
                                              if parent_exists else None),
                        "actual_platform": gm_row.get("platform_source"),
                    })
        elif global_status == "ambiguous_match_in_other_ids" and len(ambiguous_examples) < 60:
            ambiguous_examples.append({
                "evidence_id": eid, "declared_parent_id": pid,
                "candidate_count": candidate_count,
                "candidate_clean_ids": candidate_ids[:10],
                "candidate_platforms": sorted({clean_by_id.get(c, {}).get("platform_source", "") for c in candidate_ids}),
            })

        # evidence_phrase 是否在 unit_text 内
        if phrase != "":
            phrase_total_nonempty += 1
            if phrase in unit:
                phrase_in_unit += 1
            elif normalize_text(phrase) and normalize_text(phrase) in normalize_text(unit):
                phrase_norm_only += 1

        excerpt = re.sub(r"\s+", " ", str(parent_raw))[:60]
        substr = status in ("exact_substring", "normalized_substring")
        note = ""
        if global_status == "unique_match_in_other_id":
            note = f"unit_text 唯一命中 clean id={global_match_id}（parent_id 错位）"
        elif global_status == "ambiguous_match_in_other_ids":
            note = f"unit_text 命中多个 clean id（candidate_count={candidate_count}），来源不确定"
        elif global_status == "not_found_anywhere":
            note = "unit_text 在任何整洁样本中均未找到"
        linkage_rows.append({
            "evidence_id": eid,
            "parent_id": pid,
            "linkage_status": status,
            "substring_match": substr,
            "similarity_ratio": ratio if ratio is not None else "",
            "ngram_overlap": ov if ov is not None else "",
            "evidence_text": re.sub(r"\s+", " ", str(unit))[:80],
            "parent_text_excerpt": excerpt,
            "notes": note,
        })

    return {
        "total_rows": n,
        "id_unique": len(id_dupes) == 0,
        "id_duplicate_values": id_dupes,
        "parent_id_empty_count": parent_empty,
        "unit_text_empty_count": unit_empty,
        "parent_missing_count": len(parent_missing_ids),
        "parent_missing_examples": parent_missing_ids[:50],
        "parent_reference_exists_count": parent_reference_exists,
        "parent_reference_exists_rate": round(parent_reference_exists / n, 4) if n else 0,
        "parent_semantic_linkage_count": parent_semantic_linkage,
        "parent_semantic_linkage_rate": round(parent_semantic_linkage / n, 4) if n else 0,
        "invalid_mechanism_labels": dict(bad_mechanism),
        "invalid_surface_topics": dict(bad_topic),
        "invalid_confidence_values": dict(bad_conf),
        "evidence_rawtext_nonempty_count": ev_rawtext_nonempty,
        "surface_topic_distribution": dict(surface_dist),
        "mechanism_distribution": dict(mechanism_dist),
        "confidence_distribution": dict(confidence_dist),
        "linkage_status_counts": dict(status_counter),
        "global_match_counts": dict(global_counter),
        "unique_match_count": global_counter.get("unique_match_in_other_id", 0) + global_counter.get("found_in_declared_parent", 0),
        "unique_match_in_other_id_count": global_counter.get("unique_match_in_other_id", 0),
        "ambiguous_match_count": global_counter.get("ambiguous_match_in_other_ids", 0),
        "not_found_count": global_counter.get("not_found_anywhere", 0),
        "actual_source_platform_distribution_unique_only": dict(actual_platform_dist),
        "unique_offset_histogram": {str(k): v for k, v in sorted(unique_offset_hist.items(), key=lambda x: (x[0] is None, x[0]))},
        "parent_id_min": min(parent_ids_int) if parent_ids_int else None,
        "parent_id_max": max(parent_ids_int) if parent_ids_int else None,
        "parent_id_distinct": len(set(parent_ids_int)),
        "unique_offset_examples": offset_examples,
        "ambiguous_examples": ambiguous_examples,
        "evidence_phrase_total_nonempty": phrase_total_nonempty,
        "evidence_phrase_exact_in_unit": phrase_in_unit,
        "evidence_phrase_normalized_only": phrase_norm_only,
        "linkage_rows": linkage_rows,
        "_evidence_actual_source": evidence_actual_source,
    }


# ---------------------------------------------------------------------------
# 阶段三：洞察关联审计
# ---------------------------------------------------------------------------
def _topic_mech_from_insight(text):
    """从 insight 文本抽取 topic 与 mechanism（兼容有无方括号两种写法）。"""
    t = text
    m_topic = re.search(r"around\s+\[?([a-z_]+)\]?", t)
    # mechanism：形如 "[competence_frustration] signals" 或 "competence_frustration signals"
    m_mech = re.search(r"\[?([a-z_]+)\]?\s+signals", t)
    topic = m_topic.group(1) if m_topic else None
    mech = m_mech.group(1) if m_mech else None
    return topic, mech


def audit_insights(jsonl_results, evidence_rows, clean_rows, evidence_actual_source=None):
    evidence_actual_source = evidence_actual_source or {}
    evidence_ids = {str(r.get("id")) for r in evidence_rows}
    ev_by_id = {str(r.get("id")): r for r in evidence_rows}
    clean_by_id = {str(r.get("id")): r for r in clean_rows}

    parse_ok = [r for r in jsonl_results if r[1]]
    parse_fail = [r for r in jsonl_results if not r[1]]
    insights = [r[2] for r in parse_ok]

    all_supporting = []
    per_insight = []
    id_usage = Counter()

    for idx, obj in enumerate(insights, 1):
        sup = obj.get("supporting_ids", []) or []
        conf = obj.get("confidence", "")
        nhr = obj.get("needs_human_review", None)
        ftype = obj.get("frequency_type", "")
        text = obj.get("insight", "")

        missing = [s for s in sup if s not in evidence_ids]
        dup_within = [k for k, v in Counter(sup).items() if v > 1]
        for s in sup:
            id_usage[s] += 1
            all_supporting.append(s)

        # 平台 / 时间窗覆盖：使用「实际出处」（因 declared parent_id 与 clean id 空间错位）
        platforms, windows, topics_seen, mechs_seen = set(), set(), set(), set()
        declared_platforms = set()
        for s in sup:
            ev = ev_by_id.get(s)
            if not ev:
                continue
            topics_seen.add((ev.get("surface_topic") or "").strip())
            mechs_seen.add((ev.get("mechanism_label") or "").strip())
            # 声明映射（供对照）
            dparent = clean_by_id.get(str(ev.get("parent_id", "")).strip())
            if dparent:
                declared_platforms.add(dparent.get("platform_source", ""))
            # 实际出处映射（可信）
            act = evidence_actual_source.get(s)
            if act:
                platforms.add(act.get("actual_platform", ""))
                windows.add(act.get("actual_window", ""))

        it_topic, it_mech = _topic_mech_from_insight(text)
        topic_consistent = (it_topic in topics_seen) if it_topic else None
        mech_consistent = (it_mech in mechs_seen) if it_mech else None

        # confidence 与 needs_human_review 一致性检查：
        # 约定：high 置信通常 needs_human_review=false；low 置信通常 =true
        conf_review_consistent = True
        if conf == "high" and nhr is True:
            conf_review_consistent = False
        if conf == "low" and nhr is False:
            conf_review_consistent = False

        per_insight.append({
            "line": idx,
            "insight": text,
            "confidence": conf,
            "frequency_type": ftype,
            "needs_human_review": nhr,
            "support_count": len(sup),
            "unique_support_count": len(set(sup)),
            "missing_support_ids": missing,
            "duplicate_support_ids": dup_within,
            "platforms": sorted(p for p in platforms if p),
            "declared_platforms": sorted(p for p in declared_platforms if p),
            "windows": sorted(w for w in windows if w),
            "single_platform": len([p for p in platforms if p]) <= 1,
            "insight_topic": it_topic,
            "insight_mechanism": it_mech,
            "topic_consistent_with_evidence": topic_consistent,
            "mechanism_consistent_with_evidence": mech_consistent,
            "confidence_review_consistent": conf_review_consistent,
        })

    reused_ids = {k: v for k, v in id_usage.items() if v > 1}
    empty_support = [p["line"] for p in per_insight if p["support_count"] == 0]
    any_missing = [p["line"] for p in per_insight if p["missing_support_ids"]]
    high_conf_low_support = [p["line"] for p in per_insight
                             if p["confidence"] == "high" and p["support_count"] < 5]
    no_review_but_link_fail = [p["line"] for p in per_insight
                               if p["needs_human_review"] is False and p["missing_support_ids"]]
    single_platform_lines = [p["line"] for p in per_insight if p["single_platform"]]

    # 拆分：confidence 分布 与 needs_human_review 分布（两者是不同字段）
    insight_confidence_distribution = dict(Counter(p["confidence"] for p in per_insight))
    needs_human_review_distribution = dict(Counter(
        {True: "true", False: "false"}.get(p["needs_human_review"], "null")
        for p in per_insight))
    high_confidence_count = sum(1 for p in per_insight if p["confidence"] == "high")
    no_review_flag_count = sum(1 for p in per_insight if p["needs_human_review"] is False)
    high_conf_and_no_review = [p["line"] for p in per_insight
                               if p["confidence"] == "high" and p["needs_human_review"] is False]
    high_confidence_lines = [p["line"] for p in per_insight if p["confidence"] == "high"]

    return {
        "total_lines_parsed": len(insights),
        "parse_failures": [{"line": r[0], "error": r[2]} for r in parse_fail],
        "expected_count": EXPECTED_INSIGHTS,
        "count_matches_expected": len(insights) == EXPECTED_INSIGHTS,
        "empty_supporting_lines": empty_support,
        "missing_support_lines": any_missing,
        "reused_evidence_ids": reused_ids,
        "reused_evidence_id_count": len(reused_ids),
        # confidence 与 needs_human_review 分开统计（后者是模型输出字段，非人工复核状态）
        "insight_confidence_distribution": insight_confidence_distribution,
        "needs_human_review_distribution": needs_human_review_distribution,
        "high_confidence_count": high_confidence_count,
        "high_confidence_lines": high_confidence_lines,
        "no_review_flag_count": no_review_flag_count,
        "high_confidence_and_no_review_flag_count": len(high_conf_and_no_review),
        "high_confidence_and_no_review_flag_lines": high_conf_and_no_review,
        "high_confidence_low_support_lines": high_conf_low_support,
        "no_review_but_link_failure_lines": no_review_but_link_fail,
        "single_platform_lines": single_platform_lines,
        "per_insight": per_insight,
    }


# ---------------------------------------------------------------------------
# 阶段四：页面数字复算 + 特定示例（1_u2）
# ---------------------------------------------------------------------------
def audit_recompute(clean_rows, evidence_rows, insights_audit):
    clean_by_id = {str(r.get("id")): r for r in clean_rows}
    theme = Counter(r.get("theme_bucket", "") for r in clean_rows)
    platform = Counter(r.get("platform_source", "") for r in clean_rows)
    window = Counter(r.get("window_tag", "") for r in clean_rows)

    mech = Counter((r.get("mechanism_label", "") or "").strip() for r in evidence_rows)
    surf = Counter((r.get("surface_topic", "") or "").strip() for r in evidence_rows)

    # theme_bucket=balance_mechanic 按平台
    balance_by_platform = Counter()
    for r in clean_rows:
        if r.get("theme_bucket", "") == "balance_mechanic":
            balance_by_platform[r.get("platform_source", "")] += 1

    # 1_u2 示例闭合验证
    ev_by_id = {str(r.get("id")): r for r in evidence_rows}
    ex = ev_by_id.get("1_u2")
    example = {"evidence_exists": ex is not None}
    if ex:
        pid = str(ex.get("parent_id", "")).strip()
        parent = clean_by_id.get(pid)
        unit = ex.get("unit_text", "") or ""
        nu = normalize_text(unit)
        # 声明 parent 的原文是否包含 unit_text
        declared_match = parent is not None and nu and nu in normalize_text(parent.get("raw_text", ""))
        # 实际出处（全域搜索，收集所有候选；只有唯一命中才认定）
        candidates = [cid for cid, r in clean_by_id.items()
                      if nu and nu in normalize_text(r.get("raw_text", ""))]
        actual_id = candidates[0] if len(candidates) == 1 else None
        actual_platform = clean_by_id.get(actual_id, {}).get("platform_source") if actual_id else None
        example.update({
            "declared_parent_id": pid,
            "declared_parent_exists": parent is not None,
            "declared_parent_platform": parent.get("platform_source", "") if parent else None,
            "unit_text_matches_declared_parent": bool(declared_match),
            "candidate_count": len(candidates),
            "actual_source_clean_id": actual_id,
            "actual_source_platform": actual_platform,
            "mechanism_label": ex.get("mechanism_label"),
            "confidence": ex.get("confidence"),
            "surface_topic": ex.get("surface_topic"),
        })
        # 是否被某条洞察引用
        refs = [p["line"] for p in insights_audit["per_insight"] if "1_u2" in _support_ids_of(p)]
        example["referenced_by_insight_lines"] = refs
        # 页面主张：parent_id=1 且 平台 B 站；据实核对
        example["page_claim_platform"] = "B站(Bili)"
        example["page_claim_correct"] = bool(declared_match and (parent and parent.get("platform_source") == "Bili"))
        # 链条闭合 = 声明 parent 原文确实包含 unit_text 且被洞察引用
        example["chain_closed"] = bool(declared_match and len(refs) > 0)

    return {
        "clean_total": len(clean_rows),
        "evidence_total": len(evidence_rows),
        "insight_total": insights_audit["total_lines_parsed"],
        "theme_bucket_counts": dict(theme),
        "platform_counts": dict(platform),
        "window_counts": dict(window),
        "evidence_mechanism_counts": dict(mech),
        "evidence_surface_topic_counts": dict(surf),
        "theme_balance_mechanic_by_platform": dict(balance_by_platform),
        "competence_frustration_count": mech.get("competence_frustration", 0),
        "fairness_threat_count": mech.get("fairness_threat", 0),
        "uncertain_mechanism_count": mech.get("uncertain", 0),
        "surface_balance_count": surf.get("balance", 0),
        "example_1_u2": example,
    }


def _support_ids_of(per_insight_entry):
    # per_insight 未直接存 supporting_ids，此处从 platforms 无法回推；改由调用处保证。
    # 为避免额外结构，这里返回空并在 recompute 中单独查。
    return per_insight_entry.get("_supporting_ids", [])


# ---------------------------------------------------------------------------
# 阻断项判定
# ---------------------------------------------------------------------------
def determine_blocking(clean_audit, evidence_audit, insights_audit, recompute):
    blockers = []

    # 文件缺失
    for path, label in [(CLEAN_CSV, "clean_input"), (EVIDENCE_CSV, "evidence_table"),
                        (INSIGHTS_JSONL, "insights"), (ACTION_JSON, "action_matrix")]:
        if not path.exists():
            blockers.append(f"必要公开文件缺失: {label} ({path.name})")

    # parent_id 不存在
    if evidence_audit.get("parent_missing_count", 0) > 0:
        blockers.append(
            f"存在 parent_id 无法在整洁样本中找到的证据单元: "
            f"{evidence_audit['parent_missing_count']} 条")

    # 语义关联缺失：unit_text 无法匹配「声明的 parent 原文」
    psl = evidence_audit.get("parent_semantic_linkage_rate", 1.0)
    unique_other = evidence_audit.get("unique_match_in_other_id_count", 0)
    ambiguous = evidence_audit.get("ambiguous_match_count", 0)
    not_found = evidence_audit.get("not_found_count", 0)
    if psl < 0.98:
        blockers.append(
            f"parent 语义关联缺失：parent_semantic_linkage_rate={psl}"
            f"（parent_reference_exists_rate={evidence_audit.get('parent_reference_exists_rate')}）。"
            f"证据文本可在公开整洁样本中定位，但 id 错位：唯一命中于其他 id {unique_other} 条、"
            f"歧义命中 {ambiguous} 条、未找到 {not_found} 条。")

    # supporting_id 不存在
    if insights_audit.get("missing_support_lines"):
        blockers.append(
            f"存在 supporting_ids 无法在证据表中找到的洞察: "
            f"行 {insights_audit['missing_support_lines']}")

    # 空 supporting_ids
    if insights_audit.get("empty_supporting_lines"):
        blockers.append(f"存在空 supporting_ids 的洞察: 行 {insights_audit['empty_supporting_lines']}")

    # 页面示例证据链错误
    ex = recompute.get("example_1_u2", {})
    if not ex.get("chain_closed", False):
        blockers.append("页面示例证据 1_u2 的证据链未闭合")

    # id 唯一性
    if not evidence_audit.get("id_unique", True):
        blockers.append(f"证据单元 id 不唯一: {evidence_audit.get('id_duplicate_values')}")
    if not clean_audit.get("id_unique", True):
        blockers.append("整洁样本 id 不唯一或存在空 id")

    # 非法标签
    if evidence_audit.get("invalid_mechanism_labels"):
        blockers.append(f"存在非法 mechanism_label: {evidence_audit['invalid_mechanism_labels']}")

    return blockers


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------
def run_audit():
    clean_fields, clean_rows = read_csv_rows(CLEAN_CSV)
    evidence_fields, evidence_rows = read_csv_rows(EVIDENCE_CSV)
    jsonl_results = read_jsonl(INSIGHTS_JSONL)
    action_obj = None
    action_err = None
    if ACTION_JSON.exists():
        try:
            action_obj = json.loads(ACTION_JSON.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError as e:
            action_err = str(e)

    clean_audit = audit_clean(clean_rows)
    evidence_audit = audit_evidence(evidence_rows, clean_rows)
    evidence_actual_source = evidence_audit.pop("_evidence_actual_source", {})
    insights_audit = audit_insights(jsonl_results, evidence_rows, clean_rows, evidence_actual_source)

    # 为 1_u2 闭合验证补充 supporting_ids（避免修改 per_insight 结构过多）
    ev_ok = [r[2] for r in jsonl_results if r[1]]
    for entry, obj in zip(insights_audit["per_insight"], ev_ok):
        entry["_supporting_ids"] = obj.get("supporting_ids", []) or []

    recompute = audit_recompute(clean_rows, evidence_rows, insights_audit)

    # 清理临时字段
    for entry in insights_audit["per_insight"]:
        entry.pop("_supporting_ids", None)

    encodings = {
        "clean_csv": detect_encoding_report(CLEAN_CSV),
        "evidence_csv": detect_encoding_report(EVIDENCE_CSV),
        "insights_jsonl": detect_encoding_report(INSIGHTS_JSONL),
        "action_json": detect_encoding_report(ACTION_JSON),
    }

    # action_matrix 结构检查
    action_report = {"parse_ok": action_obj is not None, "error": action_err}
    if action_obj is not None:
        ap = action_obj.get("action_proposals", {})
        action_report.update({
            "keys": sorted(action_obj.keys()),
            "insight_statements_count": len(action_obj.get("insight_statements", [])),
            "mechanism_hypotheses_count": len(action_obj.get("mechanism_hypotheses", [])),
            "safe_count": len(ap.get("safe", [])),
            "balanced_count": len(ap.get("balanced", [])),
            "bold_count": len(ap.get("bold", [])),
            "has_validation_method": "validation_method" in json.dumps(action_obj),
            "has_expected_effect": "expected_effect" in json.dumps(action_obj),
            "has_source_insight_ids": "source_insight_ids" in json.dumps(action_obj),
        })

    blockers = determine_blocking(clean_audit, evidence_audit, insights_audit, recompute)

    result = {
        "schema_version": "1.0",
        "repo_root": str(REPO_ROOT),
        "files": {
            "clean_csv_fields": clean_fields,
            "evidence_csv_fields": evidence_fields,
        },
        "encodings": encodings,
        "clean_input_audit": clean_audit,
        "evidence_audit": evidence_audit,
        "insights_audit": insights_audit,
        "action_matrix_audit": action_report,
        "recompute": recompute,
        "blockers": blockers,
        "phase0_status": "BLOCKED" if blockers else "PASS",
    }
    return result


# ---------------------------------------------------------------------------
# v2 数据底座审计（Phase 1A）
# ---------------------------------------------------------------------------
def sha256_bytes(path: Path) -> str:
    import hashlib
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else ""


def run_v2_audit(v2_dir=None):
    """审计 v2 迁移底座（默认 data/v2；可传入其他目录以支持隔离测试）。

    返回结果字典，含 v2_migration_status。
    """
    v2_dir = Path(v2_dir) if v2_dir else V2_DIR
    samples_p = v2_dir / "samples_v2.csv"
    evidence_p = v2_dir / "evidence_v2.csv"
    ambiguous_p = v2_dir / "ambiguous_evidence_queue.csv"
    bili_p = v2_dir / "bili_evidence_queue.csv"
    migration_p = v2_dir / "id_migration.csv"
    manifest_p = v2_dir / "v2_manifest.json"

    issues = []       # 阻断性问题
    warnings = []     # 提示

    for p, label in [(samples_p, "samples_v2"), (evidence_p, "evidence_v2"),
                     (ambiguous_p, "ambiguous_queue"), (bili_p, "bili_queue"),
                     (migration_p, "id_migration"), (manifest_p, "manifest")]:
        if not p.exists():
            issues.append(f"v2 文件缺失: {label} ({p.name})")
    if issues:
        return {"exists": False, "issues": issues, "warnings": warnings,
                "v2_migration_status": "BLOCKED"}

    _, samples = read_csv_rows(samples_p)
    _, evidence = read_csv_rows(evidence_p)
    _, ambiguous = read_csv_rows(ambiguous_p)
    _, bili = read_csv_rows(bili_p)
    _, migration = read_csv_rows(migration_p)
    manifest = json.loads(manifest_p.read_text(encoding="utf-8"))

    sample_ids = [r.get("sample_id", "") for r in samples]
    sample_id_set = set(sample_ids)
    sample_by_id = {r.get("sample_id"): r for r in samples}

    # 样本检查
    if len(samples) != EXPECTED_CLEAN_ROWS:
        issues.append(f"samples_v2 行数 {len(samples)} != {EXPECTED_CLEAN_ROWS}")
    if len(sample_id_set) != len(samples):
        issues.append("sample_id 不唯一")
    plat = Counter(r.get("platform_source", "") for r in samples)
    if not (plat.get("Bili") == 120 and plat.get("NGA") == 120 and plat.get("Tieba") == 120):
        issues.append(f"平台数量异常: {dict(plat)}")
    bad_sample_id = [s for s in sample_ids if not SAMPLE_ID_RE.match(s)]
    if bad_sample_id:
        issues.append(f"非法 sample_id 格式: {bad_sample_id[:5]}")
    legacy_clean_ids = [r.get("legacy_clean_id", "") for r in samples]
    if len(set(legacy_clean_ids)) != len(legacy_clean_ids):
        issues.append("legacy_clean_id 不唯一")

    # samples_v2 与 legacy clean 逐行字段一致（legacy_clean_id / raw_text / source_url / platform_source）
    _, legacy_clean = read_csv_rows(CLEAN_CSV)
    legacy_clean_by_id = {str(r.get("id")): r for r in legacy_clean}
    field_mismatch = {"raw_text": 0, "source_url": 0, "platform_source": 0, "missing_legacy": 0}
    for r in samples:
        lid = str(r.get("legacy_clean_id", ""))
        lrow = legacy_clean_by_id.get(lid)
        if lrow is None:
            field_mismatch["missing_legacy"] += 1
            continue
        if r.get("raw_text", "") != lrow.get("raw_text", ""):
            field_mismatch["raw_text"] += 1
        if r.get("source_url", "") != lrow.get("url", ""):
            field_mismatch["source_url"] += 1
        if r.get("platform_source", "") != lrow.get("platform_source", ""):
            field_mismatch["platform_source"] += 1
    for fld, cnt in field_mismatch.items():
        if cnt:
            issues.append(f"samples_v2 与 legacy clean 字段不一致: {fld}={cnt} 条")

    # 证据检查
    ev_ids = [r.get("evidence_id", "") for r in evidence]
    if len(evidence) != EXPECTED_MIGRATED_EVIDENCE:
        issues.append(f"evidence_v2 迁移数量 {len(evidence)} != {EXPECTED_MIGRATED_EVIDENCE}")
    if len(set(ev_ids)) != len(ev_ids):
        issues.append("evidence_id 不唯一")
    bad_ev_id = [e for e in ev_ids if not EVIDENCE_ID_RE.match(e)]
    if bad_ev_id:
        issues.append(f"非法 evidence_id 格式: {bad_ev_id[:5]}")
    legacy_ev_ids = [r.get("legacy_evidence_id", "") for r in evidence]
    if len(set(legacy_ev_ids)) != len(legacy_ev_ids):
        issues.append("legacy_evidence_id 重复")

    # sample_id 存在性 + 前缀一致 + unit_text 匹配 sample.raw_text
    unmatched_text = 0
    prefix_mismatch = 0
    missing_sample = 0
    for r in evidence:
        sid = r.get("sample_id", "")
        eid = r.get("evidence_id", "")
        if sid not in sample_id_set:
            missing_sample += 1
            continue
        if not eid.startswith(sid + "_U"):
            prefix_mismatch += 1
        nu = normalize_text(r.get("unit_text", ""))
        nsamp = normalize_text(sample_by_id[sid].get("raw_text", ""))
        if not (nu and nu in nsamp):
            unmatched_text += 1
    if missing_sample:
        issues.append(f"evidence.sample_id 不存在于 samples_v2: {missing_sample} 条")
    if prefix_mismatch:
        issues.append(f"evidence_id 平台前缀与 sample_id 不一致: {prefix_mismatch} 条")
    if unmatched_text:
        issues.append(f"unit_text 无法匹配对应 sample.raw_text: {unmatched_text} 条")

    # review_status 全为 legacy_ai_label_unreviewed，且不得出现「人工已复核」类状态
    rs = Counter(r.get("review_status", "") for r in evidence)
    if set(rs) != {"legacy_ai_label_unreviewed"}:
        issues.append(f"review_status 非全为 legacy_ai_label_unreviewed: {dict(rs)}")
    human_reviewed_like = [r.get("evidence_id") for r in evidence
                           if r.get("review_status", "") in ("human_reviewed", "human_curated", "verified", "approved")]
    if human_reviewed_like:
        issues.append(f"存在被标为人工已复核的证据（不允许）: {human_reviewed_like[:5]}")

    # unit_index 不变量（将稳定性检查纳入审计器；手动篡改 unit_index / ID 后缀会 BLOCKED）
    unit_index_errors = {"legacy_unparseable": [], "unit_index_ne_legacy": [],
                         "suffix_ne_unit_index": [], "id_format_mismatch": [], "duplicate_key": []}
    seen_unit_keys = set()
    for r in evidence:
        eid = r.get("evidence_id", "")
        sid = r.get("sample_id", "")
        legacy_eid = r.get("legacy_evidence_id", "")
        m = LEGACY_UNIT_RE.search(legacy_eid)
        if not m:
            unit_index_errors["legacy_unparseable"].append(eid)
            continue
        legacy_ui = int(m.group(1))
        try:
            ui = int(r.get("unit_index", ""))
        except (ValueError, TypeError):
            unit_index_errors["unit_index_ne_legacy"].append(eid)
            continue
        if ui != legacy_ui:
            unit_index_errors["unit_index_ne_legacy"].append(eid)
        # evidence_id 的 _Uxx 后缀
        sm = re.search(r"_U(\d+)$", eid)
        if not sm or int(sm.group(1)) != ui:
            unit_index_errors["suffix_ne_unit_index"].append(eid)
        # evidence_id == f"{sample_id}_U{unit_index:02d}"
        if eid != f"{sid}_U{ui:02d}":
            unit_index_errors["id_format_mismatch"].append(eid)
        key = (sid, ui)
        if key in seen_unit_keys:
            unit_index_errors["duplicate_key"].append(f"{sid}_U{ui:02d}")
        seen_unit_keys.add(key)
    for kind, lst in unit_index_errors.items():
        if lst:
            issues.append(f"unit_index 不变量失败[{kind}]: {len(lst)} 条，例 {lst[:5]}")

    # 歧义队列
    if len(ambiguous) != EXPECTED_AMBIGUOUS:
        issues.append(f"歧义证据数量 {len(ambiguous)} != {EXPECTED_AMBIGUOUS}")
    amb_pending = all(r.get("resolution_status") == "pending_human_resolution" for r in ambiguous)
    if not amb_pending:
        issues.append("歧义证据未全部标记 pending_human_resolution")
    # 歧义证据不得出现在 evidence_v2（未自动迁移）
    amb_legacy = {r.get("legacy_evidence_id") for r in ambiguous}
    migrated_legacy = set(legacy_ev_ids)
    if amb_legacy & migrated_legacy:
        issues.append(f"歧义证据被自动迁移（不允许）: {amb_legacy & migrated_legacy}")

    # B 站队列完整性
    bili_sample_cover = {r.get("sample_id") for r in bili}
    bili_samples_all = {r.get("sample_id") for r in samples if r.get("platform_source") == "Bili"}
    # queue sample 集合与 Bili sample 集合完全相等（不只是子集），且不允许混入非 Bili sample
    if bili_sample_cover != bili_samples_all:
        only_queue = sorted(bili_sample_cover - bili_samples_all)   # 混入的非 Bili / 未知 sample
        only_bili = sorted(bili_samples_all - bili_sample_cover)    # 未被覆盖的 Bili sample
        if only_queue:
            issues.append(f"B 站队列混入非 Bili sample_id: {only_queue[:5]}（共 {len(only_queue)}）")
        if only_bili:
            issues.append(f"B 站队列未覆盖 Bili sample_id: {only_bili[:5]}（共 {len(only_bili)}）")
    # queue_id 唯一
    queue_ids = [r.get("queue_id", "") for r in bili]
    if len(set(queue_ids)) != len(queue_ids):
        issues.append("B 站队列 queue_id 不唯一")
    # 每个 sample 内 candidate_unit_index 连续且唯一；candidate_unit_text 与 queue raw_text 均匹配 sample.raw_text
    per_sample_idx = {}
    bili_text_unmatch = 0
    bili_rawtext_mismatch = 0
    for r in bili:
        sid = r.get("sample_id", "")
        per_sample_idx.setdefault(sid, []).append(r.get("candidate_unit_index", ""))
        samp = sample_by_id.get(sid)
        if samp is not None:
            nsamp = normalize_text(samp.get("raw_text", ""))
            ncand = normalize_text(r.get("candidate_unit_text", ""))
            if not (ncand and ncand in nsamp):
                bili_text_unmatch += 1
            # 队列 raw_text 必须与 samples_v2 完全一致（未修改）
            if r.get("raw_text", "") != samp.get("raw_text", ""):
                bili_rawtext_mismatch += 1
    idx_bad = []
    for sid, idxs in per_sample_idx.items():
        try:
            nums = [int(x) for x in idxs]
        except (ValueError, TypeError):
            idx_bad.append(sid)
            continue
        if sorted(nums) != list(range(1, len(nums) + 1)):
            idx_bad.append(sid)
    if idx_bad:
        issues.append(f"B 站队列 candidate_unit_index 非连续/唯一: {idx_bad[:5]}（共 {len(idx_bad)}）")
    if bili_text_unmatch:
        issues.append(f"B 站候选 candidate_unit_text 无法匹配 sample.raw_text: {bili_text_unmatch} 条")
    if bili_rawtext_mismatch:
        issues.append(f"B 站队列 raw_text 与 samples_v2 不一致: {bili_rawtext_mismatch} 条")
    # 机制标签必须为空或 unassigned；状态字段全量检查
    bad_mech = [r.get("queue_id") for r in bili
                if (r.get("mechanism_label_candidate", "") or "").strip() not in ("", "unassigned")]
    if bad_mech:
        issues.append(f"B 站队列含最终机制标签（不允许）: {bad_mech[:5]}")
    bad_cand_status = [r.get("queue_id") for r in bili if r.get("candidate_status") != "pending_review"]
    if bad_cand_status:
        issues.append(f"B 站队列 candidate_status 非 pending_review: {bad_cand_status[:5]}")
    bad_hr_status = [r.get("queue_id") for r in bili if r.get("human_review_status") != "not_reviewed"]
    if bad_hr_status:
        issues.append(f"B 站队列 human_review_status 非 not_reviewed: {bad_hr_status[:5]}")

    # manifest 数量一致 + SHA-256 校验（数值必须与实际队列一致，不得写死）
    if manifest.get("sample_count") != len(samples):
        issues.append("manifest.sample_count 与实际不一致")
    if manifest.get("migrated_evidence_count") != len(evidence):
        issues.append("manifest.migrated_evidence_count 与实际不一致")
    if manifest.get("ambiguous_evidence_count") != len(ambiguous):
        issues.append("manifest.ambiguous_evidence_count 与实际不一致")
    if manifest.get("platform_counts") != dict(plat):
        issues.append(f"manifest.platform_counts 与实际不一致: {manifest.get('platform_counts')} vs {dict(plat)}")
    if manifest.get("bili_samples_pending") != len(bili_sample_cover):
        issues.append(f"manifest.bili_samples_pending 与实际不一致: "
                      f"{manifest.get('bili_samples_pending')} vs {len(bili_sample_cover)}")
    if manifest.get("bili_candidate_unit_count") != len(bili):
        issues.append(f"manifest.bili_candidate_unit_count 与实际队列行数不一致（不得写死）: "
                      f"{manifest.get('bili_candidate_unit_count')} vs {len(bili)}")
    # source_data_commit 必须精确等于权威来源提交（非空 + 值正确）
    actual_commit = (manifest.get("source_data_commit") or "").strip()
    if not actual_commit:
        issues.append("manifest.source_data_commit 缺失（正式快照必须显式传入）")
    elif actual_commit != EXPECTED_V2_SOURCE_DATA_COMMIT:
        issues.append(f"manifest.source_data_commit 与权威来源提交不一致: "
                      f"{actual_commit} != {EXPECTED_V2_SOURCE_DATA_COMMIT}")
    # source_files 必须精确等于权威来源文件映射（键集合 + 路径值都要正确，不只是 POSIX 格式）
    src_files = manifest.get("source_files") or {}
    if not src_files:
        issues.append("manifest.source_files 缺失")
    elif src_files != EXPECTED_V2_SOURCE_FILES:
        issues.append(f"manifest.source_files 与权威来源文件不一致: {src_files} != {EXPECTED_V2_SOURCE_FILES}")
    hash_mismatch = []
    expected_hash_names = set(manifest.get("hashes") or {})
    if expected_hash_names != set(EXPECTED_V2_CSV_NAMES):
        issues.append(f"manifest.hashes 覆盖文件不完整: {sorted(expected_hash_names)}")
    for name, expected in (manifest.get("hashes") or {}).items():
        actual = sha256_bytes(v2_dir / name)
        if actual != expected:
            hash_mismatch.append(name)
    if hash_mismatch:
        issues.append(f"manifest SHA-256 不匹配: {hash_mismatch}")

    # 编码检查（v2 文件应为 UTF-8）
    for p in [samples_p, evidence_p, ambiguous_p, bili_p, migration_p]:
        enc = detect_encoding_report(p)
        if not enc["utf8_decodable"]:
            issues.append(f"{p.name} 非 UTF-8 可解码")

    # id_migration 分项校验
    mig_by = Counter((r.get("legacy_entity_type", ""), r.get("new_entity_type", ""),
                      r.get("migration_status", "")) for r in migration)
    clean_migrated = mig_by.get(("clean_sample", "sample", "migrated"), 0)
    ev_migrated = mig_by.get(("evidence_unit", "evidence", "migrated"), 0)
    ev_pending = mig_by.get(("evidence_unit", "evidence", "pending_human_resolution"), 0)
    insight_deferred = mig_by.get(("insight_set", "insight", "deferred_until_evidence_rebuild"), 0)
    action_deferred = mig_by.get(("action_matrix", "action", "deferred_until_evidence_rebuild"), 0)
    if clean_migrated != EXPECTED_CLEAN_ROWS:
        issues.append(f"id_migration clean_sample migrated {clean_migrated} != {EXPECTED_CLEAN_ROWS}")
    if ev_migrated != EXPECTED_MIGRATED_EVIDENCE:
        issues.append(f"id_migration evidence migrated {ev_migrated} != {EXPECTED_MIGRATED_EVIDENCE}")
    if ev_pending != EXPECTED_AMBIGUOUS:
        issues.append(f"id_migration evidence pending {ev_pending} != {EXPECTED_AMBIGUOUS}")
    if insight_deferred != 1:
        issues.append(f"id_migration insight deferred {insight_deferred} != 1")
    if action_deferred != 1:
        issues.append(f"id_migration action deferred {action_deferred} != 1")
    # 不存在无效新 ID（迁移状态为 migrated 的 evidence 必须有合法 new_id）
    bad_new_id = []
    for r in migration:
        if r.get("migration_status") == "migrated" and r.get("new_entity_type") == "evidence":
            if not EVIDENCE_ID_RE.match(r.get("new_id", "")):
                bad_new_id.append(r.get("legacy_id"))
    if bad_new_id:
        issues.append(f"id_migration 存在无效 evidence new_id: {bad_new_id[:5]}")
    # legacy id 与 new id 一一对应（sample + evidence 已迁移部分）
    sample_pairs = [(r.get("legacy_clean_id"), r.get("sample_id")) for r in samples]
    ev_pairs = [(r.get("legacy_evidence_id"), r.get("evidence_id")) for r in evidence]
    mig_sample_pairs = [(r.get("legacy_id"), r.get("new_id")) for r in migration
                        if r.get("new_entity_type") == "sample" and r.get("migration_status") == "migrated"]
    mig_ev_pairs = [(r.get("legacy_id"), r.get("new_id")) for r in migration
                    if r.get("new_entity_type") == "evidence" and r.get("migration_status") == "migrated"]
    if sorted(sample_pairs) != sorted(mig_sample_pairs):
        issues.append("id_migration sample 映射与 samples_v2 不一一对应")
    if sorted(ev_pairs) != sorted(mig_ev_pairs):
        issues.append("id_migration evidence 映射与 evidence_v2 不一一对应")

    status = "PASS" if not issues else "BLOCKED"
    return {
        "exists": True,
        "sample_count": len(samples),
        "platform_counts": dict(plat),
        "migrated_evidence_count": len(evidence),
        "ambiguous_evidence_count": len(ambiguous),
        "bili_samples_covered": len(bili_sample_cover),
        "bili_sample_set_equals_bili_samples": bili_sample_cover == bili_samples_all,
        "bili_candidate_unit_count": len(bili),
        "review_status_distribution": dict(rs),
        "manifest_hash_ok": not hash_mismatch,
        "manifest_source_data_commit": manifest.get("source_data_commit"),
        "id_migration_breakdown": {
            "clean_sample_migrated": clean_migrated,
            "evidence_migrated": ev_migrated,
            "evidence_pending": ev_pending,
            "insight_deferred": insight_deferred,
            "action_deferred": action_deferred,
        },
        "samples_field_mismatch": field_mismatch,
        "issues": issues,
        "warnings": warnings,
        "v2_migration_status": status,
    }


def run_combined_audit(dataset="both"):
    """按 dataset 组合 legacy / v2 审计，输出分层状态。"""
    out = {"dataset": dataset}
    legacy = None
    v2 = None
    if dataset in ("legacy", "both"):
        legacy = run_audit()
        out["legacy"] = legacy
        out["legacy_status"] = legacy["phase0_status"]
    if dataset in ("v2", "both"):
        v2 = run_v2_audit()
        out["v2"] = v2
        out["v2_migration_status"] = v2["v2_migration_status"]

    # provisional 三平台证据层状态（若已生成）
    prov_manifest = V2_DIR / "provisional_manifest.json"
    if prov_manifest.exists():
        try:
            pm = json.loads(prov_manifest.read_text(encoding="utf-8"))
            prov_ok = (pm.get("provisional_evidence_count", 0) > 0
                       and pm.get("platform_distribution")
                       and all(sha256_bytes(V2_DIR / n) == h for n, h in (pm.get("hashes") or {}).items()))
            out["provisional_evidence_status"] = "PASS" if prov_ok else "BLOCKED"
            out["provisional_evidence_count"] = pm.get("provisional_evidence_count")
            out["provisional_platform_distribution"] = pm.get("platform_distribution")
        except (ValueError, OSError):
            out["provisional_evidence_status"] = "BLOCKED"
    else:
        out["provisional_evidence_status"] = "NOT_BUILT"

    # 人工复核状态：当前无 reviewer_type=human 记录 -> NOT_STARTED
    out["human_review_status"] = "NOT_STARTED"

    # 发布就绪：受延期决策约束（草稿默认不公开、歧义未定案、无人工复核）-> 仍 BLOCKED
    out["publication_readiness"] = "BLOCKED"
    out["publication_readiness_reason"] = (
        "legacy 证据链错位未修复；B 站证据为 Agent 提案未经人工复核；"
        "2 条歧义证据未定案；结构化洞察与行动建议为草稿默认不公开；"
        "多项发布选择仍待用户决策（见 docs/decisions/FINAL_DECISION_PACKET.md）。")
    return out


def write_linkage_csv(result, path: Path):
    """输出证据单元逐行关联表 CSV（legacy）。字段固定，供 --csv-out 使用。"""
    rows = result["evidence_audit"]["linkage_rows"]
    path.parent.mkdir(parents=True, exist_ok=True)
    cols = ["evidence_id", "parent_id", "linkage_status", "substring_match",
            "similarity_ratio", "ngram_overlap", "evidence_text",
            "parent_text_excerpt", "notes"]
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def write_mismatch_csv(result, path: Path):
    """ID 不匹配报告：parent 缺失、supporting_id 缺失、异常链接状态。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    cols = ["issue_type", "source_id", "referenced_id", "detail"]
    out = []
    for m in result["evidence_audit"]["parent_missing_examples"]:
        out.append({"issue_type": "evidence_parent_missing", "source_id": m["evidence_id"],
                    "referenced_id": m["parent_id"], "detail": "parent_id 不在整洁样本 id 中"})
    for r in result["evidence_audit"]["linkage_rows"]:
        if r["linkage_status"] in ("no_match", "empty_text"):
            detail = f"sim={r['similarity_ratio']} ngram={r['ngram_overlap']}"
            if r.get("notes"):
                detail = r["notes"] + f"; {detail}"
            out.append({"issue_type": "evidence_unit_semantic_" + r["linkage_status"],
                        "source_id": r["evidence_id"], "referenced_id": r["parent_id"],
                        "detail": detail})
    for p in result["insights_audit"]["per_insight"]:
        for mid in p["missing_support_ids"]:
            out.append({"issue_type": "insight_supporting_id_missing",
                        "source_id": f"insight_line_{p['line']}", "referenced_id": mid,
                        "detail": "supporting_id 不在证据表 id 中"})
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in out:
            w.writerow(r)
    return len(out)


def build_arg_parser():
    ap = argparse.ArgumentParser(description="PsyLens 公开数据审计（离线 / 确定性 / 只读）")
    ap.add_argument("--dataset", choices=["legacy", "v2", "both"], default="both",
                    help="审计数据集：legacy（历史公开数据）/ v2（迁移底座）/ both（默认）")
    ap.add_argument("--json-out", default="", help="输出完整审计结果 JSON 的路径")
    ap.add_argument("--csv-out", default="", help="输出证据单元逐行关联表 CSV 的路径（legacy）")
    ap.add_argument("--mismatch-out", default="", help="输出 ID 不匹配报告 CSV 的路径（legacy）")
    ap.add_argument("--quiet", action="store_true", help="仅输出关键摘要")
    return ap


def print_summary(result):
    ca = result["clean_input_audit"]
    ea = result["evidence_audit"]
    ia = result["insights_audit"]
    rc = result["recompute"]
    print("=" * 60)
    print("PsyLens 公开数据审计摘要")
    print("=" * 60)
    print(f"整洁样本行数: {ca['total_rows']} (期望 {EXPECTED_CLEAN_ROWS}), id 唯一: {ca['id_unique']}")
    print(f"平台分布: {ca['platform_distribution']}")
    print(f"时间窗分布: {ca['window_distribution']}")
    print(f"证据单元行数: {ea['total_rows']} (期望 {EXPECTED_EVIDENCE_ROWS}), id 唯一: {ea['id_unique']}")
    print(f"parent_reference_exists_rate: {ea['parent_reference_exists_rate']} "
          f"(值存在 {ea['parent_reference_exists_count']}/{ea['total_rows']})")
    print(f"parent_semantic_linkage_rate: {ea['parent_semantic_linkage_rate']} "
          f"(语义匹配 {ea['parent_semantic_linkage_count']}/{ea['total_rows']})")
    print(f"全域匹配诊断: {ea['global_match_counts']}")
    print(f"  唯一命中={ea['unique_match_count']} 歧义命中={ea['ambiguous_match_count']} 未找到={ea['not_found_count']}")
    print(f"唯一命中偏移直方图: {ea['unique_offset_histogram']} (parent_id 范围 {ea['parent_id_min']}-{ea['parent_id_max']})")
    print(f"实际出处平台分布(仅唯一命中): {ea['actual_source_platform_distribution_unique_only']}")
    print(f"evidence_phrase 命中(精确/归一): "
          f"{ea['evidence_phrase_exact_in_unit']}+{ea['evidence_phrase_normalized_only']}"
          f"/{ea['evidence_phrase_total_nonempty']}")
    print(f"洞察数: {ia['total_lines_parsed']} (期望 {EXPECTED_INSIGHTS}), "
          f"解析失败: {len(ia['parse_failures'])}")
    print(f"supporting_id 缺失行: {ia['missing_support_lines']}")
    print(f"insight confidence 分布: {ia['insight_confidence_distribution']}")
    print(f"needs_human_review 分布(模型字段): {ia['needs_human_review_distribution']}")
    print(f"high_confidence={ia['high_confidence_count']} "
          f"no_review_flag={ia['no_review_flag_count']} "
          f"交集={ia['high_confidence_and_no_review_flag_count']}")
    print(f"机制计数: competence_frustration={rc['competence_frustration_count']} "
          f"fairness_threat={rc['fairness_threat_count']} uncertain={rc['uncertain_mechanism_count']}")
    print(f"theme_bucket=balance_mechanic 计数: "
          f"{rc['theme_bucket_counts'].get('balance_mechanic', 0)} "
          f"按平台 {rc['theme_balance_mechanic_by_platform']}")
    print(f"证据层 surface_topic=balance: {rc['surface_balance_count']}")
    print(f"示例 1_u2 闭合: {rc['example_1_u2'].get('chain_closed')} "
          f"(实际出处平台: {rc['example_1_u2'].get('actual_source_platform')}, "
          f"候选数: {rc['example_1_u2'].get('candidate_count')})")
    print("-" * 60)
    print(f"legacy 审计状态: {result['phase0_status']}")
    if result["blockers"]:
        print("阻断项:")
        for b in result["blockers"]:
            print(f"  - {b}")
    print("=" * 60)


def print_v2_summary(v2):
    print("-" * 60)
    print("v2 迁移底座审计")
    print("-" * 60)
    if not v2.get("exists"):
        for i in v2["issues"]:
            print(f"  - {i}")
        print(f"v2_migration_status: {v2['v2_migration_status']}")
        return
    print(f"samples={v2['sample_count']} platform={v2['platform_counts']}")
    print(f"migrated_evidence={v2['migrated_evidence_count']} ambiguous={v2['ambiguous_evidence_count']}")
    print(f"bili_samples_covered={v2['bili_samples_covered']} bili_candidate_units={v2['bili_candidate_unit_count']}")
    print(f"review_status 分布: {v2['review_status_distribution']}")
    print(f"manifest 哈希校验: {'OK' if v2['manifest_hash_ok'] else 'FAIL'}")
    if v2["issues"]:
        print("v2 阻断项:")
        for i in v2["issues"]:
            print(f"  - {i}")
    print(f"v2_migration_status: {v2['v2_migration_status']}")


def main(argv=None):
    args = build_arg_parser().parse_args(argv)
    combined = run_combined_audit(args.dataset)

    # JSON 输出：dataset=legacy 时输出 legacy 全量；否则输出组合结果
    if args.json_out:
        p = Path(args.json_out)
        p.parent.mkdir(parents=True, exist_ok=True)
        payload = combined.get("legacy") if args.dataset == "legacy" else combined
        p.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.csv_out and "legacy" in combined:
        write_linkage_csv(combined["legacy"], Path(args.csv_out))
    if args.mismatch_out and "legacy" in combined:
        write_mismatch_csv(combined["legacy"], Path(args.mismatch_out))

    if not args.quiet:
        if "legacy" in combined:
            print_summary(combined["legacy"])
        if "v2" in combined:
            print_v2_summary(combined["v2"])
        print("=" * 60)
        print(f"数据集: {args.dataset}")
        if "legacy_status" in combined:
            print(f"legacy_status: {combined['legacy_status']}")
        if "v2_migration_status" in combined:
            print(f"v2_migration_status: {combined['v2_migration_status']}")
        if "provisional_evidence_status" in combined:
            print(f"provisional_evidence_status: {combined['provisional_evidence_status']}")
        if "human_review_status" in combined:
            print(f"human_review_status: {combined['human_review_status']}")
        print(f"publication_readiness: {combined['publication_readiness']}")
        print(f"  原因: {combined['publication_readiness_reason']}")
        print("=" * 60)

    # 退出码：
    #  legacy -> legacy 有阻断则非零
    #  v2     -> v2 迁移有阻断则非零（迁移 PASS 时返回 0）
    #  both   -> 依 publication_readiness（BLOCKED 则非零）
    if args.dataset == "legacy":
        return 1 if combined["legacy_status"] == "BLOCKED" else 0
    if args.dataset == "v2":
        return 1 if combined["v2_migration_status"] == "BLOCKED" else 0
    return 1 if combined["publication_readiness"] == "BLOCKED" else 0


if __name__ == "__main__":
    sys.exit(main())
