# -*- coding: utf-8 -*-
"""Demo 评测打分：对 Demo 产物计算与主评测器同构的简化指标。"""
from __future__ import annotations

from . import validators


def evaluate(evidence, insights, actions, samples_by_id):
    n_ev = len(evidence)
    ev_ids = [e["evidence_id"] for e in evidence]
    prov_ids = set(ev_ids)
    insight_ids = {x["insight_id"] for x in insights}

    loc = sum(1 for e in evidence
              if validators.evidence_locatable(e["unit_text"], samples_by_id.get(e["sample_id"], {}).get("raw_text", "")))
    invalid = sum(1 for e in evidence if not validators.label_valid(e.get("mechanism_label", "")))

    def rate(a, b):
        return round(a / b, 4) if b else 1.0

    metrics = {
        "evidence_id_unique_rate": rate(len(set(ev_ids)), n_ev),
        "evidence_text_match_rate": rate(loc, n_ev),
        "invalid_label_rate": rate(invalid, n_ev),
        "insight_support_resolution_rate": rate(
            sum(1 for x in insights if validators.ids_resolvable(x["source_evidence_ids"], prov_ids)), len(insights)) if insights else 1.0,
        "action_to_insight_linkage_rate": rate(
            sum(1 for a in actions if validators.ids_resolvable(a["source_insight_ids"], insight_ids)), len(actions)) if actions else 1.0,
        "action_to_evidence_linkage_rate": rate(
            sum(1 for a in actions if validators.ids_resolvable(a["source_evidence_ids"], prov_ids)), len(actions)) if actions else 1.0,
    }
    blockers = []
    if metrics["evidence_text_match_rate"] < 0.98:
        blockers.append("evidence_text_match_rate 低于阈值")
    if metrics["invalid_label_rate"] > 0.0:
        blockers.append("存在非法标签")
    if metrics["insight_support_resolution_rate"] < 1.0:
        blockers.append("洞察引用无法全部解析")
    metrics["_status"] = "BLOCKED" if blockers else "PASS"
    metrics["_blockers"] = blockers
    return metrics
