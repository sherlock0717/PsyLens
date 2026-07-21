#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""分析争议项并生成 Codebook 改进建议（离线、确定性）。

读取共识结果，汇总争议分布与高争议标签对，并按固定相邻标签对给出可读的区分
规则建议。建议只是提案，不直接修改正式 Codebook，也不把共识写成正确答案。

用法：
    python tools/calibration/analyze_disagreements.py \
        --input artifacts/calibration/mock_consensus/consensus_reference.csv \
        --output artifacts/calibration/mock_consensus/disagreement_report.md
"""
from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TOOLS_DIR.parent.parent

# 固定的相邻标签对与普通中文区分规则（提案，不直接改 Codebook）
LABEL_PAIRS = [
    ("competence_frustration", "fairness_threat",
     "文本重点在“我难以发挥作用”时偏向胜任受挫；重点在“规则或分配本身不合理”时偏向公平受损。"),
    ("fairness_threat", "trust_communication_gap",
     "重点在“分配或匹配结果不公”偏向公平受损；重点在“官方说明与回应不足”偏向信任与沟通落差。"),
    ("trust_communication_gap", "belonging_drop",
     "重点在“沟通与解释缺位”偏向信任落差；重点在“想离开、疏远社区”偏向归属感下降。"),
    ("belonging_drop", "norm_safety_risk",
     "重点在“情感疏离与退出”偏向归属下降；涉及外挂、辱骂、误封等秩序问题偏向规范与安全风险。"),
    ("concrete_label", "uncertain",
     "证据能明确指向某一体验方向时给具体标签；文本过短、依赖上下文或多义并存时保留 uncertain。"),
]


def _read_csv(path):
    with Path(path).open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _mechs(row):
    return [row["reviewer_a_mechanism"], row["reviewer_b_mechanism"], row["reviewer_c_mechanism"]]


def analyze(rows, text_by_src=None):
    text_by_src = text_by_src or {}
    levels = Counter(r["agreement_level"] for r in rows)
    disputed = [r for r in rows if r["needs_adjudication"] == "yes"]

    pair_counter = Counter()
    for r in rows:
        distinct = sorted(set(_mechs(r)))
        for i in range(len(distinct)):
            for j in range(i + 1, len(distinct)):
                pair_counter[(distinct[i], distinct[j])] += 1

    proposals = []
    for a, b, rule in LABEL_PAIRS:
        if b == "uncertain" and a == "concrete_label":
            matched = [r for r in rows if ("uncertain" in _mechs(r)) and any(
                m != "uncertain" for m in _mechs(r))]
        else:
            matched = [r for r in rows if a in _mechs(r) and b in _mechs(r)]
        agree_ex, dispute_ex = [], []
        for r in matched:
            src = r["source_evidence_id"]
            ex = {"source_evidence_id": src, "text": text_by_src.get(src, ""),
                  "mechs": _mechs(r), "agreement_level": r["agreement_level"]}
            if r["agreement_level"] == "unanimous":
                agree_ex.append(ex)
            else:
                dispute_ex.append(ex)
        proposals.append({
            "label_pair": f"{a} vs {b}",
            "problem_pattern": "两个相邻标签在同批证据中同时出现，需明确区分边界。",
            "sample_count": len(matched),
            "agree_examples": agree_ex[:2],
            "dispute_examples": dispute_ex[:2],
            "current_rule": "当前 Codebook 主要按关键词与体验方向区分，边界样本仍有分歧。",
            "proposed_rule": rule,
            "expected_effect": "减少相邻标签互混，提升三路一致率。",
            "possible_side_effect": "可能将部分模糊样本更多推向 uncertain，需观察不确定率变化。",
            "review_priority": "high" if len(matched) >= 5 else "medium",
        })
    return levels, disputed, pair_counter, proposals


def render_disagreement_md(levels, disputed, pair_counter, rows):
    n = len(rows)
    lines = ["# 争议明细报告", "",
             f"- 参与统计的证据：{n} 条",
             f"- 需要裁决的争议项：{len(disputed)} 条", "",
             "## 一致程度分布", ""]
    for lv, c in levels.most_common():
        lines.append(f"- {lv}：{c} 条")
    lines += ["", "## 高争议标签对（同一证据中同时出现）", ""]
    for (a, b), c in pair_counter.most_common(8):
        if a == b:
            continue
        lines.append(f"- {a} | {b}：{c} 条")
    lines += ["", "## 争议样本示例", ""]
    for r in disputed[:10]:
        lines.append(f"- {r['source_evidence_id']}：A={r['reviewer_a_mechanism']}、"
                     f"B={r['reviewer_b_mechanism']}、C={r['reviewer_c_mechanism']}"
                     f"（{r['agreement_level']}）")
    lines += ["", "> 说明：争议项进入后续裁决，不直接写成正确答案。"]
    return "\n".join(lines) + "\n"


def render_codebook_md(proposals):
    lines = ["# Codebook 改进建议（提案）", "",
             "本文件是自动校准发现的相邻标签区分提案，不直接修改正式 Codebook。"
             "每条建议给出问题模式、样本数、示例、当前规则、建议规则、预期效果与可能副作用。", ""]
    for p in proposals:
        lines += [f"## {p['label_pair']}", "",
                  f"- 问题模式：{p['problem_pattern']}",
                  f"- 相关样本数：{p['sample_count']}",
                  f"- 当前规则：{p['current_rule']}",
                  f"- 建议规则：{p['proposed_rule']}",
                  f"- 预期效果：{p['expected_effect']}",
                  f"- 可能副作用：{p['possible_side_effect']}",
                  f"- 处理优先级：{p['review_priority']}", "",
                  "一致案例："]
        if p["agree_examples"]:
            for ex in p["agree_examples"]:
                lines.append(f"- {ex['source_evidence_id']}：{ex['text'][:40]}")
        else:
            lines.append("- （本批 mock 数据中该对一致案例不足，待真实运行补充）")
        lines.append("争议案例：")
        if p["dispute_examples"]:
            for ex in p["dispute_examples"]:
                lines.append(f"- {ex['source_evidence_id']}：{ex['text'][:40]}（{'/'.join(ex['mechs'])}）")
        else:
            lines.append("- （本批 mock 数据中该对争议案例不足，待真实运行补充）")
        lines.append("")
    return "\n".join(lines) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description="分析争议项并生成 Codebook 改进建议（提案，不改正式 Codebook）")
    ap.add_argument("--input", default=str(REPO_ROOT / "artifacts" / "calibration" / "mock_consensus" / "consensus_reference.csv"))
    ap.add_argument("--output", default=str(REPO_ROOT / "artifacts" / "calibration" / "mock_consensus" / "disagreement_report.md"))
    ap.add_argument("--sample", default=str(REPO_ROOT / "data" / "calibration" / "calibration_sample.csv"))
    ap.add_argument("--codebook-output", default=str(REPO_ROOT / "artifacts" / "calibration" / "codebook_revision_proposals.md"))
    args = ap.parse_args(argv)

    rows = _read_csv(args.input)
    text_by_src = {}
    if Path(args.sample).exists():
        for s in _read_csv(args.sample):
            text_by_src[s.get("source_evidence_id", "")] = s.get("public_evidence_text", "")

    levels, disputed, pair_counter, proposals = analyze(rows, text_by_src)

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(render_disagreement_md(levels, disputed, pair_counter, rows), encoding="utf-8")
    Path(args.codebook_output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.codebook_output).write_text(render_codebook_md(proposals), encoding="utf-8")

    print("争议分析完成：")
    print(f"  disputed_count={len(disputed)}")
    print(f"  disagreement_report={args.output}")
    print(f"  codebook_proposals={args.codebook_output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
