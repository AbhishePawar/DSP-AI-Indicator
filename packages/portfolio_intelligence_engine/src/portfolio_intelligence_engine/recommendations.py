"""AI Recommendations — a disclosed rule engine over already-computed signals.

This is deliberately **not** a new AI/ML model. It is a transparent,
auditable decision table that reads already-computed valuation
classification (from ``valuation_heatmap``), quality score, and risk
contribution, and maps them to one of five actions
(Increase/Reduce/Hold/Review/Watch). Every recommendation cites the exact
inputs used ("supporting_metrics") and never fabricates a signal that was
not supplied.
"""

from __future__ import annotations

from collections.abc import Sequence

from portfolio_intelligence_engine.enums import RecommendationAction, ValuationClass
from portfolio_intelligence_engine.models import HoldingSignal, PortfolioRecommendation
from portfolio_intelligence_engine.reference import (
    CONCENTRATION_SINGLE_POSITION_FLAG_PCT,
)
from portfolio_intelligence_engine.valuation_heatmap import classify_valuation

__all__ = ["generate_recommendations"]

_QUALITY_HIGH = 70.0
_QUALITY_LOW = 40.0
_RISK_CONTRIBUTION_HOT = 25.0


def _confidence(*signals: float | None) -> float | None:
    present = [s for s in signals if s is not None]
    if not present:
        return None
    return sum(present) / len(present)


def _recommend_one(h: HoldingSignal, *, total_weight: float) -> PortfolioRecommendation:
    weight_pct = h.weight / total_weight if total_weight else h.weight
    valuation_class = classify_valuation(h.margin_of_safety)
    is_concentrated = weight_pct >= CONCENTRATION_SINGLE_POSITION_FLAG_PCT
    is_hot_risk = (h.risk_contribution_pct or 0.0) >= _RISK_CONTRIBUTION_HOT

    metrics = {
        "weight_pct": weight_pct,
        "margin_of_safety": h.margin_of_safety,
        "valuation_class": valuation_class.value,
        "quality_score": h.quality_score,
        "risk_contribution_pct": h.risk_contribution_pct,
        "valuation_confidence": h.valuation_confidence,
        "committee_confidence": h.committee_confidence,
    }
    confidence = _confidence(h.valuation_confidence, h.committee_confidence)

    if valuation_class is ValuationClass.UNAVAILABLE and h.quality_score is None:
        return PortfolioRecommendation(
            symbol=h.symbol,
            action=RecommendationAction.WATCH,
            reason=(
                "No linked valuation or quality research for this holding — "
                "link a Research Object to enable a substantiated call."
            ),
            supporting_metrics=metrics,
            confidence=None,
        )

    if valuation_class is ValuationClass.OVERVALUED:
        if is_concentrated:
            return PortfolioRecommendation(
                symbol=h.symbol,
                action=RecommendationAction.REDUCE,
                reason=(
                    f"{h.symbol} is classified Overvalued (margin of safety "
                    f"{h.margin_of_safety:.1%}) and is a concentrated position "
                    f"({weight_pct:.1%} of the portfolio)."
                ),
                supporting_metrics=metrics,
                confidence=confidence,
            )
        return PortfolioRecommendation(
            symbol=h.symbol,
            action=RecommendationAction.REVIEW,
            reason=(
                f"{h.symbol} is classified Overvalued (margin of safety "
                f"{h.margin_of_safety:.1%})."
            ),
            supporting_metrics=metrics,
            confidence=confidence,
        )

    if valuation_class is ValuationClass.UNDERVALUED:
        if h.quality_score is not None and h.quality_score >= _QUALITY_HIGH:
            return PortfolioRecommendation(
                symbol=h.symbol,
                action=RecommendationAction.INCREASE,
                reason=(
                    f"{h.symbol} is classified Undervalued (margin of safety "
                    f"{h.margin_of_safety:.1%}) with a business-quality score of "
                    f"{h.quality_score:.0f}/100."
                ),
                supporting_metrics=metrics,
                confidence=confidence,
            )
        quality_phrase = (
            f"low ({round(h.quality_score)}/100)"
            if h.quality_score is not None
            else "unavailable"
        )
        return PortfolioRecommendation(
            symbol=h.symbol,
            action=RecommendationAction.REVIEW,
            reason=(
                f"{h.symbol} is classified Undervalued (margin of safety "
                f"{h.margin_of_safety:.1%}) but business-quality is "
                f"{quality_phrase} — review before increasing."
            ),
            supporting_metrics=metrics,
            confidence=confidence,
        )

    if is_hot_risk:
        return PortfolioRecommendation(
            symbol=h.symbol,
            action=RecommendationAction.WATCH,
            reason=(
                f"{h.symbol} contributes {h.risk_contribution_pct:.1f}% of total "
                "portfolio risk, disproportionate to a fairly-valued classification."
            ),
            supporting_metrics=metrics,
            confidence=confidence,
        )

    if h.quality_score is not None and h.quality_score <= _QUALITY_LOW:
        return PortfolioRecommendation(
            symbol=h.symbol,
            action=RecommendationAction.REVIEW,
            reason=(
                f"{h.symbol} is Fairly Valued but business-quality is low "
                f"({h.quality_score:.0f}/100)."
            ),
            supporting_metrics=metrics,
            confidence=confidence,
        )

    return PortfolioRecommendation(
        symbol=h.symbol,
        action=RecommendationAction.HOLD,
        reason=f"{h.symbol} is Fairly Valued with no elevated risk or quality flags.",
        supporting_metrics=metrics,
        confidence=confidence,
    )


def generate_recommendations(
    holdings: Sequence[HoldingSignal],
) -> tuple[PortfolioRecommendation, ...]:
    """Generate one rule-based recommendation per holding."""
    if not holdings:
        return ()
    total_weight = sum(h.weight for h in holdings) or 1.0
    return tuple(_recommend_one(h, total_weight=total_weight) for h in holdings)
