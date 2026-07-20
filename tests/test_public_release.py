import csv
import hashlib
import importlib.util
import json
import re
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "data" / "public"
DOCS = ROOT / "docs"
ANALYSIS_PATH = DOCS / "assets" / "data" / "analysis_summary.json"


def _csv_rows(path: Path):
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _analysis_module():
    path = ROOT / "tools" / "summarize_public_analysis.py"
    spec = importlib.util.spec_from_file_location("summarize_public_analysis", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_required_public_files_exist():
    required = [
        ROOT / "README.md",
        PUBLIC / "README.md",
        PUBLIC / "samples_public.csv",
        PUBLIC / "evidence_public.csv",
        PUBLIC / "migration_history.json",
        PUBLIC / "public_manifest.json",
        DOCS / "index.html",
        DOCS / "style.css",
        DOCS / "assets" / "data" / "showcase.json",
        ANALYSIS_PATH,
        DOCS / "methodology" / "PSYCHOLOGY_FRAMEWORK.md",
        DOCS / "methodology" / "DATA_CLEANING_AND_CODING.md",
        DOCS / "files" / "PsyLens_project_brief.docx",
        ROOT / "tools" / "build_project_brief_docx.py",
        ROOT / "tools" / "normalize_public_dataset.py",
        ROOT / "tools" / "summarize_public_analysis.py",
        ROOT / "demo" / "README.md",
        ROOT / "tools" / "run_demo.py",
    ]
    for path in required:
        assert path.exists(), path


def test_public_data_counts_and_schema():
    samples = _csv_rows(PUBLIC / "samples_public.csv")
    evidence = _csv_rows(PUBLIC / "evidence_public.csv")
    assert len(samples) == 360
    assert len(evidence) == 927
    assert list(samples[0]) == [
        "sample_id",
        "platform_source",
        "platform_sequence",
        "window_tag",
        "theme_bucket",
        "reply_type",
        "date",
        "public_text",
        "migration_status",
    ]
    assert "raw_text" not in samples[0]
    assert "source_url" not in samples[0]
    assert "source_url" not in evidence[0]
    assert all(row["surface_topic"].strip() for row in evidence)
    assert all(row["mechanism_label"].strip() for row in evidence)


def test_public_data_contains_no_external_urls():
    for name in [
        "samples_public.csv",
        "evidence_public.csv",
        "migration_history.json",
        "public_manifest.json",
    ]:
        text = (PUBLIC / name).read_text(encoding="utf-8")
        assert "http://" not in text
        assert "https://" not in text


def test_public_manifest_matches_files_and_migration_history():
    manifest = json.loads((PUBLIC / "public_manifest.json").read_text(encoding="utf-8"))
    history = json.loads((PUBLIC / "migration_history.json").read_text(encoding="utf-8"))
    assert manifest["schema_version"] == "public-2.0"
    assert manifest["files"]["samples_public.csv"]["row_count"] == 360
    assert manifest["files"]["evidence_public.csv"]["row_count"] == 927
    assert manifest["files"]["samples_public.csv"]["sha256"] == _sha256(
        PUBLIC / "samples_public.csv"
    )
    assert manifest["files"]["evidence_public.csv"]["sha256"] == _sha256(
        PUBLIC / "evidence_public.csv"
    )
    assert manifest["files"]["migration_history.json"]["sha256"] == _sha256(
        PUBLIC / "migration_history.json"
    )
    migration = history["migrations"][0]
    assert migration["migration_id"] == "public-1x-to-public-2.0"
    assert migration["transformations"]["redundant_raw_text_column_removed"] == 360
    assert migration["transformations"]["blank_surface_topic_normalized_to_other_uncertain"] == 47
    assert manifest["transformations"]["redundant_raw_text_column_removed"] == 360
    assert manifest["transformations"]["blank_surface_topic_normalized_to_other_uncertain"] == 47


def test_analysis_summary_matches_public_data():
    committed = json.loads(ANALYSIS_PATH.read_text(encoding="utf-8"))
    generated = _analysis_module().build(PUBLIC)
    assert committed == generated
    assert committed["counts"]["samples"] == 360
    assert committed["counts"]["evidence"] == 927
    assert committed["counts"]["uncertain_mechanism"] == 486
    assert committed["counts"]["inclusion_flagged_uncertain"] == 163
    assert committed["integrity"]["evidence_text_match_rate"] == 1.0
    assert committed["integrity"]["orphan_evidence_count"] == 0
    assert committed["integrity"]["sample_duplicates"]["duplicate_group_count"] == 0


def test_page_copy_contains_results_and_methods():
    html = (DOCS / "index.html").read_text(encoding="utf-8")
    banned = [
        "作品集",
        "站得住",
        "普通语言",
        "gate-screen",
        "gate-locked",
        ">ENTER<",
        "phase1/rebuild-evidence-and-demo",
        "data/v2",
    ]
    for phrase in banned:
        assert phrase not in html, phrase
    assert not re.search(r"不是.{0,40}而是", html)
    assert html.count("人工复核") == 0
    for section_id in ["design", "results", "psychology", "cleaning", "evaluation", "scope"]:
        assert f'id="{section_id}"' in html
    assert "assets/data/analysis_summary.json" in html
    assert "data-showcase=\"samples\"" in html
    assert "data-showcase=\"evidence\"" in html


def test_showcase_is_main_ready_and_evidence_is_exact():
    showcase = json.loads((DOCS / "assets" / "data" / "showcase.json").read_text(encoding="utf-8"))
    evidence = _csv_rows(PUBLIC / "evidence_public.csv")
    evidence_by_id = {row["evidence_id"]: row for row in evidence}
    assert showcase["repo_ref"] == "main"
    assert "open_decisions" not in showcase
    assert showcase["counts"]["samples"] == 360
    assert showcase["counts"]["evidence"] == 927
    assert showcase["counts"]["uncertain_mechanism"] == 486
    assert showcase["counts"]["inclusion_flagged_uncertain"] == 163
    example = showcase["evidence_example"]
    assert example["sample_excerpt"] == evidence_by_id[example["evidence_id"]]["unit_text"]
    assert "http://" not in example["sample_excerpt"]
    assert "https://" not in example["sample_excerpt"]
    for link in showcase["doc_links"].values():
        assert "/main/" in link or link.endswith("/main")


def test_readme_and_method_docs_are_consistent():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "data/public/" in readme
    assert "data/v2/" not in readme
    assert "作品集" not in readme
    assert not re.search(r"不是.{0,40}而是", readme)
    assert readme.count("## 解释边界") == 1
    assert "486" in readme and "163" in readme

    scanned = [
        ROOT / "README.md",
        ROOT / "pipeline" / "README.md",
        DOCS / "pipeline" / "FULL_PIPELINE.md",
        DOCS / "pipeline" / "FAILURE_RECOVERY.md",
        DOCS / "evaluation" / "EVALUATION_METHOD.md",
    ]
    stale = ["tools/audit_public_data.py", "tools/build_showcase_data.py", "tools/evaluate_v2.py"]
    for path in scanned:
        text = path.read_text(encoding="utf-8")
        for token in stale:
            assert token not in text, f"{path}: {token}"


def test_project_brief_is_readable_and_substantive():
    path = DOCS / "files" / "PsyLens_project_brief.docx"
    assert zipfile.is_zipfile(path)
    with zipfile.ZipFile(path) as archive:
        xml = archive.read("word/document.xml").decode("utf-8")
    for heading in [
        "执行摘要",
        "数据清洗与证据构建",
        "心理学分析框架",
        "分析结果",
        "可靠性评测",
        "产品方向与验证设计",
        "解释边界",
        "参考文献",
    ]:
        assert heading in xml
    assert "927" in xml and "52.4%" in xml and "Krippendorff" in xml
    assert xml.count("Copyright © 2026 Sherlock0717. All rights reserved.") == 1
    assert len(xml) > 60000
