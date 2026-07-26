"""Scoring primitives and rating framework for Growth Quality."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping, Sequence

from growth_quality.exceptions import GrowthQualityValidationError

__all__ = [
    "DEFAULT_GROWTH_WEIGHTS",
    "GrowthQualityDimension",
    "GrowthQualityRating",
    "GrowthQualityWeights",
    "clip_score",
    "growth_rating_from_score",
    "validate_weights",
    "weighted_mean",
]


class GrowthQualityDimension(str, Enum):
    REVENUE_GROWTH_QUALITY = "revenue_growth_quality"
    EARNINGS_GROWTH_QUALITY = "earnings_growth_quality"
    REINVESTMENT_CAPABILITY = "reinvestment_capability"
    CAPITAL_ALLOCATION_SUPPORT = "capital_allocation_support"
    GROWTH_SUSTAINABILITY = "growth_sustainability"
    GROWTH_RISK = "growth_risk"


class GrowthQualityRating(str, Enum):
    VERY_WEAK = "very_weak"
    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"
    EXCEPTIONAL = "exceptional"


@dataclass(frozen=True, slots=True)
class GrowthQualityWeights:
    revenue_growth_quality: float = 0.18
    earnings_growth_quality: float = 0.18
    reinvestment_capability: float = 0.20
    capital_allocation_support: float = 0.16
    growth_sustainability: float = 0.16
    growth_risk: float = 0.12

    def as_dict(self) -> dict[str, float]:
        return {
            GrowthQualityDimension.REVENUE_GROWTH_QUALITY.value: (
                self.revenue_growth_quality
            ),
            GrowthQualityDimension.EARNINGS_GROWTH_QUALITY.value: (
                self.earnings_growth_quality
            ),
            GrowthQualityDimension.REINVESTMENT_CAPABILITY.value: (
                self.reinvestment_capability
            ),
            GrowthQualityDimension.CAPITAL_ALLOCATION_SUPPORT.value: (
                self.capital_allocation_support
            ),
            GrowthQualityDimension.GROWTH_SUSTAINABILITY.value: (
                self.growth_sustainability
            ),
            GrowthQualityDimension.GROWTH_RISK.value: self.growth_risk,
        }

    def weight_for(self, dimension: GrowthQualityDimension) -> float:
        return self.as_dict()[dimension.value]

    def to_dict(self) -> dict[str, Any]:
        return self.as_dict()


DEFAULT_GROWTH_WEIGHTS = GrowthQualityWeights()


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


def growth_rating_from_score(score: float | None) -> GrowthQualityRating:
    if score is None:
        return GrowthQualityRating.VERY_WEAK
    if score >= 85.0:
        return GrowthQualityRating.EXCEPTIONAL
    if score >= 70.0:
        return GrowthQualityRating.STRONG
    if score >= 55.0:
        return GrowthQualityRating.MODERATE
    if score >= 40.0:
        return GrowthQualityRating.WEAK
    return GrowthQualityRating.VERY_WEAK


def validate_weights(
    weights: GrowthQualityWeights | Mapping[str, float] | None,
) -> GrowthQualityWeights:
    if weights is None:
        return DEFAULT_GROWTH_WEIGHTS
    if isinstance(weights, GrowthQualityWeights):
        payload = weights.as_dict()
    else:
        payload = {str(k): float(v) for k, v in weights.items()}
    required = {d.value for d in GrowthQualityDimension}
    missing = required - set(payload)
    if missing:
        raise GrowthQualityValidationError(
            f"Missing growth quality weight keys: {sorted(missing)}"
        )
    values = [float(payload[k]) for k in sorted(required)]
    if any(not (v == v) or v < 0 for v in values):
        raise GrowthQualityValidationError(
            "Growth quality weights must be finite and >= 0"
        )
    total = sum(values)
    if abs(total - 1.0) > 1e-6:
        raise GrowthQualityValidationError(
            f"Growth quality weights must sum to 1.0 (got {total})"
        )
    return GrowthQualityWeights(
        revenue_growth_quality=float(
            payload[GrowthQualityDimension.REVENUE_GROWTH_QUALITY.value]
        ),
        earnings_growth_quality=float(
            payload[GrowthQualityDimension.EARNINGS_GROWTH_QUALITY.value]
        ),
        reinvestment_capability=float(
            payload[GrowthQualityDimension.REINVESTMENT_CAPABILITY.value]
        ),
        capital_allocation_support=float(
            payload[GrowthQualityDimension.CAPITAL_ALLOCATION_SUPPORT.value]
        ),
        growth_sustainability=float(
            payload[GrowthQualityDimension.GROWTH_SUSTAINABILITY.value]
        ),
        growth_risk=float(payload[GrowthQualityDimension.GROWTH_RISK.value]),
    )
