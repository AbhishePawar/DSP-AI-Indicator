"""Scoring primitives, weights, and rating framework for aggregation."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping, Sequence

from business_quality_aggregator.exceptions import (
    BusinessQualityAggregatorValidationError,
)

__all__ = [
    "DEFAULT_AGGREGATOR_WEIGHTS",
    "AggregatorComponent",
    "BusinessQualityAggregatorRating",
    "BusinessQualityAggregatorWeights",
    "aggregator_rating_from_score",
    "clip_score",
    "validate_weights",
    "weighted_mean",
]


class AggregatorComponent(str, Enum):
    ECONOMIC_MOAT = "economic_moat"
    MANAGEMENT_QUALITY = "management_quality"
    FINANCIAL_STRENGTH = "financial_strength"
    EARNINGS_QUALITY = "earnings_quality"
    GROWTH_QUALITY = "growth_quality"


class BusinessQualityAggregatorRating(str, Enum):
    POOR = "poor"
    BELOW_AVERAGE = "below_average"
    AVERAGE = "average"
    GOOD = "good"
    EXCELLENT = "excellent"
    EXCEPTIONAL = "exceptional"


@dataclass(frozen=True, slots=True)
class BusinessQualityAggregatorWeights:
    """Documented default weighting methodology (Buffett-aligned)."""

    economic_moat: float = 0.25
    management_quality: float = 0.20
    financial_strength: float = 0.20
    earnings_quality: float = 0.20
    growth_quality: float = 0.15

    def as_dict(self) -> dict[str, float]:
        return {
            AggregatorComponent.ECONOMIC_MOAT.value: self.economic_moat,
            AggregatorComponent.MANAGEMENT_QUALITY.value: self.management_quality,
            AggregatorComponent.FINANCIAL_STRENGTH.value: self.financial_strength,
            AggregatorComponent.EARNINGS_QUALITY.value: self.earnings_quality,
            AggregatorComponent.GROWTH_QUALITY.value: self.growth_quality,
        }

    def weight_for(self, component: AggregatorComponent) -> float:
        return self.as_dict()[component.value]

    def to_dict(self) -> dict[str, Any]:
        return self.as_dict()


DEFAULT_AGGREGATOR_WEIGHTS = BusinessQualityAggregatorWeights()


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


def aggregator_rating_from_score(
    score: float | None,
) -> BusinessQualityAggregatorRating:
    if score is None:
        return BusinessQualityAggregatorRating.POOR
    if score >= 90.0:
        return BusinessQualityAggregatorRating.EXCEPTIONAL
    if score >= 80.0:
        return BusinessQualityAggregatorRating.EXCELLENT
    if score >= 70.0:
        return BusinessQualityAggregatorRating.GOOD
    if score >= 55.0:
        return BusinessQualityAggregatorRating.AVERAGE
    if score >= 40.0:
        return BusinessQualityAggregatorRating.BELOW_AVERAGE
    return BusinessQualityAggregatorRating.POOR


def validate_weights(
    weights: BusinessQualityAggregatorWeights | Mapping[str, float] | None,
) -> BusinessQualityAggregatorWeights:
    if weights is None:
        return DEFAULT_AGGREGATOR_WEIGHTS
    if isinstance(weights, BusinessQualityAggregatorWeights):
        payload = weights.as_dict()
    else:
        payload = {str(k): float(v) for k, v in weights.items()}
    required = {c.value for c in AggregatorComponent}
    missing = required - set(payload)
    if missing:
        raise BusinessQualityAggregatorValidationError(
            f"Missing aggregator weight keys: {sorted(missing)}"
        )
    values = [float(payload[k]) for k in sorted(required)]
    if any(not (v == v) or v < 0 for v in values):
        raise BusinessQualityAggregatorValidationError(
            "Aggregator weights must be finite and >= 0"
        )
    total = sum(values)
    if abs(total - 1.0) > 1e-6:
        raise BusinessQualityAggregatorValidationError(
            f"Aggregator weights must sum to 1.0 (got {total})"
        )
    return BusinessQualityAggregatorWeights(
        economic_moat=float(payload[AggregatorComponent.ECONOMIC_MOAT.value]),
        management_quality=float(
            payload[AggregatorComponent.MANAGEMENT_QUALITY.value]
        ),
        financial_strength=float(
            payload[AggregatorComponent.FINANCIAL_STRENGTH.value]
        ),
        earnings_quality=float(payload[AggregatorComponent.EARNINGS_QUALITY.value]),
        growth_quality=float(payload[AggregatorComponent.GROWTH_QUALITY.value]),
    )
