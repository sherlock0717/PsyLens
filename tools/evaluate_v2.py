#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PsyLens v2 评测器（离线、确定性）。

从 --input-dir 读取 provisional 证据层、草稿洞察/建议、人工复核日志与 manifest，
真实计算 A~E 五组指标（每个指标记录 value / numerator / denominator / status /
plain_explanation），将 evaluation_report.json 写入 --output-dir。

不联网、不调用模型；相同输入产生相同输出。阈值内嵌（与 evaluation/thresholds.yaml 一致）。

状态拆分为四项（不再输出单一裸露 evaluation_status）：
  structural_integrity_status  结构完整性（编号/文本/编码/manifest/哈希/可重复）
  label_review_status          标签人工复核（当前 NOT_STARTED）
  insight_draft_status         草稿洞察（DRAFT / NOT_AVAILABLE）
  release_readiness_status     发布就绪（PENDING_REVIEW）
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import tempfile
from collections import Counter
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TOOLS_DIR.parent
V2_DIR = REPO_ROOT / "data" / "v2"

_spec = importlib.util.spec_from_file_location("audit_public_data", TOOLS_DIR / "audit_public_data.py")
audit = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(audit)

_pspec = importlib.util.spec_from_file_location(
    "build_provisional_evidence", TOOLS_DIR / "build_provisional_evidence.py")
build_prov = importlib.util.module_from_spec(_pspec)
_pspec.loader.exec_module(build_prov)

ALLOWED_MECH = {"competence_frustration", "fairness_threat", "trust_communication_gap",
                "belonging_drop", "norm_safety_risk", "uncertain"}

# 阈值（与 evaluation/thresholds.yaml 一致）；(kind, value, level)
THRESHOLDS = {
    "sample_id_unique_rate": ("min", 1.0, "block"),
    "evidence_id_unique_rate": ("min", 1.0, "block"),
    "parent_reference_exists_rate": ("min", 1.0, "warn"),
    "evidence_text_match_rate": ("min", 0.98, "block"),
    "source_url_coverage": ("min", 0.0, "warn"),
    "platform_sample_coverage": ("min", 3, "warn"),
    "label_completion_rate": ("min", 0.30, "warn"),
    "uncertain_rate": ("max", 0.75, "warn"),
    "invalid_label_rate": ("max", 0.0, "block"),
    "evidence_phrase_match_rate": ("min", 0.98, "block"),
    "rule_based_proposal_coverage": ("min", 1.0, "block"),
    "support_resolution_rate": ("min", 1.0, "block"),
    "platform_coverage": ("min", 1.0, "warn"),
    "time_window_coverage": ("min", 1.0, "warn"),
    "low_support_claim_rate": ("max", 0.5, "warn"),
    "single_platform_claim_rate": ("max", 1.0, "warn"),
    "action_to_insight_linkage_rate": ("min", 1.0, "block"),
    "action_to_evidence_linkage_rate": ("min", 1.0, "block"),
    "validation_plan_coverage": ("min", 1.0, "warn"),
    "expected_effect_coverage": ("min", 1.0, "warn"),
    "parse_success_rate": ("min", 1.0, "block"),
    "stage_completion_rate": ("min", 1.0, "warn"),
    "repeatability_rate": ("min", 1.0, "warn"),
    "manifest_completeness": ("min", 1.0, "warn"),
    "output_hash_match_rate": ("min", 1.0, "block"),
}

# 结构完整性状态所依赖的指标
STRUCTURAL_METRICS = [
    "sample_id_unique_rate", "evidence_id_unique_rate", "parent_reference_exists_rate",
    "evidence_text_match_rate", "platform_sample_coverage", "invalid_label_rate",
    "evidence_phrase_match_rate", "rule_based_proposal_coverage", "parse_success_rate",
    "stage_completion_rate", "repeatability_rate", "manifest_completeness", "output_hash_match_rate",
]

# provisional 流水线计划阶段（用于 stage_completion_rate）
PLANNED_STAGES = [
    ("samples", "samples_v2.csv"),
    ("evidence_migration", "evidence_v2.csv"),
    ("rule_based_proposals", "rule_based_label_proposals.csv"),
    ("provisional_evidence", "evidence_provisional_v2.csv"),
    ("draft_insights", "structured_insights_draft.jsonl"),
    ("draft_actions", "public_action_hypotheses_draft.json"),
    ("provisional_manifest", "provisional_manifest.json"),
]

MANIFEST_REQUIRED_FIELDS = [
    "schema_version", "generated_at", "source_data_commit", "candidate_count",
    "provisional_evidence_count", "exclusion_count", "platform_distribution",
    "analysis_inclusion_distribution", "label_source_distribution", "hashes", "limitations",
]


def rate(num, den):
    return round(num / den, 4) if den else None


def judge(name, value):
    if name not in THRESHOLDS or value is None:
        return "n/a"
    kind, thr, level = THRESHOLDS[name]
    ok = value >= thr if kind == "min" else value <= thr
    return "pass" if ok else level


def _metric(value, numerator, denominator, plain, name=None, status=None):
    return {
        "value": value,
        "numerator": numerator,
        "denominator": denominator,
        "status": status if status is not None else judge(name, value),
        "plain_explanation": plain,
    }


def _read_jsonl(path):
    if not path.exists():
        return []
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


def _compute_repeatability(input_dir):
    """在两个临时目录各运行一次 provisional 生成流程，比较 3 个产物哈希。

    读取的输入来自 evaluator 实际传入的 ``input_dir``（而非仓库固定 data/v2），
    因此临时目录篡改测试可验证对应输入的可重复性。
    """
    names = ["evidence_candidates_v2.csv", "evidence_provisional_v2.csv", "evidence_exclusion_log.csv"]
    ga = "2026-07-17T16:56:33.578346+08:00"
    commit = "371d245a0ce82ed5d980472147b49568525e2986"
    try:
        with tempfile.TemporaryDirectory() as t1, tempfile.TemporaryDirectory() as t2:
            build_prov.build(Path(t1), ga, commit, input_dir=input_dir)
            build_prov.build(Path(t2), ga, commit, input_dir=input_dir)
            match = sum(1 for n in names
                        if audit.sha256_bytes(Path(t1) / n) == audit.sha256_bytes(Path(t2) / n))
    except Exception:
        return 0, len(names)
    return match, len(names)


def evaluate(input_dir=None, output_dir=None):
    input_dir = Path(input_dir) if input_dir else V2_DIR
    output_dir = Path(output_dir) if output_dir else input_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    metrics = {}
    parse_ok = 0
    parse_total = 0
    parse_errors = []

    def try_read_csv(name):
        nonlocal parse_ok, parse_total
        parse_total += 1
        try:
            _, rows = audit.read_csv_rows(input_dir / name)
            parse_ok += 1
            return rows
        except Exception as e:  # noqa: BLE001
            parse_errors.append(f"{name}: {e}")
            return []

    def try_read_json(name, default):
        nonlocal parse_ok, parse_total
        parse_total += 1
        p = input_dir / name
        try:
            data = json.loads(p.read_text(encoding="utf-8")) if p.exists() else default
            parse_ok += 1
            return data
        except Exception as e:  # noqa: BLE001
            parse_errors.append(f"{name}: {e}")
            return default

    samples = try_read_csv("samples_v2.csv")
    _ = try_read_csv("evidence_v2.csv")
    prov = try_read_csv("evidence_provisional_v2.csv")
    bili = try_read_csv("bili_evidence_queue.csv")
    proposals = try_read_csv("rule_based_label_proposals.csv")
    _ = try_read_csv("ambiguous_evidence_queue.csv")
    prov_manifest = try_read_json("provisional_manifest.json", {})
    sample_raw = {r["sample_id"]: r.get("raw_text", "") for r in samples}
    sample_ids_set = {r["sample_id"] for r in samples}

    # ---- A 数据完整性 ----
    sids = [r["sample_id"] for r in samples]
    metrics["sample_id_unique_rate"] = _metric(
        rate(len(set(sids)), len(sids)), len(set(sids)), len(sids),
        "每条反馈都有唯一编号", "sample_id_unique_rate")
    ev_ids = [r["evidence_id"] for r in prov]
    metrics["evidence_id_unique_rate"] = _metric(
        rate(len(set(ev_ids)), len(ev_ids)), len(set(ev_ids)), len(ev_ids),
        "每条证据都有唯一编号", "evidence_id_unique_rate")
    parent_ok = sum(1 for r in prov if r.get("sample_id") in sample_ids_set)
    metrics["parent_reference_exists_rate"] = _metric(
        rate(parent_ok, len(prov)), parent_ok, len(prov),
        "每条证据都指向一个真实存在的原始反馈", "parent_reference_exists_rate")
    loc = sum(1 for r in prov
              if audit.normalize_text(r.get("unit_text", "")) and
              audit.normalize_text(r.get("unit_text", "")) in audit.normalize_text(sample_raw.get(r.get("sample_id"), "")))
    metrics["evidence_text_match_rate"] = _metric(
        rate(loc, len(prov)), loc, len(prov),
        "每条展示证据都能回到对应的原始反馈", "evidence_text_match_rate")
    url_cov = sum(1 for r in samples if (r.get("source_url", "") or "").strip())
    metrics["source_url_coverage"] = _metric(
        rate(url_cov, len(samples)), url_cov, len(samples),
        "内部样本来源字段的非空率（仅字段存在性，不代表可追溯真实性；公开层不含来源字段）",
        "source_url_coverage")
    n_plat = len({r["platform_source"] for r in samples})
    metrics["platform_sample_coverage"] = _metric(
        n_plat, n_plat, 3, "覆盖的平台数", "platform_sample_coverage")

    # ---- B 编码质量 ----
    has_label = sum(1 for r in prov if (r.get("mechanism_label", "") or "").strip() not in ("", "unassigned"))
    metrics["label_completion_rate"] = _metric(
        rate(has_label, len(prov)), has_label, len(prov),
        "有多少证据被打上了机制标签（含不确定）", "label_completion_rate")
    unc = sum(1 for r in prov if r.get("mechanism_label") == "uncertain")
    metrics["uncertain_rate"] = _metric(
        rate(unc, len(prov)), unc, len(prov),
        "有多少证据的机制暂时判不准", "uncertain_rate")
    invalid = sum(1 for r in prov if (r.get("mechanism_label", "") or "").strip()
                  not in (ALLOWED_MECH | {"", "unassigned"}))
    metrics["invalid_label_rate"] = _metric(
        rate(invalid, len(prov)), invalid, len(prov),
        "有没有出现规范外的标签（应为 0）", "invalid_label_rate")
    with_phrase = [r for r in prov if (r.get("evidence_phrase", "") or "").strip()]
    phrase_ok = sum(1 for r in with_phrase
                    if audit.normalize_text(r["evidence_phrase"]) in audit.normalize_text(r.get("unit_text", "")))
    metrics["evidence_phrase_match_rate"] = _metric(
        rate(phrase_ok, len(with_phrase)), phrase_ok, len(with_phrase),
        "标注依据短语能否在证据文本中找到", "evidence_phrase_match_rate")
    metrics["rule_based_proposal_coverage"] = _metric(
        rate(len(proposals), len(bili)), len(proposals), len(bili),
        "B 站候选是否都给出了离线规则基线提案", "rule_based_proposal_coverage")

    # 人工复核：真实读取 human_review_log.csv
    human_rows = try_read_csv("human_review_log.csv")
    human_reviews = [r for r in human_rows if r.get("reviewer_type") == "human"
                     and (r.get("review_status", "") or "").strip()]
    reviewed_entities = {r.get("entity_id") for r in human_reviews if r.get("entity_id")}
    review_denominator = len(prov)
    metrics["human_review_coverage"] = _metric(
        rate(len(reviewed_entities), review_denominator), len(reviewed_entities), review_denominator,
        "有多少证据经过真人复核（当前为 0）", "human_review_coverage",
        status="not_started" if not human_reviews else judge("human_review_coverage",
                                                             rate(len(reviewed_entities), review_denominator)))
    overrides = sum(1 for r in human_reviews
                    if (r.get("final_label", "") or "") and r.get("final_label") != r.get("proposed_label"))
    if human_reviews:
        metrics["human_override_rate"] = _metric(
            rate(overrides, len(human_reviews)), overrides, len(human_reviews),
            "真人复核后改动了多少标签", "human_override_rate")
    else:
        metrics["human_override_rate"] = _metric(
            None, 0, 0, "尚无真人复核，人工推翻率不适用（n/a）", status="n/a")

    # ---- C 洞察前置 ----
    insights = _read_jsonl(input_dir / "structured_insights_draft.jsonl")
    c_available = bool(insights)
    prov_ids = {r["evidence_id"] for r in prov}
    if c_available:
        resolved = sum(1 for x in insights if all(sid in prov_ids for sid in x.get("source_evidence_ids", [])))
        metrics["support_resolution_rate"] = _metric(
            rate(resolved, len(insights)), resolved, len(insights),
            "每条洞察引用的证据是否都真实存在", "support_resolution_rate")
        plat_sum = sum(len(x.get("platform_coverage", [])) for x in insights)
        metrics["platform_coverage"] = _metric(
            rate(plat_sum, len(insights)), plat_sum, len(insights),
            "洞察平均由几个平台的证据支撑", "platform_coverage")
        win_sum = sum(len(x.get("time_window_coverage", [])) for x in insights)
        metrics["time_window_coverage"] = _metric(
            rate(win_sum, len(insights)), win_sum, len(insights),
            "洞察平均跨几个时间段", "time_window_coverage")
        low = sum(1 for x in insights if x.get("evidence_count", 0) < 5)
        metrics["low_support_claim_rate"] = _metric(
            rate(low, len(insights)), low, len(insights),
            "有多少洞察证据偏少", "low_support_claim_rate")
        singl = sum(1 for x in insights if len(x.get("platform_coverage", [])) <= 1)
        metrics["single_platform_claim_rate"] = _metric(
            rate(singl, len(insights)), singl, len(insights),
            "有多少洞察只来自一个平台", "single_platform_claim_rate")

    # ---- D 建议前置 ----
    actions_doc = try_read_json("public_action_hypotheses_draft.json", {})
    actions = (actions_doc or {}).get("actions", [])
    d_available = bool(actions)
    if d_available:
        insight_ids = {x.get("insight_id") for x in insights}
        a_ins = sum(1 for a in actions if all(i in insight_ids for i in a.get("source_insight_ids", [])))
        metrics["action_to_insight_linkage_rate"] = _metric(
            rate(a_ins, len(actions)), a_ins, len(actions),
            "每条建议能否回到具体洞察", "action_to_insight_linkage_rate")
        a_ev = sum(1 for a in actions if all(e in prov_ids for e in a.get("source_evidence_ids", [])))
        metrics["action_to_evidence_linkage_rate"] = _metric(
            rate(a_ev, len(actions)), a_ev, len(actions),
            "每条建议能否回到具体证据", "action_to_evidence_linkage_rate")
        vm = sum(1 for a in actions if a.get("validation_method"))
        metrics["validation_plan_coverage"] = _metric(
            rate(vm, len(actions)), vm, len(actions),
            "每条建议是否给了验证办法", "validation_plan_coverage")
        ee = sum(1 for a in actions if a.get("expected_effect"))
        metrics["expected_effect_coverage"] = _metric(
            rate(ee, len(actions)), ee, len(actions),
            "每条建议是否写了预期效果", "expected_effect_coverage")

    # ---- E 运行质量 ----
    metrics["parse_success_rate"] = _metric(
        rate(parse_ok, parse_total), parse_ok, parse_total,
        "目标数据文件是否都能正常读取", "parse_success_rate")
    completed = sum(1 for _, fn in PLANNED_STAGES if (input_dir / fn).exists()
                    and (input_dir / fn).stat().st_size > 0)
    metrics["stage_completion_rate"] = _metric(
        rate(completed, len(PLANNED_STAGES)), completed, len(PLANNED_STAGES),
        "分析流程走完了多少步", "stage_completion_rate")
    rep_ok, rep_total = _compute_repeatability(input_dir)
    metrics["repeatability_rate"] = _metric(
        rate(rep_ok, rep_total), rep_ok, rep_total,
        "同样的输入是否每次都得到同样的结果", "repeatability_rate")
    present_fields = sum(1 for f in MANIFEST_REQUIRED_FIELDS
                         if f in (prov_manifest or {}) and (prov_manifest.get(f) not in (None, "", [], {})))
    metrics["manifest_completeness"] = _metric(
        rate(present_fields, len(MANIFEST_REQUIRED_FIELDS)), present_fields, len(MANIFEST_REQUIRED_FIELDS),
        "运行记录（manifest）是否完整", "manifest_completeness")
    hashes = (prov_manifest or {}).get("hashes") or {}
    hash_match = sum(1 for name, h in hashes.items()
                     if (input_dir / name).exists() and audit.sha256_bytes(input_dir / name) == h)
    metrics["output_hash_match_rate"] = _metric(
        rate(hash_match, len(hashes)), hash_match, len(hashes),
        "产出文件有没有被意外改动", "output_hash_match_rate")

    # ---- 汇总失败类型 ----
    failures = Counter()
    blockers, warnings = [], []
    for name, mm in metrics.items():
        st = mm["status"]
        if st == "block":
            blockers.append(f"{name}={mm['value']} 未达阈值")
            failures["block"] += 1
        elif st == "warn":
            warnings.append(f"{name}={mm['value']} 低于建议阈值")
            failures["warn"] += 1
    if parse_errors:
        failures["parse_error"] += len(parse_errors)

    # ---- 状态拆分 ----
    structural_block = [n for n in STRUCTURAL_METRICS
                        if metrics.get(n, {}).get("status") == "block"]
    structural_integrity_status = "PASS" if not structural_block else "BLOCKED"
    label_review_status = "NOT_STARTED" if not human_reviews else "IN_PROGRESS"
    if c_available:
        insight_draft_status = "DRAFT"
    else:
        insight_draft_status = "NOT_AVAILABLE"
    # 发布就绪：草稿默认隐藏、无人工复核、歧义未定案 -> PENDING_REVIEW
    release_readiness_status = "PENDING_REVIEW"

    try:
        input_dir_label = input_dir.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        input_dir_label = input_dir.name
    report = {
        "schema_version": "eval-2.0",
        "generated_at": "2026-07-17T16:56:33.578346+08:00",
        "input_dir": input_dir_label,
        "provisional_evidence_count": len(prov),
        "insight_count": len(insights),
        "action_count": len(actions),
        "metrics": metrics,
        "insight_metrics_available": c_available,
        "action_metrics_available": d_available,
        "blockers": blockers,
        "warnings": warnings,
        "parse_errors": parse_errors,
        "failure_type_counts": dict(failures),
        "structural_integrity_status": structural_integrity_status,
        "label_review_status": label_review_status,
        "insight_draft_status": insight_draft_status,
        "release_readiness_status": release_readiness_status,
        "note": "evidence_text_match_rate 只说明证据可在公开样本中定位，不等于采集/来源/标签/人工复核真实性；"
                "标签均未经真人复核；结构化洞察与产品假设为草稿。",
    }
    (output_dir / "evaluation_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def main(argv=None):
    ap = argparse.ArgumentParser(description="PsyLens v2 评测器（离线/确定性）")
    ap.add_argument("--input-dir", default=str(V2_DIR))
    ap.add_argument("--output-dir", default=None)
    args = ap.parse_args(argv)
    r = evaluate(args.input_dir, args.output_dir)
    print("评测完成：")
    print(f"  structural_integrity_status={r['structural_integrity_status']}")
    print(f"  label_review_status={r['label_review_status']}")
    print(f"  insight_draft_status={r['insight_draft_status']}")
    print(f"  release_readiness_status={r['release_readiness_status']}")
    print(f"  blockers={len(r['blockers'])} warnings={len(r['warnings'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
