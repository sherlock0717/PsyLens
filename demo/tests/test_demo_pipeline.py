# -*- coding: utf-8 -*-
"""离线 Demo 流水线测试：确定性、输出齐全、证据可定位。"""
import hashlib
import importlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
pipeline = importlib.import_module("demo.src.pipeline")

SAMPLE = REPO_ROOT / "demo" / "examples" / "sample_feedback.csv"
OUT_FILES = [
    "input_snapshot.json",
    "evidence.jsonl",
    "insights.jsonl",
    "actions.json",
    "evaluation.json",
    "manifest.json",
    "report.md",
    "report.html",
]


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_demo_outputs_complete(tmp_path):
    out = tmp_path / "run"
    manifest = pipeline.run(SAMPLE, out, provider_name="mock", run_id="t")
    for name in OUT_FILES:
        assert (out / name).exists(), name
    assert manifest["evaluation_status"] == "PASS"
    assert manifest["offline"] is True


def test_demo_deterministic(tmp_path):
    first = tmp_path / "first"
    second = tmp_path / "second"
    pipeline.run(SAMPLE, first, provider_name="mock", run_id="t")
    pipeline.run(SAMPLE, second, provider_name="mock", run_id="t")
    for name in OUT_FILES:
        assert _sha(first / name) == _sha(second / name), name


def test_demo_manifest_hashes_match(tmp_path):
    out = tmp_path / "run"
    pipeline.run(SAMPLE, out, provider_name="mock", run_id="t")
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    for name, expected_hash in manifest["hashes"].items():
        assert _sha(out / name) == expected_hash, name


def test_demo_evidence_locatable_and_valid(tmp_path):
    out = tmp_path / "run"
    pipeline.run(SAMPLE, out, provider_name="mock", run_id="t")
    evidence = [
        json.loads(line)
        for line in (out / "evidence.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    evaluation = json.loads((out / "evaluation.json").read_text(encoding="utf-8"))
    assert evaluation["evidence_text_match_rate"] == 1.0
    assert evaluation["invalid_label_rate"] == 0.0
    assert evidence


def test_demo_does_not_touch_public_release_files(tmp_path):
    protected = [
        REPO_ROOT / "data" / "public" / "samples_public.csv",
        REPO_ROOT / "data" / "public" / "evidence_public.csv",
        REPO_ROOT / "docs" / "files" / "PsyLens_project_brief.docx",
    ]
    before = {str(path): _sha(path) for path in protected}
    pipeline.run(SAMPLE, tmp_path / "run", provider_name="mock", run_id="t")
    after = {str(path): _sha(path) for path in protected}
    assert before == after
