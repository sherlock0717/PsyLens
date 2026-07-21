# -*- coding: utf-8 -*-
"""最终发布收尾校验：项目定位、页面/README 表述、DOCX 内容与 Pages 发布。"""
import importlib.util
import re
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
README = REPO_ROOT / "README.md"
INDEX = REPO_ROOT / "docs" / "index.html"
SAMPLES = REPO_ROOT / "data" / "public" / "samples_public.csv"
EVIDENCE = REPO_ROOT / "data" / "public" / "evidence_public.csv"


def _visible(html):
    return re.sub(r"<script[\s\S]*?</script>", "", html)


def _build_docx_xml(tmp_path):
    """用当前构建器生成一份 DOCX 到临时目录，返回 document.xml 文本。"""
    path = REPO_ROOT / "tools" / "build_project_brief_docx.py"
    spec = importlib.util.spec_from_file_location("build_project_brief_docx", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    output = tmp_path / "brief.docx"
    module.build(SAMPLES, EVIDENCE, output)
    with zipfile.ZipFile(output) as archive:
        return archive.read("word/document.xml").decode("utf-8")


# ---- README 与页面定位 ----

def test_readme_drops_calibration_plan_wording():
    text = README.read_text(encoding="utf-8")
    assert "自动校准计划" not in text
    assert "自动校准工具" in text


def test_page_drops_calibration_plan_wording():
    v = _visible(INDEX.read_text(encoding="utf-8"))
    assert "自动校准计划" not in v
    assert "自动校准工具" in v


def test_page_shows_no_mock_consistency_rate():
    v = _visible(INDEX.read_text(encoding="utf-8"))
    assert "一致率" not in v
    assert "mock" not in v


def test_page_does_not_claim_real_model_run():
    v = _visible(INDEX.read_text(encoding="utf-8"))
    assert "真实模型" not in v
    assert "Kappa" not in v
    assert "Benchmark" not in v


# ---- DOCX 内容 ----

def test_docx_describes_calibration_tool(tmp_path):
    xml = _build_docx_xml(tmp_path)
    assert "自动校准工具" in xml
    assert "本地固定示例模式" in xml
    assert "300 条主样本" in xml
    assert "30 条重测样本" in xml
    assert "三名独立 Reviewer" in xml or "三路独立复检" in xml
    assert "OpenAI-compatible" in xml


def test_docx_has_no_model_performance_numbers(tmp_path):
    xml = _build_docx_xml(tmp_path)
    for banned in ["模型一致率", "模型性能", "Fleiss", "Benchmark 已", "全量校准已完成",
                   "真实模型一致率", "模型性能排名"]:
        assert banned not in xml, banned


def test_docx_copyright_appears_once(tmp_path):
    xml = _build_docx_xml(tmp_path)
    assert xml.count("Copyright © 2026 Sherlock0717. All rights reserved.") == 1


def test_docx_clarifies_scope(tmp_path):
    xml = _build_docx_xml(tmp_path)
    assert "只用于验证流程" in xml
    assert "不发布模型成绩" in xml
    assert "人工金标准" in xml
