"""Scoring primitives and rating framework for Financial Strength."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping, Sequence

from financial_strength.exceptions import FinancialStrengthValidationError

__all__ = [
    "DEFAULT_STRENGTH_WEIGHTS",
    "FinancialStrengthDimension",
    "FinancialStrengthRating",
    "FinancialStrengthWeights",
    "clip_score",
    "strength_rating_from_score",
    "validate_weights",
    "weighted_mean",
]


class FinancialStrengthDimension(str, Enum):
    """Canonical Financial Strength dimensions (Buffett-aligned)."""

    BALANCE_SHEET_STRENGTH = "balance_sheet_strength"
    LIQUIDITY = "liquidity"
    CASH_FLOW_QUALITY = "cash_flow_quality"
    SOLVENCY = "solvency"
    PROFITABILITY_STABILITY = "profitability_stability"
    FINANCIAL_RESILIENCE = "financial_resilience"


class FinancialStrengthRating(str, Enum):
    """Ordinal overall financial strength rating."""

    VERY_WEAK = "very_weak"
    WEAK = "weak"
    AVERAGE = "average"
    STRONG = "strong"
    EXCEPTIONAL = "exceptional"


@dataclass(frozen=True, slots=True)
class FinancialStrengthWeights:
    """Normalized weights for overall financial strength score."""

    balance_sheet_strength: float = 0.20
    liquidity: float = 0.15
    cash_flow_quality: float = 0.20
    solvency: float = 0.15
    profitability_stability: float = 0.15
    financial_resilience: float = 0.15

    def as_dict(self) -> dict[str, float]:
        return {
            FinancialStrengthDimension.BALANCE_SHEET_STRENGTH.value: (
                self.balance_sheet_strength
            ),
            FinancialStrengthDimension.LIQUIDITY.value: self.liquidity,
            FinancialStrengthDimension.CASH_FLOW_QUALITY.value: self.cash_flow_quality,
            FinancialStrengthDimension.SOLVENCY.value: self.solvency,
            FinancialStrengthDimension.PROFITABILITY_STABILITY.value: (
                self.profitability_stability
            ),
            FinancialStrengthDimension.FINANCIAL_RESILIENCE.value: (
                self.financial_resilience
            ),
        }

    def weight_for(self, dimension: FinancialStrengthDimension) -> float:
        return self.as_dict()[dimension.value]

    def to_dict(self) -> dict[str, Any]:
        return self.as_dict()


DEFAULT_STRENGTH_WEIGHTS = FinancialStrengthWeights()


def clip_score(value: float, *, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, value))


def weighted_mean(items: Sequence[tuple[float, float]]) -> float | None:
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


def strength_rating_from_score(score: float | None) -> FinancialStrengthRating:
    if score is None:
        return FinancialStrengthRating.VERY_WEAK
    if score >= 85.0:
        return FinancialStrengthRating.EXCEPTIONAL
    if score >= 70.0:
        return FinancialStrengthRating.STRONG
    if score >= 55.0:
        return FinancialStrengthRating.AVERAGE
    if score >= 40.0:
        return FinancialStrengthRating.WEAK
    return FinancialStrengthRating.VERY_WEAK


def validate_weights(
    weights: FinancialStrengthWeights | Mapping[str, float] | None,
) -> FinancialStrengthWeights:
    if weights is None:
        return DEFAULT_STRENGTH_WEIGHTS
    if isinstance(weights, FinancialStrengthWeights):
        payload = weights.as_dict()
    else:
        payload = {str(k): float(v) for k, v in weights.items()}
    required = {d.value for d in FinancialStrengthDimension}
    missing = required - set(payload)
    if missing:
        raise FinancialStrengthValidationError(
            f"Missing financial strength weight keys: {sorted(missing)}"
        )
    values = [float(payload[k]) for k in sorted(required)]
    if any(not (v == v) or v < 0 for v in values):
        raise FinancialStrengthValidationError(
            "Financial strength weights must be finite and >= 0"
        )
    total = sum(values)
    if abs(total - 1.0) > 1e-6:
        raise FinancialStrengthValidationError(
            f"Financial strength weights must sum to 1.0 (got {total})"
        )
    return FinancialStrengthWeights(
        balance_sheet_strength=float(
            payload[FinancialStrengthDimension.BALANCE_SHEET_STRENGTH.value]
        ),
        liquidity=float(payload[FinancialStrengthDimension.LIQUIDITY.value]),
        cash_flow_quality=float(
            payload[FinancialStrengthDimension.CASH_FLOW_QUALITY.value]
        ),
        solvency=float(payload[FinancialStrengthDimension.SOLVENCY.value]),
        profitability_stability=float(
            payload[FinancialStrengthDimension.PROFITABILITY_STABILITY.value]
        ),
        financial_resilience=float(
            payload[FinancialStrengthDimension.FINANCIAL_RESILIENCE.value]
        ),
    )
