# -*- coding: utf-8 -*-
"""隐私校验：私有映射与原始响应不被公开提交；提交文件不含密钥、Cookie 与本地绝对路径。"""
import csv
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
GITIGNORE = REPO_ROOT / ".gitignore"
PUBLIC_SAMPLE = REPO_ROOT / "data" / "calibration" / "calibration_sample.csv"

FORBIDDEN_COLUMNS = {"source_evidence_id", "platform_source", "current_surface_topic",
                     "current_mechanism_label", "label_source", "review_status",
                     "surface_topic", "mechanism_label", "sampling_stratum",
                     "is_retest", "retest_group_id"}


def test_gitignore_excludes_private_paths():
    text = GITIGNORE.read_text(encoding="utf-8")
    assert "artifacts/" in text
    assert "artifacts/calibration/private_*" in text
    assert "raw_model_responses" in text
    assert "local_secrets" in text
    assert ".env" in text


def test_private_key_lives_under_artifacts():
    # 私有映射与原始响应只写入 artifacts（已被 gitignore），不进入公开数据目录
    cfg_text = (REPO_ROOT / "config" / "calibration" / "calibration.yaml").read_text(encoding="utf-8")
    assert "artifact_dir: artifacts/calibration" in cfg_text
    assert not (REPO_ROOT / "data" / "calibration" / "private_sampling_key.csv").exists()


def test_public_sample_no_leaked_columns_or_url():
    assert PUBLIC_SAMPLE.exists()
    raw = PUBLIC_SAMPLE.read_text(encoding="utf-8")
    with PUBLIC_SAMPLE.open("r", encoding="utf-8-sig", newline="") as f:
        header = set(next(csv.reader(f)))
    assert FORBIDDEN_COLUMNS.isdisjoint(header), header
    assert "http://" not in raw and "https://" not in raw


def test_committed_calibration_files_have_no_secrets():
    scan_dirs = [REPO_ROOT / "config" / "calibration",
                 REPO_ROOT / "data" / "calibration",
                 REPO_ROOT / "tools" / "calibration"]
    banned = ["api_key=", "token=", "cookie=", "secret=", "C:\\Users", "/Users/"]
    for d in scan_dirs:
        for p in d.rglob("*"):
            if not p.is_file() or p.suffix == ".pyc":
                continue
            text = p.read_text(encoding="utf-8", errors="ignore")
            for b in banned:
                assert b not in text, f"{p} 含疑似敏感内容: {b}"
