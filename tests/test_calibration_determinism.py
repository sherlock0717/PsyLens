# -*- coding: utf-8 -*-
"""确定性校验：相同配置/输入重复运行得到相同抽样与相同 mock 复检结果。"""
import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG = REPO_ROOT / "config" / "calibration" / "calibration.yaml"


def _load(rel):
    spec = importlib.util.spec_from_file_location(Path(rel).stem, REPO_ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


sampler = _load("tools/calibration/build_calibration_sample.py")
runner = _load("tools/calibration/run_agent_reviews.py")
consensus = _load("tools/calibration/build_agent_consensus.py")


def test_sampling_is_deterministic():
    _c1, pub1, priv1, rep1 = sampler.build(CONFIG)
    _c2, pub2, priv2, rep2 = sampler.build(CONFIG)
    assert pub1 == pub2
    assert priv1 == priv2
    assert rep1 == rep2


def test_mock_review_is_deterministic():
    item = {"blinded_item_id": "CAL_0001", "public_evidence_text": "匹配机制导致连败连胜很不公平",
            "parent_context": "", "context_available": "no", "_source_evidence_id": "NGA_1_U01"}
    r1 = runner.mock_review(item, "c", "run", "mock", "c-1.0", "sha")
    r2 = runner.mock_review(item, "c", "run", "mock", "c-1.0", "sha")
    assert r1 == r2


def test_consensus_is_deterministic():
    sample_rows = [{"blinded_item_id": "CAL_0001", "source_evidence_id": "E1",
                    "is_retest": "false", "retest_group_id": ""}]
    reviews = {k: [{"blinded_item_id": "CAL_0001", "mechanism_label": "fairness_threat",
                    "surface_topic": "balance", "boundary_status": "complete", "evidence_id": "E1"}]
               for k in ("a", "b", "c")}
    r1, s1 = consensus.build_consensus(reviews, sample_rows, [])
    r2, s2 = consensus.build_consensus(reviews, sample_rows, [])
    assert r1 == r2
    assert s1 == s2
