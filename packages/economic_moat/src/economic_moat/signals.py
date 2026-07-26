"""Shared signal extraction from FinancialAnalysis and BusinessQualityAnalysis.

Reads public upstream façades only — does not recompute financials or BQ math.
"""

from __future__ import annotations

from typing import Any

__all__ = [
    "assessment_score_01",
    "gross_margin",
    "intangible_pct",
    "goodwill_pct",
    "operating_margin",
    "ratio_value",
    "safe_getattr",
]


def safe_getattr(obj: object | None, *path: str, default: Any = None) -> Any:
    """Walk attribute path; return ``default`` on missing/None."""
    cur: Any = obj
    for name in path:
        if cur is None:
            return default
        cur = getattr(cur, name, None)
    return default if cur is None else cur


def ratio_value(ratios_obj: object | None, name: str) -> float | None:
    """Extract a named RatioMetric value from a profitability/efficiency container."""
    if ratios_obj is None:
        return None
    # Mapping-like
    if isinstance(ratios_obj, dict):
        item = ratios_obj.get(name)
        if item is None:
            return None
        return float(getattr(item, "value", item))
    # Iterable of RatioMetric
    try:
        for item in ratios_obj:  # type: ignore[union-attr]
            if getattr(item, "name", None) == name:
                value = getattr(item, "value", None)
                return float(value) if value is not None else None
    except TypeError:
        pass
    # Attribute bag
    direct = getattr(ratios_obj, name, None)
    if direct is None:
        return None
    if isinstance(direct, (int, float)) and not isinstance(direct, bool):
        return float(direct)
    value = getattr(direct, "value", None)
    return float(value) if value is not None else None


def assessment_score_01(module: object | None, assessment_name: str) -> float | None:
    """Return BQ Assessment score on 0–1 scale (from 0–100 Score.value)."""
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


def gross_margin(financial_analysis: object) -> float | None:
    return safe_getattr(financial_analysis, "income", "margins", "gross_margin")


def operating_margin(financial_analysis: object) -> float | None:
    return safe_getattr(financial_analysis, "income", "margins", "operating_margin")


def intangible_pct(financial_analysis: object) -> float | None:
    return safe_getattr(
        financial_analysis, "balance_sheet", "assets", "intangible_asset_pct"
    )


def goodwill_pct(financial_analysis: object) -> float | None:
    return safe_getattr(financial_analysis, "balance_sheet", "assets", "goodwill_pct")
