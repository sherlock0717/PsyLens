# -*- coding: utf-8 -*-
"""Demo 报告渲染：Markdown 与 HTML（自包含、无外部资源）。"""
from __future__ import annotations

import html
import json


def render_markdown(run_id, evidence, insights, actions, metrics):
    lines = [f"# PsyLens 离线 Demo 报告（{run_id}）", "",
             "> 离线、确定性、mock provider 生成。全部标签为 Demo 演示，非人工复核结论。", "",
             "## 评测", "",
             f"- 状态：**{metrics['_status']}**",
             f"- 证据文本可回溯：{metrics['evidence_text_match_rate']}",
             f"- 非法标签率：{metrics['invalid_label_rate']}",
             f"- 洞察引用可解析：{metrics['insight_support_resolution_rate']}",
             f"- 建议→洞察可追溯：{metrics['action_to_insight_linkage_rate']}",
             f"- 建议→证据可追溯：{metrics['action_to_evidence_linkage_rate']}", "",
             f"## 证据单元（{len(evidence)}）", ""]
    for e in evidence[:20]:
        lines.append(f"- `{e['evidence_id']}` [{e['mechanism_label']}] {e['unit_text'][:40]}")
    lines += ["", f"## 结构化洞察（{len(insights)}）", ""]
    for x in insights:
        lines.append(f"- `{x['insight_id']}` {x['title']}：{x['evidence_count']} 条证据，平台 {'、'.join(x['platform_coverage'])}")
    lines += ["", f"## 待验证产品假设（{len(actions)}）", ""]
    for a in actions:
        lines.append(f"- `{a['action_id']}` {a['title']}（来自 {','.join(a['source_insight_ids'])}）")
    lines.append("")
    return "\n".join(lines)


def render_html(run_id, evidence, insights, actions, metrics):
    def esc(s):
        return html.escape(str(s))
    body = [f"<h1>PsyLens 离线 Demo 报告（{esc(run_id)}）</h1>",
            "<p>离线、确定性、mock provider 生成。全部标签为 Demo 演示，非人工复核结论。</p>",
            "<h2>评测</h2><ul>",
            f"<li>状态：<b>{esc(metrics['_status'])}</b></li>",
            f"<li>证据文本可回溯：{esc(metrics['evidence_text_match_rate'])}</li>",
            f"<li>非法标签率：{esc(metrics['invalid_label_rate'])}</li>",
            f"<li>洞察引用可解析：{esc(metrics['insight_support_resolution_rate'])}</li>",
            "</ul>",
            f"<h2>结构化洞察（{len(insights)}）</h2><ul>"]
    for x in insights:
        body.append(f"<li>{esc(x['title'])}：{x['evidence_count']} 条证据，平台 {esc('、'.join(x['platform_coverage']))}</li>")
    body.append("</ul>")
    return ("<!doctype html><html lang=\"zh-CN\"><head><meta charset=\"utf-8\">"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
            "<title>PsyLens Demo 报告</title></head><body>" + "".join(body) + "</body></html>")


def dumps(obj):
    return json.dumps(obj, ensure_ascii=False, indent=2)
