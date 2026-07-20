#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PsyLens deterministic offline Demo entry point.

The Demo reads sanitized sample input, generates evidence, draft observations,
product hypotheses and evaluation reports. It does not use network access or
external model APIs when the mock provider is selected.
"""
from __future__ import annotations

import argparse
import importlib
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))


def _load_pipeline():
    return importlib.import_module("demo.src.pipeline")


def main(argv=None):
    parser = argparse.ArgumentParser(description="PsyLens deterministic offline Demo")
    parser.add_argument("--input", default=str(REPO_ROOT / "demo" / "examples" / "sample_feedback.csv"))
    parser.add_argument("--output", default=str(REPO_ROOT / "artifacts" / "demo" / "default_run"))
    parser.add_argument("--provider", default="mock", choices=["mock", "real"])
    parser.add_argument("--run-id", default="demo")
    parser.add_argument("--generated-at", default="2026-07-17T16:56:33.578346+08:00")
    args = parser.parse_args(argv)

    pipeline = _load_pipeline()
    manifest = pipeline.run(
        args.input,
        args.output,
        provider_name=args.provider,
        generated_at=args.generated_at,
        run_id=args.run_id,
    )

    print("Demo completed")
    print(f"output={args.output}")
    print(f"provider={args.provider} offline={manifest['offline']}")
    print(
        f"samples={manifest['sample_count']} evidence={manifest['evidence_count']} "
        f"insights={manifest['insight_count']} actions={manifest['action_count']}"
    )
    print(f"evaluation_status={manifest['evaluation_status']}")
    return 0 if manifest["evaluation_status"] == "PASS" else 2


if __name__ == "__main__":
    sys.exit(main())
