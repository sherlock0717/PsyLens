#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""候选发现模板（reconstructed_template，公开示例）。

本脚本是**公开模板**，用于说明「候选帖子发现」这一步的输入/输出结构。
它**默认不联网**：`--dry-run`（默认开启）时只根据关键词生成示例候选清单，
不访问任何平台、不携带任何登录信息。

真实候选发现需按平台政策自行实现联网检索，并显式关闭 dry-run。
本模板不保证与最初历史运行逐字一致（历史检索逻辑未逐字保存）。

用法：
  python pipeline/discovery/candidate_discovery_template.py \
      --config pipeline/config/case.example.yaml \
      --output artifacts/pipeline/candidate_posts.csv
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

CANDIDATE_COLS = ["candidate_id", "platform", "keyword", "title", "url_placeholder", "discovered_at", "notes"]

# 示例候选（脱敏；url_placeholder 不是真实链接）
EXAMPLE_CANDIDATES = [
    {"platform": "PlatformA", "keyword": "平衡 数值", "title": "版本平衡讨论（示例）"},
    {"platform": "PlatformB", "keyword": "匹配 队友", "title": "匹配机制吐槽（示例）"},
    {"platform": "PlatformC", "keyword": "活动 奖励", "title": "活动奖励反馈（示例）"},
]


def load_keywords(config_path):
    """从 case 配置读取关键词；无 PyYAML 时退回内置示例，保证离线可运行。"""
    if not config_path or not Path(config_path).exists():
        return ["平衡", "匹配", "奖励"]
    try:
        import yaml  # noqa: PLC0415
        cfg = yaml.safe_load(Path(config_path).read_text(encoding="utf-8")) or {}
        return cfg.get("discovery", {}).get("keywords", ["平衡", "匹配", "奖励"])
    except Exception:
        return ["平衡", "匹配", "奖励"]


def discover(config_path=None, dry_run=True):
    """dry-run：返回确定性示例候选清单，不联网。"""
    if not dry_run:
        raise NotImplementedError(
            "真实候选发现需自行实现联网检索并遵守平台政策；本公开模板仅提供 dry-run 示例。")
    load_keywords(config_path)  # 演示读取关键词（离线）
    rows = []
    for i, c in enumerate(EXAMPLE_CANDIDATES, 1):
        rows.append({
            "candidate_id": f"CAND_{i:04d}",
            "platform": c["platform"],
            "keyword": c["keyword"],
            "title": c["title"],
            "url_placeholder": f"example://{c['platform'].lower()}/post/{i:04d}",
            "discovered_at": "2026-07-17T16:56:33.578346+08:00",
            "notes": "reconstructed_template 示例候选；非真实链接",
        })
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(description="候选发现模板（默认 dry-run、离线）")
    ap.add_argument("--config", default=str(REPO_ROOT / "pipeline" / "config" / "case.example.yaml"))
    ap.add_argument("--output", default="")
    ap.add_argument("--dry-run", dest="dry_run", action="store_true", default=True)
    ap.add_argument("--no-dry-run", dest="dry_run", action="store_false")
    args = ap.parse_args(argv)
    rows = discover(args.config, args.dry_run)
    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=CANDIDATE_COLS)
            w.writeheader()
            w.writerows(rows)
        print(f"已写入示例候选清单：{out}（{len(rows)} 条，dry-run）")
    else:
        print(f"dry-run 示例候选清单（{len(rows)} 条）：")
        for r in rows:
            print(f"  {r['candidate_id']} [{r['platform']}] {r['title']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
