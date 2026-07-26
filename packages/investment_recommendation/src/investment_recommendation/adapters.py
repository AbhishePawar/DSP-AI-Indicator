"""Adapters that read ONLY public surfaces from domain engines / valuation."""

from __future__ import annotations

from typing import Any

from investment_recommendation.models import (
    DecisionContribution,
    InvestmentRecommendationConfidence,
    InvestmentRecommendationScore,
    MarginOfSafetyAssessment,
)
from investment_recommendation.scoring import (
    DecisionComponent,
    mos_to_valuation_score,
)

__all__ = [
    "explained_value",
    "extract_margin_of_safety",
    "make_contribution",
    "safe_confidence",
    "safe_score_value",
]


def explained_value(obj: object | None, *path: str) -> float | None:
    """Read nested public attributes; unwrap ``.value`` when present."""
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


def safe_score_value(analysis: object | None) -> float | None:
    return explained_value(analysis, "score")


def safe_confidence(analysis: object | None, *, default: float = 0.35) -> float:
    value = explained_value(analysis, "confidence")
    if value is None:
        return default
    return max(0.0, min(1.0, value))


def extract_margin_of_safety(
    valuation: object | None,
    *,
    business_quality_confidence: float,
) -> MarginOfSafetyAssessment:
    # Prefer ValuationSignals public contract; also accept OverallValuationResult
    from investment_recommendation.valuation_signals import ValuationSignals

    if isinstance(valuation, ValuationSignals):
        ivps = valuation.intrinsic_value_per_share
        price = valuation.current_market_price
        mos = valuation.margin_of_safety
        premium = valuation.premium_discount
        val_conf = valuation.confidence
    else:
        ivps = explained_value(valuation, "overall_intrinsic_value_per_share")
        price = explained_value(valuation, "current_market_price")
        mos = explained_value(valuation, "margin_of_safety")
        premium = explained_value(valuation, "premium_discount")
        if mos is None and ivps is not None and price is not None and ivps != 0:
            mos = (ivps - price) / ivps
        if premium is None and ivps is not None and price is not None and ivps != 0:
            premium = (price - ivps) / ivps
        val_conf = explained_value(valuation, "confidence")
        if val_conf is None:
            val_conf = 0.55 if mos is not None else 0.25
        else:
            val_conf = max(0.0, min(1.0, float(val_conf)))

    valuation_score = mos_to_valuation_score(mos)

    if mos is None:
        classification = "unavailable"
        reasoning = (
            "Margin of safety unavailable — intrinsic value and/or market price missing."
        )
    elif mos >= 0.40:
        classification = "deep_value"
        reasoning = "Large discount to conservative intrinsic value per share."
    elif mos >= 0.15:
        classification = "undervalued"
        reasoning = "Material discount to intrinsic value supports a MoS buffer."
    elif mos >= -0.10:
        classification = "fairly_valued"
        reasoning = "Price is near conservative intrinsic value."
    elif mos >= -0.25:
        classification = "overvalued"
        reasoning = "Price is above intrinsic value; MoS is negative."
    else:
        classification = "extremely_overvalued"
        reasoning = (
            "Price is materially above intrinsic value; Strong Buy is blocked by rule."
        )

    # Blend valuation confidence with BQ confidence for MoS assessment note
    _ = business_quality_confidence
    return MarginOfSafetyAssessment(
        intrinsic_value_per_share=ivps,
        current_market_price=price,
        margin_of_safety=None if mos is None else round(mos, 6),
        premium_discount=None if premium is None else round(premium, 6),
        valuation_score=(
            None if valuation_score is None else round(valuation_score, 4)
        ),
        valuation_confidence=round(val_conf, 4),
        classification=classification,
        reasoning=reasoning,
    )


def make_contribution(
    component: DecisionComponent,
    score_value: float | None,
    *,
    weight: float,
    confidence: float,
) -> DecisionContribution:
    score = (
        InvestmentRecommendationScore(value=None, status="insufficient_data")
        if score_value is None
        else InvestmentRecommendationScore(
            value=round(score_value, 4), status="assessed"
        )
    )
    contribution = None if score_value is None else round(score_value * weight, 4)
    return DecisionContribution(
        component=component,
        score=score,
        weight=weight,
        weighted_contribution=contribution,
        confidence=InvestmentRecommendationConfidence(
            value=round(confidence, 4), basis=f"{component.value}_confidence"
        ),
        data_available=score_value is not None,
    )
