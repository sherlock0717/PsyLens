import csv
import hashlib
import json
import re
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "data" / "public"
DOCS = ROOT / "docs"


def _csv_rows(path: Path):
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_required_public_files_exist():
    required = [
        ROOT / "README.md",
        PUBLIC / "samples_public.csv",
        PUBLIC / "evidence_public.csv",
        PUBLIC / "public_manifest.json",
        DOCS / "index.html",
        DOCS / "style.css",
        DOCS / "assets" / "data" / "showcase.json",
        DOCS / "files" / "PsyLens_project_brief.docx",
        ROOT / "demo" / "README.md",
        ROOT / "tools" / "run_demo.py",
    ]
    for path in required:
        assert path.exists(), path


def test_public_data_counts_and_fields():
    samples = _csv_rows(PUBLIC / "samples_public.csv")
    evidence = _csv_rows(PUBLIC / "evidence_public.csv")
    assert len(samples) == 360
    assert len(evidence) == 927
    for rows in (samples, evidence):
        assert rows
        assert "source_url" not in rows[0]
        assert "url" not in rows[0]


def test_public_data_contains_no_external_urls():
    for name in ["samples_public.csv", "evidence_public.csv", "public_manifest.json"]:
        text = (PUBLIC / name).read_text(encoding="utf-8")
        assert "http://" not in text
        assert "https://" not in text


def test_public_manifest_matches_files():
    manifest = json.loads((PUBLIC / "public_manifest.json").read_text(encoding="utf-8"))
    assert manifest["contains_source_url"] is False
    assert manifest["files"]["samples_public.csv"]["row_count"] == 360
    assert manifest["files"]["evidence_public.csv"]["row_count"] == 927
    assert manifest["hashes"]["samples_public.csv"] == _sha256(PUBLIC / "samples_public.csv")
    assert manifest["hashes"]["evidence_public.csv"] == _sha256(PUBLIC / "evidence_public.csv")


def test_page_copy_is_public_facing():
    html = (DOCS / "index.html").read_text(encoding="utf-8")
    banned = [
        "作品集",
        "站得住",
        "普通语言",
        "gate-screen",
        "gate-locked",
        ">ENTER<",
        "phase1/rebuild-evidence-and-demo",
    ]
    for phrase in banned:
        assert phrase not in html, phrase
    assert not re.search(r"不是.{0,40}而是", html)
    assert "data-showcase=\"samples\"" in html
    assert "data-showcase=\"provisional_evidence\"" in html


def test_showcase_is_main_ready_and_clean():
    showcase = json.loads((DOCS / "assets" / "data" / "showcase.json").read_text(encoding="utf-8"))
    assert showcase["repo_ref"] == "main"
    assert "open_decisions" not in showcase
    assert showcase["counts"]["samples"] == 360
    assert showcase["counts"]["provisional_evidence"] == 927
    excerpt = showcase["evidence_example"]["sample_excerpt"]
    assert "http://" not in excerpt and "https://" not in excerpt
    for phrase in ["最弱智", "你妈", "作品集"]:
        assert phrase not in excerpt
    for link in showcase["doc_links"].values():
        assert "/main/" in link or link.endswith("/main")


def test_readme_uses_public_release_paths():
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "data/public/" in text
    assert "data/v2/" not in text
    assert "作品集" not in text
    assert not re.search(r"不是.{0,40}而是", text)


def test_project_brief_is_readable_docx():
    path = DOCS / "files" / "PsyLens_project_brief.docx"
    assert zipfile.is_zipfile(path)
    with zipfile.ZipFile(path) as zf:
        assert "word/document.xml" in zf.namelist()
