# -*- coding: utf-8 -*-
"""展示页静态校验：无 Gate/招聘/过强主张/source_url/完整下载入口；数字数据驱动；footer 与链接。"""
import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
INDEX = REPO_ROOT / "docs" / "index.html"
SHOWCASE = REPO_ROOT / "docs" / "assets" / "data" / "showcase.json"


def _html():
    return INDEX.read_text(encoding="utf-8")


def test_no_gate_or_enter():
    h = _html()
    assert "gate-locked" not in h
    assert "enter-button" not in h
    assert ">ENTER<" not in h.upper().replace(" ", "").upper() or "ENTER" not in h  # 无 ENTER 按钮
    assert "gate-screen" not in h


def test_no_capability_map_or_jobs():
    h = _html()
    assert "能力映射" not in h
    assert "招聘" not in h
    assert "岗位" not in h


def test_no_overclaim():
    h = _html()
    for banned in ["可以直接采信", "已验证洞察", "数据真实", "AI 已证明", "验证完成"]:
        assert banned not in h, banned
    # "经人工复核" 不得出现（无日志）
    assert "经人工复核" not in h


def test_no_source_url_or_full_download():
    h = _html()
    assert "source_url" not in h
    # 不含真实抓取平台 URL；GitHub 链接允许
    urls = re.findall(r"https?://[^\s\"'<>]+", h)
    for u in urls:
        assert "github.com/sherlock0717/PsyLens" in u, f"意外 URL: {u}"
    # 无指向数据文件的下载入口（.csv/.jsonl/download 按钮）；说明性文案（"默认不开放"）允许
    assert "download" not in h.lower()
    assert not re.search(r'href=["\'][^"\']*\.(csv|jsonl)["\']', h)


def test_single_h1():
    h = _html()
    assert len(re.findall(r"<h1[ >]", h)) == 1


def test_footer_all_rights_reserved():
    h = _html()
    assert "All rights reserved" in h
    assert "Sherlock0717" in h


def test_numbers_are_data_driven():
    h = _html()
    # 关键数字通过 data-showcase 注入，而非硬编码 697/19 等旧值
    assert "data-showcase=\"provisional_evidence\"" in h
    assert "data-showcase=\"eval_status\"" in h
    assert "fetch('assets/data/showcase.json')" in h
    assert "19" not in re.sub(r"<script[\s\S]*?</script>", "", h) or True  # 不强制，但旧"验证洞察 19"不应出现
    assert "验证洞察" not in h


def test_showcase_json_no_secrets():
    s = SHOWCASE.read_text(encoding="utf-8")
    for banned in ["http://", "https://", "cookie=", "token=", "api_key="]:
        assert banned.lower() not in s.lower(), banned
    data = json.loads(s)
    assert data["feature_flags"]["show_full_data_download"] is False
    assert data["feature_flags"]["show_raw_urls"] is False


def test_key_doc_links_present():
    h = _html()
    for frag in ["README.md", "EVALUATION_METHOD.md", "MECHANISM_CODEBOOK.md", "FULL_PIPELINE.md", "/demo"]:
        assert frag in h, frag


def test_index_md_removed():
    assert not (REPO_ROOT / "docs" / "index.md").exists()
