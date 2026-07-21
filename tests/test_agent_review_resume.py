# -*- coding: utf-8 -*-
"""--resume 运行身份校验：同 run_id 续跑；模型/参数/prompt 变化或数据损坏时阻断。"""
import importlib.util
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _load(rel):
    spec = importlib.util.spec_from_file_location(Path(rel).stem, REPO_ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


runner = _load("tools/calibration/run_agent_reviews.py")


def _items(n):
    return [{"blinded_item_id": f"CAL_{i:04d}",
             "public_evidence_text": "匹配连败很不公平的表达用于生成",
             "parent_context": "", "context_available": "no"} for i in range(1, n + 1)]


def _run(out, items, reviewer="a", provider="mock", model=None, prompt=None,
         temperature=0.0, seed=20260720, resume=False):
    return runner.run_one_reviewer(items, reviewer, out, provider, model, prompt,
                                   True, temperature, seed, None, resume)


# ---- 4.1 同 run_id 正常续跑 ----

def test_resume_same_run_id_appends_new_items(tmp_path):
    out = tmp_path / "reviews"
    r1 = _run(out, _items(2))
    assert r1["parsed_ok"] == 2 and not r1.get("error")
    # 同参数续跑，输入扩到 4 条：跳过已完成 2 条，追加 2 条
    r2 = _run(out, _items(4), resume=True)
    assert not r2.get("error")
    assert r2["parsed_ok"] == 2
    # 输出共 4 行，run_id 唯一
    lines = [json.loads(x) for x in (out / "agent_reviews_a.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
    assert len(lines) == 4
    assert len({x["run_id"] for x in lines}) == 1


# ---- 4.2 更换模型阻断 ----

def test_resume_model_change_blocks(tmp_path):
    out = tmp_path / "reviews"
    _run(out, _items(2), provider="openai_compatible", model="model-a")
    r = _run(out, _items(2), provider="openai_compatible", model="model-b", resume=True)
    assert r["error"] == "resume_run_id_mismatch"
    assert r["parsed_ok"] == 0 and r["parse_failed"] == 0


# ---- 4.3 参数变化阻断 ----

def test_resume_temperature_change_blocks(tmp_path):
    out = tmp_path / "reviews"
    _run(out, _items(2), temperature=0.0)
    r = _run(out, _items(2), temperature=0.7, resume=True)
    assert r["error"] == "resume_run_id_mismatch"


def test_resume_seed_change_blocks(tmp_path):
    out = tmp_path / "reviews"
    _run(out, _items(2), seed=1)
    r = _run(out, _items(2), seed=2, resume=True)
    assert r["error"] == "resume_run_id_mismatch"


def test_resume_prompt_version_change_blocks(tmp_path):
    out = tmp_path / "reviews"
    _run(out, _items(2))  # 内置 prompt_version=a-1.0
    other = tmp_path / "reviewer_a.md"
    other.write_text("# custom\nprompt_version: a-9.9\n", encoding="utf-8")
    r = _run(out, _items(2), prompt=str(other), resume=True)
    assert r["error"] == "resume_run_id_mismatch"


def test_resume_provider_change_blocks(tmp_path):
    out = tmp_path / "reviews"
    _run(out, _items(2), provider="mock")
    # provider 改为 openai_compatible（dry_run=True 仍走 mock 逻辑，但 run_id 含 provider）
    r = _run(out, _items(2), provider="openai_compatible", resume=True)
    assert r["error"] == "resume_run_id_mismatch"


# ---- 4.4 混合 run_id 阻断 ----

def test_resume_mixed_run_ids_blocks(tmp_path):
    out = tmp_path / "reviews"
    out.mkdir()
    p = out / "agent_reviews_a.jsonl"
    p.write_text(
        json.dumps({"blinded_item_id": "CAL_0001", "run_id": "id-1"}) + "\n"
        + json.dumps({"blinded_item_id": "CAL_0002", "run_id": "id-2"}) + "\n",
        encoding="utf-8")
    r = _run(out, _items(2), resume=True)
    assert r["error"] == "resume_mixed_run_ids"


# ---- 4.5 损坏结果阻断 ----

def test_resume_invalid_json_blocks(tmp_path):
    out = tmp_path / "reviews"
    out.mkdir()
    (out / "agent_reviews_a.jsonl").write_text("这不是合法 JSON\n", encoding="utf-8")
    r = _run(out, _items(2), resume=True)
    assert r["error"] == "resume_output_invalid"


def test_resume_missing_run_id_blocks(tmp_path):
    out = tmp_path / "reviews"
    out.mkdir()
    (out / "agent_reviews_a.jsonl").write_text(
        json.dumps({"blinded_item_id": "CAL_0001"}) + "\n", encoding="utf-8")
    r = _run(out, _items(2), resume=True)
    assert r["error"] == "resume_run_id_missing"


def test_resume_missing_blinded_id_blocks(tmp_path):
    out = tmp_path / "reviews"
    out.mkdir()
    (out / "agent_reviews_a.jsonl").write_text(
        json.dumps({"run_id": "id-1"}) + "\n", encoding="utf-8")
    r = _run(out, _items(2), resume=True)
    assert r["error"] == "resume_output_invalid"


def test_resume_error_has_full_fields(tmp_path):
    out = tmp_path / "reviews"
    _run(out, _items(2), seed=1)
    r = _run(out, _items(2), seed=2, resume=True)
    for k in ["reviewer_id", "error", "message", "expected_run_id", "existing_run_ids",
              "output_path", "parsed_ok", "parse_failed", "elapsed_seconds", "token_estimate"]:
        assert k in r, k
    assert r["existing_run_ids"] and r["expected_run_id"] not in r["existing_run_ids"]


# ---- 4.6 run report 含 run_ids ----

def test_run_report_contains_run_ids(tmp_path):
    out = tmp_path / "reviews"
    rc = runner.main(["--provider", "mock", "--input", str(_write_sample(tmp_path)),
                      "--max-items", "6", "--output", str(out)])
    assert rc == 0
    report = json.loads((out / "run_report.json").read_text(encoding="utf-8"))
    assert set(report["run_ids"]) == {"a", "b", "c"}
    for rid, run_id in report["run_ids"].items():
        assert run_id and f"-{rid}-" in run_id
        assert "mock" in run_id and "t0.0" in run_id and "s20260720" in run_id


def _write_sample(tmp_path):
    import csv
    p = tmp_path / "sample.csv"
    with p.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["blinded_item_id", "public_evidence_text", "parent_context",
                    "context_available", "length_bucket"])
        for i in range(1, 7):
            w.writerow([f"CAL_{i:04d}", "匹配连败很不公平用于生成文本", "", "no", "short"])
    return p
