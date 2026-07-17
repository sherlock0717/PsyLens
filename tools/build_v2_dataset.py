#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PSYLENS-PHASE1A-001：稳定 ID、证据迁移与 B 站待处理队列生成脚本。

本脚本只做**确定性**的数据底座搭建与迁移设计：
  - 为 360 条公开样本建立稳定平台前缀 ID（方案 B）；
  - 将审计器判定为「唯一命中」的 legacy 证据迁移到正确样本；
  - 单独隔离 2 条歧义证据，不自动定案；
  - 为 B 站 120 条样本做**候选**文本切分（不生成最终机制标签）；
  - 生成 id_migration.csv 与 v2_manifest.json。

严格约束：
  - 不联网、不调用模型/API、不读取任何 Cookie/Token/Key；
  - 只读取 docs/files 历史数据，绝不覆盖；只写入 data/v2/；
  - 相同输入产生相同结果（确定性）；unit_text / source_url 不修改；
  - 不把 legacy 标签写成已人工复核；不生成最终洞察/建议。

复用 tools/audit_public_data.py 的归一化与匹配逻辑，保证与审计口径一致。
"""
from __future__ import annotations

import csv
import datetime
import hashlib
import importlib.util
import json
import re
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TOOLS_DIR.parent
V2_DIR = REPO_ROOT / "data" / "v2"

# 复用审计器（同一归一化/匹配口径）
_spec = importlib.util.spec_from_file_location("audit_public_data", TOOLS_DIR / "audit_public_data.py")
audit = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(audit)

# 平台前缀映射（platform_source -> ID 前缀）
PLATFORM_PREFIX = {"Bili": "BILI", "NGA": "NGA", "Tieba": "TIEBA"}

# B 站候选切分标点（句号/问号/感叹号/分号/换行）
SPLIT_PATTERN = re.compile(r"[。！？；\n]+|[.!?;]+")
MIN_UNIT_LEN = 6  # 过短语气词不单独作为候选证据


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def read_head_commit() -> str | None:
    """从 .git 读取当前 HEAD commit（只读本地元数据，不联网）。失败返回 None，不伪造。"""
    git_dir = REPO_ROOT / ".git"
    try:
        # worktree 情形下 .git 可能是一个文件，指向真实 gitdir
        if git_dir.is_file():
            content = git_dir.read_text(encoding="utf-8").strip()
            m = re.match(r"gitdir:\s*(.+)", content)
            if m:
                git_dir = Path(m.group(1))
                if not git_dir.is_absolute():
                    git_dir = (REPO_ROOT / git_dir).resolve()
        head = (git_dir / "HEAD").read_text(encoding="utf-8").strip()
        if head.startswith("ref:"):
            ref = head.split(" ", 1)[1].strip()
            # 先查 commondir 下的 packed/loose ref
            commondir_file = git_dir / "commondir"
            base = git_dir
            if commondir_file.exists():
                cd = commondir_file.read_text(encoding="utf-8").strip()
                base = (git_dir / cd).resolve() if not Path(cd).is_absolute() else Path(cd)
            ref_path = base / ref
            if ref_path.exists():
                return ref_path.read_text(encoding="utf-8").strip()
            return None
        return head  # detached HEAD 直接是 sha
    except OSError:
        return None


def build_sample_ids(clean_rows):
    """按平台内部出现顺序生成稳定 sample_id；返回 (sample_rows, legacy_to_sample)。"""
    seq = {"BILI": 0, "NGA": 0, "TIEBA": 0}
    legacy_to_sample = {}
    sample_rows = []
    for r in clean_rows:
        legacy_id = str(r.get("id"))
        platform = r.get("platform_source", "")
        prefix = PLATFORM_PREFIX.get(platform)
        if prefix is None:
            raise ValueError(f"未知平台 platform_source={platform!r}（legacy id={legacy_id}）")
        seq[prefix] += 1
        platform_sequence = seq[prefix]
        sample_id = f"{prefix}_{platform_sequence:04d}"
        legacy_to_sample[legacy_id] = sample_id
        sample_rows.append({
            "sample_id": sample_id,
            "legacy_clean_id": legacy_id,
            "platform_source": platform,
            "platform_sequence": platform_sequence,
            "window_tag": r.get("window_tag", ""),
            "theme_bucket": r.get("theme_bucket", ""),
            "reply_type": r.get("reply_type", ""),
            "date": r.get("date", ""),
            "raw_text": r.get("raw_text", ""),         # 不修改
            "source_url": r.get("url", ""),            # 不修改
            "thread_or_video_title": r.get("thread_or_video_title", ""),
            "migration_status": "migrated_from_legacy_clean",
        })
    return sample_rows, legacy_to_sample


def resolve_evidence(evidence_rows, clean_rows):
    """用审计器的多候选逻辑判定每条证据的唯一/歧义/未命中。

    返回 dict: legacy_evidence_id -> {
        candidate_clean_ids, candidate_count, resolved_clean_id(None if not unique)
    }
    """
    clean_norm = {str(r.get("id")): audit.normalize_text(r.get("raw_text", "")) for r in clean_rows}
    result = {}
    for r in evidence_rows:
        eid = str(r.get("id"))
        unit = r.get("unit_text", "") or ""
        nu = audit.normalize_text(unit)
        candidates = [cid for cid, cn in clean_norm.items() if nu and nu in cn]
        resolved = candidates[0] if len(candidates) == 1 else None
        result[eid] = {
            "candidate_clean_ids": candidates,
            "candidate_count": len(candidates),
            "resolved_clean_id": resolved,
        }
    return result


def parse_legacy_unit_index(legacy_evidence_id):
    """从 legacy evidence id（形如 '1_u2'）解析单元序号。"""
    m = re.search(r"_u(\d+)$", legacy_evidence_id)
    return int(m.group(1)) if m else None


def build_evidence_v2(evidence_rows, resolution, legacy_to_sample):
    """迁移唯一命中证据（candidate_count==1）。返回 evidence_v2_rows。"""
    evidence_v2 = []
    # 同一 sample 下按 legacy unit 序号稳定排序 -> 重新分配连续 unit_index
    resolved_items = []  # (sample_id, legacy_unit_index, legacy_eid, row, resolved_clean_id)
    for r in evidence_rows:
        eid = str(r.get("id"))
        res = resolution[eid]
        if res["candidate_count"] == 1:
            resolved_clean_id = res["resolved_clean_id"]
            sample_id = legacy_to_sample[resolved_clean_id]
            resolved_items.append((sample_id, parse_legacy_unit_index(eid), eid, r, resolved_clean_id))
    # 稳定排序：sample_id，然后 legacy unit 序号，再 legacy_eid
    resolved_items.sort(key=lambda x: (x[0], x[1] if x[1] is not None else 9999, x[2]))
    unit_counter = {}
    for sample_id, _legacy_ui, legacy_eid, r, resolved_clean_id in resolved_items:
        unit_counter[sample_id] = unit_counter.get(sample_id, 0) + 1
        unit_index = unit_counter[sample_id]
        evidence_id = f"{sample_id}_U{unit_index:02d}"
        evidence_v2.append({
            "evidence_id": evidence_id,
            "sample_id": sample_id,
            "unit_index": unit_index,
            "legacy_evidence_id": legacy_eid,
            "legacy_parent_id": str(r.get("parent_id", "")),
            "resolved_legacy_clean_id": resolved_clean_id,
            "unit_text": r.get("unit_text", ""),                    # 不修改
            "surface_topic_legacy": r.get("surface_topic", ""),
            "mechanism_label_legacy": r.get("mechanism_label", ""),
            "confidence_legacy": r.get("confidence", ""),
            "evidence_phrase": r.get("evidence_phrase", ""),
            "migration_method": "unique_normalized_substring_match",
            "review_status": "legacy_ai_label_unreviewed",
            "review_note": "legacy AI 标签，尚未人工复核；confidence 为模型置信度而非证据强度",
        })
    return evidence_v2


def _excerpt(text, n=50):
    return re.sub(r"\s+", " ", str(text)).strip()[:n]


def build_ambiguous(evidence_rows, resolution, legacy_to_sample, clean_by_id):
    ambiguous = []
    for r in evidence_rows:
        eid = str(r.get("id"))
        res = resolution[eid]
        if res["candidate_count"] > 1:
            cids = res["candidate_clean_ids"]
            ambiguous.append({
                "legacy_evidence_id": eid,
                "legacy_parent_id": str(r.get("parent_id", "")),
                "unit_text": r.get("unit_text", ""),
                "candidate_clean_ids": "|".join(cids),
                "candidate_sample_ids": "|".join(legacy_to_sample.get(c, "") for c in cids),
                "candidate_count": res["candidate_count"],
                "candidate_platforms": "|".join(sorted({clean_by_id[c].get("platform_source", "") for c in cids})),
                "candidate_text_excerpts": " || ".join(
                    f"{c}:{_excerpt(clean_by_id[c].get('raw_text',''))}" for c in cids),
                "resolution_status": "pending_human_resolution",
                "resolution_note": "多候选，来源不确定；不得自动定案，等待人工确认",
            })
    return ambiguous


def build_bili_queue(sample_rows):
    """对 B 站样本做确定性候选切分；不生成最终机制标签。"""
    rows = []
    qid = 0
    for s in sample_rows:
        if s["platform_source"] != "Bili":
            continue
        raw = s["raw_text"] or ""
        parts = SPLIT_PATTERN.split(raw)
        cand_idx = 0
        for p in parts:
            seg = p.strip()
            if len(seg) < MIN_UNIT_LEN:
                continue  # 过短语气词不单独作为候选
            cand_idx += 1
            qid += 1
            rows.append({
                "queue_id": f"BQ_{qid:04d}",
                "sample_id": s["sample_id"],
                "legacy_clean_id": s["legacy_clean_id"],
                "raw_text": raw,                       # 不修改
                "candidate_unit_index": cand_idx,
                "candidate_unit_text": seg,
                "split_method": "punctuation_split(。！？；.!?; and newline); min_len=%d" % MIN_UNIT_LEN,
                "surface_topic_candidate": "",         # 允许为空
                "mechanism_label_candidate": "unassigned",  # 必须为空或 unassigned
                "candidate_status": "pending_review",
                "human_review_status": "not_reviewed",
                "notes": "确定性候选切分，非最终证据；机制标签待人工/模型辅助标注",
            })
    return rows


def build_id_migration(sample_rows, evidence_v2, ambiguous):
    rows = []
    for s in sample_rows:
        rows.append({
            "legacy_entity_type": "clean_sample",
            "legacy_id": s["legacy_clean_id"],
            "new_entity_type": "sample",
            "new_id": s["sample_id"],
            "resolved_clean_id": s["legacy_clean_id"],
            "migration_status": "migrated",
            "migration_method": "platform_sequence_stable_id",
            "notes": "",
        })
    for e in evidence_v2:
        rows.append({
            "legacy_entity_type": "evidence_unit",
            "legacy_id": e["legacy_evidence_id"],
            "new_entity_type": "evidence",
            "new_id": e["evidence_id"],
            "resolved_clean_id": e["resolved_legacy_clean_id"],
            "migration_status": "migrated",
            "migration_method": "unique_normalized_substring_match",
            "notes": "legacy AI 标签未人工复核",
        })
    for a in ambiguous:
        rows.append({
            "legacy_entity_type": "evidence_unit",
            "legacy_id": a["legacy_evidence_id"],
            "new_entity_type": "evidence",
            "new_id": "",
            "resolved_clean_id": "",
            "migration_status": "pending_human_resolution",
            "migration_method": "ambiguous_multi_candidate",
            "notes": f"candidate_count={a['candidate_count']}，来源不确定",
        })
    # legacy insight / action 不迁移，仅标记
    rows.append({
        "legacy_entity_type": "insight_set",
        "legacy_id": "04_validated_insights.jsonl",
        "new_entity_type": "insight",
        "new_id": "",
        "resolved_clean_id": "",
        "migration_status": "deferred_until_evidence_rebuild",
        "migration_method": "",
        "notes": "结构化洞察待证据层重建后再生成",
    })
    rows.append({
        "legacy_entity_type": "action_matrix",
        "legacy_id": "05_action_matrix.json",
        "new_entity_type": "action",
        "new_id": "",
        "resolved_clean_id": "",
        "migration_status": "deferred_until_evidence_rebuild",
        "migration_method": "",
        "notes": "行动建议待证据/洞察重建后再生成",
    })
    return rows


def write_csv(path: Path, cols, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in cols})


SAMPLE_COLS = ["sample_id", "legacy_clean_id", "platform_source", "platform_sequence",
               "window_tag", "theme_bucket", "reply_type", "date", "raw_text",
               "source_url", "thread_or_video_title", "migration_status"]
EVIDENCE_COLS = ["evidence_id", "sample_id", "unit_index", "legacy_evidence_id",
                 "legacy_parent_id", "resolved_legacy_clean_id", "unit_text",
                 "surface_topic_legacy", "mechanism_label_legacy", "confidence_legacy",
                 "evidence_phrase", "migration_method", "review_status", "review_note"]
AMBIGUOUS_COLS = ["legacy_evidence_id", "legacy_parent_id", "unit_text",
                  "candidate_clean_ids", "candidate_sample_ids", "candidate_count",
                  "candidate_platforms", "candidate_text_excerpts",
                  "resolution_status", "resolution_note"]
BILI_COLS = ["queue_id", "sample_id", "legacy_clean_id", "raw_text",
             "candidate_unit_index", "candidate_unit_text", "split_method",
             "surface_topic_candidate", "mechanism_label_candidate",
             "candidate_status", "human_review_status", "notes"]
MIGRATION_COLS = ["legacy_entity_type", "legacy_id", "new_entity_type", "new_id",
                  "resolved_clean_id", "migration_status", "migration_method", "notes"]


def main():
    _, clean_rows = audit.read_csv_rows(audit.CLEAN_CSV)
    _, evidence_rows = audit.read_csv_rows(audit.EVIDENCE_CSV)
    clean_by_id = {str(r.get("id")): r for r in clean_rows}

    sample_rows, legacy_to_sample = build_sample_ids(clean_rows)
    resolution = resolve_evidence(evidence_rows, clean_rows)

    # 迁移唯一命中；隔离歧义
    evidence_v2 = build_evidence_v2(evidence_rows, resolution, legacy_to_sample)
    ambiguous = build_ambiguous(evidence_rows, resolution, legacy_to_sample, clean_by_id)
    bili_queue = build_bili_queue(sample_rows)
    id_migration = build_id_migration(sample_rows, evidence_v2, ambiguous)

    write_csv(V2_DIR / "samples_v2.csv", SAMPLE_COLS, sample_rows)
    write_csv(V2_DIR / "evidence_v2.csv", EVIDENCE_COLS, evidence_v2)
    write_csv(V2_DIR / "ambiguous_evidence_queue.csv", AMBIGUOUS_COLS, ambiguous)
    write_csv(V2_DIR / "bili_evidence_queue.csv", BILI_COLS, bili_queue)
    write_csv(V2_DIR / "id_migration.csv", MIGRATION_COLS, id_migration)

    platform_counts = {}
    for s in sample_rows:
        platform_counts[s["platform_source"]] = platform_counts.get(s["platform_source"], 0) + 1
    bili_samples = sorted({b["sample_id"] for b in bili_queue})

    manifest = {
        "schema_version": "v2.0",
        "generated_at": datetime.datetime.now().astimezone().isoformat(),
        "source_commit": read_head_commit(),  # 读取本地 HEAD；读不到则留 null，不伪造
        "source_files": {
            "clean_csv": str(audit.CLEAN_CSV.relative_to(REPO_ROOT)),
            "evidence_csv": str(audit.EVIDENCE_CSV.relative_to(REPO_ROOT)),
        },
        "sample_count": len(sample_rows),
        "platform_counts": platform_counts,
        "migrated_evidence_count": len(evidence_v2),
        "ambiguous_evidence_count": len(ambiguous),
        "bili_samples_pending": len(bili_samples),
        "bili_candidate_unit_count": len(bili_queue),
        "id_scheme": {
            "sample_id": "<PLATFORM>_<0001-0120>（平台内出现顺序，稳定）",
            "evidence_id": "<sample_id>_U<两位单元序号>",
            "insight_id": "INSIGHT_001（本阶段仅格式，不生成实体）",
            "action_id": "ACTION_001（本阶段仅格式，不生成实体）",
        },
        "hashes": {},
        "limitations": [
            "legacy 标签尚未完成系统人工复核（review_status=legacy_ai_label_unreviewed）",
            "B 站证据仍在待处理队列（bili_evidence_queue.csv），未形成最终机制标签",
            "结构化洞察尚未重建",
            "行动建议尚未重建",
            "v2 尚不用于公开页面",
        ],
    }
    # 计算已生成文件的 SHA-256
    for name in ["samples_v2.csv", "evidence_v2.csv", "ambiguous_evidence_queue.csv",
                 "bili_evidence_queue.csv", "id_migration.csv"]:
        manifest["hashes"][name] = sha256_file(V2_DIR / name)

    (V2_DIR / "v2_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    print("v2 生成完成：")
    print(f"  samples={len(sample_rows)} platform_counts={platform_counts}")
    print(f"  migrated_evidence={len(evidence_v2)} ambiguous={len(ambiguous)}")
    print(f"  bili_samples_pending={len(bili_samples)} bili_candidate_units={len(bili_queue)}")


if __name__ == "__main__":
    main()
