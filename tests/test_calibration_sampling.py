# -*- coding: utf-8 -*-
"""分层校准抽样校验：确定性、样本量、覆盖与公开表不泄漏原标签/平台。"""
import csv
import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG = REPO_ROOT / "config" / "calibration" / "calibration.yaml"
PUBLIC_SAMPLE = REPO_ROOT / "data" / "calibration" / "calibration_sample.csv"

FORBIDDEN_PUBLIC_COLUMNS = {"platform_source", "current_surface_topic",
                            "current_mechanism_label", "label_source", "review_status",
                            "surface_topic", "mechanism_label"}


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
    main = [r for r in public_rows if r["is_retest"] == "false"]
    retest = [r for r in public_rows if r["is_retest"] == "true"]
    assert len(main) == 300
    assert len(retest) == 30


def test_retest_uses_new_blinded_id():
    _cfg, public_rows, _priv, _report = sampler.build(CONFIG)
    main_ids = {r["blinded_item_id"] for r in public_rows if r["is_retest"] == "false"}
    retest_ids = {r["blinded_item_id"] for r in public_rows if r["is_retest"] == "true"}
    assert main_ids.isdisjoint(retest_ids)
    # 重测项以 retest_group 关联主项，reviewer 看不到该分组（分组仅用于分析）
    for r in public_rows:
        if r["is_retest"] == "true":
            assert r["retest_group_id"]


def test_coverage():
    _cfg, _pub, _priv, report = sampler.build(CONFIG)
    cov = report["coverage"]
    assert len(cov["platform_source"]) == 3
    # 五类具体机制 + uncertain 均有覆盖
    for mech in ["competence_frustration", "fairness_threat", "trust_communication_gap",
                 "belonging_drop", "norm_safety_risk", "uncertain"]:
        assert cov["mechanism_label"].get(mech, 0) >= 1, mech
    # 两种编码来源、两种纳入状态、三种长度桶
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
