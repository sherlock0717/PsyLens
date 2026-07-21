#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""汇总多代理复检结果，输出共识与争议分析（离线、确定性）。

共识只作为自动校准参考，不是最终正确答案，也不覆盖公开数据的现有标签。
多数一致的标签不会被直接写成真值；三路分歧和边界冲突进入争议队列，供后续
人工裁决。

用法：
    python tools/calibration/build_agent_consensus.py \
        --input-dir artifacts/calibration/mock_reviews \
        --output-dir artifacts/calibration/mock_consensus

输出：
    consensus_reference.csv    每条证据的三路标签、共识与一致程度
    disagreement_queue.csv     需要裁决的争议项
    calibration_report.json    统计结果
    calibration_report.md      统计结果 + 普通中文解释
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TOOLS_DIR.parent.parent
CALIBRATION_VERSION = "calibration-1.1"
MECHS = ["competence_frustration", "fairness_threat", "trust_communication_gap",
         "belonging_drop", "norm_safety_risk", "uncertain"]

CONSENSUS_FIELDS = ["source_evidence_id", "reviewer_a_topic", "reviewer_b_topic",
                    "reviewer_c_topic", "consensus_topic", "reviewer_a_mechanism",
                    "reviewer_b_mechanism", "reviewer_c_mechanism", "consensus_mechanism",
                    "agreement_level", "topic_entropy", "mechanism_entropy",
                    "boundary_agreement", "needs_adjudication", "calibration_version"]


def _read_jsonl(path):
    p = Path(path)
    if not p.exists():
        return []
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]


def _read_csv(path):
    p = Path(path)
    if not p.exists():
        return []
    with p.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def entropy(labels):
    """标签分布的香农熵（bits）。0 表示完全一致，越大表示越分散。"""
    n = len(labels)
    if n == 0:
        return 0.0
    counts = Counter(labels)
    h = -sum((c / n) * math.log2(c / n) for c in counts.values())
    return round(h, 4)


def agreement_of(labels):
    counts = Counter(labels)
    top = counts.most_common(1)[0][1]
    if top == 3:
        return "unanimous", counts.most_common(1)[0][0]
    if top == 2:
        return "majority", counts.most_common(1)[0][0]
    return "disputed", ""


def fleiss_kappa(items_label_lists):
    """items_label_lists：每项一个长度为 3 的标签列表。返回 Fleiss' Kappa。"""
    n_raters = 3
    valid = [x for x in items_label_lists if len(x) == n_raters]
    N = len(valid)
    if N == 0:
        return None
    cats = MECHS
    p_j = {c: 0 for c in cats}
    P_sum = 0.0
    for labels in valid:
        counts = Counter(labels)
        for c in cats:
            p_j[c] += counts.get(c, 0)
        s = sum(counts.get(c, 0) ** 2 for c in cats)
        P_i = (s - n_raters) / (n_raters * (n_raters - 1))
        P_sum += P_i
    for c in cats:
        p_j[c] /= (N * n_raters)
    P_bar = P_sum / N
    P_e = sum(v ** 2 for v in p_j.values())
    if abs(1 - P_e) < 1e-12:
        return 1.0
    return round((P_bar - P_e) / (1 - P_e), 4)


def build_consensus(reviews_by_reviewer, sample_rows, private_rows):
    # blinded_item_id -> reviewer -> row
    by_blinded = defaultdict(dict)
    for rid, rows in reviews_by_reviewer.items():
        for r in rows:
            by_blinded[r.get("blinded_item_id", r.get("evidence_id"))][rid] = r

    sample_map = {r["blinded_item_id"]: r for r in sample_rows}
    private_map = {r["blinded_item_id"]: r for r in private_rows}

    main_blinded = [b for b, s in sample_map.items() if s.get("is_retest") == "false"] or list(by_blinded)
    consensus_rows = []
    mech_label_lists = []

    for blinded in sorted(main_blinded):
        per = by_blinded.get(blinded, {})
        if not all(k in per for k in ("a", "b", "c")):
            continue
        topics = [per[r]["surface_topic"] for r in ("a", "b", "c")]
        mechs = [per[r]["mechanism_label"] for r in ("a", "b", "c")]
        bounds = [per[r]["boundary_status"] for r in ("a", "b", "c")]
        mech_label_lists.append(mechs)

        m_level, m_top = agreement_of(mechs)
        _t_level, t_top = agreement_of(topics)
        boundary_conflict = ("not_evidence" in bounds) and any(b != "not_evidence" for b in bounds)
        boundary_agreement = "agree" if len(set(bounds)) == 1 else "disagree"

        level = "boundary_disputed" if boundary_conflict and m_level != "unanimous" else m_level
        consensus_mech = m_top if m_level in ("unanimous", "majority") else ""
        consensus_topic = t_top if _t_level in ("unanimous", "majority") else ""
        needs_adj = level != "unanimous"

        src = sample_map.get(blinded, {}).get("source_evidence_id", per["a"].get("evidence_id", ""))
        consensus_rows.append({
            "source_evidence_id": src,
            "reviewer_a_topic": topics[0], "reviewer_b_topic": topics[1], "reviewer_c_topic": topics[2],
            "consensus_topic": consensus_topic,
            "reviewer_a_mechanism": mechs[0], "reviewer_b_mechanism": mechs[1],
            "reviewer_c_mechanism": mechs[2], "consensus_mechanism": consensus_mech,
            "agreement_level": level,
            "topic_entropy": entropy(topics), "mechanism_entropy": entropy(mechs),
            "boundary_agreement": boundary_agreement,
            "needs_adjudication": "yes" if needs_adj else "no",
            "calibration_version": CALIBRATION_VERSION,
        })

    stats = _compute_stats(consensus_rows, mech_label_lists, by_blinded, sample_map, private_map,
                           reviews_by_reviewer)
    return consensus_rows, stats


def _compute_stats(rows, mech_label_lists, by_blinded, sample_map, private_map, reviews_by_reviewer):
    n = len(rows)
    levels = Counter(r["agreement_level"] for r in rows)
    unanimous = levels.get("unanimous", 0)
    majority = levels.get("majority", 0)
    disputed = levels.get("disputed", 0) + levels.get("boundary_disputed", 0)

    def pair_rate(i, j):
        match = sum(1 for m in mech_label_lists if m[i] == m[j])
        return {"rate": round(match / len(mech_label_lists), 4) if mech_label_lists else None,
                "numerator": match, "denominator": len(mech_label_lists)}

    mech_dispute = sum(1 for r in rows if r["agreement_level"] in ("disputed", "boundary_disputed"))
    topic_dispute = sum(1 for r in rows if r["reviewer_a_topic"] != r["reviewer_b_topic"]
                        or r["reviewer_b_topic"] != r["reviewer_c_topic"])
    boundary_dispute = sum(1 for r in rows if r["boundary_agreement"] == "disagree")

    # 每个机制标签的一致率（在多数标签为该标签的项中，全一致占比）
    per_label = {}
    for lab in MECHS:
        subset = [r for r in rows if r["consensus_mechanism"] == lab]
        unan = sum(1 for r in subset if r["agreement_level"] == "unanimous")
        per_label[lab] = {"consensus_count": len(subset),
                          "unanimous_rate": round(unan / len(subset), 4) if subset else None}

    # uncertain 转移（需私有当前标签）
    transitions = None
    confusion = None
    if private_map:
        cur_by_src = {}
        for b, pr in private_map.items():
            if pr.get("is_retest") == "false":
                cur_by_src[pr["source_evidence_id"]] = pr.get("current_mechanism_label", "")
        cur_uncertain = concrete = u2c = c2u = 0
        conf = defaultdict(Counter)
        for r in rows:
            cur = cur_by_src.get(r["source_evidence_id"], "")
            cons = r["consensus_mechanism"] or "no_consensus"
            if not cur:
                continue
            conf[cur][cons] += 1
            if cur == "uncertain":
                cur_uncertain += 1
                if cons not in ("uncertain", "no_consensus"):
                    u2c += 1
            else:
                concrete += 1
                if cons == "uncertain":
                    c2u += 1
        transitions = {
            "current_uncertain_count": cur_uncertain,
            "uncertain_retained_rate": round((cur_uncertain - u2c) / cur_uncertain, 4) if cur_uncertain else None,
            "uncertain_to_concrete_rate": round(u2c / cur_uncertain, 4) if cur_uncertain else None,
            "current_concrete_count": concrete,
            "concrete_to_uncertain_rate": round(c2u / concrete, 4) if concrete else None,
        }
        confusion = {k: dict(v) for k, v in conf.items()}

    # 重测一致率：同一 reviewer 在主项与重测项上的机制是否一致
    retest_groups = defaultdict(dict)  # group -> reviewer -> [labels]
    for b, s in sample_map.items():
        grp = s.get("retest_group_id", "")
        if not grp:
            continue
        for rid, rows_r in reviews_by_reviewer.items():
            row = next((x for x in rows_r if x.get("blinded_item_id") == b), None)
            if row:
                retest_groups[grp].setdefault(rid, []).append(row["mechanism_label"])
    rt_total = rt_match = 0
    for grp, per in retest_groups.items():
        for rid, labs in per.items():
            if len(labs) == 2:
                rt_total += 1
                if labs[0] == labs[1]:
                    rt_match += 1
    retest = {"rate": round(rt_match / rt_total, 4) if rt_total else None,
              "numerator": rt_match, "denominator": rt_total}

    # 高争议标签对
    pair_counter = Counter()
    for m in mech_label_lists:
        distinct = sorted(set(m))
        for a in range(len(distinct)):
            for b in range(a + 1, len(distinct)):
                pair_counter[f"{distinct[a]} | {distinct[b]}"] += 1
    high_dispute_pairs = pair_counter.most_common(5)

    return {
        "item_count": n,
        "three_way_agreement": {"rate": round(unanimous / n, 4) if n else None,
                                "numerator": unanimous, "denominator": n},
        "majority_agreement": {"rate": round((unanimous + majority) / n, 4) if n else None,
                               "numerator": unanimous + majority, "denominator": n},
        "disputed": {"rate": round(disputed / n, 4) if n else None,
                     "numerator": disputed, "denominator": n},
        "pairwise_agreement": {"a_b": pair_rate(0, 1), "a_c": pair_rate(0, 2), "b_c": pair_rate(1, 2)},
        "topic_dispute": {"rate": round(topic_dispute / n, 4) if n else None,
                          "numerator": topic_dispute, "denominator": n},
        "mechanism_dispute": {"rate": round(mech_dispute / n, 4) if n else None,
                              "numerator": mech_dispute, "denominator": n},
        "boundary_dispute": {"rate": round(boundary_dispute / n, 4) if n else None,
                             "numerator": boundary_dispute, "denominator": n},
        "per_label_agreement": per_label,
        "label_transitions": transitions,
        "confusion_current_vs_consensus": confusion,
        "retest_consistency": retest,
        "high_dispute_label_pairs": [{"pair": p, "count": c} for p, c in high_dispute_pairs],
        "fleiss_kappa_mechanism": fleiss_kappa(mech_label_lists),
        "note": "共识为自动校准参考，不是人工金标准，也不覆盖公开数据现有标签。",
    }


def render_report_md(stats):
    def rate(d):
        if not d or d.get("rate") is None:
            return "n/a"
        return f"{d['rate'] * 100:.1f}%（{d['numerator']}/{d['denominator']}）"

    lines = ["# 自动校准共识报告", "",
             "本报告汇总三个独立代理对分层证据的复检结果。共识只作为自动校准参考，"
             "用于发现稳定结果和争议案例，不是人工金标准。", "",
             f"- 参与统计的证据：{stats['item_count']} 条", "",
             "## 一致程度", "",
             f"- 三路完全一致：{rate(stats['three_way_agreement'])}。三名代理给出相同机制标签的比例。",
             f"- 多数一致（含完全一致）：{rate(stats['majority_agreement'])}。至少两名代理一致的比例。",
             f"- 存在分歧：{rate(stats['disputed'])}。三路不同或边界判断冲突，进入争议队列。", "",
             "## 两两一致率", "",
             f"- A 与 B：{rate(stats['pairwise_agreement']['a_b'])}",
             f"- A 与 C：{rate(stats['pairwise_agreement']['a_c'])}",
             f"- B 与 C：{rate(stats['pairwise_agreement']['b_c'])}", "",
             "## 争议分布", "",
             f"- 机制争议率：{rate(stats['mechanism_dispute'])}",
             f"- 话题争议率：{rate(stats['topic_dispute'])}",
             f"- 边界争议率：{rate(stats['boundary_dispute'])}", ""]
    k = stats.get("fleiss_kappa_mechanism")
    lines += ["## 一致性系数", "",
              f"- Fleiss' Kappa（机制）：{k if k is not None else 'n/a'}。"
              "Fleiss' Kappa 用来衡量三个代理的一致程度，并扣除随机碰巧一致的部分；"
              "数值越接近 1 表示一致性越强，接近 0 表示与随机一致相当。", ""]
    rt = stats.get("retest_consistency")
    lines += ["## 重测稳定性", "",
              f"- 重测一致率：{rate(rt)}。同一代理在重复出现的相同证据上给出相同机制标签的比例，"
              "用来观察判断是否稳定。", ""]
    lines += ["## 高争议标签对", ""]
    for item in stats.get("high_dispute_label_pairs", []):
        lines.append(f"- {item['pair']}：在 {item['count']} 条证据中同时出现，是重点区分对象。")
    tr = stats.get("label_transitions")
    if tr:
        lines += ["", "## 不确定标签的流向", "",
                  f"- 当前 uncertain 证据：{tr['current_uncertain_count']} 条。",
                  f"- 仍保持 uncertain 的比例：{tr['uncertain_retained_rate']}。",
                  f"- 由 uncertain 转为具体机制的比例：{tr['uncertain_to_concrete_rate']}。",
                  f"- 由具体机制转为 uncertain 的比例：{tr['concrete_to_uncertain_rate']}。"]
    lines += ["", "> 说明：以上结果用于发现稳定结论和需要重点核对的标签，"
              "不作为最终正确答案，也不修改公开数据的现有标签。"]
    return "\n".join(lines) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description="汇总多代理复检的共识与争议（共识为参考，非金标准）")
    ap.add_argument("--input-dir", default=str(REPO_ROOT / "artifacts" / "calibration" / "mock_reviews"))
    ap.add_argument("--output-dir", default=str(REPO_ROOT / "artifacts" / "calibration" / "mock_consensus"))
    ap.add_argument("--sample", default=str(REPO_ROOT / "data" / "calibration" / "calibration_sample.csv"))
    ap.add_argument("--private-key", default=str(REPO_ROOT / "artifacts" / "calibration" / "private_sampling_key.csv"))
    args = ap.parse_args(argv)

    input_dir = Path(args.input_dir)
    reviews = {rid: _read_jsonl(input_dir / f"agent_reviews_{rid}.jsonl") for rid in ("a", "b", "c")}
    sample_rows = _read_csv(args.sample)
    private_rows = _read_csv(args.private_key)

    rows, stats = build_consensus(reviews, sample_rows, private_rows)

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    with (out_dir / "consensus_reference.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CONSENSUS_FIELDS)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    with (out_dir / "disagreement_queue.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CONSENSUS_FIELDS)
        w.writeheader()
        for r in rows:
            if r["needs_adjudication"] == "yes":
                w.writerow(r)
    (out_dir / "calibration_report.json").write_text(
        json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "calibration_report.md").write_text(render_report_md(stats), encoding="utf-8")

    print("共识分析完成：")
    print(f"  item_count={stats['item_count']}")
    tw = stats["three_way_agreement"]
    print(f"  three_way_agreement={tw['numerator']}/{tw['denominator']}")
    print(f"  output_path={out_dir}")
    print("  next_action=运行 analyze_disagreements.py 生成争议明细")
    return 0


if __name__ == "__main__":
    sys.exit(main())
