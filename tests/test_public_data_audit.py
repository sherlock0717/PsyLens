# -*- coding: utf-8 -*-
"""tools/audit_public_data.py 的特征测试（characterization tests）。

原则：
  - 测试不修改任何历史公开数据。
  - 测试为离线、确定性；不联网、不调用模型、不读取密钥。
  - 覆盖纯函数、多候选匹配、指标拆分，以及对真实公开数据的端到端断言。
"""
import importlib.util
import json
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


# --------------------------- Phase 1A：v2 数据底座 ---------------------------
# 加载生成脚本模块
_v2spec = importlib.util.spec_from_file_location("build_v2_dataset", REPO_ROOT / "tools" / "build_v2_dataset.py")
build_v2 = importlib.util.module_from_spec(_v2spec)
sys.modules["build_v2_dataset"] = build_v2
_v2spec.loader.exec_module(build_v2)

V2_DIR = REPO_ROOT / "data" / "v2"
V2_CSV_NAMES = ["samples_v2.csv", "evidence_v2.csv", "ambiguous_evidence_queue.csv",
                "bili_evidence_queue.csv", "id_migration.csv"]
V2_ALL_NAMES = V2_CSV_NAMES + ["v2_manifest.json"]

# 正式快照的固定参数（用于确定性测试；与已提交 data/v2 一致）
FIXED_GENERATED_AT = "2026-07-17T16:56:33.578346+08:00"
FIXED_SOURCE_COMMIT = "371d245a0ce82ed5d980472147b49568525e2986"


def _read_csv(path):
    import csv as _csv
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(_csv.DictReader(f))


def _sha256(path):
    import hashlib
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _hashes(dir_path, names):
    return {n: _sha256(dir_path / n) for n in names}


# ---- 生成器：隔离到 tmp_path，不写入 tracked data/v2 ----
def test_v2_generator_deterministic_full_snapshot(tmp_path):
    """固定 generated_at/source_data_commit，连续生成两次，六个输出文件 SHA-256 全部一致。"""
    out1 = tmp_path / "v2a"
    out2 = tmp_path / "v2b"
    build_v2.build_v2_dataset(out1, FIXED_GENERATED_AT, FIXED_SOURCE_COMMIT)
    build_v2.build_v2_dataset(out2, FIXED_GENERATED_AT, FIXED_SOURCE_COMMIT)
    h1 = _hashes(out1, V2_ALL_NAMES)
    h2 = _hashes(out2, V2_ALL_NAMES)
    assert h1 == h2
    assert set(h1) == set(V2_ALL_NAMES)  # 六个文件齐全（含 manifest）


def test_v2_generator_does_not_touch_tracked_dir(tmp_path):
    """生成器测试运行前后，仓库 data/v2/ 的文件哈希保持不变（不修改 tracked 文件）。"""
    before = _hashes(V2_DIR, V2_ALL_NAMES)
    build_v2.build_v2_dataset(tmp_path / "v2", FIXED_GENERATED_AT, FIXED_SOURCE_COMMIT)
    after = _hashes(V2_DIR, V2_ALL_NAMES)
    assert before == after


def test_v2_generator_snapshot_matches_committed(tmp_path):
    """固定参数生成的六个文件应与已提交 data/v2 快照字节一致。"""
    out = tmp_path / "v2"
    build_v2.build_v2_dataset(out, FIXED_GENERATED_AT, FIXED_SOURCE_COMMIT)
    assert _hashes(out, V2_ALL_NAMES) == _hashes(V2_DIR, V2_ALL_NAMES)


def test_v2_manifest_uses_passed_source_commit_and_posix(tmp_path):
    out = tmp_path / "v2"
    manifest = build_v2.build_v2_dataset(out, FIXED_GENERATED_AT, "DEADBEEF_TEST_COMMIT")
    assert manifest["source_data_commit"] == "DEADBEEF_TEST_COMMIT"
    assert manifest["generated_at"] == FIXED_GENERATED_AT
    # source_files 路径均为 POSIX（无反斜杠、非绝对路径）
    for v in manifest["source_files"].values():
        assert "\\" not in v
        assert not v.startswith("/")
        assert "/" in v
    on_disk = json.loads((out / "v2_manifest.json").read_text(encoding="utf-8"))
    assert on_disk["source_data_commit"] == "DEADBEEF_TEST_COMMIT"
    assert on_disk["source_files"] == manifest["source_files"]


# ---- sample ID 稳定性：打乱输入行顺序，映射不变 ----
def test_v2_sample_id_mapping_stable_under_shuffle():
    import random
    _, clean_rows = audit.read_csv_rows(audit.CLEAN_CSV)
    _, map1 = build_v2.build_sample_ids(list(clean_rows))
    shuffled = list(clean_rows)
    random.Random(20260717).shuffle(shuffled)
    _, map2 = build_v2.build_sample_ids(shuffled)
    assert map1 == map2
    # 且与已提交快照一致
    committed = {r["legacy_clean_id"]: r["sample_id"] for r in _read_csv(V2_DIR / "samples_v2.csv")}
    assert map1 == committed


# ---- evidence unit_index 保留 legacy _uN 后缀（不压缩计数器）----
def test_v2_unit_index_preserves_legacy_suffix():
    ev = _read_csv(V2_DIR / "evidence_v2.csv")
    for r in ev:
        legacy_ui = build_v2.parse_legacy_unit_index(r["legacy_evidence_id"])
        assert legacy_ui is not None
        assert int(r["unit_index"]) == legacy_ui
        u_suffix = int(r["evidence_id"].rsplit("_U", 1)[1])
        assert u_suffix == legacy_ui


def test_v2_no_unit_index_conflict():
    ev = _read_csv(V2_DIR / "evidence_v2.csv")
    seen = set()
    for r in ev:
        key = (r["sample_id"], r["unit_index"])
        assert key not in seen, f"unit_index 冲突: {key}"
        seen.add(key)


# ---- 只读校验：直接读取已提交 data/v2 快照 ----
def test_v2_samples_count_and_platforms():
    rows = _read_csv(V2_DIR / "samples_v2.csv")
    assert len(rows) == 360
    plat = Counter(r["platform_source"] for r in rows)
    assert plat["Bili"] == 120 and plat["NGA"] == 120 and plat["Tieba"] == 120


def test_v2_sample_id_unique_and_format():
    rows = _read_csv(V2_DIR / "samples_v2.csv")
    ids = [r["sample_id"] for r in rows]
    assert len(set(ids)) == len(ids)
    assert all(re.match(r"^(BILI|NGA|TIEBA)_\d{4}$", i) for i in ids)


def test_v2_samples_fields_match_legacy_clean():
    """samples_v2 的 legacy_clean_id / raw_text / source_url / platform_source 与 legacy clean 逐行一致。"""
    _, legacy = audit.read_csv_rows(audit.CLEAN_CSV)
    legacy_by_id = {str(r.get("id")): r for r in legacy}
    for r in _read_csv(V2_DIR / "samples_v2.csv"):
        lrow = legacy_by_id[r["legacy_clean_id"]]
        assert r["raw_text"] == lrow.get("raw_text", "")
        assert r["source_url"] == lrow.get("url", "")
        assert r["platform_source"] == lrow.get("platform_source", "")


def test_v2_migrated_evidence_count_695():
    rows = _read_csv(V2_DIR / "evidence_v2.csv")
    assert len(rows) == 695


def test_v2_ambiguous_not_auto_migrated():
    amb = _read_csv(V2_DIR / "ambiguous_evidence_queue.csv")
    assert len(amb) == 2
    ev = _read_csv(V2_DIR / "evidence_v2.csv")
    migrated_legacy = {r["legacy_evidence_id"] for r in ev}
    amb_legacy = {r["legacy_evidence_id"] for r in amb}
    assert amb_legacy.isdisjoint(migrated_legacy)
    assert all(r["resolution_status"] == "pending_human_resolution" for r in amb)


def test_v2_evidence_id_unique_and_prefix_matches_sample():
    ev = _read_csv(V2_DIR / "evidence_v2.csv")
    ids = [r["evidence_id"] for r in ev]
    assert len(set(ids)) == len(ids)
    for r in ev:
        assert r["evidence_id"].startswith(r["sample_id"] + "_U")
        assert re.match(r"^(BILI|NGA|TIEBA)_\d{4}_U\d{2}$", r["evidence_id"])


def test_v2_unit_text_matches_sample_rawtext():
    samples = {r["sample_id"]: r for r in _read_csv(V2_DIR / "samples_v2.csv")}
    ev = _read_csv(V2_DIR / "evidence_v2.csv")
    for r in ev:
        nu = audit.normalize_text(r["unit_text"])
        nsamp = audit.normalize_text(samples[r["sample_id"]]["raw_text"])
        assert nu and nu in nsamp


def test_v2_legacy_evidence_id_no_duplicate():
    ev = _read_csv(V2_DIR / "evidence_v2.csv")
    legacy = [r["legacy_evidence_id"] for r in ev]
    assert len(set(legacy)) == len(legacy)


def test_v2_review_status_all_unreviewed_no_human_reviewed():
    ev = _read_csv(V2_DIR / "evidence_v2.csv")
    statuses = {r["review_status"] for r in ev}
    assert statuses == {"legacy_ai_label_unreviewed"}
    forbidden = {"human_reviewed", "human_curated", "verified", "approved"}
    assert not (statuses & forbidden)


def test_v2_bili_queue_full_integrity():
    samples = _read_csv(V2_DIR / "samples_v2.csv")
    bili_samples = {r["sample_id"] for r in samples if r["platform_source"] == "Bili"}
    sample_raw = {r["sample_id"]: r["raw_text"] for r in samples}
    bili = _read_csv(V2_DIR / "bili_evidence_queue.csv")
    covered = {r["sample_id"] for r in bili}
    # 集合完全相等（不只是子集），不混入非 Bili
    assert covered == bili_samples
    assert len(bili_samples) == 120
    # queue_id 唯一
    qids = [r["queue_id"] for r in bili]
    assert len(set(qids)) == len(qids)
    # 每个 sample 内 candidate_unit_index 连续且唯一
    per_sample = {}
    for r in bili:
        per_sample.setdefault(r["sample_id"], []).append(int(r["candidate_unit_index"]))
    for sid, idxs in per_sample.items():
        assert sorted(idxs) == list(range(1, len(idxs) + 1)), sid
    # candidate_unit_text 可在 sample.raw_text 定位；queue raw_text 与 samples_v2 一致
    for r in bili:
        assert r["raw_text"] == sample_raw[r["sample_id"]]
        ncand = audit.normalize_text(r["candidate_unit_text"])
        nsamp = audit.normalize_text(sample_raw[r["sample_id"]])
        assert ncand and ncand in nsamp
        assert (r["mechanism_label_candidate"] or "").strip() in ("", "unassigned")
        assert r["candidate_status"] == "pending_review"
        assert r["human_review_status"] == "not_reviewed"


def test_v2_manifest_counts_and_sha256():
    manifest = json.loads((V2_DIR / "v2_manifest.json").read_text(encoding="utf-8"))
    assert manifest["sample_count"] == 360
    assert manifest["migrated_evidence_count"] == 695
    assert manifest["ambiguous_evidence_count"] == 2
    assert manifest["source_data_commit"] == FIXED_SOURCE_COMMIT
    # bili_candidate_unit_count 必须与实际队列行数一致（不写死）
    bili = _read_csv(V2_DIR / "bili_evidence_queue.csv")
    assert manifest["bili_candidate_unit_count"] == len(bili)
    assert manifest["bili_samples_pending"] == 120
    # source_files 为 POSIX 相对路径
    for v in manifest["source_files"].values():
        assert "\\" not in v and not v.startswith("/")
    for name, expected in manifest["hashes"].items():
        assert _sha256(V2_DIR / name) == expected, f"{name} SHA-256 不一致"


def test_v2_id_migration_breakdown():
    v2 = audit.run_v2_audit()
    bd = v2["id_migration_breakdown"]
    assert bd["clean_sample_migrated"] == 360
    assert bd["evidence_migrated"] == 695
    assert bd["evidence_pending"] == 2
    assert bd["insight_deferred"] == 1
    assert bd["action_deferred"] == 1


def test_v2_audit_layered_status():
    combined = audit.run_combined_audit("both")
    assert combined["legacy_status"] == "BLOCKED"
    assert combined["v2_migration_status"] == "PASS"
    assert combined["publication_readiness"] == "BLOCKED"


def test_v2_audit_no_invalid_new_ids():
    v2 = audit.run_v2_audit()
    assert v2["v2_migration_status"] == "PASS"
    assert v2["issues"] == []


def test_legacy_phase0_still_blocked():
    # 原有 Phase 0 审计继续 BLOCKED（未因 v2 改动而放松）
    result = audit.run_audit()
    assert result["phase0_status"] == "BLOCKED"
