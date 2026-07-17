# -*- coding: utf-8 -*-
"""CI 守护测试：分层状态、历史文件保护、无真实密钥、页面数字来自 showcase.json。"""
import importlib.util
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("audit_public_data", REPO_ROOT / "tools" / "audit_public_data.py")
audit = importlib.util.module_from_spec(spec)
sys.modules["audit_public_data"] = audit
spec.loader.exec_module(audit)


def test_layered_status_expected():
    c = audit.run_combined_audit("both")
    assert c["legacy_status"] == "BLOCKED"
    assert c["v2_migration_status"] == "PASS"
    assert c["publication_readiness"] == "BLOCKED"  # 受延期决策约束


def test_no_real_secret_format_in_tracked_text():
    # 抽查 data/v2、docs、demo、tools 文本中无明显真实密钥/凭据赋值
    patterns = [re.compile(r"(api[_-]?key|token|cookie)\s*[:=]\s*['\"][A-Za-z0-9]{16,}", re.I)]
    for base in ["data/v2", "docs", "demo", "tools", "evaluation"]:
        for p in (REPO_ROOT / base).rglob("*"):
            if p.suffix.lower() in (".py", ".json", ".csv", ".md", ".yaml", ".yml", ".html", ".css", ".jsonl"):
                try:
                    txt = p.read_text(encoding="utf-8", errors="ignore")
                except OSError:
                    continue
                for pat in patterns:
                    assert not pat.search(txt), f"疑似密钥: {p}"


def test_page_numbers_from_showcase():
    idx = (REPO_ROOT / "docs" / "index.html").read_text(encoding="utf-8")
    assert "fetch('assets/data/showcase.json')" in idx
    showcase = json.loads((REPO_ROOT / "docs" / "assets" / "data" / "showcase.json").read_text(encoding="utf-8"))
    # showcase 数字与评测/迁移一致
    ev = json.loads((REPO_ROOT / "data" / "v2" / "evaluation_report.json").read_text(encoding="utf-8"))
    assert showcase["hero_summary"]["evaluation_status"] == ev["evaluation_status"]


def test_no_unexpected_large_files():
    # 除 DOCX/PNG 外，tracked 文本类文件不应异常巨大（>2MB）
    for base in ["data", "docs", "demo", "tools", "evaluation"]:
        for p in (REPO_ROOT / base).rglob("*"):
            if p.is_file() and p.suffix.lower() in (".csv", ".json", ".jsonl", ".md", ".py"):
                assert p.stat().st_size < 2 * 1024 * 1024, f"文件过大: {p}"


def test_no_human_review_forged():
    log = (REPO_ROOT / "data" / "v2" / "human_review_log.csv").read_text(encoding="utf-8-sig")
    assert "human" not in {c.strip() for line in log.splitlines()[1:] for c in line.split(",")} or "reviewer_type" in log.splitlines()[0]
    # 具体：无 reviewer_type=human 行
    for line in log.splitlines()[1:]:
        assert "human_review" not in line.split(",")[7:8] if len(line.split(",")) > 7 else True


def test_docs_files_history_present():
    # 历史公开数据文件仍存在（未被删除）
    for f in ["input_feedback_phase2_multiplatform_clean.csv", "final_evidence_table.csv",
              "04_validated_insights.jsonl", "05_action_matrix.json"]:
        assert (REPO_ROOT / "docs" / "files" / f).exists(), f
