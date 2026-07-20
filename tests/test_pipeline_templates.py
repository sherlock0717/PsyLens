# -*- coding: utf-8 -*-
"""抓取链模板与规则基线口径校验。"""
import csv
import importlib.util
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
PIPELINE = REPO_ROOT / "pipeline"
V2_DIR = REPO_ROOT / "data" / "v2"


def _load_path(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


discovery = _load_path("candidate_discovery_template", PIPELINE / "discovery" / "candidate_discovery_template.py")


def test_pipeline_structure_present():
    for rel in ["discovery/candidate_discovery_template.py", "config/case.example.yaml",
                "config/platforms.example.yaml", "prompts/curation.md", "prompts/evidence_extraction.md",
                "prompts/topic_coding.md", "prompts/mechanism_coding.md", "prompts/insight_generation.md",
                "prompts/action_generation.md", "examples/candidate_posts.example.csv",
                "examples/raw_feedback.example.jsonl", "requirements-legacy.txt", "README.md"]:
        assert (PIPELINE / rel).exists(), rel


def test_discovery_dry_run_offline():
    rows = discovery.discover(dry_run=True)
    assert len(rows) >= 1
    assert all(r["url_placeholder"].startswith("example://") for r in rows)


def test_discovery_real_run_not_implemented():
    with pytest.raises(NotImplementedError):
        discovery.discover(dry_run=False)


def test_prompts_marked_reconstructed():
    for p in (PIPELINE / "prompts").glob("*.md"):
        assert "reconstructed_template" in p.read_text(encoding="utf-8"), p.name


def test_config_no_secrets():
    for p in (PIPELINE / "config").glob("*.yaml"):
        txt = p.read_text(encoding="utf-8").lower()
        for banned in ["cookie=", "token=", "api_key=", "apikey="]:
            assert banned not in txt, p.name
        # 不出现真实长凭据串
        assert "sk-" not in txt


def test_examples_no_real_urls():
    for p in (PIPELINE / "examples").glob("*"):
        txt = p.read_text(encoding="utf-8")
        assert "http://" not in txt and "https://" not in txt, p.name


def test_proposals_are_rule_based_not_agent():
    path = V2_DIR / "rule_based_label_proposals.csv"
    assert path.exists()
    with path.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    assert rows
    assert {r["proposer_type"] for r in rows} == {"rule_based_baseline"}
    assert {r["proposal_status"] for r in rows} == {"rule_based_proposed_unreviewed"}
    # 旧命名不再出现
    assert not (V2_DIR / "agent_label_proposals.csv").exists()


def test_provisional_label_source_renamed():
    with (V2_DIR / "evidence_provisional_v2.csv").open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    label_sources = {r["label_source"] for r in rows}
    assert "agent_proposed" not in label_sources
    assert label_sources <= {"legacy_ai", "rule_based_proposal"}
    review_statuses = {r["review_status"] for r in rows}
    assert "agent_proposed_unreviewed" not in review_statuses


def test_readme_and_page_do_not_call_rules_agent_semantic():
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    index = (REPO_ROOT / "docs" / "index.html").read_text(encoding="utf-8")
    for txt in (readme, index):
        assert "机器语义判断" not in txt
        assert "Agent 编码" not in txt
    assert "规则基线" in readme
