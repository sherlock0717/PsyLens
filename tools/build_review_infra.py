#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""复核基础设施与 B 站 Agent 标签提案生成器（确定性、离线、不调用任何模型）。

产出：
  data/v2/review_queue.csv           待复核队列（legacy 证据 / B 站候选 / 歧义）
  data/v2/human_review_log.csv       人工复核日志（仅表头 + system_migration 事件，无 human）
  data/v2/agent_label_proposals.csv  B 站 279 候选的 Agent 提案

设计要点：
  - 提案完全由本地规则依据 codebook 生成，**不调用外部模型 API / 在线模型**；
  - 相同输入产生相同输出（确定性）；
  - proposer_type=agent，proposal_status=agent_proposed_unreviewed；
  - include_as_evidence ∈ {yes, no, uncertain}，uncertain 真实使用；
  - mechanism_label_proposed 严格取自 codebook 六项；
  - evidence_phrase_proposed 从 candidate_unit_text 确定性提取，保证可定位；
  - 不删除任何原候选；279 条全部有记录。

规则说明见 docs/methodology/MECHANISM_CODEBOOK.md 与 SURFACE_TOPIC_CODEBOOK.md。
"""
from __future__ import annotations

import argparse
import csv
import importlib.util
import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TOOLS_DIR.parent
V2_DIR = REPO_ROOT / "data" / "v2"

_spec = importlib.util.spec_from_file_location("audit_public_data", TOOLS_DIR / "audit_public_data.py")
audit = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(audit)

MIN_EVIDENCE_LEN = 8  # 短于此且无明确指向者倾向 no/uncertain

# ---- 机制关键词（依据 codebook；顺序即冲突裁决优先级）----
# norm_safety_risk 优先，其次 trust，其次 fairness，其次 belonging，其次 competence
MECH_RULES = [
    ("norm_safety_risk", ["外挂", "挂哥", "开挂", "代练", "举报", "封号", "封了", "盗号", "骂", "喷",
                          "辱骂", "骚扰", "演员", "挂机", "送人头", "故意送", "国粹", "嘴臭"]),
    ("trust_communication_gap", ["官方", "策划", "设计师", "暗改", "公告", "更新说明", "客服", "反馈",
                                 "不听", "已读", "承诺", "说好的", "跌麻"]),
    ("fairness_threat", ["不公平", "针对", "氪金", "氪佬", "平民", "坑", "偏", "凭什么", "不合理",
                         "让个", "让3000", "一边倒", "反常识", "恶心玩家", "恶心人"]),
    ("belonging_drop", ["退坑", "弃游", "不想玩", "不玩了", "寒心", "环境", "乌烟瘴气", "失望",
                        "走了", "单机游戏", "没意思"]),
    ("competence_frustration", ["打不过", "太难", "太肝", "做不完", "白练", "白搭", "折磨", "劝退",
                                "门槛", "卡关", "打不动", "输出", "存活", "克制", "打不死", "承伤",
                                "性价比", "超模", "垃圾", "抗", "回血", "吸血", "重伤", "覆盖率"]),
]

# ---- 表层话题关键词 ----
TOPIC_RULES = [
    ("matchmaking", ["匹配", "队友", "排位", "单排", "双排", "三排", "段位", "排队", "人机", "牛马"]),
    ("communication_transparency", ["官方", "公告", "暗改", "更新说明", "客服", "反馈", "策划", "设计师"]),
    ("community_conflict", ["喷", "骂", "嘴臭", "互刚", "红叉区", "对喷", "国粹", "举报", "演员"]),
    ("rewards", ["奖励", "产出", "掉落", "任务", "性价比", "回报", "散件", "给钱"]),
    ("progression", ["养成", "升级", "肝", "进度", "门槛", "练", "成长"]),
    ("new_player_onboarding", ["新手", "萌新", "新人", "入门", "教程"]),
    ("event_design", ["活动", "玩法", "模式", "大乱斗", "限时"]),
    ("balance", ["英雄", "装备", "海克斯", "狂妄", "移速", "重伤", "绿穿", "红穿", "反甲", "鬼书",
                 "超模", "数值", "羁绊", "叠角龙", "坦克", "adc", "法师", "刺客", "克制", "版本",
                 "凡性", "破败", "轻语", "链锯剑", "属性"]),
]

# 过短或纯上下文依赖倾向 no 的信号
LOW_VALUE_HINTS = ["确实", "还有", "再说", "最后", "总结", "一开始", "除去", "除非", "比如"]


def normalize_for_match(s: str) -> str:
    return audit.normalize_text(s)


def find_first_keyword(text: str, keywords):
    """返回文本中最先出现的关键词（按在文本中的位置），无则 None。"""
    best = None
    best_pos = len(text) + 1
    for kw in keywords:
        pos = text.find(kw)
        if pos != -1 and pos < best_pos:
            best_pos = pos
            best = kw
    return best


def propose_topic(text: str):
    for topic, kws in TOPIC_RULES:
        if find_first_keyword(text, kws) is not None:
            return topic
    return ""  # 允许为空


def propose_mechanism(text: str):
    """返回 (mechanism_label 或 uncertain, matched_keyword 或 None)。"""
    for mech, kws in MECH_RULES:
        kw = find_first_keyword(text, kws)
        if kw is not None:
            return mech, kw
    return "uncertain", None


def decide_inclusion(text: str, mech: str, matched_kw):
    """判定 include_as_evidence 与 confidence / needs_human_review / reason。"""
    t = text.strip()
    n = len(t)
    # 过短且无机制指向 -> no
    if n < MIN_EVIDENCE_LEN and mech == "uncertain":
        return "no", "low", "true", "过短且无明确机制指向，视为语气/连接片段"
    # 纯上下文起始词开头且较短、无机制 -> uncertain
    starts_low = any(t.startswith(h) for h in LOW_VALUE_HINTS)
    if mech == "uncertain":
        if n < 15 or starts_low:
            return "no", "low", "true", "无明确机制指向且依赖上下文，暂不作为独立证据"
        return "uncertain", "low", "true", "有内容但机制指向不明确，需人工判断"
    # 有机制指向
    if matched_kw and n >= 15:
        return "yes", "medium", "true", f"命中机制关键信号「{matched_kw}」，可作候选证据（待人工复核）"
    if matched_kw:
        return "uncertain", "low", "true", f"命中「{matched_kw}」但文本较短，存疑"
    return "uncertain", "low", "true", "机制指向不确定"


def pick_evidence_phrase(text: str, matched_kw):
    """从 candidate_unit_text 中确定性提取 evidence_phrase（保证可定位）。"""
    t = text.strip()
    if matched_kw and matched_kw in t:
        # 取包含关键词的一个短窗口（关键词前后各 8 字），并确保是 t 的子串
        idx = t.find(matched_kw)
        start = max(0, idx - 8)
        end = min(len(t), idx + len(matched_kw) + 8)
        phrase = t[start:end]
        return phrase
    # 无关键词时取前 20 字作为定位短语
    return t[:20]


def build_proposals(bili_rows):
    proposals = []
    for i, r in enumerate(bili_rows, 1):
        text = r.get("candidate_unit_text", "") or ""
        topic = propose_topic(text)
        mech, kw = propose_mechanism(text)
        include, conf, needs_review, reason = decide_inclusion(text, mech, kw)
        # include=no 时不强行给机制标签
        mech_out = mech if include in ("yes", "uncertain") else ""
        phrase = pick_evidence_phrase(text, kw) if include in ("yes", "uncertain") else ""
        # 保证 evidence_phrase 可在 candidate_unit_text 定位
        if phrase and phrase not in text:
            phrase = text[:20]
        proposals.append({
            "proposal_id": f"AP_{i:04d}",
            "queue_id": r.get("queue_id", ""),
            "sample_id": r.get("sample_id", ""),
            "candidate_unit_index": r.get("candidate_unit_index", ""),
            "candidate_unit_text": text,
            "include_as_evidence": include,
            "surface_topic_proposed": topic if include in ("yes", "uncertain") else "",
            "mechanism_label_proposed": mech_out,
            "evidence_phrase_proposed": phrase,
            "proposal_confidence": conf,
            "needs_human_review": needs_review,
            "proposal_reason": reason,
            "proposer_type": "agent",
            "proposal_status": "agent_proposed_unreviewed",
        })
    return proposals


PROPOSAL_COLS = ["proposal_id", "queue_id", "sample_id", "candidate_unit_index",
                 "candidate_unit_text", "include_as_evidence", "surface_topic_proposed",
                 "mechanism_label_proposed", "evidence_phrase_proposed", "proposal_confidence",
                 "needs_human_review", "proposal_reason", "proposer_type", "proposal_status"]

REVIEW_QUEUE_COLS = ["queue_item_id", "entity_type", "entity_id", "source_sample_id",
                     "current_status", "priority", "notes"]

HUMAN_LOG_COLS = ["review_event_id", "entity_type", "entity_id", "source_sample_id",
                  "original_label", "proposed_label", "final_label", "reviewer_type",
                  "review_status", "decision_reason", "reviewed_at", "notes"]


def build_review_queue(evidence_rows, bili_rows, ambiguous_rows):
    rows = []
    n = 0
    for e in evidence_rows:
        n += 1
        rows.append({
            "queue_item_id": f"RQ_{n:05d}", "entity_type": "legacy_evidence",
            "entity_id": e.get("evidence_id", ""), "source_sample_id": e.get("sample_id", ""),
            "current_status": "legacy_ai_label_unreviewed", "priority": "normal",
            "notes": "legacy 迁移证据待人工复核",
        })
    for b in bili_rows:
        n += 1
        rows.append({
            "queue_item_id": f"RQ_{n:05d}", "entity_type": "bili_candidate",
            "entity_id": b.get("queue_id", ""), "source_sample_id": b.get("sample_id", ""),
            "current_status": "agent_proposed_unreviewed", "priority": "normal",
            "notes": "B 站候选单元 + Agent 提案待人工复核",
        })
    for a in ambiguous_rows:
        n += 1
        rows.append({
            "queue_item_id": f"RQ_{n:05d}", "entity_type": "ambiguous_evidence",
            "entity_id": a.get("legacy_evidence_id", ""), "source_sample_id": "",
            "current_status": "pending_human_resolution", "priority": "high",
            "notes": "歧义证据待人工确认候选",
        })
    return rows


def build_human_review_log(evidence_count):
    """只创建 schema + system_migration 事件；不得出现 reviewer_type=human。"""
    return [{
        "review_event_id": "RE_00001", "entity_type": "dataset",
        "entity_id": "evidence_v2", "source_sample_id": "",
        "original_label": "", "proposed_label": "", "final_label": "",
        "reviewer_type": "system_migration", "review_status": "migrated",
        "decision_reason": f"系统迁移 {evidence_count} 条 legacy 证据，标签保持 legacy_ai_label_unreviewed",
        "reviewed_at": "2026-07-17T16:56:33.578346+08:00",
        "notes": "非人工复核事件；当前无 reviewer_type=human 记录",
    }]


def write_csv(path: Path, cols, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in cols})


def build_all(output_dir=None):
    output_dir = Path(output_dir) if output_dir else V2_DIR
    _, evidence_rows = audit.read_csv_rows(V2_DIR / "evidence_v2.csv")
    _, bili_rows = audit.read_csv_rows(V2_DIR / "bili_evidence_queue.csv")
    _, ambiguous_rows = audit.read_csv_rows(V2_DIR / "ambiguous_evidence_queue.csv")

    proposals = build_proposals(bili_rows)
    review_queue = build_review_queue(evidence_rows, bili_rows, ambiguous_rows)
    human_log = build_human_review_log(len(evidence_rows))

    write_csv(output_dir / "agent_label_proposals.csv", PROPOSAL_COLS, proposals)
    write_csv(output_dir / "review_queue.csv", REVIEW_QUEUE_COLS, review_queue)
    write_csv(output_dir / "human_review_log.csv", HUMAN_LOG_COLS, human_log)
    return proposals, review_queue, human_log


def main(argv=None):
    ap = argparse.ArgumentParser(description="复核基础设施与 B 站 Agent 提案生成（离线/确定性）")
    ap.add_argument("--output-dir", default=str(V2_DIR))
    args = ap.parse_args(argv)
    proposals, review_queue, human_log = build_all(args.output_dir)
    from collections import Counter
    inc = Counter(p["include_as_evidence"] for p in proposals)
    print("Agent 提案生成完成：")
    print(f"  proposals={len(proposals)} include={dict(inc)}")
    print(f"  review_queue={len(review_queue)} human_log={len(human_log)}(仅 system_migration)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
