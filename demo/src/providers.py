# -*- coding: utf-8 -*-
"""Demo 标签 provider：默认确定性 mock；real 仅提供接口，不在 CI 运行。"""
from __future__ import annotations

import json
from pathlib import Path

DEMO_ROOT = Path(__file__).resolve().parent.parent


class MockProvider:
    """确定性 mock：按 deterministic_responses.json 的关键词规则打标签。不联网、不调用模型。"""

    def __init__(self, rules_path=None):
        rules_path = Path(rules_path) if rules_path else DEMO_ROOT / "mock" / "deterministic_responses.json"
        cfg = json.loads(rules_path.read_text(encoding="utf-8"))
        self.rules = cfg["rules"]
        self.default = cfg["default"]

    def label(self, text: str):
        for r in self.rules:
            if any(kw in text for kw in r["keywords"]):
                return {"surface_topic": r["surface_topic"], "mechanism_label": r["mechanism_label"]}
        return dict(self.default)


class RealProvider:
    """真实模型 provider 接口占位。默认不启用；CI 永不运行；需用户显式配置。"""

    def __init__(self, *args, **kwargs):
        pass

    def label(self, text: str):
        raise RuntimeError(
            "RealProvider 未启用：Demo 默认离线 mock。真实运行需用户显式配置且不得在 CI 中执行。")


def get_provider(name="mock", **kwargs):
    if name == "mock":
        return MockProvider(**kwargs)
    if name == "real":
        return RealProvider(**kwargs)
    raise ValueError(f"未知 provider: {name}")
