#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""构建页面数据驱动文件 docs/assets/data/showcase.json（离线、确定性）。

所有关键计数与状态**从数据文件与审计结果计算**，不硬编码：
  data/v2/samples_v2.csv                样本数、平台数
  data/v2/evidence_v2.csv               迁移证据数
  data/v2/bili_evidence_queue.csv       B 站候选数
  data/v2/ambiguous_evidence_queue.csv  未定案歧义数
  data/v2/provisional_manifest.json     provisional 证据数（与 CSV 交叉校验）
  data/v2/evidence_provisional_v2.csv   provisional 行数交叉校验、uncertain flagged 数
  data/v2/evaluation_report.json        四分状态与普通语言指标
  data/v2/human_review_log.csv          人工复核状态
  data/decisions/decision_register.json 待决策项

GitHub 文档链接由 --repo-ref 参数生成（如 phase1/rebuild-evidence-and-demo 或 main）。
公开 JSON 不含 source_url、账号、Cookie、Token、真实身份、完整未审查文本、私密备注。
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TOOLS_DIR.parent
V2_DIR = REPO_ROOT / "data" / "v2"
OUT = REPO_ROOT / "docs" / "assets" / "data" / "showcase.json"
DEFAULT_REPO_REF = "phase1/rebuild-evidence-and-demo"
REPO_URL = "https://github.com/sherlock0717/PsyLens"

_spec = importlib.util.spec_from_file_location("audit_public_data", TOOLS_DIR / "audit_public_data.py")
audit = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(audit)

FEATURE_FLAGS = {
    "show_full_data_download": False,
    "show_raw_urls": False,
    "show_draft_v2_insights": False,
    "show_draft_action_hypotheses": False,
    "show_historical_findings": True,
}

# 页面展示的普通语言指标（key 对应 evaluation_report.metrics）
PLAIN_METRIC_KEYS = [
    ("sample_id_unique_rate", "样本编号完整性"),
    ("evidence_text_match_rate", "证据可回溯"),
    ("platform_sample_coverage", "平台覆盖"),
    ("label_completion_rate", "标签覆盖"),
    ("uncertain_rate", "不确定项"),
    ("human_review_coverage", "人工复核覆盖"),
    ("repeatability_rate", "离线 Demo 复现"),
]

DOC_PATHS = {
    "readme": "README.md",
    "demo": "demo",
    "evaluation_method": "docs/evaluation/EVALUATION_METHOD.md",
    "codebook": "docs/methodology/MECHANISM_CODEBOOK.md",
    "pipeline": "pipeline/README.md",
    "project_brief": "docs/files/PsyLens_project_brief.docx",
    "public_data": "data/public",
}


def _read_json(p, default=None):
    return json.loads(Path(p).read_text(encoding="utf-8")) if Path(p).exists() else default


def _doc_link(repo_ref, rel_path):
    kind = "tree" if ("." not in Path(rel_path).name) else "blob"
    return f"{REPO_URL}/{kind}/{repo_ref}/{rel_path}"


def _platform_alias(samples):
    """将真实平台名映射为匿名标签（平台 A/B/C…），确定性、避免暴露平台身份。"""
    plats = sorted({(r.get("platform_source", "") or "").strip() for r in samples if r.get("platform_source")})
    return {p: f"平台 {chr(ord('A') + i)}" for i, p in enumerate(plats)}


def _pick_evidence_example(prov_rows, samples):
    """从 provisional 证据中确定性选取一条 legacy AI 示例；文本截断、平台匿名化。"""
    alias = _platform_alias(samples)
    row = next((r for r in prov_rows if r.get("label_source") == "legacy_ai"), None)
    if row is None and prov_rows:
        row = prov_rows[0]
    if row is None:
        return {
            "sample_excerpt": "",
            "platform": "",
            "label_source": "历史 AI 标签（未人工复核）",
            "note": "该示例的证据文本可在对应原始反馈中唯一定位；不展示原始链接与内部编号",
        }
    text = (row.get("unit_text", "") or "").strip()
    excerpt = text if len(text) <= 60 else text[:60] + "……"
    return {
        "sample_excerpt": excerpt,
        "platform": alias.get((row.get("platform_source", "") or "").strip(), ""),
        "label_source": "历史 AI 标签（未人工复核）",
        "note": "该示例的证据文本可在对应原始反馈中唯一定位；不展示原始链接与内部编号",
    }


def build(output=None, repo_ref=DEFAULT_REPO_REF, input_dir=None, decisions_path=None):
    output = Path(output) if output else OUT
    input_dir = Path(input_dir) if input_dir else V2_DIR
    decisions_path = Path(decisions_path) if decisions_path else (REPO_ROOT / "data" / "decisions" / "decision_register.json")
    _, samples = audit.read_csv_rows(input_dir / "samples_v2.csv")
    _, evidence = audit.read_csv_rows(input_dir / "evidence_v2.csv")
    _, bili = audit.read_csv_rows(input_dir / "bili_evidence_queue.csv")
    _, ambiguous = audit.read_csv_rows(input_dir / "ambiguous_evidence_queue.csv")
    _, prov_rows = audit.read_csv_rows(input_dir / "evidence_provisional_v2.csv")
    _, human_rows = audit.read_csv_rows(input_dir / "human_review_log.csv")
    prov = _read_json(input_dir / "provisional_manifest.json", {}) or {}
    ev = _read_json(input_dir / "evaluation_report.json", {}) or {}
    decisions = (_read_json(decisions_path, {}) or {}).get("decisions", [])

    # ---- 计数：全部从文件读取 ----
    sample_count = len(samples)
    platform_count = len({r.get("platform_source") for r in samples})
    per_platform = sample_count // platform_count if platform_count else 0
    migrated_evidence = len(evidence)
    bili_candidates = len(bili)
    unresolved_ambiguous = sum(1 for r in ambiguous
                               if (r.get("resolution_status", "") or "") == "pending_human_resolution")
    provisional_evidence_csv = len(prov_rows)
    provisional_evidence_manifest = prov.get("provisional_evidence_count")
    # 交叉校验 manifest 与 CSV 一致
    if provisional_evidence_manifest is not None and provisional_evidence_manifest != provisional_evidence_csv:
        raise ValueError(f"provisional 计数不一致：manifest={provisional_evidence_manifest} "
                         f"vs csv={provisional_evidence_csv}")
    provisional_evidence = provisional_evidence_csv
    uncertain_flagged = (prov.get("analysis_inclusion_distribution", {}) or {}).get("included_flagged_uncertain")
    insights_path = input_dir / "structured_insights_draft.jsonl"
    draft_insights = len([x for x in insights_path.read_text(encoding="utf-8").splitlines() if x.strip()]) \
        if insights_path.exists() else 0
    actions = (_read_json(input_dir / "public_action_hypotheses_draft.json", {}) or {}).get("actions", [])
    draft_actions = len(actions)

    # ---- 状态：从评测报告与人工日志计算 ----
    human_reviews = [r for r in human_rows if r.get("reviewer_type") == "human"]
    structural_status = ev.get("structural_integrity_status")
    label_review_status = ev.get("label_review_status") or ("NOT_STARTED" if not human_reviews else "IN_PROGRESS")
    insight_draft_status = ev.get("insight_draft_status")
    release_status = ev.get("release_readiness_status")

    def _cn_struct(s):
        return "已通过" if s == "PASS" else ("未通过" if s == "BLOCKED" else "进行中")

    def _cn_label(s):
        return "待人工复核" if s == "NOT_STARTED" else ("复核中" if s == "IN_PROGRESS" else "部分复核")

    hero_status = [
        {"label": "结构校验", "value": _cn_struct(structural_status)},
        {"label": "标签状态", "value": _cn_label(label_review_status)},
        {"label": "当前编码", "value": "规则基线"},
    ]

    # ---- 普通语言指标：从评测报告的 plain_explanation 取 ----
    metrics = ev.get("metrics", {})
    plain_metrics = []
    for key, label in PLAIN_METRIC_KEYS:
        mm = metrics.get(key, {})
        plain_metrics.append({
            "key": key,
            "label": label,
            "plain": mm.get("plain_explanation", ""),
        })

    # ---- 证据示例：从稳定 v2 provisional 证据自动读取（平台匿名化，不硬编码）----
    evidence_example = _pick_evidence_example(prov_rows, samples)

    doc_links = {k: _doc_link(repo_ref, v) for k, v in DOC_PATHS.items()}

    showcase = {
        "schema_version": "showcase-2.0",
        "generated_at": ev.get("generated_at") or prov.get("generated_at"),
        "repo_ref": repo_ref,
        "brand": "PsyLens",
        "tagline": "社区反馈分析与可靠性评测",
        "hero_summary": {
            "case": "三平台社区反馈案例",
            "sample_count": sample_count,
            "platform_count": platform_count,
            "provisional_evidence_count": provisional_evidence,
        },
        "hero_status": hero_status,
        "feature_flags": FEATURE_FLAGS,
        "plain_metrics": plain_metrics,
        "evidence_example": evidence_example,
        "counts": {
            "samples": sample_count,
            "per_platform": per_platform,
            "migrated_evidence": migrated_evidence,
            "bili_candidates": bili_candidates,
            "provisional_evidence": provisional_evidence,
            "provisional_uncertain_flagged": uncertain_flagged,
            "draft_insights": draft_insights,
            "draft_actions": draft_actions,
            "unresolved_ambiguous": unresolved_ambiguous,
        },
        "status": {
            "structural_integrity_status": structural_status,
            "label_review_status": label_review_status,
            "insight_draft_status": insight_draft_status,
            "release_readiness_status": release_status,
        },
        "provisional_note": (
            f"其中 {uncertain_flagged} 条为暂不确定项，全部尚未经过真人复核；"
            "该数字是 provisional 证据数，不是最终有效证据数量。"),
        "doc_links": doc_links,
        "open_decisions": [
            {"decision_id": d["decision_id"], "title": d["title"],
             "recommended_option": d["recommended_option"], "status": d["status"]}
            for d in decisions
        ],
        "note": "所有关键计数与状态由数据文件与评测结果计算；草稿洞察与产品假设默认不公开；"
                "页面不展示原始 URL 与完整数据下载；B 站编码为离线规则基线提案，非人工或模型语义复核。",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(showcase, ensure_ascii=False, indent=2), encoding="utf-8")

    # 安全自检：无真实 URL 与凭据（doc_links 指向 github.com/sherlock0717/PsyLens，允许）
    dumped = json.dumps(showcase, ensure_ascii=False)
    for banned in ("cookie=", "token=", "api_key="):
        assert banned.lower() not in dumped.lower(), f"showcase.json 含禁止内容: {banned}"
    import re as _re
    for u in _re.findall(r"https?://[^\s\"']+", dumped):
        assert u.startswith(REPO_URL), f"showcase.json 含非仓库 URL: {u}"
    return showcase


def main(argv=None):
    ap = argparse.ArgumentParser(description="构建页面数据驱动 showcase.json（离线/确定性）")
    ap.add_argument("--output", default=str(OUT))
    ap.add_argument("--repo-ref", default=DEFAULT_REPO_REF)
    args = ap.parse_args(argv)
    s = build(args.output, args.repo_ref)
    c = s["counts"]
    print("showcase.json 生成完成：")
    print(f"  repo_ref={s['repo_ref']}")
    print(f"  samples={c['samples']} platforms={s['hero_summary']['platform_count']} "
          f"provisional={c['provisional_evidence']} (uncertain_flagged={c['provisional_uncertain_flagged']})")
    print(f"  status={s['status']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
