# -*- coding: utf-8 -*-
"""离线 Demo 流水线测试：确定性、离线、输出齐全、评测 PASS。"""
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

_spec = importlib.util.spec_from_file_location("demo.src.pipeline", REPO_ROOT / "demo" / "src" / "pipeline.py")
# 通过包导入以支持相对 import
import importlib
for pkg in ("demo", "demo.src"):
    init = REPO_ROOT / pkg.replace(".", "/") / "__init__.py"
    if not init.exists():
        init.write_text("", encoding="utf-8")
pipeline = importlib.import_module("demo.src.pipeline")

SAMPLE = REPO_ROOT / "demo" / "examples" / "sample_feedback.csv"
OUT_FILES = ["input_snapshot.json", "evidence.jsonl", "insights.jsonl",
             "actions.json", "evaluation.json", "manifest.json", "report.md", "report.html"]


def _sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def test_demo_outputs_complete(tmp_path):
    out = tmp_path / "run"
    m = pipeline.run(SAMPLE, out, provider_name="mock", run_id="t")
    for name in OUT_FILES:
        assert (out / name).exists(), name
    assert m["evaluation_status"] == "PASS"
    assert m["offline"] is True


def test_demo_deterministic(tmp_path):
    a = tmp_path / "a"
    b = tmp_path / "b"
    pipeline.run(SAMPLE, a, provider_name="mock", run_id="t")
    pipeline.run(SAMPLE, b, provider_name="mock", run_id="t")
    for name in OUT_FILES:
        assert _sha(a / name) == _sha(b / name), name


def test_demo_manifest_hashes_match(tmp_path):
    out = tmp_path / "run"
    pipeline.run(SAMPLE, out, provider_name="mock", run_id="t")
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    for name, h in manifest["hashes"].items():
        assert _sha(out / name) == h, name


def test_demo_evidence_locatable_and_valid(tmp_path):
    out = tmp_path / "run"
    pipeline.run(SAMPLE, out, provider_name="mock", run_id="t")
    ev = [json.loads(x) for x in (out / "evidence.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
    ev_eval = json.loads((out / "evaluation.json").read_text(encoding="utf-8"))
    assert ev_eval["evidence_text_match_rate"] == 1.0
    assert ev_eval["invalid_label_rate"] == 0.0
    assert len(ev) > 0


def test_demo_does_not_touch_repo_data(tmp_path):
    # Demo 不覆盖 data/v2 与 docs/files
    v2 = REPO_ROOT / "data" / "v2" / "evidence_v2.csv"
    docs = REPO_ROOT / "docs" / "files" / "final_evidence_table.csv"
    before = (_sha(v2), _sha(docs))
    pipeline.run(SAMPLE, tmp_path / "run", provider_name="mock", run_id="t")
    after = (_sha(v2), _sha(docs))
    assert before == after
