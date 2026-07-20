#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build a deterministic public-facing analysis summary from data/public."""
from __future__ import annotations

import argparse
import csv
import json
import re
import statistics
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_DIR = ROOT / "data" / "public"
DEFAULT_OUTPUT = ROOT / "artifacts" / "public_analysis_summary.json"
URL_PATTERN = re.compile(r"https?://", re.IGNORECASE)
SPACE_PATTERN = re.compile(r"\s+")


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def normalized_text(value: str) -> str:
    return SPACE_PATTERN.sub("", (value or "").strip())


def sorted_counts(values, denominator: int | None = None) -> list[dict[str, object]]:
    counter = Counter(value or "(empty)" for value in values)
    total = denominator if denominator is not None else sum(counter.values())
    return [
        {"key": key, "count": count, "rate": round(count / total, 6) if total else 0.0}
        for key, count in sorted(counter.items(), key=lambda item: (-item[1], item[0]))
    ]


def nearest_rank(values: list[int], percentile: float) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int(round((len(ordered) - 1) * percentile))))
    return ordered[index]


def text_stats(values: list[str]) -> dict[str, object]:
    lengths = [len(value or "") for value in values]
    if not lengths:
        return {"min": 0, "median": 0, "mean": 0.0, "p90": 0, "max": 0}
    return {
        "min": min(lengths),
        "median": statistics.median(lengths),
        "mean": round(statistics.mean(lengths), 2),
        "p90": nearest_rank(lengths, 0.90),
        "max": max(lengths),
    }


def duplicate_summary(rows: list[dict[str, str]], field: str) -> dict[str, object]:
    groups: dict[str, list[str]] = defaultdict(list)
    id_field = "sample_id" if "sample_id" in rows[0] else "evidence_id"
    for row in rows:
        value = normalized_text(row.get(field, ""))
        if value:
            groups[value].append(row.get(id_field, ""))
    duplicated = [ids for ids in groups.values() if len(ids) > 1]
    return {
        "duplicate_group_count": len(duplicated),
        "rows_in_duplicate_groups": sum(len(ids) for ids in duplicated),
        "largest_group_size": max((len(ids) for ids in duplicated), default=1),
        "example_groups": sorted(duplicated, key=lambda ids: (-len(ids), ids))[:5],
    }


def build(public_dir: Path = PUBLIC_DIR) -> dict[str, object]:
    samples = read_rows(public_dir / "samples_public.csv")
    evidence = read_rows(public_dir / "evidence_public.csv")
    sample_by_id = {row["sample_id"]: row for row in samples}
    sample_ids = [row["sample_id"] for row in samples]
    evidence_ids = [row["evidence_id"] for row in evidence]

    evidence_by_sample = Counter(row.get("sample_id", "") for row in evidence)
    evidence_density = [evidence_by_sample.get(sample_id, 0) for sample_id in sample_ids]

    orphan_evidence: list[str] = []
    platform_mismatches: list[str] = []
    text_mismatches: list[str] = []
    for row in evidence:
        sample = sample_by_id.get(row.get("sample_id", ""))
        if sample is None:
            orphan_evidence.append(row.get("evidence_id", ""))
            continue
        if row.get("platform_source", "") != sample.get("platform_source", ""):
            platform_mismatches.append(row.get("evidence_id", ""))
        unit = normalized_text(row.get("unit_text", ""))
        parent = normalized_text(sample.get("public_text") or sample.get("raw_text", ""))
        if unit and unit not in parent:
            text_mismatches.append(row.get("evidence_id", ""))

    topic_mechanism = Counter(
        (row.get("surface_topic", "(empty)"), row.get("mechanism_label", "(empty)"))
        for row in evidence
    )
    cross_distribution = [
        {
            "surface_topic": topic,
            "mechanism_label": mechanism,
            "count": count,
            "rate": round(count / len(evidence), 6) if evidence else 0.0,
        }
        for (topic, mechanism), count in sorted(
            topic_mechanism.items(), key=lambda item: (-item[1], item[0][0], item[0][1])
        )
    ]
    specific_intersections = [
        item
        for item in cross_distribution
        if item["surface_topic"] != "other_uncertain" and item["mechanism_label"] != "uncertain"
    ]

    assigned_mechanisms = [
        row.get("mechanism_label", "")
        for row in evidence
        if row.get("mechanism_label", "") not in {"", "uncertain", "unassigned"}
    ]
    specific_topics = [
        row.get("surface_topic", "")
        for row in evidence
        if row.get("surface_topic", "") not in {"", "other_uncertain"}
    ]

    platform_breakdown = {}
    for platform in sorted({row.get("platform_source", "") for row in samples}):
        platform_samples = [row for row in samples if row.get("platform_source", "") == platform]
        platform_evidence = [row for row in evidence if row.get("platform_source", "") == platform]
        platform_assigned = [
            row.get("mechanism_label", "")
            for row in platform_evidence
            if row.get("mechanism_label", "") not in {"", "uncertain", "unassigned"}
        ]
        platform_breakdown[platform] = {
            "sample_count": len(platform_samples),
            "evidence_count": len(platform_evidence),
            "evidence_per_sample": round(len(platform_evidence) / max(1, len(platform_samples)), 3),
            "surface_topics": sorted_counts(row.get("surface_topic", "") for row in platform_evidence),
            "mechanisms": sorted_counts(row.get("mechanism_label", "") for row in platform_evidence),
            "assigned_mechanisms": sorted_counts(platform_assigned),
        }

    raw_column_present = bool(samples and "raw_text" in samples[0])
    raw_public_differences = None
    if raw_column_present:
        raw_public_differences = sum(
            1
            for row in samples
            if (row.get("raw_text", "") or "") != (row.get("public_text", "") or "")
        )

    url_hits = []
    for filename in ("samples_public.csv", "evidence_public.csv", "public_manifest.json"):
        text = (public_dir / filename).read_text(encoding="utf-8")
        if URL_PATTERN.search(text):
            url_hits.append(filename)

    empty_fields = {
        "samples": {
            field: sum(1 for row in samples if not (row.get(field, "") or "").strip())
            for field in samples[0]
        },
        "evidence": {
            field: sum(1 for row in evidence if not (row.get(field, "") or "").strip())
            for field in evidence[0]
        },
    }

    inclusion_flags = sum(
        1 for row in evidence if row.get("analysis_inclusion_status", "") == "included_flagged_uncertain"
    )
    uncertain_mechanisms = sum(
        1 for row in evidence if row.get("mechanism_label", "") == "uncertain"
    )

    return {
        "schema_version": "public-analysis-1.1",
        "counts": {
            "samples": len(samples),
            "evidence": len(evidence),
            "platforms": len({row.get("platform_source", "") for row in samples}),
            "samples_without_evidence": sum(1 for count in evidence_density if count == 0),
            "uncertain_mechanism": uncertain_mechanisms,
            "uncertain_mechanism_rate": round(uncertain_mechanisms / len(evidence), 6) if evidence else 0.0,
            "other_uncertain_topic": sum(
                1 for row in evidence if row.get("surface_topic", "") == "other_uncertain"
            ),
            "inclusion_flagged_uncertain": inclusion_flags,
            "inclusion_flagged_uncertain_rate": round(inclusion_flags / len(evidence), 6) if evidence else 0.0,
            "assigned_mechanism_evidence": len(assigned_mechanisms),
            "specific_topic_evidence": len(specific_topics),
        },
        "sample_distributions": {
            "platform": sorted_counts(row.get("platform_source", "") for row in samples),
            "window_tag": sorted_counts(row.get("window_tag", "") for row in samples),
            "theme_bucket": sorted_counts(row.get("theme_bucket", "") for row in samples),
            "reply_type": sorted_counts(row.get("reply_type", "") for row in samples),
            "text_length": text_stats([row.get("public_text", "") for row in samples]),
        },
        "evidence_distributions": {
            "platform": sorted_counts(row.get("platform_source", "") for row in evidence),
            "surface_topic": sorted_counts(row.get("surface_topic", "") for row in evidence),
            "specific_surface_topic": sorted_counts(specific_topics),
            "mechanism": sorted_counts(row.get("mechanism_label", "") for row in evidence),
            "assigned_mechanism": sorted_counts(assigned_mechanisms),
            "label_source": sorted_counts(row.get("label_source", "") for row in evidence),
            "review_status": sorted_counts(row.get("review_status", "") for row in evidence),
            "analysis_inclusion_status": sorted_counts(
                row.get("analysis_inclusion_status", "") for row in evidence
            ),
            "text_length": text_stats([row.get("unit_text", "") for row in evidence]),
            "per_sample": {
                "min": min(evidence_density, default=0),
                "median": statistics.median(evidence_density) if evidence_density else 0,
                "mean": round(statistics.mean(evidence_density), 3) if evidence_density else 0.0,
                "p90": nearest_rank(evidence_density, 0.90),
                "max": max(evidence_density, default=0),
            },
        },
        "topic_mechanism_cross": cross_distribution,
        "specific_topic_mechanism_cross": specific_intersections,
        "platform_breakdown": platform_breakdown,
        "integrity": {
            "sample_id_unique": len(sample_ids) == len(set(sample_ids)),
            "evidence_id_unique": len(evidence_ids) == len(set(evidence_ids)),
            "orphan_evidence_count": len(orphan_evidence),
            "orphan_evidence_examples": orphan_evidence[:10],
            "platform_mismatch_count": len(platform_mismatches),
            "platform_mismatch_examples": platform_mismatches[:10],
            "evidence_text_mismatch_count": len(text_mismatches),
            "evidence_text_match_rate": round(
                (len(evidence) - len(text_mismatches) - len(orphan_evidence)) / len(evidence), 6
            )
            if evidence
            else 0.0,
            "url_hit_files": url_hits,
            "raw_text_column_present": raw_column_present,
            "raw_public_text_difference_count": raw_public_differences,
            "sample_duplicates": duplicate_summary(samples, "public_text"),
            "evidence_duplicates": duplicate_summary(evidence, "unit_text"),
            "empty_fields": empty_fields,
        },
        "interpretation": {
            "balanced_sampling": "三个平台各 120 条为分析设计，不能解释为平台真实讨论量相同。",
            "segmentation_effect": "证据数量同时受原文长度和切分粒度影响，平台比较需结合每样本证据密度。",
            "uncertainty_layers": "机制标签 uncertain 与 inclusion flagged uncertain 是两个字段，分别表示机制无法明确归类与证据纳入时需提醒。",
            "coding_sources": "公开编码由历史 AI 结果与离线规则提案组成，分布用于方法审计和探索性描述。",
        },
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Summarize PsyLens public data")
    parser.add_argument("--public-dir", default=str(PUBLIC_DIR))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args(argv)
    result = build(Path(args.public_dir))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result["counts"], ensure_ascii=False, sort_keys=True))
    print(f"analysis_summary={output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
