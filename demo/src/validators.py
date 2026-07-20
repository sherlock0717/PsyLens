# -*- coding: utf-8 -*-
"""Demo 数据校验：证据文本可定位、标签合法、引用可解析。"""
from __future__ import annotations

import re

ALLOWED_MECH = {"competence_frustration", "fairness_threat", "trust_communication_gap",
                "belonging_drop", "norm_safety_risk", "uncertain"}

_WS = re.compile(r"\s+")


def normalize(s: str) -> str:
    return _WS.sub("", (s or "").strip().lower())


def evidence_locatable(unit_text: str, raw_text: str) -> bool:
    nu = normalize(unit_text)
    return bool(nu) and nu in normalize(raw_text)


def label_valid(mechanism_label: str) -> bool:
    return (mechanism_label or "") in (ALLOWED_MECH | {"", "unassigned"})


def ids_resolvable(ref_ids, universe) -> bool:
    return all(i in universe for i in ref_ids)
