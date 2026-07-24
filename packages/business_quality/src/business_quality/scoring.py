"""Generic scoring primitives for Business Quality (no domain logic)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping, Sequence

__all__ = [
    "Confidence",
    "EvidenceLevel",
    "Rating",
    "RiskLevel",
    "Score",
    "WeightedScore",
    "Assessment",
]


class Confidence(str, Enum):
    """Generic confidence band (framework primitive)."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INSUFFICIENT = "insufficient"


class EvidenceLevel(str, Enum):
    """Generic evidence strength (framework primitive)."""

    STRONG = "strong"
    ADEQUATE = "adequate"
    LIMITED = "limited"
    NONE = "none"
    UNKNOWN = "unknown"


class Rating(str, Enum):
    """Generic ordinal rating (framework primitive)."""

    EXCELLENT = "excellent"
    STRONG = "strong"
    AVERAGE = "average"
    WEAK = "weak"
    POOR = "poor"
    UNKNOWN = "unknown"
    INSUFFICIENT_DATA = "insufficient_data"


class RiskLevel(str, Enum):
    """Generic risk band (framework primitive)."""

    LOW = "low"
    MODERATE = "moderate"
    ELEVATED = "elevated"
    HIGH = "high"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class Score:
    """Numeric score container — no interpretation logic."""

    value: float | None
    scale_min: float = 0.0
    scale_max: float = 100.0
    unit: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "value": self.value,
            "scale_min": self.scale_min,
            "scale_max": self.scale_max,
            "unit": self.unit,
        }


@dataclass(frozen=True, slots=True)
class WeightedScore:
    """Weighted contribution toward a composite — composition only."""

    name: str
    score: Score
    weight: float
    contribution: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "score": self.score.to_dict(),
            "weight": self.weight,
            "contribution": self.contribution,
        }


@dataclass(frozen=True, slots=True)
class Assessment:
    """Generic assessment envelope for future domain modules."""

    name: str
    rating: Rating = Rating.UNKNOWN
    score: Score | None = None
    confidence: Confidence = Confidence.INSUFFICIENT
    evidence_level: EvidenceLevel = EvidenceLevel.UNKNOWN
    risk_level: RiskLevel = RiskLevel.UNKNOWN
    notes: str = ""
    components: tuple[WeightedScore, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "rating": self.rating.value,
            "score": self.score.to_dict() if self.score is not None else None,
            "confidence": self.confidence.value,
            "evidence_level": self.evidence_level.value,
            "risk_level": self.risk_level.value,
            "notes": self.notes,
            "components": [c.to_dict() for c in self.components],
        }


def clip_score(value: float, *, lo: float = 0.0, hi: float = 100.0) -> float:
    """Clamp a numeric value into ``[lo, hi]`` (pure helper, no domain meaning)."""
    return max(lo, min(hi, value))


def weighted_mean(
    items: Sequence[tuple[float, float]],
) -> float | None:
    """Return weighted mean of ``(value, weight)`` pairs; ``None`` if empty/zero weight."""
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


def score_from_mapping(
    payload: Mapping[str, Any],
    *,
    default_scale: tuple[float, float] = (0.0, 100.0),
) -> Score:
    """Build a ``Score`` from a plain mapping (serialization helper)."""
    lo, hi = default_scale
    return Score(
        value=payload.get("value"),
        scale_min=float(payload.get("scale_min", lo)),
        scale_max=float(payload.get("scale_max", hi)),
        unit=str(payload.get("unit", "")),
    )
