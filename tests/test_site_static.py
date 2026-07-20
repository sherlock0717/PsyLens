# -*- coding: utf-8 -*-
"""展示页静态校验：无 Gate/招聘/过强主张/内部阻断术语/source_url/完整下载；数字数据驱动；状态自然表达。"""
import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
INDEX = REPO_ROOT / "docs" / "index.html"
SHOWCASE = REPO_ROOT / "docs" / "assets" / "data" / "showcase.json"
REPO_URL = "https://github.com/sherlock0717/PsyLens"


def _html():
    return INDEX.read_text(encoding="utf-8")


def _visible(h):
    """去掉 <script> 后的可见 HTML。"""
    return re.sub(r"<script[\s\S]*?</script>", "", h)


def test_no_gate_or_enter():
    h = _html()
    assert "gate-locked" not in h
    assert "enter-button" not in h
    assert "gate-screen" not in h


def test_no_capability_map_or_jobs():
    h = _html()
    assert "能力映射" not in h
    assert "招聘" not in h
    assert "岗位" not in h


def test_no_overclaim():
    h = _html()
    for banned in ["可以直接采信", "已验证洞察", "数据真实", "AI 已证明", "验证完成", "经人工复核"]:
        assert banned not in h, banned


def test_no_internal_blocking_terms():
    """页面不出现 P0/P1/BLOCKED/裸露 PASS/内部审计指标。"""
    v = _visible(_html())
    for banned in ["P0", "P1", "BLOCKED", "PASS", "parent_semantic_linkage", "发布阻断"]:
        assert banned not in v, banned


def test_status_expression_natural():
    """页面用自然语言表达状态：结构校验 / 待人工复核 / 规则基线。"""
    h = _html()
    assert "结构校验" in h
    assert "待人工复核" in h
    assert "规则基线" in h


def test_no_source_url_or_full_download():
    h = _html()
    assert "source_url" not in h
    for u in re.findall(r"https?://[^\s\"'<>]+", h):
        assert u.startswith(REPO_URL), f"意外 URL: {u}"
    assert "download" not in h.lower()
    assert not re.search(r'href=["\'][^"\']*\.(csv|jsonl)["\']', h)


def test_single_h1():
    assert len(re.findall(r"<h1[ >]", _html())) == 1


def test_footer_all_rights_reserved():
    h = _html()
    assert "All rights reserved" in h
    assert "Sherlock0717" in h


def test_numbers_are_data_driven():
    h = _html()
    assert 'data-showcase="provisional_evidence"' in h
    assert 'data-showcase="samples"' in h
    assert "fetch('assets/data/showcase.json')" in h
    # 不出现旧硬编码"验证洞察 19"
    assert "验证洞察" not in h


def test_body_no_hardcoded_project_counts():
    """HTML 正文（去脚本）不硬编码具体项目计数；数字由 showcase 注入。"""
    v = _visible(_html())
    for num in ["360", "120", "927", "695", "279", "163"]:
        assert num not in v, f"HTML 正文硬编码了项目计数 {num}"
    # "2" 作为项目计数（如"2 条""共 2 个"）不得硬编码；版权年份/比例等不算
    assert not re.search(r"(?<![\d.])2(?![\d.])\s*(条|个|项|平台)", v), "HTML 正文疑似硬编码计数 2"


def test_hero_and_case_counts_injected():
    """样本数、平台数、每平台数量均以 data-showcase 注入，静态回退不含数字。"""
    h = _html()
    for key in ["samples", "platforms", "per_platform"]:
        assert f'data-showcase="{key}"' in h, key
    # JS 注入 per_platform
    assert "setText('per_platform'" in h


def test_js_uses_textcontent_not_innerhtml():
    """showcase 文案通过 textContent / createElement 注入，禁止 innerHTML。"""
    h = _html()
    assert "innerHTML" not in h
    assert "textContent" in h
    assert "createElement" in h


def test_doc_links_are_ref_driven():
    """文档链接带 data-doc，可由 repo-ref 生成，避免手工改分支名。"""
    h = _html()
    for key in ["readme", "demo", "evaluation_method", "codebook", "pipeline", "project_brief"]:
        assert f'data-doc="{key}"' in h, key


def test_links_official_docx():
    assert "PsyLens_project_brief.docx" in _html()


def test_showcase_json_no_secrets():
    s = SHOWCASE.read_text(encoding="utf-8")
    for banned in ["cookie=", "token=", "api_key="]:
        assert banned.lower() not in s.lower(), banned
    # 仅允许仓库自身 URL
    for u in re.findall(r"https?://[^\s\"']+", s):
        assert u.startswith(REPO_URL), f"showcase 含非仓库 URL: {u}"
    data = json.loads(s)
    assert data["feature_flags"]["show_full_data_download"] is False
    assert data["feature_flags"]["show_raw_urls"] is False


def test_key_doc_links_present():
    h = _html()
    for frag in ["README.md", "EVALUATION_METHOD.md", "MECHANISM_CODEBOOK.md", "/demo"]:
        assert frag in h, frag


def test_index_md_removed():
    assert not (REPO_ROOT / "docs" / "index.md").exists()
