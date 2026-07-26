"""Public-signal extraction for committee reviewers (no internal models)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

__all__ = ["CommitteeSignals", "build_signals", "explained_value", "safe_score"]


def explained_value(obj: object | None, *path: str) -> float | None:
    cur: Any = obj
    for name in path:
        if cur is None:
            return None
        cur = getattr(cur, name, None)
    if cur is None:
        return None
    if isinstance(cur, (int, float)) and not isinstance(cur, bool):
        return float(cur)
    value = getattr(cur, "value", None)
    if value is None:
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    return None


def safe_score(analysis: object | None) -> float | None:
    return explained_value(analysis, "score")


@dataclass(frozen=True, slots=True)
class CommitteeSignals:
    """Flattened public metrics consumed by deterministic reviewers."""

    business_quality: float | None
    economic_moat: float | None
    management_quality: float | None
    financial_strength: float | None
    earnings_quality: float | None
    growth_quality: float | None
    investment_score: float | None
    recommendation: str | None
    mos_ratio: float | None
    premium_discount: float | None
    mos_classification: str | None
    ir_confidence: float
    bq_confidence: float
    valuation_confidence: float
    conflict_count: int
    ir_triggered_rules: tuple[str, ...]


def build_signals(
    *,
    recommendation: object,
    business_quality: object,
    economic_moat: object,
    management_quality: object,
    financial_strength: object,
    earnings_quality: object,
    growth_quality: object,
    valuation: object,
) -> CommitteeSignals:
    mos_obj = getattr(recommendation, "margin_of_safety", None)
    mos_ratio = explained_value(mos_obj, "margin_of_safety")
    if mos_ratio is None:
        mos_ratio = explained_value(valuation, "margin_of_safety")
    if mos_ratio is None and hasattr(valuation, "margin_of_safety"):
        # ValuationSignals
        raw = getattr(valuation, "margin_of_safety", None)
        if isinstance(raw, (int, float)) and not isinstance(raw, bool):
            mos_ratio = float(raw)

    premium = explained_value(mos_obj, "premium_discount")
    if premium is None:
        premium = explained_value(valuation, "premium_discount")
    if premium is None:
        raw_p = getattr(valuation, "premium_discount", None)
        if isinstance(raw_p, (int, float)) and not isinstance(raw_p, bool):
            premium = float(raw_p)

    classification = None
    if mos_obj is not None:
        classification = getattr(mos_obj, "classification", None)
    if classification is None:
        classification = "unavailable"

    rec = getattr(recommendation, "recommendation", None)
    rec_value = getattr(rec, "value", rec)
    rules = getattr(recommendation, "triggered_rules", ()) or ()
    rule_ids = tuple(
        str(getattr(r, "rule_id", r)) for r in rules
    )
    conflicts = getattr(business_quality, "conflict_adjustments", ()) or ()

    val_conf = explained_value(valuation, "confidence")
    if val_conf is None:
        val_conf = explained_value(mos_obj, "valuation_confidence") or 0.55

    return CommitteeSignals(
        business_quality=safe_score(business_quality),
        economic_moat=safe_score(economic_moat),
        management_quality=safe_score(management_quality),
        financial_strength=safe_score(financial_strength),
        earnings_quality=safe_score(earnings_quality),
        growth_quality=safe_score(growth_quality),
        investment_score=safe_score(recommendation),
        recommendation=str(rec_value) if rec_value is not None else None,
        mos_ratio=mos_ratio,
        premium_discount=premium,
        mos_classification=str(classification),
        ir_confidence=explained_value(recommendation, "confidence") or 0.4,
        bq_confidence=explained_value(business_quality, "confidence") or 0.4,
        valuation_confidence=float(val_conf),
        conflict_count=len(tuple(conflicts)),
        ir_triggered_rules=rule_ids,
    )
