# -*- coding: utf-8 -*-
"""tools/audit_public_data.py 的特征测试（characterization tests）。

原则：
  - 测试不修改任何历史公开数据。
  - 测试为离线、确定性；不联网、不调用模型、不读取密钥。
  - 既覆盖纯函数（归一化 / n-gram / linkage 分类），也对真实公开数据做端到端断言。
"""
import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "tools" / "audit_public_data.py"

spec = importlib.util.spec_from_file_location("audit_public_data", MODULE_PATH)
audit = importlib.util.module_from_spec(spec)
sys.modules["audit_public_data"] = audit
spec.loader.exec_module(audit)


# --------------------------- 纯函数测试 ---------------------------
def test_normalize_fullwidth_and_whitespace():
    # 全角数字 / 空白 / 大小写 归一
    assert audit.normalize_text("ＡＢＣ　１２３") == "abc123"
    assert audit.normalize_text("  hello   world  ") == "helloworld"


def test_normalize_punctuation_unify():
    # 中文标点 -> 英文标点，连续重复折叠
    assert audit.normalize_text("好！！！") == "好!"
    assert audit.normalize_text("a，b。c") == "a,b.c"


def test_normalize_html_unescape():
    assert audit.normalize_text("a&amp;b") == "a&b"


def test_ngram_overlap_identical():
    assert audit.ngram_overlap("abcdef", "abcdef") == 1.0


def test_ngram_overlap_disjoint():
    assert audit.ngram_overlap("aaaa", "bbbb") == 0.0


def test_classify_linkage_exact_substring():
    status, ratio, ov = audit.classify_linkage("bcd", "abcde", True)
    assert status == "exact_substring"


def test_classify_linkage_missing_parent():
    status, _, _ = audit.classify_linkage("x", "", False)
    assert status == "missing_parent"


def test_classify_linkage_empty_text():
    status, _, _ = audit.classify_linkage("", "abc", True)
    assert status == "empty_text"


def test_classify_linkage_no_match():
    status, _, _ = audit.classify_linkage("完全不相关的文本内容", "另一段毫无关系的话", True)
    assert status in ("no_match", "partial_overlap")


def test_pii_scan_detects_email_and_phone():
    hits = audit.scan_pii("联系 test@example.com 或 13800138000")
    assert "email" in hits and "phone_cn" in hits


# --------------------------- 端到端（真实公开数据）---------------------------
def test_run_audit_core_counts():
    result = audit.run_audit()
    assert result["clean_input_audit"]["total_rows"] == audit.EXPECTED_CLEAN_ROWS
    assert result["evidence_audit"]["total_rows"] == audit.EXPECTED_EVIDENCE_ROWS
    assert result["insights_audit"]["total_lines_parsed"] == audit.EXPECTED_INSIGHTS


def test_run_audit_platform_and_window():
    result = audit.run_audit()
    dist = result["clean_input_audit"]["platform_distribution"]
    assert dist == {"Bili": 120, "NGA": 120, "Tieba": 120}
    assert result["clean_input_audit"]["window_distribution"] == {"w1": 260, "w2": 100}


def test_run_audit_mechanism_counts_match_page():
    result = audit.run_audit()
    rc = result["recompute"]
    assert rc["competence_frustration_count"] == 268
    assert rc["fairness_threat_count"] == 72
    assert rc["uncertain_mechanism_count"] == 336
    assert rc["theme_bucket_counts"]["balance_mechanic"] == 236
    assert rc["surface_balance_count"] == 192


def test_run_audit_is_blocked_due_to_parent_offset():
    # 已知阻断：证据 parent_id 与公开 clean CSV 的 id 空间错位
    result = audit.run_audit()
    assert result["phase0_status"] == "BLOCKED"
    assert len(result["blockers"]) >= 1
    gm = result["evidence_audit"]["global_match_counts"]
    # 全部证据单元文本仍可在整洁样本中定位（数据真实），只是 id 错位
    assert gm.get("not_found_anywhere", 0) == 0


def test_run_audit_supporting_ids_all_exist():
    result = audit.run_audit()
    assert result["insights_audit"]["missing_support_lines"] == []
    assert result["insights_audit"]["empty_supporting_lines"] == []


def test_run_audit_example_1u2_platform_mismatch():
    # 页面称 1_u2 来自 B 站(Bili)，实际来自 NGA
    result = audit.run_audit()
    ex = result["recompute"]["example_1_u2"]
    assert ex["declared_parent_platform"] == "Bili"
    assert ex["actual_source_platform"] == "NGA"
    assert ex["page_claim_correct"] is False


def test_run_audit_deterministic():
    r1 = audit.run_audit()
    r2 = audit.run_audit()
    assert r1["blockers"] == r2["blockers"]
    assert r1["recompute"] == r2["recompute"]
    assert r1["evidence_audit"]["global_match_counts"] == r2["evidence_audit"]["global_match_counts"]
