# -*- coding: utf-8 -*-
"""共识与争议逻辑校验：3/3、2/3、分歧、熵、重测一致率、分母、空输入、非金标准。"""
import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _load(rel):
    spec = importlib.util.spec_from_file_location(Path(rel).stem, REPO_ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


consensus = _load("tools/calibration/build_agent_consensus.py")


def _rev(blinded, mech, topic="balance", boundary="complete", eid="E"):
    return {"blinded_item_id": blinded, "mechanism_label": mech, "surface_topic": topic,
            "boundary_status": boundary, "evidence_id": eid}


def _fixture():
    sample_rows = [
        {"blinded_item_id": "CAL_0001", "source_evidence_id": "E1", "is_retest": "false", "retest_group_id": "RT1"},
        {"blinded_item_id": "CAL_0002", "source_evidence_id": "E2", "is_retest": "false", "retest_group_id": ""},
        {"blinded_item_id": "CAL_0003", "source_evidence_id": "E3", "is_retest": "false", "retest_group_id": ""},
        {"blinded_item_id": "CAL_R1", "source_evidence_id": "E1", "is_retest": "true", "retest_group_id": "RT1"},
    ]
    reviews = {
        "a": [_rev("CAL_0001", "competence_frustration"), _rev("CAL_0002", "fairness_threat"),
              _rev("CAL_0003", "competence_frustration"), _rev("CAL_R1", "competence_frustration")],
        "b": [_rev("CAL_0001", "competence_frustration"), _rev("CAL_0002", "fairness_threat"),
              _rev("CAL_0003", "fairness_threat"), _rev("CAL_R1", "competence_frustration")],
        "c": [_rev("CAL_0001", "competence_frustration"), _rev("CAL_0002", "uncertain"),
              _rev("CAL_0003", "uncertain"), _rev("CAL_R1", "competence_frustration")],
    }
    return reviews, sample_rows


def test_agreement_levels_and_consensus():
    reviews, sample_rows = _fixture()
    rows, _stats = consensus.build_consensus(reviews, sample_rows, [])
    by_src = {r["source_evidence_id"]: r for r in rows}
    # 3/3 一致
    assert by_src["E1"]["agreement_level"] == "unanimous"
    assert by_src["E1"]["consensus_mechanism"] == "competence_frustration"
    assert by_src["E1"]["mechanism_entropy"] == 0.0
    assert by_src["E1"]["needs_adjudication"] == "no"
    # 2/3 多数
    assert by_src["E2"]["agreement_level"] == "majority"
    assert by_src["E2"]["consensus_mechanism"] == "fairness_threat"
    assert by_src["E2"]["needs_adjudication"] == "yes"
    # 三路分歧
    assert by_src["E3"]["agreement_level"] == "disputed"
    assert by_src["E3"]["consensus_mechanism"] == ""
    assert by_src["E3"]["mechanism_entropy"] > 1.5


def test_stats_denominators_and_retest():
    reviews, sample_rows = _fixture()
    _rows, stats = consensus.build_consensus(reviews, sample_rows, [])
    assert stats["item_count"] == 3
    assert stats["three_way_agreement"] == {"rate": round(1 / 3, 4), "numerator": 1, "denominator": 3}
    assert stats["majority_agreement"]["numerator"] == 2
    # 重测：同一 reviewer 主项与重测项标签一致，3 名一致 -> 3/3
    assert stats["retest_consistency"]["numerator"] == 3
    assert stats["retest_consistency"]["denominator"] == 3
    assert stats["retest_consistency"]["rate"] == 1.0


def test_entropy_values():
    assert consensus.entropy(["x", "x", "x"]) == 0.0
    assert consensus.entropy(["x", "y", "z"]) > 1.5
    assert consensus.entropy([]) == 0.0


def test_empty_input_is_safe():
    rows, stats = consensus.build_consensus({"a": [], "b": [], "c": []}, [], [])
    assert rows == []
    assert stats["item_count"] == 0
    assert stats["three_way_agreement"]["rate"] is None


def test_consensus_not_named_gold():
    # 共识字段与统计中不得出现 gold / 金标准 命名
    joined = " ".join(consensus.CONSENSUS_FIELDS).lower()
    assert "gold" not in joined
    reviews, sample_rows = _fixture()
    _rows, stats = consensus.build_consensus(reviews, sample_rows, [])
    assert "金标准" in stats["note"] and "不是" in stats["note"]
