# -*- coding: utf-8 -*-
"""分层校准抽样校验：确定性、样本量、覆盖，以及公开表不泄漏来源/平台/重测关系。"""
import csv
import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG = REPO_ROOT / "config" / "calibration" / "calibration.yaml"
PUBLIC_SAMPLE = REPO_ROOT / "data" / "calibration" / "calibration_sample.csv"

# 公开校准表禁止出现的列：来源编号、平台、当前标签、复核状态、分层与重测关系。
FORBIDDEN_PUBLIC_COLUMNS = {"source_evidence_id", "platform_source", "current_surface_topic",
                            "current_mechanism_label", "label_source", "review_status",
                            "surface_topic", "mechanism_label", "sampling_stratum",
                            "is_retest", "retest_group_id"}
# 三个平台的真实标识，公开表列名与取值都不得出现。
PLATFORM_TOKENS = ["BILI", "NGA", "TIEBA", "Bili", "Tieba", "bili", "nga", "tieba"]


def _load(rel):
    spec = importlib.util.spec_from_file_location(Path(rel).stem, REPO_ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


sampler = _load("tools/calibration/build_calibration_sample.py")


def test_sample_counts():
    _cfg, public_rows, private_rows, report = sampler.build(CONFIG)
    assert report["main_sample_count"] == 300
    assert report["retest_count"] == 30
    assert len(public_rows) == 330
    assert len(private_rows) == 330
    # 重测标记只在私有映射
    main = [r for r in private_rows if r["is_retest"] == "false"]
    retest = [r for r in private_rows if r["is_retest"] == "true"]
    assert len(main) == 300
    assert len(retest) == 30


def test_public_rows_only_blinded_fields():
    _cfg, public_rows, _priv, _report = sampler.build(CONFIG)
    for r in public_rows:
        assert set(r.keys()) == set(sampler.PUBLIC_FIELDS)
        assert FORBIDDEN_PUBLIC_COLUMNS.isdisjoint(r.keys())


def test_retest_relation_only_in_private():
    _cfg, public_rows, private_rows, _report = sampler.build(CONFIG)
    # 公开行没有 is_retest / retest_group_id / source_evidence_id
    for r in public_rows:
        assert "is_retest" not in r
        assert "retest_group_id" not in r
        assert "source_evidence_id" not in r
    # 主项与重测项的盲测编号互不相同
    main_ids = {r["blinded_item_id"] for r in private_rows if r["is_retest"] == "false"}
    retest_ids = {r["blinded_item_id"] for r in private_rows if r["is_retest"] == "true"}
    assert main_ids.isdisjoint(retest_ids)
    # 每个重测项在私有映射里都有 retest_group_id
    for r in private_rows:
        if r["is_retest"] == "true":
            assert r["retest_group_id"]


def test_coverage():
    _cfg, _pub, _priv, report = sampler.build(CONFIG)
    cov = report["coverage"]
    assert len(cov["platform_source"]) == 3
    for mech in ["competence_frustration", "fairness_threat", "trust_communication_gap",
                 "belonging_drop", "norm_safety_risk", "uncertain"]:
        assert cov["mechanism_label"].get(mech, 0) >= 1, mech
    assert len(cov["label_source"]) >= 2
    assert len(cov["analysis_inclusion_status"]) >= 2
    assert set(cov["length_bucket"]).issubset({"short", "medium", "long"})
    assert len(cov["length_bucket"]) >= 2


def test_deterministic_same_seed():
    _c1, pub1, _p1, _r1 = sampler.build(CONFIG)
    _c2, pub2, _p2, _r2 = sampler.build(CONFIG)
    assert pub1 == pub2


def test_public_sample_no_leaked_columns():
    assert PUBLIC_SAMPLE.exists(), "需先运行 build_calibration_sample.py 生成公开样本"
    with PUBLIC_SAMPLE.open("r", encoding="utf-8-sig", newline="") as f:
        header = set(next(csv.reader(f)))
    assert FORBIDDEN_PUBLIC_COLUMNS.isdisjoint(header), header
    assert header == set(sampler.PUBLIC_FIELDS)


def test_public_csv_cannot_identify_platform():
    """公开 CSV 的列名和取值都不能识别出 BILI/NGA/TIEBA。"""
    assert PUBLIC_SAMPLE.exists()
    raw = PUBLIC_SAMPLE.read_text(encoding="utf-8")
    with PUBLIC_SAMPLE.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        header = next(reader)
        # 列名不含平台标识
        for token in PLATFORM_TOKENS:
            assert token not in " ".join(header)
        # blinded_item_id 一律为 CAL_ 前缀，不携带平台缩写
        bid = header.index("blinded_item_id")
        for row in reader:
            assert row[bid].startswith(("CAL_", "CAL_R"))
    # 整表不出现平台缩写标识（正文脱敏文本可能含中文平台词，此处只查缩写）
    for token in ["BILI", "NGA", "TIEBA"]:
        assert token not in raw, token


def test_private_key_recovers_source_and_retest():
    """私有映射能正确恢复来源编号与重测组，并与公开盲测编号一一对应。"""
    _cfg, public_rows, private_rows, _report = sampler.build(CONFIG)
    pub_ids = {r["blinded_item_id"] for r in public_rows}
    priv_by_id = {r["blinded_item_id"]: r for r in private_rows}
    # 私有与公开盲测编号一一对应
    assert set(priv_by_id) == pub_ids
    # 每条私有记录都能给出来源编号
    for r in private_rows:
        assert r["source_evidence_id"]
    # 重测组能把重测项映射回同一来源的主项
    for r in private_rows:
        if r["is_retest"] == "true":
            grp = r["retest_group_id"]
            mains = [m for m in private_rows if m["is_retest"] == "false"
                     and m["retest_group_id"] == grp]
            assert len(mains) == 1
            assert mains[0]["source_evidence_id"] == r["source_evidence_id"]
