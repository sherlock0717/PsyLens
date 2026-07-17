#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""重建可追溯草稿产品假设（离线、确定性）。

从高支持结构化洞察生成"待验证产品假设"草稿，每条可回到洞察与证据。

输出：
  data/v2/public_action_hypotheses_draft.json
  data/v2/action_evaluation.json

规则：
  - source_insight_ids / source_evidence_ids 全部存在；
  - 每条有 expected_effect / validation_method / 可衡量 success_metric；
  - 不使用"应该立即实施"，使用"待验证产品假设"；
  - author_type=agent_compiled，review_status=agent_compiled_draft，publication_status=hidden_pending_review。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
V2_DIR = REPO_ROOT / "data" / "v2"

# 机制 -> 通用干预方向模板（保守、待验证；不下达执行指令）
MECH_ACTION = {
    "competence_frustration": (
        "针对能力挫败：评估是否存在难度/投入回报失衡，考虑分层难度或进度补偿的待验证方案",
        "目标群体的挫败类反馈占比下降、留存/完成率上升",
        "选取相关任务/对局做 A/B，对照组与实验组比较完成率与挫败类反馈占比"),
    "fairness_threat": (
        "针对公平受损：核查被质疑的机制/数值是否存在系统性偏向，评估透明化或平衡调整的待验证方案",
        "公平质疑类反馈占比下降、对局结果分布更均衡",
        "调整前后对比公平质疑反馈占比与结果分布指标"),
    "trust_communication_gap": (
        "针对信任与沟通落差：评估更主动的公告/回应机制的待验证方案",
        "沟通类负面反馈占比下降、官方回应触达率上升",
        "对比机制上线前后沟通类反馈占比与回应触达率"),
    "belonging_drop": (
        "针对归属感下降：评估社区关怀/老玩家回流的待验证方案",
        "退坑/疏离类表达占比下降、回流率上升",
        "对比干预前后疏离类表达占比与回流率"),
    "norm_safety_risk": (
        "针对规范与安全风险：评估举报处置时效与外挂/骚扰治理的待验证方案",
        "安全类反馈占比下降、举报处置时效提升",
        "对比治理前后安全类反馈占比与处置时效"),
}


def build(output_dir=None):
    output_dir = Path(output_dir) if output_dir else V2_DIR
    insights = [json.loads(l) for l in (V2_DIR / "structured_insights_draft.jsonl").read_text(
        encoding="utf-8").splitlines() if l.strip()]
    # 取高支持洞察，按证据数降序，最多 6 条生成建议
    high = sorted([x for x in insights if x["support_level"] == "high_support"],
                  key=lambda x: (-x["evidence_count"], x["insight_id"]))[:6]

    actions = []
    for i, ins in enumerate(high, 1):
        mech = ins["mechanism_label"]
        tmpl = MECH_ACTION.get(mech)
        if not tmpl:
            continue
        summary, effect, method = tmpl
        ev_sample = ins["source_evidence_ids"][:5]  # 取前 5 条作为引用样本
        actions.append({
            "action_id": f"ACTION_{i:03d}",
            "title": f"{ins['title']} 待验证产品假设",
            "summary": summary,
            "source_insight_ids": [ins["insight_id"]],
            "source_evidence_ids": ev_sample,
            "evidence_summary": f"基于结构化洞察 {ins['insight_id']}（{ins['evidence_count']} 条证据，"
                                f"平台 {'、'.join(ins['platform_coverage'])}）",
            "expected_effect": effect,
            "validation_method": method,
            "success_metric": effect,  # 可衡量指标与预期效果对应
            "risk": "样本为公开社区反馈、非随机抽样；标签未人工复核；结论为草稿假设",
            "priority_basis": f"支撑证据数 {ins['evidence_count']}，"
                              + ("单平台" if ins["single_platform"] else "多平台"),
            "author_type": "agent_compiled",
            "review_status": "agent_compiled_draft",
            "publication_status": "hidden_pending_review",
        })

    payload = {
        "schema_version": "action-draft-1.0",
        "note": "待验证产品假设草稿；author_type=agent_compiled；默认 hidden_pending_review；未人工整理/复核。",
        "actions": actions,
    }
    (output_dir / "public_action_hypotheses_draft.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    # 评测
    insight_ids = {x["insight_id"] for x in insights}
    prov = (V2_DIR / "evidence_provisional_v2.csv").read_text(encoding="utf-8-sig").splitlines()
    prov_ids = {line.split(",")[0] for line in prov[1:]}
    n = len(actions)
    ev = {
        "schema_version": "action-eval-1.0",
        "total_actions": n,
        "action_to_insight_linkage_rate": round(
            sum(1 for a in actions if all(i in insight_ids for i in a["source_insight_ids"])) / n, 4) if n else 1.0,
        "action_to_evidence_linkage_rate": round(
            sum(1 for a in actions if all(e in prov_ids for e in a["source_evidence_ids"])) / n, 4) if n else 1.0,
        "validation_plan_coverage": round(sum(1 for a in actions if a["validation_method"]) / n, 4) if n else 1.0,
        "expected_effect_coverage": round(sum(1 for a in actions if a["expected_effect"]) / n, 4) if n else 1.0,
        "human_curated_rate": 0.0,
        "note": "全部为草稿，未人工整理。",
    }
    (output_dir / "action_evaluation.json").write_text(
        json.dumps(ev, ensure_ascii=False, indent=2), encoding="utf-8")
    return actions, ev


def main(argv=None):
    ap = argparse.ArgumentParser(description="重建可追溯草稿产品假设（离线/确定性）")
    ap.add_argument("--output-dir", default=str(V2_DIR))
    args = ap.parse_args(argv)
    actions, ev = build(args.output_dir)
    print("草稿产品假设生成完成：")
    print(f"  total_actions={ev['total_actions']}")
    print(f"  insight_linkage={ev['action_to_insight_linkage_rate']} "
          f"evidence_linkage={ev['action_to_evidence_linkage_rate']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
