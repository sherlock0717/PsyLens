#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PsyLens 离线 Demo 入口。

默认：脱敏示例输入 -> 证据拆分 -> 确定性 mock 标签 -> 草稿洞察 -> 草稿产品假设 -> 评测 -> 报告。
默认离线、不联网、不调用模型、不读取 .env/Cookie/Key，不覆盖 data/v2 与 docs/files。

用法：
  python tools/run_demo.py
  python tools/run_demo.py --input demo/examples/sample_feedback.csv --output artifacts/demo/test_run
  python tools/run_demo.py --provider mock --output artifacts/demo/ci
"""
from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEMO_SRC = REPO_ROOT / "demo" / "src"

# 以包方式加载 demo.src.pipeline
sys.path.insert(0, str(REPO_ROOT))
_spec = importlib.util.spec_from_file_location("demo.src.pipeline", DEMO_SRC / "pipeline.py")


def _load_pipeline():
    import importlib
    # 确保 demo 与 demo.src 作为包可导入
    for pkg in ("demo", "demo.src"):
        init = REPO_ROOT / pkg.replace(".", "/") / "__init__.py"
        if not init.exists():
            init.parent.mkdir(parents=True, exist_ok=True)
            init.write_text("", encoding="utf-8")
    return importlib.import_module("demo.src.pipeline")


def main(argv=None):
    ap = argparse.ArgumentParser(description="PsyLens 离线 Demo（默认 mock、确定性、离线）")
    ap.add_argument("--input", default=str(REPO_ROOT / "demo" / "examples" / "sample_feedback.csv"))
    ap.add_argument("--output", default=str(REPO_ROOT / "artifacts" / "demo" / "default_run"))
    ap.add_argument("--provider", default="mock", choices=["mock", "real"])
    ap.add_argument("--run-id", default="demo")
    ap.add_argument("--generated-at", default="2026-07-17T16:56:33.578346+08:00")
    args = ap.parse_args(argv)

    pipeline = _load_pipeline()
    manifest = pipeline.run(args.input, args.output, provider_name=args.provider,
                            generated_at=args.generated_at, run_id=args.run_id)
    print("Demo 运行完成：")
    print(f"  output={args.output} provider={args.provider} offline={manifest['offline']}")
    print(f"  samples={manifest['sample_count']} evidence={manifest['evidence_count']} "
          f"insights={manifest['insight_count']} actions={manifest['action_count']}")
    print(f"  evaluation_status={manifest['evaluation_status']}")
    return 0 if manifest["evaluation_status"] == "PASS" else 2


if __name__ == "__main__":
    sys.exit(main())
