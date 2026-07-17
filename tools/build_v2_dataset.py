#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PSYLENS-PHASE1A：稳定 ID、证据迁移与 B 站待处理队列生成脚本。

本脚本只做数据底座搭建与迁移设计：
  - 为 360 条公开样本建立稳定平台前缀 ID（方案 B）；
  - 将审计器判定为「唯一命中」的 legacy 证据迁移到正确样本；
  - 单独隔离歧义证据，不自动定案；
  - 为 B 站样本做**候选**文本切分（不生成最终机制标签）；
  - 生成 id_migration.csv 与 v2_manifest.json。

确定性口径（PSYLENS-PHASE1A-002 修正后）：
  - 五个 CSV 由固定输入确定性生成，字节可复现；
  - manifest 的 generated_at 与 source_data_commit **不再从当前时间/HEAD 自动推断**，
    而是由调用方显式传入；只有在固定 generated_at + 固定 source_data_commit 时，
    完整 v2 快照（含 manifest）才字节级可复现。

严格约束：
  - 不联网、不调用模型/API、不读取任何 Cookie/Token/Key；
  - 只读取 docs/files 历史数据，绝不覆盖；输出目录由参数指定；
  - unit_text / source_url 不修改；
  - 不把 legacy 标签写成已人工复核；不生成最终洞察/建议。

复用 tools/audit_public_data.py 的归一化与匹配逻辑，保证与审计口径一致。
"""
from __future__ import annotations

import argparse
import csv
import datetime
import hashlib
import importlib.util
import json
import re
import sys
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
# 平台固定排序（仅用于稳定遍历，不影响平台内独立编号）
PLATFORM_ORDER = {"Bili": 0, "NGA": 1, "Tieba": 2}

# B 站候选切分标点（句号/问号/感叹号/分号/换行）
SPLIT_PATTERN = re.compile(r"[。！？；\n]+|[.!?;]+")
MIN_UNIT_LEN = 6  # 过短语气词不单独作为候选证据


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def build_sample_ids(clean_rows):
    """按 platform_source + numeric legacy_clean_id 的稳定顺序生成 sample_id。

    不依赖 clean_rows 当前遍历顺序：即使输入行被打乱，
    legacy_clean_id -> sample_id 的映射也保持不变。
    返回 (sample_rows, legacy_to_sample)。
    """
    def sort_key(r):
        platform = r.get("platform_source", "")
        try:
            nid = int(str(r.get("id")))
        except (ValueError, TypeError):
            nid = 10 ** 9
        return (PLATFORM_ORDER.get(platform, 99), nid)

    ordered = sorted(clean_rows, key=sort_key)
    seq = {"BILI": 0, "NGA": 0, "TIEBA": 0}
    legacy_to_sample = {}
    sample_rows = []
    for r in ordered:
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
    """迁移唯一命中证据（candidate_count==1）。返回 evidence_v2_rows。

    unit_index 直接**保留 legacy evidence id 的 _uN 后缀**，
    不使用压缩连续计数器；同一 sample_id + unit_index 冲突时抛错（BLOCKED），
    不静默重新编号。
    """
    evidence_v2 = []
    resolved_items = []  # (sample_id, legacy_unit_index, legacy_eid, row, resolved_clean_id)
    for r in evidence_rows:
        eid = str(r.get("id"))
        res = resolution[eid]
        if res["candidate_count"] == 1:
            resolved_clean_id = res["resolved_clean_id"]
            sample_id = legacy_to_sample[resolved_clean_id]
            resolved_items.append(
                (sample_id, parse_legacy_unit_index(eid), eid, r, resolved_clean_id))
    # 稳定排序：sample_id，然后 legacy unit 序号，再 legacy_eid
    resolved_items.sort(key=lambda x: (x[0], x[1] if x[1] is not None else 9999, x[2]))

    seen = {}  # (sample_id, unit_index) -> legacy_eid，用于冲突检测
    for sample_id, legacy_ui, legacy_eid, r, resolved_clean_id in resolved_items:
        if legacy_ui is None:
            raise ValueError(f"无法解析 legacy unit 序号: {legacy_eid!r}；BLOCKED")
        unit_index = legacy_ui                       # 保留 _uN 后缀，不压缩
        key = (sample_id, unit_index)
        if key in seen:
            raise ValueError(
                f"unit_index 冲突: sample={sample_id} unit_index={unit_index} "
                f"（legacy {seen[key]} vs {legacy_eid}）；BLOCKED，不静默重新编号")
        seen[key] = legacy_eid
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

CSV_FILENAMES = ["samples_v2.csv", "evidence_v2.csv", "ambiguous_evidence_queue.csv",
                 "bili_evidence_queue.csv", "id_migration.csv"]


def build_v2_dataset(output_dir, generated_at, source_data_commit, generator_commit=None):
    """确定性生成 v2 数据底座到 output_dir。

    参数：
      output_dir           输出目录（核心函数不固定写入 data/v2/）。
      generated_at         写入 manifest 的生成时间（由调用方显式传入，不自动取当前时间）。
      source_data_commit   数据来源快照 commit（由调用方显式传入，不从当前 HEAD 推断覆盖）。
      generator_commit     可选：生成器代码所在 commit（不得用测试时 HEAD 覆盖来源快照）。

    返回生成的 manifest dict。
    """
    output_dir = Path(output_dir)

    _, clean_rows = audit.read_csv_rows(audit.CLEAN_CSV)
    _, evidence_rows = audit.read_csv_rows(audit.EVIDENCE_CSV)
    clean_by_id = {str(r.get("id")): r for r in clean_rows}

    sample_rows, legacy_to_sample = build_sample_ids(clean_rows)
    resolution = resolve_evidence(evidence_rows, clean_rows)

    evidence_v2 = build_evidence_v2(evidence_rows, resolution, legacy_to_sample)
    ambiguous = build_ambiguous(evidence_rows, resolution, legacy_to_sample, clean_by_id)
    bili_queue = build_bili_queue(sample_rows)
    id_migration = build_id_migration(sample_rows, evidence_v2, ambiguous)

    write_csv(output_dir / "samples_v2.csv", SAMPLE_COLS, sample_rows)
    write_csv(output_dir / "evidence_v2.csv", EVIDENCE_COLS, evidence_v2)
    write_csv(output_dir / "ambiguous_evidence_queue.csv", AMBIGUOUS_COLS, ambiguous)
    write_csv(output_dir / "bili_evidence_queue.csv", BILI_COLS, bili_queue)
    write_csv(output_dir / "id_migration.csv", MIGRATION_COLS, id_migration)

    platform_counts = {}
    for s in sample_rows:
        platform_counts[s["platform_source"]] = platform_counts.get(s["platform_source"], 0) + 1
    bili_samples = sorted({b["sample_id"] for b in bili_queue})

    manifest = {
        "schema_version": "v2.0",
        "generated_at": generated_at,
        "source_data_commit": source_data_commit,     # 显式传入，不自动推断
        "generator_commit": generator_commit,         # 可选
        "source_files": {
            "clean_csv": audit.CLEAN_CSV.relative_to(REPO_ROOT).as_posix(),
            "evidence_csv": audit.EVIDENCE_CSV.relative_to(REPO_ROOT).as_posix(),
        },
        "sample_count": len(sample_rows),
        "platform_counts": platform_counts,
        "migrated_evidence_count": len(evidence_v2),
        "ambiguous_evidence_count": len(ambiguous),
        "bili_samples_pending": len(bili_samples),
        "bili_candidate_unit_count": len(bili_queue),
        "id_scheme": {
            "sample_id": "<PLATFORM>_<0001-0120>（平台内按 numeric legacy id 稳定排序）",
            "evidence_id": "<sample_id>_U<两位单元序号，保留 legacy _uN>",
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
    for name in CSV_FILENAMES:
        manifest["hashes"][name] = sha256_file(output_dir / name)

    (output_dir / "v2_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    return manifest


def build_arg_parser():
    ap = argparse.ArgumentParser(description="PsyLens v2 数据底座生成（离线 / 确定性 / 只读历史数据）")
    ap.add_argument("--output-dir", default=str(V2_DIR),
                    help="输出目录（默认 data/v2；测试应传入 tmp_path）")
    ap.add_argument("--generated-at", default=None,
                    help="写入 manifest 的生成时间（ISO 8601）；不传则用当前时间（交互运行，非字节级可复现）")
    ap.add_argument("--source-data-commit", default=None,
                    help="数据来源快照 commit（正式快照必须显式传入；不从 HEAD 推断）")
    ap.add_argument("--generator-commit", default=None,
                    help="可选：生成器代码所在 commit")
    return ap


def main(argv=None):
    args = build_arg_parser().parse_args(argv)
    generated_at = args.generated_at
    if generated_at is None:
        # 交互运行的兜底：使用当前时间；此时整包非字节级可复现（仅 CSV 确定）
        generated_at = datetime.datetime.now().astimezone().isoformat()
    manifest = build_v2_dataset(
        output_dir=args.output_dir,
        generated_at=generated_at,
        source_data_commit=args.source_data_commit,
        generator_commit=args.generator_commit,
    )
    print("v2 生成完成：")
    print(f"  output_dir={args.output_dir}")
    print(f"  samples={manifest['sample_count']} platform_counts={manifest['platform_counts']}")
    print(f"  migrated_evidence={manifest['migrated_evidence_count']} "
          f"ambiguous={manifest['ambiguous_evidence_count']}")
    print(f"  bili_samples_pending={manifest['bili_samples_pending']} "
          f"bili_candidate_units={manifest['bili_candidate_unit_count']}")
    print(f"  source_data_commit={manifest['source_data_commit']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
