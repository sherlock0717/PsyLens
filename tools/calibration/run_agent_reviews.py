#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""多代理独立复检运行器。

支持两种明确分开的运行方式：

- ``--provider mock``（默认）：本地固定示例模式。运行器生成确定性示例输出，
  用于跑通结构、解析和后续共识流程。结果只是结构自测，不是真实模型校准，
  报告标注 ``result_type=mock_pipeline_self_test``，默认写入
  ``artifacts/calibration/mock_self_test/reviews``。
- ``--provider openai_compatible``：真实模型模式。按 OpenAI 兼容接口调用外部
  模型，读取环境变量 ``PSYLENS_LLM_BASE_URL`` / ``PSYLENS_LLM_API_KEY`` /
  ``PSYLENS_LLM_MODEL``；Prompt 真实传入，temperature 与 seed 进入请求体，
  原始响应单独保存，解析失败进入 retry queue，429、超时与网络错误按退避重试，
  支持断点续跑。运行器不记录密钥。

代理只获得盲测证据文本与可选父样本上下文，看不到来源编号、平台名称、当前标签、
编码来源、重测关系或其他代理的结果。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TOOLS_DIR.parent.parent
MOCK_OUTPUT = REPO_ROOT / "artifacts" / "calibration" / "mock_self_test" / "reviews"
REAL_OUTPUT = REPO_ROOT / "artifacts" / "calibration" / "agent_reviews"
PROMPT_DIR = REPO_ROOT / "config" / "calibration" / "prompts"

MOCK_RESULT_TYPE = "mock_pipeline_self_test"
REAL_RESULT_TYPE = "real_agent_calibration"

ALLOWED_MECH = ["competence_frustration", "fairness_threat", "trust_communication_gap",
                "belonging_drop", "norm_safety_risk", "uncertain"]
ALLOWED_TOPIC = ["balance", "matchmaking", "event_design", "progression",
                 "community_conflict", "communication_transparency", "rewards",
                 "new_player_onboarding", "other_uncertain"]
ALLOWED_BOUNDARY = ["complete", "needs_parent_context", "over_segmented",
                    "under_segmented", "not_evidence"]
ALLOWED_CONFIDENCE = ["high", "medium", "low"]
ALLOWED_ABSTAIN = ["none", "insufficient_context", "multiple_mechanisms",
                   "unclear_topic", "unclear_boundary", "other"]
# 复检输出以 blinded_item_id 为主键；不含来源编号，来源只在共识后经私有映射回填。
REQUIRED_FIELDS = ["run_id", "reviewer_id", "blinded_item_id", "model_name",
                   "prompt_version", "prompt_sha256", "evidence_text", "boundary_status",
                   "surface_topic", "mechanism_label", "evidence_phrase", "confidence_band",
                   "abstain_reason", "decision_basis", "created_at"]
# 模型只需填写的字段（其余由程序补充：run_id、model_name、prompt_* 与 created_at）。
MODEL_OUTPUT_FIELDS = ["boundary_status", "surface_topic", "mechanism_label",
                       "evidence_phrase", "confidence_band", "abstain_reason", "decision_basis"]
OPTIONAL_EMPTY = {"surface_topic", "evidence_phrase"}

# 关键词 -> 机制（简单启发式，仅用于本地固定示例模式，不代表真实模型能力）
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
    p = Path(prompt_path) if prompt_path else PROMPT_DIR / f"reviewer_{reviewer_id}.md"
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
    """构造盲测输入：只保留代理可见字段（盲测编号、文本与上下文）。

    不含来源编号、平台名称与重测关系，代理无法反推样本身份。
    """
    return [{
        "blinded_item_id": r.get("blinded_item_id", ""),
        "public_evidence_text": r.get("public_evidence_text", ""),
        "parent_context": r.get("parent_context", ""),
        "context_available": r.get("context_available", "no"),
    } for r in rows]


def _all_mechanism_hits(text):
    return [mech for mech, kws in MECH_KEYWORDS if any(k in text for k in kws)]


def _topic(text):
    for topic, kws in TOPIC_KEYWORDS:
        if any(k in text for k in kws):
            return topic
    return "other_uncertain"


def mock_review(item, reviewer_id, run_id, model_name, prompt_version, prompt_sha):
    """确定性示例判断（本地固定示例模式），不同 reviewer 使用不同判断结构。"""
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
        "evidence_text": text,
        "boundary_status": boundary,
        "surface_topic": _topic(text) if mech != "uncertain" else "other_uncertain",
        "mechanism_label": mech,
        "evidence_phrase": text[:12],
        "confidence_band": conf,
        "abstain_reason": abstain,
        "decision_basis": f"reviewer_{reviewer_id} 依据文本关键词与边界判断得出（本地固定示例）",
        "created_at": "2026-07-20T00:00:00+08:00",
    }


def validate(row):
    """校验一条复检结果：必填字段、全部枚举，以及两项交叉约束。

    - evidence_phrase 非空时必须是 evidence_text 的子串（防止杜撰引用）；
    - mechanism_label=uncertain 时 abstain_reason 不能为 none（弃权必须给出原因）。
    返回问题列表，空列表表示通过。
    """
    problems = [f for f in REQUIRED_FIELDS
                if f not in row or (row[f] == "" and f not in OPTIONAL_EMPTY)]
    if row.get("mechanism_label") not in ALLOWED_MECH:
        problems.append("mechanism_label:invalid")
    if row.get("boundary_status") not in ALLOWED_BOUNDARY:
        problems.append("boundary_status:invalid")
    if row.get("confidence_band") not in ALLOWED_CONFIDENCE:
        problems.append("confidence_band:invalid")
    if row.get("abstain_reason") not in ALLOWED_ABSTAIN:
        problems.append("abstain_reason:invalid")
    # surface_topic 允许留空（OPTIONAL_EMPTY）；非空时必须是合法值
    topic = row.get("surface_topic", "")
    if topic and topic not in ALLOWED_TOPIC:
        problems.append("surface_topic:invalid")
    # evidence_phrase 非空时须出现在 evidence_text 中
    phrase = (row.get("evidence_phrase") or "").strip()
    if phrase and phrase not in (row.get("evidence_text") or ""):
        problems.append("evidence_phrase:not_in_text")
    # uncertain 必须给出弃权原因
    if row.get("mechanism_label") == "uncertain" and row.get("abstain_reason") == "none":
        problems.append("abstain_reason:required_for_uncertain")
    return problems


# ---- 真实 provider：OpenAI 兼容接口 ----

def llm_config_from_env():
    """从环境变量读取真实模型配置；缺失项返回 None（不记录密钥内容）。"""
    base_url = os.environ.get("PSYLENS_LLM_BASE_URL", "").strip()
    api_key = os.environ.get("PSYLENS_LLM_API_KEY", "").strip()
    model = os.environ.get("PSYLENS_LLM_MODEL", "").strip()
    if not (base_url and api_key and model):
        return None
    return {"base_url": base_url.rstrip("/"), "api_key": api_key, "model": model}


def build_messages(prompt_text, item):
    """把 Prompt 与盲测证据组装成 OpenAI 兼容 messages（真实传入模型）。"""
    ctx = item.get("parent_context", "") or "（无）"
    user = (f"证据编号：{item['blinded_item_id']}\n"
            f"证据文本：{item['public_evidence_text']}\n"
            f"父样本上下文：{ctx}\n"
            "请按 schema 输出 JSON。")
    return [{"role": "system", "content": prompt_text},
            {"role": "user", "content": user}]


class RetryableError(Exception):
    """可重试错误：429、超时或网络错误。"""


def _http_post_json(url, headers, body, timeout):
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
            return resp.status, resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        status = e.code
        text = e.read().decode("utf-8", errors="replace")
        if status == 429 or 500 <= status < 600:
            raise RetryableError(f"http_{status}") from e
        return status, text
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise RetryableError(f"network:{type(e).__name__}") from e


def call_openai_compatible(llm, messages, temperature, seed, timeout=60, max_retries=4):
    """调用 OpenAI 兼容 /chat/completions；429、超时与网络错误按退避重试。

    返回 ``(content_text, meta)``；密钥只用于请求头，不写入日志或返回值。
    """
    url = f"{llm['base_url']}/chat/completions"
    payload = {"model": llm["model"], "messages": messages,
               "temperature": temperature, "seed": seed,
               "response_format": {"type": "json_object"}}
    body = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json",
               "Authorization": f"Bearer {llm['api_key']}"}
    last_err = None
    for attempt in range(max_retries):
        try:
            status, text = _http_post_json(url, headers, body, timeout)
        except RetryableError as e:
            last_err = str(e)
            time.sleep(min(2 ** attempt, 8))
            continue
        if status != 200:
            return None, {"http_status": status, "error": "non_200"}
        data = json.loads(text)
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        usage = data.get("usage", {})
        return content, {"http_status": 200, "usage": usage}
    return None, {"error": "retry_exhausted", "last_error": last_err}


def _strip_code_fence(content):
    """去除模型输出外层的 ```json ... ``` 或 ``` ... ``` 代码块围栏。"""
    if not isinstance(content, str):
        return content
    text = content.strip()
    m = re.match(r"^```[a-zA-Z0-9_-]*\s*\n?(.*?)\n?```$", text, re.DOTALL)
    if m:
        return m.group(1).strip()
    return text


def parse_model_json(content, item, reviewer_id, run_id, model_name, prompt_version, prompt_sha):
    """解析模型返回的 JSON，补全运行元数据。解析失败返回 None。

    模型只需填写 MODEL_OUTPUT_FIELDS；run_id、model_name、prompt_* 与 created_at
    由程序补充。支持去除外层 ```json 代码块围栏。
    """
    try:
        obj = json.loads(_strip_code_fence(content))
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(obj, dict):
        return None
    row = {
        "run_id": run_id,
        "reviewer_id": reviewer_id,
        "blinded_item_id": item["blinded_item_id"],
        "model_name": model_name,
        "prompt_version": prompt_version,
        "prompt_sha256": prompt_sha,
        "evidence_text": item["public_evidence_text"],
        "boundary_status": obj.get("boundary_status", ""),
        "surface_topic": obj.get("surface_topic", ""),
        "mechanism_label": obj.get("mechanism_label", ""),
        "evidence_phrase": obj.get("evidence_phrase", ""),
        "confidence_band": obj.get("confidence_band", ""),
        "abstain_reason": obj.get("abstain_reason", "none"),
        "decision_basis": obj.get("decision_basis", ""),
        "created_at": obj.get("created_at", "") or time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    return row


def _load_done_ids(out_path):
    done = set()
    if out_path.exists():
        for line in out_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    done.add(json.loads(line)["blinded_item_id"])
                except Exception:  # noqa: BLE001
                    pass
    return done


def make_run_id(provider, model_name, reviewer_id, prompt_version, temperature, seed):
    """运行标识包含 provider、model、reviewer、prompt_version、temperature、seed，
    以便区分不同模型/参数的运行，避免产物混淆。"""
    safe_model = re.sub(r"[^A-Za-z0-9_.-]", "_", str(model_name))
    return f"{provider}-{safe_model}-{reviewer_id}-{prompt_version}-t{temperature}-s{seed}"


def run_one_reviewer(items, reviewer_id, output_dir, provider, model, prompt_path,
                     dry_run, temperature=0.0, seed=20260720, llm=None, resume=False):
    prompt_text, prompt_version, prompt_sha = load_prompt(reviewer_id, prompt_path)
    use_real = provider == "openai_compatible" and not dry_run
    model_name = model or (llm["model"] if (use_real and llm) else "mock-deterministic")
    run_id = make_run_id(provider, model_name, reviewer_id, prompt_version, temperature, seed)
    output_dir = Path(output_dir)
    # raw 响应与 retry 队列按 run_id 分开，避免不同模型/参数的运行混在一起。
    raw_dir = output_dir / "raw_model_responses" / run_id
    raw_dir.mkdir(parents=True, exist_ok=True)

    out_path = output_dir / f"agent_reviews_{reviewer_id}.jsonl"
    retry_path = output_dir / f"retry_queue_{run_id}.jsonl"

    # 输出安全：非 resume 且输出已存在且非空时，拒绝继续 append。
    if not resume and out_path.exists() and out_path.stat().st_size > 0:
        return {"reviewer_id": reviewer_id, "error": "output_exists_nonempty",
                "message": f"{out_path} 已存在且非空；请改用新的 --output 目录，或加 --resume 续跑。",
                "parsed_ok": 0, "parse_failed": 0, "elapsed_seconds": 0.0, "token_estimate": 0}
    done_ids = _load_done_ids(out_path) if resume else set()

    t0 = time.time()
    ok, failed, tokens = 0, 0, 0
    raw_path = raw_dir / f"raw_{reviewer_id}.jsonl"
    with out_path.open("a", encoding="utf-8") as fout, \
            raw_path.open("a", encoding="utf-8") as fraw:
        for item in items:
            if item["blinded_item_id"] in done_ids:
                continue
            if use_real:
                messages = build_messages(prompt_text, item)
                content, meta = call_openai_compatible(llm, messages, temperature, seed)
                tokens += (meta.get("usage") or {}).get("total_tokens", 0) or 0
                fraw.write(json.dumps({"blinded_item_id": item["blinded_item_id"],
                                       "raw": content, "meta": meta}, ensure_ascii=False) + "\n")
                row = parse_model_json(content, item, reviewer_id, run_id, model_name,
                                       prompt_version, prompt_sha) if content else None
            else:
                row = mock_review(item, reviewer_id, run_id, model_name, prompt_version, prompt_sha)
                fraw.write(json.dumps({"blinded_item_id": item["blinded_item_id"],
                                       "raw": row["decision_basis"]}, ensure_ascii=False) + "\n")
            missing = validate(row) if row else ["parse_failed"]
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
            "elapsed_seconds": elapsed, "token_estimate": tokens}


def main(argv=None):
    ap = argparse.ArgumentParser(description="多代理独立复检运行器（代理互相盲测，输出以盲测编号为主键）")
    ap.add_argument("--provider", default="mock", choices=["mock", "openai_compatible"],
                    help="mock=本地固定示例模式；openai_compatible=真实模型模式")
    ap.add_argument("--model", default=None, help="真实模型名称；默认取环境变量 PSYLENS_LLM_MODEL")
    ap.add_argument("--reviewer-id", default=None, choices=["a", "b", "c"])
    ap.add_argument("--input", default=str(REPO_ROOT / "data" / "calibration" / "calibration_sample.csv"))
    ap.add_argument("--output", default=None, help="输出目录；mock 默认 mock_self_test/reviews")
    ap.add_argument("--prompt", default=None)
    ap.add_argument("--temperature", type=float, default=0.0)
    ap.add_argument("--seed", type=int, default=20260720)
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--max-items", type=int, default=None)
    ap.add_argument("--dry-run", action="store_true", help="不调用真实模型，仅跑本地固定示例")
    args = ap.parse_args(argv)

    is_mock = args.provider == "mock" or args.dry_run
    llm = None
    if not is_mock:
        llm = llm_config_from_env()
        if llm is None:
            print("provider=openai_compatible 需要环境变量 PSYLENS_LLM_BASE_URL / "
                  "PSYLENS_LLM_API_KEY / PSYLENS_LLM_MODEL；未配置，退出。",
                  file=sys.stderr)
            return 2

    default_out = MOCK_OUTPUT if is_mock else REAL_OUTPUT
    output_dir = Path(args.output) if args.output else default_out
    output_dir.mkdir(parents=True, exist_ok=True)

    rows = read_sample(args.input)
    items = reviewer_input(rows)
    if args.max_items:
        items = items[:args.max_items]

    reviewers = [args.reviewer_id] if args.reviewer_id else ["a", "b", "c"]
    results = [run_one_reviewer(items, rid, output_dir, args.provider, args.model,
                                args.prompt, args.dry_run, args.temperature, args.seed,
                                llm, args.resume) for rid in reviewers]

    # 输出安全：若有 reviewer 因输出已存在而拒绝写入，明确报错并退出。
    errored = [r for r in results if r.get("error")]
    if errored:
        for r in errored:
            print(f"错误：{r['message']}", file=sys.stderr)
        return 3

    total_ok = sum(r["parsed_ok"] for r in results)
    total_fail = sum(r["parse_failed"] for r in results)
    denom = total_ok + total_fail
    if is_mock:
        report = {
            "schema_version": "agent-review-run-1.0",
            "result_type": MOCK_RESULT_TYPE,
            "agent_review_execution": "READY_NOT_RUN",
            "execution_note": "本地固定示例模式，未调用真实模型；结构、解析与后续共识流程已跑通。"
                              "结果仅为结构自测，不能作为真实模型校准或标签可靠性结论。",
            "provider": args.provider,
        }
    else:
        report = {
            "schema_version": "agent-review-run-1.0",
            "result_type": REAL_RESULT_TYPE,
            "agent_review_execution": "RUN",
            "execution_note": "真实模型模式，已按 OpenAI 兼容接口调用外部模型。",
            "provider": args.provider,
            "model_name": llm["model"] if llm else args.model,
            "temperature": args.temperature,
            "seed": args.seed,
        }
    report.update({
        "input_items": len(items),
        "reviewers": results,
        "parse_success_rate": round(total_ok / denom, 4) if denom else None,
        "parse_success_numerator": total_ok,
        "parse_success_denominator": denom,
    })
    (output_dir / "run_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("多代理复检运行完成：")
    print(f"  result_type={report['result_type']}")
    print(f"  agent_review_execution={report['agent_review_execution']}")
    print(f"  input_count={len(items)} reviewers={','.join(reviewers)}")
    print(f"  parse_success={total_ok}/{denom}")
    print(f"  output_path={output_dir}")
    print("  next_action=运行 tools/calibration/build_agent_consensus.py 汇总共识与争议")
    return 0


if __name__ == "__main__":
    sys.exit(main())
