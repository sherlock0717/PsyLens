#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Normalize the public PsyLens dataset into a compact, explicit schema."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "data" / "public"
DEFAULT_OUTPUT_DIR = ROOT / "artifacts" / "normalized_public"

SAMPLE_FIELDS = [
    "sample_id",
    "platform_source",
    "platform_sequence",
    "window_tag",
    "theme_bucket",
    "reply_type",
    "date",
    "public_text",
    "migration_status",
]
EVIDENCE_FIELDS = [
    "evidence_id",
    "sample_id",
    "platform_source",
    "unit_index",
    "unit_text",
    "surface_topic",
    "mechanism_label",
    "label_source",
    "review_status",
    "analysis_inclusion_status",
]


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def read_manifest(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def previous_transformations(source_dir: Path) -> dict[str, int]:
    manifest = read_manifest(source_dir / "public_manifest.json")
    values = manifest.get("transformations", {})
    if not isinstance(values, dict):
        return {}
    result: dict[str, int] = {}
    for key, value in values.items():
        if isinstance(value, int) and value >= 0:
            result[key] = value
    return result


def write_rows(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows({field: row.get(field, "") for field in fields} for row in rows)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalize(source_dir: Path, output_dir: Path) -> dict[str, object]:
    samples = read_rows(source_dir / "samples_public.csv")
    evidence = read_rows(source_dir / "evidence_public.csv")
    previous = previous_transformations(source_dir)

    raw_text_present = bool(samples and "raw_text" in samples[0])
    raw_public_equal = 0
    if raw_text_present:
        raw_public_equal = sum(
            1
            for row in samples
            if (row.get("raw_text", "") or "") == (row.get("public_text", "") or "")
        )

    blank_topics = 0
    normalized_evidence = []
    for row in evidence:
        normalized = dict(row)
        if not (normalized.get("surface_topic", "") or "").strip():
            normalized["surface_topic"] = "other_uncertain"
            blank_topics += 1
        normalized_evidence.append(normalized)

    samples_path = output_dir / "samples_public.csv"
    evidence_path = output_dir / "evidence_public.csv"
    write_rows(samples_path, SAMPLE_FIELDS, samples)
    write_rows(evidence_path, EVIDENCE_FIELDS, normalized_evidence)

    transformations = {
        "redundant_raw_text_column_removed": max(
            raw_public_equal,
            previous.get("redundant_raw_text_column_removed", 0),
        ),
        "blank_surface_topic_normalized_to_other_uncertain": max(
            blank_topics,
            previous.get("blank_surface_topic_normalized_to_other_uncertain", 0),
        ),
        "empty_date_count": sum(1 for row in samples if not (row.get("date", "") or "").strip()),
    }

    manifest = {
        "schema_version": "public-2.0",
        "files": {
            "samples_public.csv": {
                "row_count": len(samples),
                "fields": SAMPLE_FIELDS,
                "sha256": sha256(samples_path),
            },
            "evidence_public.csv": {
                "row_count": len(normalized_evidence),
                "fields": EVIDENCE_FIELDS,
                "sha256": sha256(evidence_path),
            },
        },
        "transformations": transformations,
        "sanitization_policy": [
            "不包含原始来源链接、账号标识和平台内部定位字段",
            "文本字段使用公开脱敏版本 public_text",
            "公开表层话题缺失值统一写为 other_uncertain",
        ],
        "interpretation_notes": [
            "平台各 120 条属于平衡采样设计，不能据此推断各平台真实讨论量",
            "证据数量受文本长度与切分粒度影响，跨平台比较应结合每样本证据密度",
            "analysis_inclusion_status 与 mechanism_label 表示不同层面的不确定性",
        ],
    }
    (output_dir / "public_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return manifest


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Normalize PsyLens public dataset")
    parser.add_argument("--source-dir", default=str(SOURCE_DIR))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args(argv)
    manifest = normalize(Path(args.source_dir), Path(args.output_dir))
    print(json.dumps(manifest["transformations"], ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
