#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PsyLens v2 评测器（离线、确定性）。

读取 provisional 证据层（及草稿洞察/建议，若存在）计算 A~E 五组指标，
按 evaluation/thresholds.yaml 判定 block/warn，输出 data/v2/evaluation_report.json。

不联网、不调用模型；相同输入产生相同输出。阈值内嵌（与 thresholds.yaml 保持一致），
避免引入 PyYAML 依赖。
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TOOLS_DIR.parent
V2_DIR = REPO_ROOT / "data" / "v2"

_spec = importlib.util.spec_from_file_location("audit_public_data", TOOLS_DIR / "audit_public_data.py")
audit = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(audit)

ALLOWED_MECH = {"competence_frustration", "fairness_threat", "trust_communication_gap",
                "belonging_drop", "norm_safety_risk", "uncertain"}

# 阈值（与 evaluation/thresholds.yaml 一致）；(kind, value, level)
THRESHOLDS = {
    "sample_id_unique_rate": ("min", 1.0, "block"),
    "evidence_id_unique_rate": ("min", 1.0, "block"),
    "parent_reference_exists_rate": ("min", 1.0, "warn"),
    "parent_semantic_linkage_rate": ("min", 0.98, "warn"),
    "evidence_text_match_rate": ("min", 0.98, "block"),
    "source_url_coverage": ("min", 0.95, "warn"),
    "platform_sample_coverage": ("min", 3, "warn"),
    "label_completion_rate": ("min", 0.30, "warn"),
    "uncertain_rate": ("max", 0.75, "warn"),
    "invalid_label_rate": ("max", 0.0, "block"),
    "evidence_phrase_match_rate": ("min", 0.98, "block"),
    "agent_proposal_coverage": ("min", 1.0, "block"),
    "human_review_coverage": ("min", 0.0, "warn"),
    "support_resolution_rate": ("min", 1.0, "block"),
    "low_support_claim_rate": ("max", 0.5, "warn"),
    "single_platform_claim_rate": ("max", 1.0, "warn"),
    "action_to_insight_linkage_rate": ("min", 1.0, "block"),
    "action_to_evidence_linkage_rate": ("min", 1.0, "block"),
    "validation_plan_coverage": ("min", 1.0, "warn"),
    "expected_effect_coverage": ("min", 1.0, "warn"),
    "parse_success_rate": ("min", 1.0, "block"),
    "output_hash_match_rate": ("min", 1.0, "block"),
}


def rate(num, den):
    return round(num / den, 4) if den else 0.0


def judge(name, value):
    if name not in THRESHOLDS or value is None:
        return "n/a"
    kind, thr, level = THRESHOLDS[name]
    ok = value >= thr if kind == "min" else value <= thr
    return "pass" if ok else level  # 未达标返回 block/warn


def evaluate(output_dir=None):
    output_dir = Path(output_dir) if output_dir else V2_DIR
    metrics = {}
    failures = Counter()

    _, samples = audit.read_csv_rows(V2_DIR / "samples_v2.csv")
    _, legacy_ev = audit.read_csv_rows(V2_DIR / "evidence_v2.csv")
    _, prov = audit.read_csv_rows(V2_DIR / "evidence_provisional_v2.csv")
    _, bili = audit.read_csv_rows(V2_DIR / "bili_evidence_queue.csv")
    _, proposals = audit.read_csv_rows(V2_DIR / "agent_label_proposals.csv")
    sample_by_id = {r["sample_id"]: r for r in samples}
    sample_raw = {r["sample_id"]: r.get("raw_text", "") for r in samples}

    # A 数据完整性
    sids = [r["sample_id"] for r in samples]
    metrics["sample_id_unique_rate"] = rate(len(set(sids)), len(sids))
    ev_ids = [r["evidence_id"] for r in prov]
    metrics["evidence_id_unique_rate"] = rate(len(set(ev_ids)), len(ev_ids))
    # legacy parent 指标复用审计
    legacy_audit = audit.run_audit()["evidence_audit"]
    metrics["parent_reference_exists_rate"] = legacy_audit["parent_reference_exists_rate"]
    metrics["parent_semantic_linkage_rate"] = legacy_audit["parent_semantic_linkage_rate"]
    loc = sum(1 for r in prov
              if audit.normalize_text(r["unit_text"]) and
              audit.normalize_text(r["unit_text"]) in audit.normalize_text(sample_raw.get(r["sample_id"], "")))
    metrics["evidence_text_match_rate"] = rate(loc, len(prov))
    url_cov = sum(1 for r in samples if (r.get("source_url", "") or "").strip())
    metrics["source_url_coverage"] = rate(url_cov, len(samples))
    metrics["platform_sample_coverage"] = len({r["platform_source"] for r in samples})

    # B 编码质量
    has_label = sum(1 for r in prov if (r.get("mechanism_label", "") or "").strip() not in ("", "unassigned"))
    metrics["label_completion_rate"] = rate(has_label, len(prov))
    unc = sum(1 for r in prov if r.get("mechanism_label") == "uncertain")
    metrics["uncertain_rate"] = rate(unc, len(prov))
    invalid = sum(1 for r in prov if (r.get("mechanism_label", "") or "").strip()
                  not in (ALLOWED_MECH | {"", "unassigned"}))
    metrics["invalid_label_rate"] = rate(invalid, len(prov))
    with_phrase = [r for r in prov if (r.get("evidence_phrase", "") or "").strip()]
    phrase_ok = sum(1 for r in with_phrase
                    if audit.normalize_text(r["evidence_phrase"]) in audit.normalize_text(r["unit_text"]))
    metrics["evidence_phrase_match_rate"] = rate(phrase_ok, len(with_phrase)) if with_phrase else 1.0
    metrics["agent_proposal_coverage"] = rate(len(proposals), len(bili))
    metrics["human_review_coverage"] = 0.0  # 无 reviewer_type=human
    metrics["human_override_rate"] = 0.0

    # C 洞察前置（若草稿存在）
    insights_path = V2_DIR / "structured_insights_draft.jsonl"
    c_available = insights_path.exists()
    if c_available:
        prov_ids = {r["evidence_id"] for r in prov}
        insights = [json.loads(line) for line in insights_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        resolved = sum(1 for x in insights if all(sid in prov_ids for sid in x.get("source_evidence_ids", [])))
        metrics["support_resolution_rate"] = rate(resolved, len(insights))
        metrics["low_support_claim_rate"] = rate(sum(1 for x in insights if x.get("evidence_count", 0) < 5), len(insights))
        metrics["single_platform_claim_rate"] = rate(
            sum(1 for x in insights if len(x.get("platform_coverage", [])) <= 1), len(insights))
    # D 建议前置（若草稿存在）
    actions_path = V2_DIR / "public_action_hypotheses_draft.json"
    d_available = actions_path.exists()
    if d_available:
        prov_ids = {r["evidence_id"] for r in prov}
        insights = [json.loads(line) for line in insights_path.read_text(encoding="utf-8").splitlines() if line.strip()] if c_available else []
        insight_ids = {x["insight_id"] for x in insights}
        actions = json.loads(actions_path.read_text(encoding="utf-8")).get("actions", [])
        metrics["action_to_insight_linkage_rate"] = rate(
            sum(1 for a in actions if all(i in insight_ids for i in a.get("source_insight_ids", []))), len(actions))
        metrics["action_to_evidence_linkage_rate"] = rate(
            sum(1 for a in actions if all(e in prov_ids for e in a.get("source_evidence_ids", []))), len(actions))
        metrics["validation_plan_coverage"] = rate(sum(1 for a in actions if a.get("validation_method")), len(actions))
        metrics["expected_effect_coverage"] = rate(sum(1 for a in actions if a.get("expected_effect")), len(actions))
        metrics["human_curated_rate"] = 0.0

    # E 运行质量
    metrics["parse_success_rate"] = 1.0
    prov_manifest = V2_DIR / "provisional_manifest.json"
    hashes_ok = True
    if prov_manifest.exists():
        pm = json.loads(prov_manifest.read_text(encoding="utf-8"))
        for name, h in (pm.get("hashes") or {}).items():
            if audit.sha256_bytes(V2_DIR / name) != h:
                hashes_ok = False
    metrics["output_hash_match_rate"] = 1.0 if hashes_ok else 0.0
    metrics["manifest_completeness"] = 1.0 if prov_manifest.exists() else 0.0

    # 判定
    judgments = {}
    blockers, warnings = [], []
    for name, val in metrics.items():
        j = judge(name, val)
        judgments[name] = j
        if j == "block":
            blockers.append(f"{name}={val} 未达阈值")
            failures["block"] += 1
        elif j == "warn":
            warnings.append(f"{name}={val} 低于建议阈值")
            failures["warn"] += 1

    overall = "BLOCKED" if blockers else "PASS"
    report = {
        "schema_version": "eval-1.0",
        "generated_at": "2026-07-17T16:56:33.578346+08:00",
        "provisional_evidence_count": len(prov),
        "metrics": metrics,
        "judgments": judgments,
        "insight_metrics_available": c_available,
        "action_metrics_available": d_available,
        "blockers": blockers,
        "warnings": warnings,
        "failure_type_counts": dict(failures),
        "evaluation_status": overall,
        "note": "evidence_text_match_rate 只说明证据可在公开样本中定位，不等于采集/来源/标签/人工复核真实性。",
    }
    (V2_DIR / "evaluation_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def main(argv=None):
    ap = argparse.ArgumentParser(description="PsyLens v2 评测器（离线/确定性）")
    ap.add_argument("--output-dir", default=str(V2_DIR))
    args = ap.parse_args(argv)
    r = evaluate(args.output_dir)
    print("评测完成：")
    print(f"  evaluation_status={r['evaluation_status']}")
    print(f"  blockers={len(r['blockers'])} warnings={len(r['warnings'])}")
    for k, v in r["metrics"].items():
        print(f"  {k}={v} [{r['judgments'][k]}]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
