# -*- coding: utf-8 -*-
"""公开文案检查器与页面/README 文案质量校验。"""
import importlib.util
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG = REPO_ROOT / "config" / "public_copy_rules.yaml"
INDEX = REPO_ROOT / "docs" / "index.html"
README = REPO_ROOT / "README.md"


def _load(rel):
    spec = importlib.util.spec_from_file_location(Path(rel).stem, REPO_ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


lint = _load("tools/lint_public_copy.py")
RULES = lint.load_rules(CONFIG)


def _types(tmp_path, name, text):
    p = tmp_path / "f.md"
    p.write_text(text, encoding="utf-8")
    return {f["issue_type"] for f in lint.lint_file(p, name, RULES)}


def _visible(html):
    return re.sub(r"<script[\s\S]*?</script>", "", html)


# ---- 检查器单元测试 ----

def test_detects_template_phrase(tmp_path):
    assert "template_phrase" in _types(tmp_path, "a.md", "本模块深度洞察，全方位赋能业务。")


def test_detects_not_this_but_that(tmp_path):
    assert "not_this_but_that" in _types(tmp_path, "a.md", "这不是一次分析而是一次演示。")


def test_detects_negative_framing(tmp_path):
    assert "negative_framing" in _types(tmp_path, "a.md", "当前质量风险偏高，需要关注。")


def test_detects_long_sentence(tmp_path):
    long = ("这是一段故意写得非常冗长的说明文字用来触发长句检查规则从而验证检查器能够识别"
            "超过阈值的句子长度并且继续堆叠更多内容以确保整句字符数明显超过六十个字符从而稳定命中长句规则")
    assert "long_sentence" in _types(tmp_path, "a.md", long)


def test_allowlist_exempts_file(tmp_path):
    # 白名单文件即便含受限词也不判模板/负面
    types = _types(tmp_path, "docs/CONTENT_STYLE_GUIDE.md", "深度洞察 赋能 质量风险")
    assert "template_phrase" not in types
    assert "negative_framing" not in types


def test_strict_returns_nonzero_on_p0(tmp_path):
    # README.md 命中默认扫描目标；含 P0 模板词时 strict 应返回非零
    p = tmp_path / "README.md"
    p.write_text("本项目全方位赋能业务。", encoding="utf-8")
    rc = lint.main(["--root", str(tmp_path), "--format", "json", "--strict",
                    "--config", str(CONFIG)])
    assert rc == 1


# ---- 页面与 README 文案质量 ----

def test_page_has_no_not_this_but_that():
    v = _visible(INDEX.read_text(encoding="utf-8"))
    assert not re.search(r"不是[^，。；！？]{0,40}而是", v)


def test_page_no_risk_or_missing_card_titles():
    v = _visible(INDEX.read_text(encoding="utf-8"))
    for banned in ["质量风险", "当前风险", "机制不确定率提示编码仍偏粗"]:
        assert banned not in v, banned


def test_page_no_internal_process_language():
    v = _visible(INDEX.read_text(encoding="utf-8"))
    for banned in ["phase1/", "phase2/", "Issue #", "返修", "BLOCKED", "发布阻断"]:
        assert banned not in v, banned


def test_page_no_repeated_human_review_status():
    v = _visible(INDEX.read_text(encoding="utf-8"))
    assert v.count("人工复核") <= 1


def test_page_uses_positive_calibration_framing():
    v = _visible(INDEX.read_text(encoding="utf-8"))
    assert "自动校准计划" in v
    assert "校准重点" in v
    assert "结果使用说明" in v


def test_readme_scope_note_once():
    text = README.read_text(encoding="utf-8")
    assert text.count("结果使用说明") == 1
    assert "解释边界" not in text


def test_readme_explains_key_terms():
    text = README.read_text(encoding="utf-8")
    assert "证据单元" in text and "从一条完整反馈" in text
    assert "体验机制" in text
    assert "自动校准参考集" in text
