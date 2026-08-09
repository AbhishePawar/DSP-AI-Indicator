"""Scoring, weights, and recommendation scale for Investment Recommendation."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping

from investment_recommendation.exceptions import (
    InvestmentRecommendationValidationError,
)

__all__ = [
    "DEFAULT_DECISION_WEIGHTS",
    "DecisionComponent",
    "InvestmentRecommendationAction",
    "DecisionWeights",
    "action_from_score",
    "clip_score",
    "mos_to_valuation_score",
    "validate_weights",
    "weighted_mean",
]


class DecisionComponent(str, Enum):
    BUSINESS_QUALITY = "business_quality"
    VALUATION_MOS = "valuation_mos"
    ECONOMIC_MOAT = "economic_moat"
    MANAGEMENT_QUALITY = "management_quality"
    FINANCIAL_STRENGTH = "financial_strength"
    EARNINGS_QUALITY = "earnings_quality"
    GROWTH_QUALITY = "growth_quality"


class InvestmentRecommendationAction(str, Enum):
    UNAVAILABLE = "unavailable"
    STRONG_SELL = "strong_sell"
    SELL = "sell"
    REDUCE = "reduce"
    HOLD = "hold"
    ACCUMULATE = "accumulate"
    BUY = "buy"
    STRONG_BUY = "strong_buy"


@dataclass(frozen=True, slots=True)
class DecisionWeights:
    """Documented decision blend (Buffett-aligned; quality + MoS primary)."""

    business_quality: float = 0.40
    valuation_mos: float = 0.35
    economic_moat: float = 0.08
    management_quality: float = 0.06
    financial_strength: float = 0.05
    earnings_quality: float = 0.03
    growth_quality: float = 0.03

    def as_dict(self) -> dict[str, float]:
        return {
            DecisionComponent.BUSINESS_QUALITY.value: self.business_quality,
            DecisionComponent.VALUATION_MOS.value: self.valuation_mos,
            DecisionComponent.ECONOMIC_MOAT.value: self.economic_moat,
            DecisionComponent.MANAGEMENT_QUALITY.value: self.management_quality,
            DecisionComponent.FINANCIAL_STRENGTH.value: self.financial_strength,
            DecisionComponent.EARNINGS_QUALITY.value: self.earnings_quality,
            DecisionComponent.GROWTH_QUALITY.value: self.growth_quality,
        }

    def to_dict(self) -> dict[str, Any]:
        return self.as_dict()


DEFAULT_DECISION_WEIGHTS = DecisionWeights()


def clip_score(value: float, *, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, value))


def weighted_mean(items: list[tuple[float, float]] | tuple[tuple[float, float], ...]) -> float | None:
    total_w = 0.0
    acc = 0.0
    for value, weight in items:
        if weight <= 0:
            continue
        total_w += weight
        acc += value * weight
    if total_w <= 0:
        return None
    return acc / total_w


def mos_to_valuation_score(mos_ratio: float | None) -> float | None:
    """Map margin-of-safety ratio to 0–100 (higher MoS = more attractive).

    MoS = (IV − Price) / IV.  ~40% MoS → ~90; fair (~0) → ~50; −40% → ~10.
    """
    if mos_ratio is None:
        return None
    # Linear map: mos -0.40 → 10, 0 → 50, +0.40 → 90
    return clip_score(50.0 + float(mos_ratio) * 100.0)


def action_from_score(score: float | None) -> InvestmentRecommendationAction:
    # CV-001 / CV-005 — insufficient score must not invent HOLD.
    if score is None:
        return InvestmentRecommendationAction.UNAVAILABLE
    if score >= 85.0:
        return InvestmentRecommendationAction.STRONG_BUY
    if score >= 75.0:
        return InvestmentRecommendationAction.BUY
    if score >= 65.0:
        return InvestmentRecommendationAction.ACCUMULATE
    if score >= 50.0:
        return InvestmentRecommendationAction.HOLD
    if score >= 40.0:
        return InvestmentRecommendationAction.REDUCE
    if score >= 25.0:
        return InvestmentRecommendationAction.SELL
    return InvestmentRecommendationAction.STRONG_SELL


def validate_weights(
    weights: DecisionWeights | Mapping[str, float] | None,
) -> DecisionWeights:
    if weights is None:
        return DEFAULT_DECISION_WEIGHTS
    if isinstance(weights, DecisionWeights):
        payload = weights.as_dict()
    else:
        payload = {str(k): float(v) for k, v in weights.items()}
    required = {c.value for c in DecisionComponent}
    missing = required - set(payload)
    if missing:
        raise InvestmentRecommendationValidationError(
            f"Missing decision weight keys: {sorted(missing)}"
        )
    values = [float(payload[k]) for k in sorted(required)]
    if any(not (v == v) or v < 0 for v in values):
        raise InvestmentRecommendationValidationError(
            "Decision weights must be finite and >= 0"
        )
    total = sum(values)
    if abs(total - 1.0) > 1e-6:
        raise InvestmentRecommendationValidationError(
            f"Decision weights must sum to 1.0 (got {total})"
        )
    return DecisionWeights(
        business_quality=float(payload[DecisionComponent.BUSINESS_QUALITY.value]),
        valuation_mos=float(payload[DecisionComponent.VALUATION_MOS.value]),
        economic_moat=float(payload[DecisionComponent.ECONOMIC_MOAT.value]),
        management_quality=float(
            payload[DecisionComponent.MANAGEMENT_QUALITY.value]
        ),
        financial_strength=float(
            payload[DecisionComponent.FINANCIAL_STRENGTH.value]
        ),
        earnings_quality=float(payload[DecisionComponent.EARNINGS_QUALITY.value]),
        growth_quality=float(payload[DecisionComponent.GROWTH_QUALITY.value]),
    )
