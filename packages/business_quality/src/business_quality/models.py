"""Immutable models for the Business Quality Framework (F3.1)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from business_quality.explainability import BusinessQualityExplainability
from business_quality.metadata import BusinessQualityMetadata
from business_quality.scoring import Assessment, Confidence, Rating, Score
from business_quality.validation import BusinessQualityValidation

__all__ = [
    "BusinessQualityFlag",
    "BusinessQualityScore",
    "BusinessQualitySummary",
    "BusinessQualityAnalysis",
]


class BusinessQualityFlag(str, Enum):
    """Standardized business-quality classification flags (framework)."""

    EXCELLENT = "excellent"
    STRONG = "strong"
    AVERAGE = "average"
    WEAK = "weak"
    POOR = "poor"
    UNKNOWN = "unknown"
    INSUFFICIENT_DATA = "insufficient_data"


@dataclass(frozen=True, slots=True)
class BusinessQualityScore:
    """Top-level score envelope for a future analysis result."""

    overall: Score
    rating: Rating = Rating.UNKNOWN
    confidence: Confidence = Confidence.INSUFFICIENT
    assessments: tuple[Assessment, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "overall": self.overall.to_dict(),
            "rating": self.rating.value,
            "confidence": self.confidence.value,
            "assessments": [a.to_dict() for a in self.assessments],
        }


@dataclass(frozen=True, slots=True)
class BusinessQualitySummary:
    """Narrative summary placeholders for future analysis composition."""

    headline: str = ""
    strengths: tuple[str, ...] = ()
    weaknesses: tuple[str, ...] = ()
    key_observations: tuple[str, ...] = ()
    flag: BusinessQualityFlag = BusinessQualityFlag.UNKNOWN

    def to_dict(self) -> dict[str, Any]:
        return {
            "headline": self.headline,
            "strengths": list(self.strengths),
            "weaknesses": list(self.weaknesses),
            "key_observations": list(self.key_observations),
            "flag": self.flag.value,
        }


@dataclass(frozen=True, slots=True)
class BusinessQualityAnalysis:
    """Canonical Business Quality analysis artifact (framework shell).

    Populated by future F3.x modules — F3.1 provides structure only.
    """

    metadata: BusinessQualityMetadata
    validation: BusinessQualityValidation
    score: BusinessQualityScore | None
    summary: BusinessQualitySummary
    quality_flags: tuple[BusinessQualityFlag, ...]
    explainability: tuple[BusinessQualityExplainability, ...]
    research_disclaimer: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "metadata": self.metadata.to_dict(),
            "validation": self.validation.to_dict(),
            "score": self.score.to_dict() if self.score is not None else None,
            "summary": self.summary.to_dict(),
            "quality_flags": [f.value for f in self.quality_flags],
            "explainability": [e.to_dict() for e in self.explainability],
            "research_disclaimer": self.research_disclaimer,
        }
