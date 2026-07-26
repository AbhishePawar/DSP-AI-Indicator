"""Scoring primitives and rating framework for Earnings Quality."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping, Sequence

from earnings_quality.exceptions import EarningsQualityValidationError

__all__ = [
    "DEFAULT_EARNINGS_WEIGHTS",
    "EarningsQualityDimension",
    "EarningsQualityRating",
    "EarningsQualityWeights",
    "clip_score",
    "earnings_rating_from_score",
    "validate_weights",
    "weighted_mean",
]


class EarningsQualityDimension(str, Enum):
    """Canonical Earnings Quality & Predictability dimensions."""

    EARNINGS_CONSISTENCY = "earnings_consistency"
    EARNINGS_QUALITY = "earnings_quality"
    MARGIN_STABILITY = "margin_stability"
    EARNINGS_PREDICTABILITY = "earnings_predictability"
    ACCOUNTING_QUALITY = "accounting_quality"
    LONG_TERM_SUSTAINABILITY = "long_term_sustainability"


class EarningsQualityRating(str, Enum):
    """Ordinal overall earnings quality rating."""

    VERY_POOR = "very_poor"
    POOR = "poor"
    AVERAGE = "average"
    GOOD = "good"
    EXCELLENT = "excellent"


@dataclass(frozen=True, slots=True)
class EarningsQualityWeights:
    """Normalized weights for overall earnings quality score."""

    earnings_consistency: float = 0.18
    earnings_quality: float = 0.20
    margin_stability: float = 0.15
    earnings_predictability: float = 0.17
    accounting_quality: float = 0.15
    long_term_sustainability: float = 0.15

    def as_dict(self) -> dict[str, float]:
        return {
            EarningsQualityDimension.EARNINGS_CONSISTENCY.value: (
                self.earnings_consistency
            ),
            EarningsQualityDimension.EARNINGS_QUALITY.value: self.earnings_quality,
            EarningsQualityDimension.MARGIN_STABILITY.value: self.margin_stability,
            EarningsQualityDimension.EARNINGS_PREDICTABILITY.value: (
                self.earnings_predictability
            ),
            EarningsQualityDimension.ACCOUNTING_QUALITY.value: self.accounting_quality,
            EarningsQualityDimension.LONG_TERM_SUSTAINABILITY.value: (
                self.long_term_sustainability
            ),
        }

    def weight_for(self, dimension: EarningsQualityDimension) -> float:
        return self.as_dict()[dimension.value]

    def to_dict(self) -> dict[str, Any]:
        return self.as_dict()


DEFAULT_EARNINGS_WEIGHTS = EarningsQualityWeights()


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


def earnings_rating_from_score(score: float | None) -> EarningsQualityRating:
    if score is None:
        return EarningsQualityRating.VERY_POOR
    if score >= 85.0:
        return EarningsQualityRating.EXCELLENT
    if score >= 70.0:
        return EarningsQualityRating.GOOD
    if score >= 55.0:
        return EarningsQualityRating.AVERAGE
    if score >= 40.0:
        return EarningsQualityRating.POOR
    return EarningsQualityRating.VERY_POOR


def validate_weights(
    weights: EarningsQualityWeights | Mapping[str, float] | None,
) -> EarningsQualityWeights:
    if weights is None:
        return DEFAULT_EARNINGS_WEIGHTS
    if isinstance(weights, EarningsQualityWeights):
        payload = weights.as_dict()
    else:
        payload = {str(k): float(v) for k, v in weights.items()}
    required = {d.value for d in EarningsQualityDimension}
    missing = required - set(payload)
    if missing:
        raise EarningsQualityValidationError(
            f"Missing earnings quality weight keys: {sorted(missing)}"
        )
    values = [float(payload[k]) for k in sorted(required)]
    if any(not (v == v) or v < 0 for v in values):
        raise EarningsQualityValidationError(
            "Earnings quality weights must be finite and >= 0"
        )
    total = sum(values)
    if abs(total - 1.0) > 1e-6:
        raise EarningsQualityValidationError(
            f"Earnings quality weights must sum to 1.0 (got {total})"
        )
    return EarningsQualityWeights(
        earnings_consistency=float(
            payload[EarningsQualityDimension.EARNINGS_CONSISTENCY.value]
        ),
        earnings_quality=float(payload[EarningsQualityDimension.EARNINGS_QUALITY.value]),
        margin_stability=float(
            payload[EarningsQualityDimension.MARGIN_STABILITY.value]
        ),
        earnings_predictability=float(
            payload[EarningsQualityDimension.EARNINGS_PREDICTABILITY.value]
        ),
        accounting_quality=float(
            payload[EarningsQualityDimension.ACCOUNTING_QUALITY.value]
        ),
        long_term_sustainability=float(
            payload[EarningsQualityDimension.LONG_TERM_SUSTAINABILITY.value]
        ),
    )
