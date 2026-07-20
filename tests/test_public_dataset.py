# -*- coding: utf-8 -*-
"""公开脱敏数据校验：无 source_url、无 URL、无账号字段、哈希与 manifest 一致。"""
import csv
import hashlib
import importlib.util
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PUBLIC_DIR = REPO_ROOT / "data" / "public"


def _load(name):
    spec = importlib.util.spec_from_file_location(name, REPO_ROOT / "tools" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


build_public = _load("build_public_dataset")

ACCOUNT_FIELDS = {"source_url", "url", "uid", "account", "user_id", "username",
                  "thread_or_video_title", "author", "nickname"}


def _read(path):
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def test_public_files_exist():
    for n in ["samples_public.csv", "evidence_public.csv", "public_manifest.json"]:
        assert (PUBLIC_DIR / n).exists(), n


def test_samples_public_no_source_url_or_account_fields():
    rows = _read(PUBLIC_DIR / "samples_public.csv")
    assert rows
    cols = set(rows[0].keys())
    assert not (cols & ACCOUNT_FIELDS), f"公开样本含身份/来源字段: {cols & ACCOUNT_FIELDS}"


def test_evidence_public_no_account_fields():
    rows = _read(PUBLIC_DIR / "evidence_public.csv")
    cols = set(rows[0].keys())
    assert not (cols & ACCOUNT_FIELDS), f"公开证据含身份/来源字段: {cols & ACCOUNT_FIELDS}"


def test_public_no_urls():
    for n in ["samples_public.csv", "evidence_public.csv", "public_manifest.json"]:
        txt = (PUBLIC_DIR / n).read_text(encoding="utf-8")
        assert "http://" not in txt and "https://" not in txt, n


def test_public_hashes_match_manifest():
    manifest = json.loads((PUBLIC_DIR / "public_manifest.json").read_text(encoding="utf-8"))
    for name, h in manifest["hashes"].items():
        actual = hashlib.sha256((PUBLIC_DIR / name).read_bytes()).hexdigest()
        assert actual == h, f"{name} 哈希与 manifest 不一致"
    assert manifest["contains_source_url"] is False
    assert manifest["human_review_coverage"] == 0.0


def test_build_public_dataset_tmp(tmp_path):
    m = build_public.build(tmp_path)
    assert (tmp_path / "samples_public.csv").exists()
    assert m["contains_source_url"] is False
    txt = (tmp_path / "samples_public.csv").read_text(encoding="utf-8")
    assert "https://" not in txt


def test_sanitizer_masks_pii():
    masked, changed = build_public.sanitize("联系我 https://x.com 微信：abcdef12 手机 13800001111")
    assert changed
    assert "https://" not in masked
    assert "13800001111" not in masked
