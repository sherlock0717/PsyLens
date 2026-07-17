# -*- coding: utf-8 -*-
"""tools/audit_public_data.py 的特征测试（characterization tests）。

原则：
  - 测试不修改任何历史公开数据。
  - 测试为离线、确定性；不联网、不调用模型、不读取密钥。
  - 覆盖纯函数、多候选匹配、指标拆分，以及对真实公开数据的端到端断言。
"""
import importlib.util
import re
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "tools" / "audit_public_data.py"

spec = importlib.util.spec_from_file_location("audit_public_data", MODULE_PATH)
audit = importlib.util.module_from_spec(spec)
sys.modules["audit_public_data"] = audit
spec.loader.exec_module(audit)


# --------------------------- 纯函数测试 ---------------------------
def test_normalize_fullwidth_and_whitespace():
    assert audit.normalize_text("ＡＢＣ　１２３") == "abc123"
    assert audit.normalize_text("  hello   world  ") == "helloworld"


def test_normalize_punctuation_unify():
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


# ---- Phase 0 快照（问题状态）：保留 ----
def test_run_audit_is_blocked_due_to_parent_offset():
    result = audit.run_audit()
    assert result["phase0_status"] == "BLOCKED"
    assert len(result["blockers"]) >= 1


def test_run_audit_supporting_ids_all_exist():
    result = audit.run_audit()
    assert result["insights_audit"]["missing_support_lines"] == []
    assert result["insights_audit"]["empty_supporting_lines"] == []


# ---- 新增：parent 指标拆分 ----
def test_parent_reference_exists_rate_is_one():
    result = audit.run_audit()
    assert result["evidence_audit"]["parent_reference_exists_rate"] == 1.0


def test_parent_semantic_linkage_rate_is_zero():
    result = audit.run_audit()
    assert result["evidence_audit"]["parent_semantic_linkage_rate"] == 0.0


# ---- 新增：多候选匹配 ----
def test_global_match_categories_present():
    result = audit.run_audit()
    ea = result["evidence_audit"]
    # 唯一命中 + 歧义命中 + 未找到 = 全部证据（found_in_declared_parent 本轮为 0）
    total = (ea["unique_match_count"] + ea["ambiguous_match_count"] + ea["not_found_count"])
    assert total == ea["total_rows"]
    assert ea["ambiguous_match_count"] >= 1  # 存在多候选歧义命中


def test_ambiguous_matches_not_assigned_platform():
    # 歧义命中不得计入实际出处平台分布（仅唯一命中计入）
    result = audit.run_audit()
    ea = result["evidence_audit"]
    plat_total = sum(ea["actual_source_platform_distribution_unique_only"].values())
    assert plat_total == ea["unique_match_count"]
    # 歧义示例中允许跨平台候选，但不得出现在平台分布计数里
    assert plat_total + ea["ambiguous_match_count"] + ea["not_found_count"] == ea["total_rows"]


def test_only_unique_matches_have_offset():
    # 唯一命中偏移直方图总数 == unique_match_in_other_id 数
    result = audit.run_audit()
    ea = result["evidence_audit"]
    hist_total = sum(ea["unique_offset_histogram"].values())
    assert hist_total == ea["unique_match_in_other_id_count"]
    # 本轮偏移应为纯 +120
    assert ea["unique_offset_histogram"] == {"120": 695}


# ---- 新增：confidence 与 needs_human_review 分开统计 ----
def test_confidence_and_review_are_separate_fields():
    result = audit.run_audit()
    ia = result["insights_audit"]
    assert ia["high_confidence_count"] == 7          # confidence=high
    assert ia["no_review_flag_count"] == 8           # needs_human_review=false
    assert ia["high_confidence_and_no_review_flag_count"] == 7
    # 二者不相等，证明是不同字段
    assert ia["high_confidence_count"] != ia["no_review_flag_count"]


# ---- 新增：1_u2 平台错误（据实核对）----
def test_run_audit_example_1u2_platform_mismatch():
    result = audit.run_audit()
    ex = result["recompute"]["example_1_u2"]
    assert ex["declared_parent_platform"] == "Bili"
    assert ex["actual_source_platform"] == "NGA"
    assert ex["candidate_count"] == 1
    assert ex["chain_closed"] is False


# ---- 新增：不生成不存在的 evidence_id ----
def test_audit_never_invents_nonexistent_evidence_ids():
    # 审计输出中出现的所有 evidence_id 必须真实存在于证据表
    result = audit.run_audit()
    _, evidence_rows = audit.read_csv_rows(audit.EVIDENCE_CSV)
    real_ids = {str(r.get("id")) for r in evidence_rows}
    for row in result["evidence_audit"]["linkage_rows"]:
        assert row["evidence_id"] in real_ids
    # 洞察 supporting_ids 亦不得引入证据表以外的 id（缺失应被检出，而非被伪造为存在）
    assert result["insights_audit"]["missing_support_lines"] == []


# ---- 新增：不得声称“数据真实性已证明” ----
def test_no_data_authenticity_claim_in_output():
    result = audit.run_audit()
    dump = str(result)
    for banned in ["数据真实性", "采集真实性", "来源真实性", "人工复核真实性"]:
        assert banned not in dump


def test_run_audit_deterministic():
    r1 = audit.run_audit()
    r2 = audit.run_audit()
    assert r1["blockers"] == r2["blockers"]
    assert r1["recompute"] == r2["recompute"]
    assert r1["evidence_audit"]["global_match_counts"] == r2["evidence_audit"]["global_match_counts"]


# --------------------------- 报告一致性校验 ---------------------------
DOCS_AUDIT = REPO_ROOT / "docs" / "audit"


def _parse_claim_statuses():
    """从 PUBLIC_CLAIM_AUDIT.md 的主张核对表逐行提取 (claim_id, status)。"""
    text = (DOCS_AUDIT / "PUBLIC_CLAIM_AUDIT.md").read_text(encoding="utf-8")
    statuses = {}
    valid = {"verified", "partially_verified", "unsupported", "contradicted", "unclear"}
    for line in text.splitlines():
        m = re.match(r"^\|\s*(C\d{2})\s*\|", line)
        if not m:
            continue
        cid = m.group(1)
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        # 状态列可能带 ** 强调，取第一个命中的合法状态词
        found = None
        for cell in cells:
            token = cell.replace("*", "").strip()
            if token in valid:
                found = token
                break
        assert found is not None, f"{cid} 未找到合法状态: {line}"
        statuses[cid] = found
    return statuses


def test_public_claim_status_totals_consistent():
    """PHASE0_SUMMARY 的状态计数之和 == PUBLIC_CLAIM_AUDIT 的 claim_id 数量，
    且各状态分项与逐条状态一致。"""
    statuses = _parse_claim_statuses()
    n_claims = len(statuses)
    assert n_claims == 22  # C01-C22

    counts = Counter(statuses.values())
    # 逐条状态汇总
    assert counts["verified"] == 15
    assert counts["partially_verified"] == 4
    assert counts["unsupported"] == 2
    assert counts["contradicted"] == 1
    # 各状态数量之和 == claim_id 数量
    assert sum(counts.values()) == n_claims

    # PHASE0_SUMMARY 中声明的合计必须与 claim_id 数量一致
    summary = (DOCS_AUDIT / "PHASE0_SUMMARY.md").read_text(encoding="utf-8")
    m = re.search(r"verified\s*(\d+)、partially_verified\s*(\d+)、unsupported\s*(\d+)、contradicted\s*(\d+)", summary)
    assert m is not None, "PHASE0_SUMMARY 未找到状态计数声明"
    declared = [int(x) for x in m.groups()]
    assert declared == [counts["verified"], counts["partially_verified"],
                        counts["unsupported"], counts["contradicted"]]
    assert sum(declared) == n_claims
