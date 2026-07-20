#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""重建草稿结构化洞察（离线、确定性）。

按 (surface_topic, mechanism_label) 聚合 provisional 证据（analysis_inclusion_status=included，
即不含 uncertain flagged、不含 2 条歧义），形成草稿"结构化洞察"。

输出：
  data/v2/structured_insights_draft.jsonl
  data/v2/insight_evaluation.json

规则：
  - 至少 5 条有效证据 -> 高支持洞察（其余仍生成但标 low_support）；
  - 单平台洞察必须标明 single_platform；
  - 不把相关性表述为因果；不把置信度写成证据强度；不隐藏 uncertain；
  - 所有 source_evidence_ids 必须存在于 provisional 证据；
  - author_type=agent_compiled，review_status=agent_compiled_draft，publication_status=hidden_pending_review。
禁用词：validated insights / 已验证洞察 / 可直接采信。统一称"结构化洞察"。
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from collections import defaultdict
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TOOLS_DIR.parent
V2_DIR = REPO_ROOT / "data" / "v2"

_spec = importlib.util.spec_from_file_location("audit_public_data", TOOLS_DIR / "audit_public_data.py")
audit = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(audit)

MIN_HIGH_SUPPORT = 5

TOPIC_CN = {
    "balance": "平衡与数值", "matchmaking": "匹配与对局分配", "rewards": "奖励与产出",
    "progression": "成长与养成", "communication_transparency": "沟通与透明度",
    "community_conflict": "社区冲突与氛围", "event_design": "活动与玩法设计",
    "new_player_onboarding": "新手引导与体验", "other_uncertain": "其他",
}
MECH_CN = {
    "competence_frustration": "能力挫败", "fairness_threat": "公平受损",
    "trust_communication_gap": "信任与沟通落差", "belonging_drop": "归属感下降",
    "norm_safety_risk": "规范与安全风险", "uncertain": "机制不确定",
}


def build(output_dir=None):
    output_dir = Path(output_dir) if output_dir else V2_DIR
    _, samples = audit.read_csv_rows(V2_DIR / "samples_v2.csv")
    _, prov = audit.read_csv_rows(V2_DIR / "evidence_provisional_v2.csv")
    win_by_sample = {r["sample_id"]: r.get("window_tag", "") for r in samples}

    # 仅纳入 included（不含 uncertain flagged），且机制非 uncertain/空
    groups = defaultdict(list)
    for r in prov:
        if r.get("analysis_inclusion_status") != "included":
            continue
        mech = (r.get("mechanism_label", "") or "").strip()
        topic = (r.get("surface_topic", "") or "").strip()
        if mech in ("", "uncertain", "unassigned"):
            continue
        if not topic:
            continue
        groups[(topic, mech)].append(r)

    insights = []
    idx = 0
    for (topic, mech), rows in sorted(groups.items(), key=lambda x: (-len(x[1]), x[0])):
        idx += 1
        iid = f"INSIGHT_{idx:03d}"
        platforms = sorted({x["platform_source"] for x in rows})
        windows = sorted({win_by_sample.get(x["sample_id"], "") for x in rows if win_by_sample.get(x["sample_id"], "")})
        ev_ids = [x["evidence_id"] for x in rows]
        count = len(rows)
        single = len(platforms) <= 1
        topic_cn = TOPIC_CN.get(topic, topic)
        mech_cn = MECH_CN.get(mech, mech)
        support_level = "high_support" if count >= MIN_HIGH_SUPPORT else "low_support"
        statement = (f"在「{topic_cn}」话题上，有 {count} 条证据指向「{mech_cn}」机制"
                     f"（覆盖平台：{'、'.join(platforms)}）。"
                     + ("该洞察当前仅由单一平台证据支撑，不代表跨平台共识。" if single
                        else "该洞察由多个平台证据共同出现，但仍为草稿、未经人工复核。"))
        insights.append({
            "insight_id": iid,
            "title": f"{topic_cn} × {mech_cn}",
            "statement": statement,
            "surface_topic": topic,
            "mechanism_label": mech,
            "source_evidence_ids": ev_ids,
            "evidence_count": count,
            "platform_coverage": platforms,
            "time_window_coverage": windows,
            "support_level": support_level,
            "support_summary": f"{count} 条 provisional 证据（含 legacy AI 标签与 B 站离线规则基线提案，均未人工复核）",
            "counter_evidence": "未系统检索反例；相关性不代表因果",
            "limitations": "草稿建立在 legacy AI 标签与 B 站离线规则基线提案之上，未经人工复核；机制为共现统计而非因果；uncertain 证据未纳入本条",
            "author_type": "agent_compiled",
            "review_status": "agent_compiled_draft",
            "publication_status": "hidden_pending_review",
            "single_platform": single,
        })

    # 写 JSONL
    (output_dir / "structured_insights_draft.jsonl").write_text(
        "\n".join(json.dumps(x, ensure_ascii=False) for x in insights) + "\n", encoding="utf-8")

    # 评测：引用可解析、平台覆盖等
    prov_ids = {r["evidence_id"] for r in prov}
    resolved = sum(1 for x in insights if all(e in prov_ids for e in x["source_evidence_ids"]))
    high = [x for x in insights if x["support_level"] == "high_support"]
    single_cnt = sum(1 for x in insights if x["single_platform"])
    ev = {
        "schema_version": "insight-eval-1.0",
        "total_insights": len(insights),
        "high_support_insights": len(high),
        "low_support_insights": len(insights) - len(high),
        "support_resolution_rate": round(resolved / len(insights), 4) if insights else 1.0,
        "single_platform_insights": single_cnt,
        "single_platform_rate": round(single_cnt / len(insights), 4) if insights else 0.0,
        "note": "全部为 agent_compiled_draft，默认 hidden_pending_review；未人工复核。",
    }
    (output_dir / "insight_evaluation.json").write_text(
        json.dumps(ev, ensure_ascii=False, indent=2), encoding="utf-8")
    return insights, ev


def main(argv=None):
    ap = argparse.ArgumentParser(description="重建草稿结构化洞察（离线/确定性）")
    ap.add_argument("--output-dir", default=str(V2_DIR))
    args = ap.parse_args(argv)
    insights, ev = build(args.output_dir)
    print("草稿结构化洞察生成完成：")
    print(f"  total={ev['total_insights']} high_support={ev['high_support_insights']} "
          f"single_platform={ev['single_platform_insights']}")
    print(f"  support_resolution_rate={ev['support_resolution_rate']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
