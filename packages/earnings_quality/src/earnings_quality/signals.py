"""Shared signal extraction from FinancialAnalysis and BusinessQualityAnalysis."""

from __future__ import annotations

from typing import Any

__all__ = ["assessment_score_01", "ratio_value", "safe_getattr"]


def safe_getattr(obj: object | None, *path: str, default: Any = None) -> Any:
    cur: Any = obj
    for name in path:
        if cur is None:
            return default
        cur = getattr(cur, name, None)
    return default if cur is None else cur


def ratio_value(ratios_obj: object | None, name: str) -> float | None:
    if ratios_obj is None:
        return None
    if isinstance(ratios_obj, dict):
        item = ratios_obj.get(name)
        if item is None:
            return None
        return float(getattr(item, "value", item))
    try:
        for item in ratios_obj:  # type: ignore[union-attr]
            if getattr(item, "name", None) == name:
                value = getattr(item, "value", None)
                return float(value) if value is not None else None
    except TypeError:
        pass
    direct = getattr(ratios_obj, name, None)
    if direct is None:
        return None
    if isinstance(direct, (int, float)) and not isinstance(direct, bool):
        return float(direct)
    value = getattr(direct, "value", None)
    return float(value) if value is not None else None


def assessment_score_01(module: object | None, assessment_name: str) -> float | None:
    if module is None:
        return None
    assessments = getattr(module, "assessments", ()) or ()
    for item in assessments:
        if getattr(item, "name", None) != assessment_name:
            continue
        score = getattr(item, "score", None)
        if score is None:
            return None
        value = getattr(score, "value", None)
        if value is None:
            return None
        return max(0.0, min(1.0, float(value) / 100.0))
    return None
