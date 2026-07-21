# -*- coding: utf-8 -*-
"""代理复检 schema 与输出校验：合法标签、必填字段、解析失败进入队列不静默丢弃。"""
import importlib.util
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA = REPO_ROOT / "data" / "calibration" / "agent_review_schema.json"


def _load(rel):
    spec = importlib.util.spec_from_file_location(Path(rel).stem, REPO_ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


runner = _load("tools/calibration/run_agent_reviews.py")


def test_schema_structure():
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    props = schema["properties"]
    assert set(schema["required"]).issubset(props)
    assert props["mechanism_label"]["enum"] == runner.ALLOWED_MECH
    assert len(props["boundary_status"]["enum"]) == 5
    assert set(props["confidence_band"]["enum"]) == {"high", "medium", "low"}
    assert len(props["abstain_reason"]["enum"]) == 6
    # reviewer 不可见字段包含当前标签与平台
    for hidden in ["current_mechanism_label", "label_source", "platform_source",
                   "review_status", "other_reviewer_results"]:
        assert hidden in schema["reviewer_hidden_fields"]


def _item(text, blinded="CAL_0001", src="NGA_0001_U01"):
    return {"blinded_item_id": blinded, "public_evidence_text": text,
            "parent_context": text, "context_available": "yes", "_source_evidence_id": src}


def test_mock_review_is_valid():
    row = runner.mock_review(_item("这个英雄强度太低了根本打不出输出"), "b",
                             "run", "mock", "b-1.0", "sha")
    assert runner.validate(row) == []
    assert row["mechanism_label"] in runner.ALLOWED_MECH
    for field in runner.REQUIRED_FIELDS:
        assert field in row


def test_validate_flags_missing_and_invalid():
    row = runner.mock_review(_item("测试文本足够长用于判断"), "a", "r", "mock", "a-1.0", "sha")
    bad = dict(row)
    del bad["created_at"]
    assert "created_at" in runner.validate(bad)
    bad2 = dict(row)
    bad2["mechanism_label"] = "not_a_label"
    assert "mechanism_label:invalid" in runner.validate(bad2)


def test_reviewer_input_hides_labels():
    rows = [{"blinded_item_id": "CAL_0001", "source_evidence_id": "NGA_0001_U01",
             "public_evidence_text": "文本", "parent_context": "父文本",
             "context_available": "yes", "mechanism_label": "fairness_threat",
             "surface_topic": "balance", "platform_source": "NGA"}]
    items = runner.reviewer_input(rows)
    keys = set(items[0].keys())
    for hidden in ["mechanism_label", "surface_topic", "platform_source"]:
        assert hidden not in keys, hidden
    assert "public_evidence_text" in keys


def test_parse_failure_goes_to_retry_queue(tmp_path):
    # 构造一条会解析失败的输入（空 blinded/文本），确认写入 retry_queue 而非丢弃
    items = [{"blinded_item_id": "CAL_X", "public_evidence_text": "有效文本用于生成",
              "parent_context": "", "context_available": "no",
              "_source_evidence_id": "NGA_9999_U01"}]
    out = tmp_path / "reviews"
    # 猴子补丁：让 mock_review 产出缺字段的行，验证进入 retry_queue
    orig = runner.mock_review

    def broken(item, rid, *a, **k):
        row = orig(item, rid, *a, **k)
        del row["confidence_band"]
        return row

    runner.mock_review = broken
    try:
        result = runner.run_one_reviewer(items, "a", out, "mock", None, None, True)
    finally:
        runner.mock_review = orig
    assert result["parse_failed"] == 1
    assert result["parsed_ok"] == 0
    assert (out / "retry_queue.jsonl").exists()
