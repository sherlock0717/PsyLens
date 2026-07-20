# -*- coding: utf-8 -*-
"""评测器校验：tmp_path 隔离、指标真实分子分母、输入变化指标随之变化、人工复核状态真实计算。"""
import csv
import importlib.util
import shutil
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
V2_DIR = REPO_ROOT / "data" / "v2"


def _load(name):
    spec = importlib.util.spec_from_file_location(name, REPO_ROOT / "tools" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


evaluator = _load("evaluate_v2")


def _copy_v2(tmp_path):
    dst = tmp_path / "v2"
    shutil.copytree(V2_DIR, dst)
    return dst


def test_output_dir_isolated(tmp_path):
    out = tmp_path / "out"
    r = evaluator.evaluate(input_dir=V2_DIR, output_dir=out)
    assert (out / "evaluation_report.json").exists()
    # 不写回 data/v2（输出到 tmp）
    assert r["structural_integrity_status"] == "PASS"


def test_metrics_have_numerator_denominator(tmp_path):
    r = evaluator.evaluate(input_dir=V2_DIR, output_dir=tmp_path)
    for name, mm in r["metrics"].items():
        assert set(["value", "numerator", "denominator", "status", "plain_explanation"]).issubset(mm), name


def test_metric_changes_when_input_changes(tmp_path):
    base = evaluator.evaluate(input_dir=V2_DIR, output_dir=tmp_path / "a")
    dst = _copy_v2(tmp_path)
    # 删除若干 provisional 证据行
    prov = dst / "evidence_provisional_v2.csv"
    with prov.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.reader(f))
    header, body = rows[0], rows[1:]
    trimmed = [header] + body[:-10]
    with prov.open("w", encoding="utf-8", newline="") as f:
        csv.writer(f).writerows(trimmed)
    changed = evaluator.evaluate(input_dir=dst, output_dir=tmp_path / "b")
    assert changed["provisional_evidence_count"] == base["provisional_evidence_count"] - 10
    assert changed["metrics"]["evidence_id_unique_rate"]["denominator"] == base["provisional_evidence_count"] - 10


def test_human_review_not_started_by_default(tmp_path):
    r = evaluator.evaluate(input_dir=V2_DIR, output_dir=tmp_path)
    assert r["label_review_status"] == "NOT_STARTED"
    assert r["metrics"]["human_review_coverage"]["status"] == "not_started"
    assert r["metrics"]["human_review_coverage"]["numerator"] == 0
    # human_override_rate 无复核时为 n/a，不写 0.0
    assert r["metrics"]["human_override_rate"]["value"] is None
    assert r["metrics"]["human_override_rate"]["status"] == "n/a"


def test_human_review_coverage_changes_with_human_row(tmp_path):
    dst = _copy_v2(tmp_path)
    log = dst / "human_review_log.csv"
    with log.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.reader(f))
    header = rows[0]
    # 追加一条真实人工复核行
    row = {c: "" for c in header}
    row.update({"review_event_id": "RE_TEST", "entity_type": "evidence",
                "entity_id": "NGA_0001_U01", "reviewer_type": "human",
                "review_status": "human_reviewed", "proposed_label": "fairness_threat",
                "final_label": "competence_frustration"})
    with log.open("a", encoding="utf-8", newline="") as f:
        csv.writer(f).writerow([row[c] for c in header])
    r = evaluator.evaluate(input_dir=dst, output_dir=tmp_path / "out")
    assert r["metrics"]["human_review_coverage"]["numerator"] == 1
    assert r["label_review_status"] == "IN_PROGRESS"
    # override 计算真实生效（final != proposed）
    assert r["metrics"]["human_override_rate"]["value"] == 1.0


def test_no_bare_evaluation_status(tmp_path):
    r = evaluator.evaluate(input_dir=V2_DIR, output_dir=tmp_path)
    assert "evaluation_status" not in r
    for k in ["structural_integrity_status", "label_review_status",
              "insight_draft_status", "release_readiness_status"]:
        assert k in r
