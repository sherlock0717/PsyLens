#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成正式项目说明 DOCX：docs/files/PsyLens_project_brief.docx（离线、确定性）。

内容与最新 README / 页面 / 评测方法一致，数字从 data 文件读取以保持一致。
主体面向外部阅读；P0/P1、阻断清单与详细审计不进入正文，必要边界集中在「方法范围」。
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
OUT = REPO_ROOT / "docs" / "files" / "PsyLens_project_brief.docx"

_spec = importlib.util.spec_from_file_location("audit_public_data", TOOLS_DIR / "audit_public_data.py")
audit = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(audit)


def _counts():
    _, samples = audit.read_csv_rows(V2_DIR / "samples_v2.csv")
    _, evidence = audit.read_csv_rows(V2_DIR / "evidence_v2.csv")
    _, bili = audit.read_csv_rows(V2_DIR / "bili_evidence_queue.csv")
    prov = json.loads((V2_DIR / "provisional_manifest.json").read_text(encoding="utf-8"))
    insights = [x for x in (V2_DIR / "structured_insights_draft.jsonl").read_text(
        encoding="utf-8").splitlines() if x.strip()]
    actions = json.loads((V2_DIR / "public_action_hypotheses_draft.json").read_text(
        encoding="utf-8")).get("actions", [])
    return {
        "samples": len(samples),
        "platforms": len({r.get("platform_source") for r in samples}),
        "migrated_evidence": len(evidence),
        "bili_candidates": len(bili),
        "provisional": prov.get("provisional_evidence_count"),
        "uncertain_flagged": (prov.get("analysis_inclusion_distribution", {}) or {}).get(
            "included_flagged_uncertain"),
        "insights": len(insights),
        "actions": len(actions),
    }


def _set_cjk_font(document):
    """设置正文与标题字体，含中文东亚字体回退。"""
    from docx.oxml.ns import qn
    for style_name in ["Normal", "Title", "Heading 1", "Heading 2"]:
        try:
            style = document.styles[style_name]
        except KeyError:
            continue
        rpr = style.element.get_or_add_rPr()
        rfonts = rpr.find(qn("w:rFonts"))
        if rfonts is None:
            from docx.oxml import OxmlElement
            rfonts = OxmlElement("w:rFonts")
            rpr.append(rfonts)
        rfonts.set(qn("w:ascii"), "Calibri")
        rfonts.set(qn("w:hAnsi"), "Calibri")
        rfonts.set(qn("w:eastAsia"), "Microsoft YaHei")


def build(output=None):
    from docx import Document
    from docx.shared import Pt

    output = Path(output) if output else OUT
    c = _counts()
    doc = Document()
    _set_cjk_font(doc)

    doc.add_heading("PsyLens 项目说明", level=0)
    doc.add_paragraph("社区反馈分析与可靠性评测")
    doc.add_paragraph("Copyright © 2026 Sherlock0717. All rights reserved.")

    def section(title, paras):
        doc.add_heading(title, level=1)
        for p in paras:
            doc.add_paragraph(p)

    section("1. 项目概述", [
        "PsyLens 把公开社区反馈整理成可回溯的证据，并评估从编码到产品假设的每一步是否可靠。",
        "它偏向一个可核查的评测型分析案例：不仅给出分析结论，更提供样本、证据、编码、洞察、"
        "产品假设的完整链路与可靠性指标，并提供默认离线、不联网、不调用真实模型的可运行 Demo。",
    ])
    section("2. 当前案例", [
        f"整合三个社区平台的公开反馈，共 {c['samples']} 条样本（每平台各 120 条），覆盖 {c['platforms']} 个平台。",
        "数据分为样本层（一条完整反馈原文）与证据层（从原文切出的可单独判断的证据单元），"
        "因此证据数量不等于样本数量。",
        f"已迁移 {c['migrated_evidence']} 条唯一命中的 legacy 证据；B 站 {c['bili_candidates']} 条候选由"
        "离线规则基线生成初步提案。所有标签均未经真人复核。",
    ])
    section("3. 分析与评测流程", [
        "反馈 → 证据单元 → 主题与机制编码 → 结构化洞察 → 产品假设 → 可靠性评测。",
        "每一步都保留可追溯关系：证据可回到原始反馈，洞察可回到证据，产品假设可回到洞察与证据。",
    ])
    section("4. 证据链", [
        f"provisional 证据层共 {c['provisional']} 条（其中 {c['uncertain_flagged']} 条为暂不确定项，单独标记）。",
        "证据文本可在对应原始反馈中定位；公开数据副本不含来源链接与身份定位字段。",
    ])
    section("5. 评测框架", [
        "评测覆盖数据完整性、编码质量、洞察前置质量、建议前置质量与运行质量五组指标，"
        "每个指标记录数值、分子、分母、判定与普通语言解释。",
        "总体状态拆分为四项：结构完整性、标签复核状态、草稿洞察状态与发布就绪状态；"
        "结构完整性当前通过，标签复核尚未开始。",
    ])
    section("6. 离线 Demo", [
        "输入几条脱敏反馈，Demo 会离线生成证据单元、草稿结构化洞察、待验证产品假设与评测报告。",
        "默认不联网、不调用模型、不运行抓取；相同输入产生相同输出。运行：python tools/run_demo.py",
    ])
    section("7. 当前观察", [
        f"当前形成 {c['insights']} 条草稿结构化洞察与 {c['actions']} 条待验证产品假设，均默认不公开、未经人工复核。",
        "历史 legacy 分析观察作为中间产物保留，正用 v2 证据层重新复核。",
    ])
    section("8. 产品假设", [
        "产品建议以「待验证假设」呈现，每条包含预期效果、验证办法与可衡量指标，"
        "并可回到具体洞察与证据；在实验验证前不作为正式结论。",
    ])
    section("9. 方法范围", [
        "离线规则基线提案由关键词规则依据编码手册生成，不是人工或模型语义复核；",
        "草稿洞察与产品假设尚未成为正式结论；",
        "原始来源链接不在展示页与公开数据副本中提供，内部来源字段不进入发布合并范围；",
        "两条极短证据来源不确定，仍待人工确认；产品假设仍需实验验证。",
    ])
    section("10. 文件与运行入口", [
        "README：仓库根目录；离线 Demo：demo/；评测方法：docs/evaluation/；编码手册：docs/methodology/；",
        "采集与分析流程：pipeline/README.md；公开分析数据：data/public/。",
    ])

    doc.add_paragraph("")
    tail = doc.add_paragraph("Copyright © 2026 Sherlock0717. All rights reserved.")
    tail.runs[0].font.size = Pt(9)

    output.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(output))
    return output


def main(argv=None):
    ap = argparse.ArgumentParser(description="生成正式项目说明 DOCX（离线/确定性）")
    ap.add_argument("--output", default=str(OUT))
    args = ap.parse_args(argv)
    out = build(args.output)
    print(f"项目说明 DOCX 已生成：{out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
