#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""构建 provisional 三平台证据层（离线、确定性）。

输出：
  data/v2/evidence_candidates_v2.csv   全部候选（695 迁移 + 279 B 站规则基线提案 + 2 歧义状态）
  data/v2/evidence_provisional_v2.csv  临时证据（695 + B 站 include=yes；uncertain 单独标记；不含 2 歧义）
  data/v2/evidence_exclusion_log.csv   排除记录（B 站 no/uncertain、2 歧义）
  data/v2/provisional_manifest.json    provisional 状态与哈希

原则：
  - unit_text 不修改；
  - label_source ∈ {legacy_ai, rule_based_proposal}；
  - review_status ∈ {legacy_ai_label_unreviewed, rule_based_proposed_unreviewed}；不得出现 human_* / verified / approved；
  - 2 条 unresolved 歧义证据不进入 provisional；
  - 相同输入产生相同输出。
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TOOLS_DIR.parent
V2_DIR = REPO_ROOT / "data" / "v2"

_spec = importlib.util.spec_from_file_location("audit_public_data", TOOLS_DIR / "audit_public_data.py")
audit = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(audit)

CANDIDATE_COLS = ["candidate_id", "source_kind", "evidence_id", "sample_id", "platform_source",
                  "unit_text", "surface_topic", "mechanism_label", "label_source",
                  "include_as_evidence", "review_status", "notes"]

PROVISIONAL_COLS = ["evidence_id", "sample_id", "platform_source", "unit_index", "unit_text",
                    "surface_topic", "mechanism_label", "evidence_phrase", "label_source",
                    "proposal_confidence", "review_status", "analysis_inclusion_status",
                    "legacy_evidence_id", "queue_id", "notes"]

EXCLUSION_COLS = ["excluded_id", "source_kind", "sample_id", "platform_source", "unit_text",
                  "exclusion_reason", "recoverable", "notes"]


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(output_dir, generated_at, source_data_commit, input_dir=None):
    output_dir = Path(output_dir)
    input_dir = Path(input_dir) if input_dir else V2_DIR
    _, samples = audit.read_csv_rows(input_dir / "samples_v2.csv")
    _, evidence = audit.read_csv_rows(input_dir / "evidence_v2.csv")
    _, proposals = audit.read_csv_rows(input_dir / "rule_based_label_proposals.csv")
    _, ambiguous = audit.read_csv_rows(input_dir / "ambiguous_evidence_queue.csv")
    sample_by_id = {r["sample_id"]: r for r in samples}

    candidates = []
    provisional = []
    exclusions = []

    # 1) 695 条迁移 legacy 证据
    for e in evidence:
        sid = e["sample_id"]
        platform = sample_by_id.get(sid, {}).get("platform_source", "")
        candidates.append({
            "candidate_id": e["evidence_id"], "source_kind": "legacy_migrated",
            "evidence_id": e["evidence_id"], "sample_id": sid, "platform_source": platform,
            "unit_text": e["unit_text"], "surface_topic": e.get("surface_topic_legacy", ""),
            "mechanism_label": e.get("mechanism_label_legacy", ""), "label_source": "legacy_ai",
            "include_as_evidence": "yes", "review_status": "legacy_ai_label_unreviewed",
            "notes": "legacy 迁移证据",
        })
        provisional.append({
            "evidence_id": e["evidence_id"], "sample_id": sid, "platform_source": platform,
            "unit_index": e.get("unit_index", ""), "unit_text": e["unit_text"],
            "surface_topic": e.get("surface_topic_legacy", ""),
            "mechanism_label": e.get("mechanism_label_legacy", ""),
            "evidence_phrase": e.get("evidence_phrase", ""), "label_source": "legacy_ai",
            "proposal_confidence": e.get("confidence_legacy", ""),
            "review_status": "legacy_ai_label_unreviewed",
            "analysis_inclusion_status": "included",
            "legacy_evidence_id": e.get("legacy_evidence_id", ""), "queue_id": "",
            "notes": "legacy AI 标签未人工复核",
        })

    # 2) 279 B 站提案：yes -> provisional included；uncertain -> provisional included_flagged；no -> 排除
    bili_evidence_seq = {}
    for p in proposals:
        sid = p["sample_id"]
        platform = sample_by_id.get(sid, {}).get("platform_source", "Bili")
        inc = p["include_as_evidence"]
        candidates.append({
            "candidate_id": p["proposal_id"], "source_kind": "bili_rule_based_proposal",
            "evidence_id": "", "sample_id": sid, "platform_source": platform,
            "unit_text": p["candidate_unit_text"], "surface_topic": p.get("surface_topic_proposed", ""),
            "mechanism_label": p.get("mechanism_label_proposed", ""), "label_source": "rule_based_proposal",
            "include_as_evidence": inc, "review_status": "rule_based_proposed_unreviewed",
            "notes": p.get("proposal_reason", ""),
        })
        if inc == "no":
            exclusions.append({
                "excluded_id": p["proposal_id"], "source_kind": "bili_rule_based_proposal",
                "sample_id": sid, "platform_source": platform, "unit_text": p["candidate_unit_text"],
                "exclusion_reason": "规则基线提案 include_as_evidence=no（过短/上下文依赖/无机制指向）",
                "recoverable": "yes", "notes": p.get("proposal_reason", ""),
            })
            continue
        # yes 或 uncertain 进入 provisional，分配 B 站 evidence_id
        n = bili_evidence_seq.get(sid, 0) + 1
        bili_evidence_seq[sid] = n
        ev_id = f"{sid}_U{n:02d}"
        analysis_status = "included" if inc == "yes" else "included_flagged_uncertain"
        provisional.append({
            "evidence_id": ev_id, "sample_id": sid, "platform_source": platform,
            "unit_index": n, "unit_text": p["candidate_unit_text"],
            "surface_topic": p.get("surface_topic_proposed", ""),
            "mechanism_label": p.get("mechanism_label_proposed", ""),
            "evidence_phrase": p.get("evidence_phrase_proposed", ""), "label_source": "rule_based_proposal",
            "proposal_confidence": p.get("proposal_confidence", ""),
            "review_status": "rule_based_proposed_unreviewed",
            "analysis_inclusion_status": analysis_status,
            "legacy_evidence_id": "", "queue_id": p.get("queue_id", ""),
            "notes": "B 站离线规则基线提案，未人工复核" + ("；uncertain 单独标记" if inc == "uncertain" else ""),
        })
        if inc == "uncertain":
            exclusions.append({
                "excluded_id": ev_id, "source_kind": "bili_rule_based_proposal_uncertain",
                "sample_id": sid, "platform_source": platform, "unit_text": p["candidate_unit_text"],
                "exclusion_reason": "规则基线提案 include_as_evidence=uncertain（默认不计入正式分析分子，单独标记）",
                "recoverable": "yes", "notes": "保留在 provisional 但 analysis_inclusion_status=included_flagged_uncertain",
            })

    # 3) 2 条 unresolved 歧义证据：仅记录状态，不进入 provisional
    for a in ambiguous:
        candidates.append({
            "candidate_id": a["legacy_evidence_id"], "source_kind": "ambiguous_unresolved",
            "evidence_id": "", "sample_id": "", "platform_source": "",
            "unit_text": a["unit_text"], "surface_topic": "", "mechanism_label": "",
            "label_source": "legacy_ai", "include_as_evidence": "pending",
            "review_status": "pending_human_resolution",
            "notes": f"候选数 {a.get('candidate_count','')}，来源不确定",
        })
        exclusions.append({
            "excluded_id": a["legacy_evidence_id"], "source_kind": "ambiguous_unresolved",
            "sample_id": "", "platform_source": "|".join(a.get("candidate_platforms", "").split("|")),
            "unit_text": a["unit_text"],
            "exclusion_reason": "多候选未定案（pending_human_resolution），不进入 provisional",
            "recoverable": "yes", "notes": "见 docs/review/AMBIGUOUS_EVIDENCE_DECISION_PACKET.md",
        })

    _write(output_dir / "evidence_candidates_v2.csv", CANDIDATE_COLS, candidates)
    _write(output_dir / "evidence_provisional_v2.csv", PROVISIONAL_COLS, provisional)
    _write(output_dir / "evidence_exclusion_log.csv", EXCLUSION_COLS, exclusions)

    # provisional 平台分布
    from collections import Counter
    plat_dist = Counter(r["platform_source"] for r in provisional)
    incl_dist = Counter(r["analysis_inclusion_status"] for r in provisional)
    label_src = Counter(r["label_source"] for r in provisional)

    manifest = {
        "schema_version": "provisional-1.0",
        "generated_at": generated_at,
        "source_data_commit": source_data_commit,
        "candidate_count": len(candidates),
        "provisional_evidence_count": len(provisional),
        "exclusion_count": len(exclusions),
        "platform_distribution": dict(plat_dist),
        "analysis_inclusion_distribution": dict(incl_dist),
        "label_source_distribution": dict(label_src),
        "review_status_note": "全部为 legacy_ai_label_unreviewed 或 rule_based_proposed_unreviewed；无人工复核",
        "hashes": {},
        "limitations": [
            "provisional 证据含 legacy AI 标签与 B 站离线规则基线提案，均未人工复核",
            "uncertain 的 B 站提案以 included_flagged_uncertain 单独标记，默认不计入正式分子",
            "2 条歧义证据未进入 provisional",
            "结构化洞察与行动建议为草稿，默认不公开",
        ],
    }
    for name in ["evidence_candidates_v2.csv", "evidence_provisional_v2.csv", "evidence_exclusion_log.csv"]:
        manifest["hashes"][name] = sha256_file(output_dir / name)
    (output_dir / "provisional_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


def _write(path: Path, cols, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in cols})


def main(argv=None):
    ap = argparse.ArgumentParser(description="构建 provisional 三平台证据层（离线/确定性）")
    ap.add_argument("--input-dir", default=str(V2_DIR))
    ap.add_argument("--output-dir", default=str(V2_DIR))
    ap.add_argument("--generated-at", default="2026-07-17T16:56:33.578346+08:00")
    ap.add_argument("--source-data-commit", default="371d245a0ce82ed5d980472147b49568525e2986")
    args = ap.parse_args(argv)
    m = build(args.output_dir, args.generated_at, args.source_data_commit, input_dir=args.input_dir)
    print("provisional 证据层生成完成：")
    print(f"  candidates={m['candidate_count']} provisional={m['provisional_evidence_count']} "
          f"exclusions={m['exclusion_count']}")
    print(f"  platform={m['platform_distribution']}")
    print(f"  inclusion={m['analysis_inclusion_distribution']}")
    print(f"  label_source={m['label_source_distribution']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
