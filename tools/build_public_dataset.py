#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""构建公开脱敏数据副本（离线、确定性）。

从内部 v2 数据生成不含来源 URL 与身份定位字段的公开副本：
  data/public/samples_public.csv     样本层（无 source_url / 标题 / 账号）
  data/public/evidence_public.csv    证据层（provisional，无来源 URL / 内部备注）
  data/public/public_manifest.json   文件、字段、SHA-256、脱敏策略、无 URL 声明、人工复核覆盖=0

原则：
  - 不改写内部 data/v2/samples_v2.raw_text；仅在公开副本生成脱敏字段；
  - 若 raw_text 含明确 URL / 用户名 / 联系方式 / 账号，生成脱敏 public_text；
  - 公开文件不含 source_url、平台内部标题、账号/UID 等身份定位字段；
  - 相同输入产生相同输出。
"""
from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import re
import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TOOLS_DIR.parent
V2_DIR = REPO_ROOT / "data" / "v2"
PUBLIC_DIR = REPO_ROOT / "data" / "public"

_spec = importlib.util.spec_from_file_location("audit_public_data", TOOLS_DIR / "audit_public_data.py")
audit = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(audit)

SAMPLES_COLS = ["sample_id", "platform_source", "platform_sequence", "window_tag",
                "theme_bucket", "reply_type", "date", "raw_text", "public_text", "migration_status"]
EVIDENCE_COLS = ["evidence_id", "sample_id", "platform_source", "unit_index", "unit_text",
                 "surface_topic", "mechanism_label", "label_source", "review_status",
                 "analysis_inclusion_status"]

GENERATED_AT = "2026-07-17T16:56:33.578346+08:00"

# 脱敏正则（保守）：URL / 邮箱 / 手机号 / @用户名 / QQ / 微信
_PATTERNS = [
    (re.compile(r"https?://\S+"), "[链接已移除]"),
    (re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}"), "[邮箱已移除]"),
    (re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)"), "[号码已移除]"),
    (re.compile(r"@[\w\u4e00-\u9fff]{2,20}"), "[用户名已移除]"),
    (re.compile(r"(?:QQ|qq|扣扣)[:：\s]*\d{5,12}"), "[QQ已移除]"),
    (re.compile(r"(?:微信|weixin|wechat|vx|VX)[:：\s]*[A-Za-z0-9_\-]{5,20}"), "[微信已移除]"),
]


def sanitize(text: str):
    """返回 (脱敏文本, 是否发生脱敏)。"""
    out = text or ""
    changed = False
    for pat, repl in _PATTERNS:
        new = pat.sub(repl, out)
        if new != out:
            changed = True
        out = new
    return out, changed


def _write(path: Path, cols, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in cols})


def build(output_dir=None):
    output_dir = Path(output_dir) if output_dir else PUBLIC_DIR
    _, samples = audit.read_csv_rows(V2_DIR / "samples_v2.csv")
    _, prov = audit.read_csv_rows(V2_DIR / "evidence_provisional_v2.csv")
    _, human_rows = audit.read_csv_rows(V2_DIR / "human_review_log.csv")

    sanitized_count = 0
    pub_samples = []
    for r in samples:
        public_text, changed = sanitize(r.get("raw_text", ""))
        if changed:
            sanitized_count += 1
        pub_samples.append({
            "sample_id": r.get("sample_id", ""),
            "platform_source": r.get("platform_source", ""),
            "platform_sequence": r.get("platform_sequence", ""),
            "window_tag": r.get("window_tag", ""),
            "theme_bucket": r.get("theme_bucket", ""),
            "reply_type": r.get("reply_type", ""),
            "date": r.get("date", ""),
            # 公开副本不泄露：若发生脱敏则 raw_text 也用脱敏文本；否则保留原文（已确认无 URL）
            "raw_text": public_text if changed else r.get("raw_text", ""),
            "public_text": public_text,
            "migration_status": r.get("migration_status", ""),
        })

    pub_evidence = []
    for r in prov:
        unit_text, _c = sanitize(r.get("unit_text", ""))
        pub_evidence.append({
            "evidence_id": r.get("evidence_id", ""),
            "sample_id": r.get("sample_id", ""),
            "platform_source": r.get("platform_source", ""),
            "unit_index": r.get("unit_index", ""),
            "unit_text": unit_text,
            "surface_topic": r.get("surface_topic", ""),
            "mechanism_label": r.get("mechanism_label", ""),
            "label_source": r.get("label_source", ""),
            "review_status": r.get("review_status", ""),
            "analysis_inclusion_status": r.get("analysis_inclusion_status", ""),
        })

    _write(output_dir / "samples_public.csv", SAMPLES_COLS, pub_samples)
    _write(output_dir / "evidence_public.csv", EVIDENCE_COLS, pub_evidence)

    human_reviews = [r for r in human_rows if r.get("reviewer_type") == "human"]

    manifest = {
        "schema_version": "public-1.0",
        "generated_at": GENERATED_AT,
        "files": {
            "samples_public.csv": {
                "row_count": len(pub_samples),
                "fields": SAMPLES_COLS,
            },
            "evidence_public.csv": {
                "row_count": len(pub_evidence),
                "fields": EVIDENCE_COLS,
            },
        },
        "sanitization_policy": [
            "移除 source_url、平台内部标题、账号/UID 等身份定位字段",
            "对 raw_text 生成 public_text：屏蔽 URL、邮箱、手机号、@用户名、QQ、微信",
            "不改写内部 data/v2/samples_v2.raw_text，仅在公开副本脱敏",
        ],
        "sanitized_sample_count": sanitized_count,
        "contains_source_url": False,
        "human_review_coverage": 0.0 if not human_reviews else None,
        "human_review_note": "当前公开数据的人工复核覆盖为 0（无 reviewer_type=human 记录）",
        "hashes": {},
        "limitations": [
            "公开副本不含来源链接；来源字段仅存于内部 data/v2，不进入发布合并范围（见 RESTRICTED_DATA_FILES.md）",
            "证据标签均未经真人复核（legacy_ai_label_unreviewed 或 rule_based_proposed_unreviewed）",
        ],
    }
    for name in ["samples_public.csv", "evidence_public.csv"]:
        manifest["hashes"][name] = audit.sha256_bytes(output_dir / name)
    (output_dir / "public_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    # 安全自检：公开文件不得含 URL
    for name in ["samples_public.csv", "evidence_public.csv", "public_manifest.json"]:
        txt = (output_dir / name).read_text(encoding="utf-8")
        assert "http://" not in txt and "https://" not in txt, f"{name} 含 URL（脱敏失败）"
    return manifest


def main(argv=None):
    ap = argparse.ArgumentParser(description="构建公开脱敏数据副本（离线/确定性）")
    ap.add_argument("--output-dir", default=str(PUBLIC_DIR))
    args = ap.parse_args(argv)
    m = build(args.output_dir)
    print("公开脱敏数据副本生成完成：")
    print(f"  samples_public={m['files']['samples_public.csv']['row_count']} "
          f"evidence_public={m['files']['evidence_public.csv']['row_count']}")
    print(f"  sanitized_sample_count={m['sanitized_sample_count']} contains_source_url={m['contains_source_url']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
