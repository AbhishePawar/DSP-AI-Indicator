"""Scoring primitives and rating framework for Management Quality."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping, Sequence

from management_quality.exceptions import ManagementQualityValidationError

__all__ = [
    "DEFAULT_MANAGEMENT_WEIGHTS",
    "ManagementDimension",
    "ManagementRating",
    "ManagementWeights",
    "clip_score",
    "management_rating_from_score",
    "validate_weights",
    "weighted_mean",
]


class ManagementDimension(str, Enum):
    """Canonical Management Quality dimensions (Buffett/Munger-aligned)."""

    CAPITAL_ALLOCATION = "capital_allocation"
    SHAREHOLDER_ORIENTATION = "shareholder_orientation"
    GOVERNANCE = "governance"
    FINANCIAL_DISCIPLINE = "financial_discipline"
    EXECUTION_QUALITY = "execution_quality"
    INTEGRITY_TRANSPARENCY = "integrity_transparency"


class ManagementRating(str, Enum):
    """Ordinal overall management quality rating."""

    POOR = "poor"
    BELOW_AVERAGE = "below_average"
    AVERAGE = "average"
    GOOD = "good"
    EXCELLENT = "excellent"


@dataclass(frozen=True, slots=True)
class ManagementWeights:
    """Normalized weights for overall management score composition."""

    capital_allocation: float = 0.22
    shareholder_orientation: float = 0.18
    governance: float = 0.15
    financial_discipline: float = 0.18
    execution_quality: float = 0.15
    integrity_transparency: float = 0.12

    def as_dict(self) -> dict[str, float]:
        return {
            ManagementDimension.CAPITAL_ALLOCATION.value: self.capital_allocation,
            ManagementDimension.SHAREHOLDER_ORIENTATION.value: (
                self.shareholder_orientation
            ),
            ManagementDimension.GOVERNANCE.value: self.governance,
            ManagementDimension.FINANCIAL_DISCIPLINE.value: self.financial_discipline,
            ManagementDimension.EXECUTION_QUALITY.value: self.execution_quality,
            ManagementDimension.INTEGRITY_TRANSPARENCY.value: (
                self.integrity_transparency
            ),
        }

    def weight_for(self, dimension: ManagementDimension) -> float:
        return self.as_dict()[dimension.value]

    def to_dict(self) -> dict[str, Any]:
        return self.as_dict()


DEFAULT_MANAGEMENT_WEIGHTS = ManagementWeights()


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


def management_rating_from_score(score: float | None) -> ManagementRating:
    if score is None:
        return ManagementRating.POOR
    if score >= 85.0:
        return ManagementRating.EXCELLENT
    if score >= 70.0:
        return ManagementRating.GOOD
    if score >= 55.0:
        return ManagementRating.AVERAGE
    if score >= 40.0:
        return ManagementRating.BELOW_AVERAGE
    return ManagementRating.POOR


def validate_weights(
    weights: ManagementWeights | Mapping[str, float] | None,
) -> ManagementWeights:
    if weights is None:
        return DEFAULT_MANAGEMENT_WEIGHTS
    if isinstance(weights, ManagementWeights):
        payload = weights.as_dict()
    else:
        payload = {str(k): float(v) for k, v in weights.items()}
    required = {d.value for d in ManagementDimension}
    missing = required - set(payload)
    if missing:
        raise ManagementQualityValidationError(
            f"Missing management weight keys: {sorted(missing)}"
        )
    values = [float(payload[k]) for k in sorted(required)]
    if any(not (v == v) or v < 0 for v in values):
        raise ManagementQualityValidationError(
            "Management weights must be finite and >= 0"
        )
    total = sum(values)
    if abs(total - 1.0) > 1e-6:
        raise ManagementQualityValidationError(
            f"Management weights must sum to 1.0 (got {total})"
        )
    return ManagementWeights(
        capital_allocation=float(payload[ManagementDimension.CAPITAL_ALLOCATION.value]),
        shareholder_orientation=float(
            payload[ManagementDimension.SHAREHOLDER_ORIENTATION.value]
        ),
        governance=float(payload[ManagementDimension.GOVERNANCE.value]),
        financial_discipline=float(
            payload[ManagementDimension.FINANCIAL_DISCIPLINE.value]
        ),
        execution_quality=float(payload[ManagementDimension.EXECUTION_QUALITY.value]),
        integrity_transparency=float(
            payload[ManagementDimension.INTEGRITY_TRANSPARENCY.value]
        ),
    )
