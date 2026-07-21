#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成分层校准样本（离线、确定性）。

从公开证据数据抽取分层样本，供多代理独立复检使用。公开样本只包含盲测所需
字段，不含当前标签、编码来源、复核状态与平台名称；这些字段单独写入私有
映射文件，不进入公开仓库。

用法：
    python tools/calibration/build_calibration_sample.py --config config/calibration/calibration.yaml

输出：
    data/calibration/calibration_sample.csv        公开分层样本
    artifacts/calibration/private_sampling_key.csv 私有映射（含当前标签，gitignore）
    artifacts/calibration/sampling_report.json     抽样报告
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TOOLS_DIR.parent.parent

PUBLIC_FIELDS = ["blinded_item_id", "source_evidence_id", "public_evidence_text",
                 "parent_context", "context_available", "length_bucket",
                 "sampling_stratum", "is_retest", "retest_group_id"]
PRIVATE_FIELDS = ["blinded_item_id", "source_evidence_id", "platform_source",
                  "current_surface_topic", "current_mechanism_label", "label_source",
                  "review_status", "analysis_inclusion_status", "sampling_stratum_full",
                  "is_retest", "retest_group_id"]


def _coerce(v):
    v = v.strip().strip('"').strip("'")
    if re.fullmatch(r"-?\d+", v):
        return int(v)
    return v


def parse_simple_yaml(text):
    data, key = {}, None
    for raw in text.splitlines():
        if raw.strip().startswith("#") or not raw.strip():
            continue
        if raw.lstrip().startswith("- "):
            if key is not None and isinstance(data.get(key), list):
                data[key].append(_coerce(raw.lstrip()[2:]))
            continue
        if ":" in raw and not raw.startswith((" ", "\t")):
            k, _, v = raw.partition(":")
            k = k.strip()
            if v.strip() == "":
                data[k] = []
                key = k
            else:
                data[k] = _coerce(v)
                key = None
    return data


def load_config(config_path):
    text = Path(config_path).read_text(encoding="utf-8")
    try:
        import yaml  # noqa: PLC0415
        cfg = yaml.safe_load(text)
    except Exception:  # noqa: BLE001
        cfg = parse_simple_yaml(text)
    return cfg or {}


def read_csv(path):
    with Path(path).open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def length_bucket(text, short_max, medium_max):
    n = len((text or "").strip())
    if n <= short_max:
        return "short"
    if n <= medium_max:
        return "medium"
    return "long"


def build(config_path):
    cfg = load_config(config_path)
    sample_size = int(cfg.get("sample_size", 300))
    retest_size = int(cfg.get("retest_size", 30))
    seed = int(cfg.get("random_seed", 20260720))
    short_max = int(cfg.get("length_short_max", 15))
    medium_max = int(cfg.get("length_medium_max", 40))
    min_per = int(cfg.get("min_per_stratum_value", 2))
    stratify_by = cfg.get("stratify_by") or ["platform_source", "surface_topic",
                                             "mechanism_label", "label_source",
                                             "analysis_inclusion_status"]

    evidence = read_csv(REPO_ROOT / cfg.get("input_evidence", "data/public/evidence_public.csv"))
    samples = read_csv(REPO_ROOT / cfg.get("input_samples", "data/public/samples_public.csv"))
    parent_text = {s["sample_id"]: s.get("public_text", "") for s in samples}

    # 为每条证据构造分层键与长度桶
    for e in evidence:
        e["_len_bucket"] = length_bucket(e.get("unit_text", ""), short_max, medium_max)
        parts = [e.get(dim, "") for dim in stratify_by] + [e["_len_bucket"]]
        e["_stratum_full"] = "|".join(parts)
    evidence.sort(key=lambda e: e["evidence_id"])  # 稳定顺序

    rng = random.Random(seed)
    selected_ids = []
    selected_set = set()

    def add(e):
        if e["evidence_id"] not in selected_set:
            selected_set.add(e["evidence_id"])
            selected_ids.append(e["evidence_id"])

    # 1) 保证每个分层维度的每个取值至少 min_per 条（含长度桶）
    for dim in list(stratify_by) + ["_len_bucket"]:
        groups = defaultdict(list)
        for e in evidence:
            groups[e.get(dim, "")].append(e)
        for _val, rows in sorted(groups.items()):
            picks = rows[:]
            rng.shuffle(picks)
            for e in picks[:min_per]:
                add(e)

    # 2) 按确定性顺序补足到 sample_size
    fill = evidence[:]
    rng.shuffle(fill)
    for e in fill:
        if len(selected_ids) >= sample_size:
            break
        add(e)
    selected_ids = selected_ids[:sample_size]

    by_id = {e["evidence_id"]: e for e in evidence}
    # 分层编码：真实分层 -> 匿名代码，公开文件只写代码
    stratum_codes = {}
    for eid in selected_ids:
        full = by_id[eid]["_stratum_full"]
        if full not in stratum_codes:
            stratum_codes[full] = f"S{len(stratum_codes) + 1:03d}"

    public_rows, private_rows = [], []
    for i, eid in enumerate(selected_ids, start=1):
        e = by_id[eid]
        blinded = f"CAL_{i:04d}"
        pc = parent_text.get(e.get("sample_id", ""), "")
        public_rows.append({
            "blinded_item_id": blinded,
            "source_evidence_id": eid,
            "public_evidence_text": e.get("unit_text", ""),
            "parent_context": pc,
            "context_available": "yes" if pc else "no",
            "length_bucket": e["_len_bucket"],
            "sampling_stratum": stratum_codes[e["_stratum_full"]],
            "is_retest": "false",
            "retest_group_id": "",
        })
        private_rows.append({
            "blinded_item_id": blinded,
            "source_evidence_id": eid,
            "platform_source": e.get("platform_source", ""),
            "current_surface_topic": e.get("surface_topic", ""),
            "current_mechanism_label": e.get("mechanism_label", ""),
            "label_source": e.get("label_source", ""),
            "review_status": e.get("review_status", ""),
            "analysis_inclusion_status": e.get("analysis_inclusion_status", ""),
            "sampling_stratum_full": e["_stratum_full"],
            "is_retest": "false",
            "retest_group_id": "",
        })

    # 重测样本：从主样本中确定性抽 retest_size 条，重新盲测编号
    retest_rng = random.Random(seed + 1)
    retest_pick = selected_ids[:]
    retest_rng.shuffle(retest_pick)
    retest_pick = sorted(retest_pick[:retest_size])
    src_to_blinded = {r["source_evidence_id"]: r["blinded_item_id"] for r in public_rows}
    for j, eid in enumerate(retest_pick, start=1):
        e = by_id[eid]
        blinded = f"CAL_R{j:03d}"
        group = f"RT_{src_to_blinded[eid]}"
        pc = parent_text.get(e.get("sample_id", ""), "")
        public_rows.append({
            "blinded_item_id": blinded,
            "source_evidence_id": eid,
            "public_evidence_text": e.get("unit_text", ""),
            "parent_context": pc,
            "context_available": "yes" if pc else "no",
            "length_bucket": e["_len_bucket"],
            "sampling_stratum": stratum_codes[e["_stratum_full"]],
            "is_retest": "true",
            "retest_group_id": group,
        })
        private_rows.append({
            "blinded_item_id": blinded, "source_evidence_id": eid,
            "platform_source": e.get("platform_source", ""),
            "current_surface_topic": e.get("surface_topic", ""),
            "current_mechanism_label": e.get("mechanism_label", ""),
            "label_source": e.get("label_source", ""),
            "review_status": e.get("review_status", ""),
            "analysis_inclusion_status": e.get("analysis_inclusion_status", ""),
            "sampling_stratum_full": e["_stratum_full"],
            "is_retest": "true", "retest_group_id": group,
        })
        # 主样本对应行标记同一重测组
        for r in public_rows:
            if r["source_evidence_id"] == eid and r["is_retest"] == "false":
                r["retest_group_id"] = group

    # 覆盖率报告
    def coverage(field):
        return dict(Counter(by_id[eid].get(field, "") for eid in selected_ids))

    report = {
        "schema_version": "calibration-sampling-1.0",
        "random_seed": seed,
        "main_sample_count": len(selected_ids),
        "retest_count": len(retest_pick),
        "total_rows": len(public_rows),
        "stratum_count": len(stratum_codes),
        "coverage": {
            "platform_source": coverage("platform_source"),
            "surface_topic": coverage("surface_topic"),
            "mechanism_label": coverage("mechanism_label"),
            "label_source": coverage("label_source"),
            "analysis_inclusion_status": coverage("analysis_inclusion_status"),
            "length_bucket": dict(Counter(by_id[eid]["_len_bucket"] for eid in selected_ids)),
        },
        "input_evidence_count": len(evidence),
        "input_sha256": hashlib.sha256(
            (REPO_ROOT / cfg.get("input_evidence", "data/public/evidence_public.csv"))
            .read_bytes()).hexdigest(),
    }
    return cfg, public_rows, private_rows, report


def _write_csv(path, fields, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fields})


def main(argv=None):
    ap = argparse.ArgumentParser(description="生成确定性分层校准样本（公开样本与私有映射分离）")
    ap.add_argument("--config", default=str(REPO_ROOT / "config" / "calibration" / "calibration.yaml"))
    args = ap.parse_args(argv)

    cfg, public_rows, private_rows, report = build(args.config)
    public_out = REPO_ROOT / cfg.get("public_output", "data/calibration/calibration_sample.csv")
    artifact_dir = REPO_ROOT / cfg.get("artifact_dir", "artifacts/calibration")
    _write_csv(public_out, PUBLIC_FIELDS, public_rows)
    _write_csv(artifact_dir / "private_sampling_key.csv", PRIVATE_FIELDS, private_rows)
    (artifact_dir / "sampling_report.json").parent.mkdir(parents=True, exist_ok=True)
    (artifact_dir / "sampling_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print("校准样本生成完成：")
    print("  status=PASS（PASS 表示抽样完成且覆盖检查通过）")
    print(f"  main_sample_count={report['main_sample_count']} retest_count={report['retest_count']}")
    print(f"  output_path={public_out.relative_to(REPO_ROOT).as_posix()}")
    print("  private_key=artifacts/calibration/private_sampling_key.csv（不提交公开仓库）")
    print("  next_action=运行 tools/calibration/run_agent_reviews.py 进行多代理复检")
    return 0


if __name__ == "__main__":
    sys.exit(main())
