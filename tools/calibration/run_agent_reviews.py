#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""多代理独立复检运行器（默认离线、确定性 mock）。

代理只获得盲测证据文本与可选父样本上下文，看不到当前标签、编码来源、平台
名称或其他代理的结果。若本地没有可用模型或 API，运行器生成确定性 mock 输出，
用于跑通 schema、解析和后续共识分析；此时不声称调用过真实模型，运行状态记为
READY_NOT_RUN。

用法：
    python tools/calibration/run_agent_reviews.py --dry-run \
        --input data/calibration/calibration_sample.csv --max-items 30

输出（默认写入 artifacts/calibration/mock_reviews）：
    agent_reviews_a.jsonl / agent_reviews_b.jsonl / agent_reviews_c.jsonl
    raw_model_responses/**（原始响应，gitignore）
    retry_queue.jsonl（解析失败项，不静默丢弃）
    run_report.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TOOLS_DIR.parent.parent
DEFAULT_OUTPUT = REPO_ROOT / "artifacts" / "calibration" / "mock_reviews"
PROMPT_DIR = REPO_ROOT / "config" / "calibration" / "prompts"

ALLOWED_MECH = ["competence_frustration", "fairness_threat", "trust_communication_gap",
                "belonging_drop", "norm_safety_risk", "uncertain"]
REQUIRED_FIELDS = ["run_id", "reviewer_id", "model_name", "prompt_version", "prompt_sha256",
                   "sample_id", "evidence_id", "evidence_text", "boundary_status",
                   "surface_topic", "mechanism_label", "evidence_phrase", "confidence_band",
                   "abstain_reason", "decision_basis", "created_at"]

# 关键词 -> 机制（简单启发式，仅用于 mock 判断，不代表真实模型能力）
MECH_KEYWORDS = [
    ("norm_safety_risk", ["外挂", "举报", "封号", "辱骂", "脚本", "挂机"]),
    ("trust_communication_gap", ["官方", "公告", "说明", "回应", "解释", "客服"]),
    ("belonging_drop", ["退游", "不想玩", "弃游", "离开", "失望", "退坑"]),
    ("fairness_threat", ["公平", "匹配", "连败", "连胜", "分配", "队友", "坑"]),
    ("competence_frustration", ["发挥", "打不", "做不", "输出", "伤害", "强度", "难"]),
]
TOPIC_KEYWORDS = [
    ("matchmaking", ["匹配", "连败", "连胜", "队友", "段位", "对局"]),
    ("balance", ["强度", "加强", "削弱", "数值", "平衡", "英雄", "装备", "机制"]),
    ("communication_transparency", ["官方", "公告", "说明", "回应"]),
]


def _sha256_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_prompt(reviewer_id, prompt_path):
    if prompt_path:
        p = Path(prompt_path)
    else:
        p = PROMPT_DIR / f"reviewer_{reviewer_id}.md"
    if p.exists():
        text = p.read_text(encoding="utf-8")
    else:
        text = f"# Reviewer {reviewer_id} (built-in)\nprompt_version: {reviewer_id}-1.0\n"
    version = f"{reviewer_id}-1.0"
    for line in text.splitlines():
        if line.strip().startswith("prompt_version:"):
            version = line.split(":", 1)[1].strip()
            break
    return text, version, _sha256_text(text)


def read_sample(path):
    import csv  # noqa: PLC0415
    with Path(path).open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def reviewer_input(rows):
    """构造盲测输入：只保留代理可见字段。"""
    return [{
        "blinded_item_id": r.get("blinded_item_id", ""),
        "public_evidence_text": r.get("public_evidence_text", ""),
        "parent_context": r.get("parent_context", ""),
        "context_available": r.get("context_available", "no"),
        # 以下仅供运行器回填溯源，不进入模型输入
        "_source_evidence_id": r.get("source_evidence_id", ""),
    } for r in rows]


def _base_mechanism(text):
    hits = [mech for mech, kws in MECH_KEYWORDS if any(k in text for k in kws)]
    return hits[0] if hits else "uncertain"


def _all_mechanism_hits(text):
    return [mech for mech, kws in MECH_KEYWORDS if any(k in text for k in kws)]


def _topic(text):
    for topic, kws in TOPIC_KEYWORDS:
        if any(k in text for k in kws):
            return topic
    return "other_uncertain"


def mock_review(item, reviewer_id, run_id, model_name, prompt_version, prompt_sha):
    """确定性 mock 判断，不同 reviewer 使用不同判断结构。"""
    text = item["public_evidence_text"] or ""
    hits = _all_mechanism_hits(text)
    base = hits[0] if hits else "uncertain"
    h = int(hashlib.sha256((reviewer_id + item["blinded_item_id"] + text).encode("utf-8")).hexdigest(), 16)
    short = len(text.strip()) < 12

    if reviewer_id == "a":  # 保守：证据不足倾向 uncertain
        mech = "uncertain" if (short or base == "uncertain" or h % 6 == 0) else base
    elif reviewer_id == "b":  # 主要诉求优先
        mech = base
    else:  # c：排除法，多命中时可能选相邻标签
        mech = hits[1] if len(hits) > 1 and h % 3 == 0 else base

    if mech == "uncertain":
        boundary = "needs_parent_context" if short else "complete"
        abstain = "insufficient_context" if short else "multiple_mechanisms"
        conf = "low"
    else:
        boundary = "complete"
        abstain = "none"
        conf = "high" if len(hits) == 1 else "medium"

    return {
        "run_id": run_id,
        "reviewer_id": reviewer_id,
        "blinded_item_id": item["blinded_item_id"],
        "model_name": model_name,
        "prompt_version": prompt_version,
        "prompt_sha256": prompt_sha,
        "sample_id": item["_source_evidence_id"].rsplit("_U", 1)[0] if "_U" in item["_source_evidence_id"] else "",
        "evidence_id": item["_source_evidence_id"],
        "evidence_text": text,
        "boundary_status": boundary,
        "surface_topic": _topic(text) if mech != "uncertain" else "other_uncertain",
        "mechanism_label": mech,
        "evidence_phrase": text[:12],
        "confidence_band": conf,
        "abstain_reason": abstain,
        "decision_basis": f"reviewer_{reviewer_id} 依据文本关键词与边界判断得出（mock）",
        "created_at": "2026-07-20T00:00:00+08:00",
    }


def validate(row):
    missing = [f for f in REQUIRED_FIELDS if f not in row or row[f] == "" and f not in ("surface_topic", "evidence_phrase", "sample_id")]
    if row.get("mechanism_label") not in ALLOWED_MECH:
        missing.append("mechanism_label:invalid")
    return missing


def run_one_reviewer(items, reviewer_id, output_dir, provider, model, prompt_path, dry_run):
    prompt_text, prompt_version, prompt_sha = load_prompt(reviewer_id, prompt_path)
    run_id = f"{provider}-{reviewer_id}-{prompt_version}"
    model_name = model or ("mock-deterministic" if provider == "mock" or dry_run else provider)
    output_dir = Path(output_dir)
    raw_dir = output_dir / "raw_model_responses"
    raw_dir.mkdir(parents=True, exist_ok=True)

    out_path = output_dir / f"agent_reviews_{reviewer_id}.jsonl"
    retry_path = output_dir / "retry_queue.jsonl"
    done_ids = set()
    if out_path.exists():  # resume：跳过已完成项
        for line in out_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    done_ids.add(json.loads(line)["evidence_id"])
                except Exception:  # noqa: BLE001
                    pass

    t0 = time.time()
    ok, failed = 0, 0
    raw_path = raw_dir / f"raw_{reviewer_id}.jsonl"
    with out_path.open("a", encoding="utf-8") as fout, \
            raw_path.open("a", encoding="utf-8") as fraw:
        for item in items:
            if item["_source_evidence_id"] in done_ids:
                continue
            row = mock_review(item, reviewer_id, run_id, model_name, prompt_version, prompt_sha)
            fraw.write(json.dumps({"blinded_item_id": item["blinded_item_id"],
                                   "raw": row["decision_basis"]}, ensure_ascii=False) + "\n")
            missing = validate(row)
            if missing:
                failed += 1
                with retry_path.open("a", encoding="utf-8") as fq:
                    fq.write(json.dumps({"reviewer_id": reviewer_id,
                                         "blinded_item_id": item["blinded_item_id"],
                                         "missing": missing}, ensure_ascii=False) + "\n")
                continue
            fout.write(json.dumps(row, ensure_ascii=False) + "\n")
            ok += 1
    elapsed = round(time.time() - t0, 4)
    return {"reviewer_id": reviewer_id, "prompt_version": prompt_version,
            "prompt_sha256": prompt_sha, "parsed_ok": ok, "parse_failed": failed,
            "elapsed_seconds": elapsed, "token_estimate": 0}


def main(argv=None):
    ap = argparse.ArgumentParser(description="多代理独立复检运行器（默认离线 mock，代理互相盲测）")
    ap.add_argument("--provider", default="mock")
    ap.add_argument("--model", default=None)
    ap.add_argument("--reviewer-id", default=None, choices=["a", "b", "c"])
    ap.add_argument("--input", default=str(REPO_ROOT / "data" / "calibration" / "calibration_sample.csv"))
    ap.add_argument("--output", default=str(DEFAULT_OUTPUT))
    ap.add_argument("--prompt", default=None)
    ap.add_argument("--temperature", type=float, default=0.0)
    ap.add_argument("--seed", type=int, default=20260720)
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--max-items", type=int, default=None)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    real_model = args.provider not in ("mock", "") and not args.dry_run
    if real_model:
        print("未配置真实模型调用后端；本运行器默认离线。请以 --provider mock 或 --dry-run 运行。",
              file=sys.stderr)
        return 2

    rows = read_sample(args.input)
    items = reviewer_input(rows)
    if args.max_items:
        items = items[:args.max_items]

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    reviewers = [args.reviewer_id] if args.reviewer_id else ["a", "b", "c"]
    results = [run_one_reviewer(items, rid, output_dir, args.provider, args.model,
                                args.prompt, args.dry_run) for rid in reviewers]

    total_ok = sum(r["parsed_ok"] for r in results)
    total_fail = sum(r["parse_failed"] for r in results)
    denom = total_ok + total_fail
    report = {
        "schema_version": "agent-review-run-1.0",
        "agent_review_execution": "READY_NOT_RUN",
        "execution_note": "本次为离线 mock，未调用真实模型；结构、解析与后续共识流程已跑通。",
        "provider": args.provider,
        "input_items": len(items),
        "reviewers": results,
        "parse_success_rate": round(total_ok / denom, 4) if denom else None,
        "parse_success_numerator": total_ok,
        "parse_success_denominator": denom,
    }
    (output_dir / "run_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("多代理复检运行完成：")
    print("  agent_review_execution=READY_NOT_RUN（结构与解析已跑通，未调用真实模型）")
    print(f"  input_count={len(items)} reviewers={','.join(reviewers)}")
    print(f"  parse_success={total_ok}/{denom}")
    print(f"  output_path={output_dir}")
    print("  next_action=运行 tools/calibration/build_agent_consensus.py 汇总共识与争议")
    return 0


if __name__ == "__main__":
    sys.exit(main())
