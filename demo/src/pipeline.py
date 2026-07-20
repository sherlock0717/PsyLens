# -*- coding: utf-8 -*-
"""Demo 离线流水线：脱敏输入 -> 候选证据拆分 -> 确定性 mock 标签 -> 草稿洞察 ->
草稿产品假设 -> 评测 -> 报告。默认离线、确定性；不联网、不读取密钥。"""
from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path

from . import report, scoring
from .providers import get_provider

SPLIT = re.compile(r"[。！？；\n]+|[.!?;]+")
MIN_UNIT_LEN = 6

MECH_CN = {
    "competence_frustration": "能力挫败", "fairness_threat": "公平受损",
    "trust_communication_gap": "信任与沟通落差", "belonging_drop": "归属感下降",
    "norm_safety_risk": "规范与安全风险", "uncertain": "机制不确定",
}


def _read_samples(input_path):
    with Path(input_path).open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _sha256(path: Path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(input_path, output_dir, provider_name="mock", min_high_support=1,
        generated_at="2026-07-17T16:56:33.578346+08:00", run_id="demo"):
    # 注：Demo 规模小，min_high_support 默认降为 1 仅用于演示完整链路；
    # 正式评测使用 evaluation/thresholds.yaml 的阈值。
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    samples = _read_samples(input_path)
    samples_by_id = {s["feedback_id"]: s for s in samples}
    provider = get_provider(provider_name)

    # 1) 候选证据拆分 + 2) 确定性 mock 标签
    evidence = []
    for s in samples:
        raw = s.get("raw_text", "")
        parts = [p.strip() for p in SPLIT.split(raw) if len(p.strip()) >= MIN_UNIT_LEN]
        for idx, seg in enumerate(parts, 1):
            lab = provider.label(seg)
            evidence.append({
                "evidence_id": f"{s['feedback_id']}_U{idx:02d}",
                "sample_id": s["feedback_id"],
                "platform_source": s.get("platform", ""),
                "window_tag": s.get("window_tag", ""),
                "unit_index": idx,
                "unit_text": seg,
                "surface_topic": lab["surface_topic"],
                "mechanism_label": lab["mechanism_label"],
                "label_source": f"demo_{provider_name}",
            })

    # 3) 草稿结构化洞察：按 (topic, mech) 聚合，mech!=uncertain
    groups = defaultdict(list)
    for e in evidence:
        if e["mechanism_label"] in ("", "uncertain", "unassigned") or not e["surface_topic"]:
            continue
        groups[(e["surface_topic"], e["mechanism_label"])].append(e)
    insights = []
    for i, ((topic, mech), rows) in enumerate(sorted(groups.items(), key=lambda x: (-len(x[1]), x[0])), 1):
        platforms = sorted({r["platform_source"] for r in rows})
        insights.append({
            "insight_id": f"DEMO_INSIGHT_{i:03d}",
            "title": f"{topic} × {MECH_CN.get(mech, mech)}",
            "mechanism_label": mech,
            "surface_topic": topic,
            "source_evidence_ids": [r["evidence_id"] for r in rows],
            "evidence_count": len(rows),
            "platform_coverage": platforms,
            "support_level": "high_support" if len(rows) >= min_high_support else "low_support",
            "single_platform": len(platforms) <= 1,
        })

    # 4) 草稿产品假设：高支持洞察 -> 假设
    actions = []
    high = [x for x in insights if x["support_level"] == "high_support"]
    for i, ins in enumerate(high, 1):
        actions.append({
            "action_id": f"DEMO_ACTION_{i:03d}",
            "title": f"{ins['title']} 待验证产品假设",
            "source_insight_ids": [ins["insight_id"]],
            "source_evidence_ids": ins["source_evidence_ids"][:3],
            "expected_effect": "相关负面反馈占比下降（待验证）",
            "validation_method": "A/B 对照，比较干预前后该类反馈占比",
            "success_metric": "该类负面反馈占比",
        })

    # 5) 评测
    metrics = scoring.evaluate(evidence, insights, actions, samples_by_id)

    # 6) 输出
    input_snapshot = {"input": str(input_path), "provider": provider_name,
                      "sample_count": len(samples), "generated_at": generated_at,
                      "samples": samples}
    (output_dir / "input_snapshot.json").write_text(report.dumps(input_snapshot), encoding="utf-8")
    (output_dir / "evidence.jsonl").write_text(
        "\n".join(json.dumps(e, ensure_ascii=False) for e in evidence) + "\n", encoding="utf-8")
    (output_dir / "insights.jsonl").write_text(
        "\n".join(json.dumps(x, ensure_ascii=False) for x in insights) + "\n", encoding="utf-8")
    (output_dir / "actions.json").write_text(report.dumps({"actions": actions}), encoding="utf-8")
    (output_dir / "evaluation.json").write_text(report.dumps(metrics), encoding="utf-8")
    (output_dir / "report.md").write_text(
        report.render_markdown(run_id, evidence, insights, actions, metrics), encoding="utf-8")
    (output_dir / "report.html").write_text(
        report.render_html(run_id, evidence, insights, actions, metrics), encoding="utf-8")

    # manifest（含产物哈希，供确定性校验）
    manifest = {
        "run_id": run_id, "generated_at": generated_at, "provider": provider_name,
        "offline": True, "sample_count": len(samples), "evidence_count": len(evidence),
        "insight_count": len(insights), "action_count": len(actions),
        "evaluation_status": metrics["_status"], "hashes": {},
    }
    for name in ["input_snapshot.json", "evidence.jsonl", "insights.jsonl",
                 "actions.json", "evaluation.json", "report.md", "report.html"]:
        manifest["hashes"][name] = _sha256(output_dir / name)
    (output_dir / "manifest.json").write_text(report.dumps(manifest), encoding="utf-8")
    return manifest
