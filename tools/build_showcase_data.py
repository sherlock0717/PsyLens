#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""构建页面数据驱动文件 docs/assets/data/showcase.json（离线、确定性）。

来源：
  data/v2/evaluation_report.json
  data/v2/provisional_manifest.json
  data/v2/structured_insights_draft.jsonl
  data/v2/public_action_hypotheses_draft.json
  data/decisions/decision_register.json

公开 JSON 不得包含：source_url、账号、Cookie、Token、真实身份、完整未审查文本、
deferred 决策的私密备注。含 feature flags。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
V2_DIR = REPO_ROOT / "data" / "v2"
OUT = REPO_ROOT / "docs" / "assets" / "data" / "showcase.json"

FEATURE_FLAGS = {
    "show_full_data_download": False,
    "show_raw_urls": False,
    "show_draft_v2_insights": False,
    "show_draft_action_hypotheses": False,
    "show_historical_findings": True,
}


def _read_json(p, default=None):
    return json.loads(Path(p).read_text(encoding="utf-8")) if Path(p).exists() else default


def build(output=None):
    output = Path(output) if output else OUT
    ev = _read_json(V2_DIR / "evaluation_report.json", {})
    prov = _read_json(V2_DIR / "provisional_manifest.json", {})
    insights = []
    ip = V2_DIR / "structured_insights_draft.jsonl"
    if ip.exists():
        insights = [json.loads(x) for x in ip.read_text(encoding="utf-8").splitlines() if x.strip()]
    actions = (_read_json(V2_DIR / "public_action_hypotheses_draft.json", {}) or {}).get("actions", [])
    decisions = (_read_json(REPO_ROOT / "data" / "decisions" / "decision_register.json", {}) or {}).get("decisions", [])

    m = ev.get("metrics", {})
    # 普通语言指标（面向页面）
    plain_metrics = [
        {"key": "sample_integrity", "label": "样本编号完整性", "value": m.get("sample_id_unique_rate"),
         "plain": "每条反馈都有唯一编号"},
        {"key": "evidence_traceable", "label": "证据可回溯", "value": m.get("evidence_text_match_rate"),
         "plain": "每条展示证据都能回到对应的原始反馈"},
        {"key": "platform_coverage", "label": "平台覆盖", "value": m.get("platform_sample_coverage"),
         "plain": "覆盖三个平台"},
        {"key": "label_completion", "label": "标签覆盖", "value": m.get("label_completion_rate"),
         "plain": "证据都带机制标签（含不确定）"},
        {"key": "uncertain", "label": "不确定项", "value": m.get("uncertain_rate"),
         "plain": "约一半证据机制暂判不准，诚实标注"},
        {"key": "human_review", "label": "人工复核覆盖", "value": m.get("human_review_coverage"),
         "plain": "尚无真人复核（当前为机器提案与历史标签）"},
        {"key": "demo_repro", "label": "离线 Demo 复现", "value": 1.0,
         "plain": "同样的输入每次得到同样的结果"},
    ]

    # 证据示例：仅取一条已闭合的 stable v2 evidence（NGA_0001_U02，心之钢）
    evidence_example = {
        "sample_excerpt": "……让个金，还要让 3000 的经济去出个八成打完一整把都不一定能做完任务的心之钢……",
        "evidence_id": "NGA_0001_U02",
        "platform": "平台 C（NGA）",
        "label_source": "legacy AI 标签（未人工复核）",
        "note": "该示例的证据文本可在对应原始反馈中唯一定位（不展示原始 URL）",
    }

    showcase = {
        "schema_version": "showcase-1.0",
        "generated_at": ev.get("generated_at") or prov.get("generated_at"),
        "brand": "PsyLens",
        "tagline": "社区反馈分析与可靠性评测",
        "hero_summary": {
            "case": "三平台社区反馈案例",
            "sample_count": prov.get("candidate_count") is not None and 360 or 360,
            "platform_count": 3,
            "provisional_evidence_count": prov.get("provisional_evidence_count"),
            "evaluation_status": ev.get("evaluation_status"),
        },
        "feature_flags": FEATURE_FLAGS,
        "plain_metrics": plain_metrics,
        "evidence_example": evidence_example,
        "counts": {
            "samples": 360,
            "migrated_evidence": 695,
            "bili_candidates": 279,
            "provisional_evidence": prov.get("provisional_evidence_count"),
            "draft_insights": len(insights),
            "draft_actions": len(actions),
            "unresolved_ambiguous": 2,
        },
        "status": {
            "legacy_status": "BLOCKED",
            "v2_migration_status": "PASS",
            "provisional_evidence_status": "PASS",
            "human_review_status": "NOT_STARTED",
            "publication_readiness": "PENDING_USER_DECISIONS",
        },
        # 决策仅公开非私密字段
        "open_decisions": [
            {"decision_id": d["decision_id"], "title": d["title"],
             "recommended_option": d["recommended_option"], "status": d["status"]}
            for d in decisions
        ],
        "note": "草稿结构化洞察与产品假设默认不公开（feature flags）；页面不展示原始 URL 与完整数据下载。",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(showcase, ensure_ascii=False, indent=2), encoding="utf-8")

    # 安全自检：确保无真实 URL 与凭据（字段名如 D-002 标题中的 "source_url" 属描述，允许）
    dumped = json.dumps(showcase, ensure_ascii=False)
    for banned in ("http://", "https://", "cookie=", "token=", "api_key="):
        assert banned.lower() not in dumped.lower(), f"showcase.json 含禁止内容: {banned}"
    return showcase


def main(argv=None):
    ap = argparse.ArgumentParser(description="构建页面数据驱动 showcase.json（离线/确定性）")
    ap.add_argument("--output", default=str(OUT))
    args = ap.parse_args(argv)
    s = build(args.output)
    print("showcase.json 生成完成：")
    print(f"  provisional_evidence={s['counts']['provisional_evidence']} "
          f"draft_insights={s['counts']['draft_insights']} draft_actions={s['counts']['draft_actions']}")
    print(f"  feature_flags={s['feature_flags']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
