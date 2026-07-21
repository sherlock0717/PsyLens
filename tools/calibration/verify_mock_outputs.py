#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""校验 mock 校准产物与公开样本的结构化字段安全性（供 CI 与本地使用）。

检查项：
- 复检与共识报告的 result_type 均为 mock_pipeline_self_test；
- 公开校准样本中是否存在结构化的平台字段、来源编号字段、当前标签字段、
  重测字段，以及 BILI / NGA / TIEBA 等内部来源编号前缀。

只检查结构化字段与来源编号前缀，不判断脱敏文本内容。任一检查不通过则以非零码退出，
便于 CI 阻断。
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

MOCK_RESULT_TYPE = "mock_pipeline_self_test"
FORBIDDEN_HEADER_TOKENS = ["platform", "source_evidence", "mechanism_label",
                           "surface_topic", "label_source", "review_status",
                           "is_retest", "retest_group", "sampling_stratum",
                           "original_main"]
PLATFORM_TOKENS = ["BILI", "NGA", "TIEBA"]


def _check_result_type(path, label, problems):
    p = Path(path)
    if not p.exists():
        problems.append(f"{label} 不存在：{path}")
        return
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        problems.append(f"{label} 不是合法 JSON：{path}")
        return
    if data.get("result_type") != MOCK_RESULT_TYPE:
        problems.append(f"{label} 的 result_type={data.get('result_type')}，应为 {MOCK_RESULT_TYPE}")


def _check_public_sample(path, problems):
    p = Path(path)
    if not p.exists():
        problems.append(f"公开样本不存在：{path}")
        return
    raw = p.read_text(encoding="utf-8")
    with p.open("r", encoding="utf-8-sig", newline="") as f:
        header = next(csv.reader(f))
    joined_header = " ".join(header).lower()
    for token in FORBIDDEN_HEADER_TOKENS:
        if token in joined_header:
            problems.append(f"公开样本列名疑似泄漏：{token}")
    for token in PLATFORM_TOKENS:
        if token in raw:
            problems.append(f"公开样本出现平台标识：{token}")


def main(argv=None):
    ap = argparse.ArgumentParser(description="校验 mock 校准产物与公开样本安全性")
    ap.add_argument("--run-report", required=True)
    ap.add_argument("--consensus-report", required=True)
    ap.add_argument("--public-sample", required=True)
    args = ap.parse_args(argv)

    problems = []
    _check_result_type(args.run_report, "复检报告", problems)
    _check_result_type(args.consensus_report, "共识报告", problems)
    _check_public_sample(args.public_sample, problems)

    if problems:
        print("校准产物校验未通过：", file=sys.stderr)
        for msg in problems:
            print(f"  - {msg}", file=sys.stderr)
        return 1
    print("校准产物校验通过：result_type=mock_pipeline_self_test，"
          "公开样本未包含结构化来源、当前标签或重测字段。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
