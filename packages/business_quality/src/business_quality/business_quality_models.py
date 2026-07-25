"""Immutable models for the canonical Business Quality Engine (F3.6)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from business_quality.business_characteristics_models import (
    BusinessCharacteristicsAnalysis,
)
from business_quality.capital_allocation_models import CapitalAllocationAnalysis
from business_quality.competitive_position_models import CompetitivePositionAnalysis
from business_quality.earnings_quality_models import EarningsQualityAnalysis
from business_quality.explainability import BusinessQualityExplainability
from business_quality.metadata import BusinessQualityMetadata
from business_quality.scoring import Assessment, Confidence, Rating, Score
from business_quality.validation import BusinessQualityValidation

__all__ = [
    "AggregatedFlag",
    "AggregatedFlags",
    "BusinessQualityAnalysis",
    "BusinessQualityFlag",
    "BusinessQualityScore",
    "BusinessQualitySummary",
    "BusinessQualityWeights",
    "DEFAULT_BUSINESS_QUALITY_WEIGHTS",
    "FlagSeverity",
    "OverallAssessment",
    "OverallRating",
]


class OverallRating(str, Enum):
    """Standardized overall business-quality ratings (F3.6)."""

    EXCELLENT = "excellent"
    STRONG = "strong"
    GOOD = "good"
    AVERAGE = "average"
    WEAK = "weak"
    POOR = "poor"


class FlagSeverity(str, Enum):
    """Severity band for aggregated module flags."""

    CRITICAL = "critical"
    WARNING = "warning"
    POSITIVE = "positive"


class BusinessQualityFlag(str, Enum):
    """Standardized business-quality classification flags."""

    EXCELLENT = "excellent"
    STRONG = "strong"
    GOOD = "good"
    AVERAGE = "average"
    WEAK = "weak"
    POOR = "poor"
    UNKNOWN = "unknown"
    INSUFFICIENT_DATA = "insufficient_data"


@dataclass(frozen=True, slots=True)
class BusinessQualityWeights:
    """Configurable module weights for overall score composition."""

    earnings_quality: float = 0.30
    capital_allocation: float = 0.30
    business_characteristics: float = 0.20
    competitive_position: float = 0.20

    def as_dict(self) -> dict[str, float]:
        return {
            "earnings_quality": self.earnings_quality,
            "capital_allocation": self.capital_allocation,
            "business_characteristics": self.business_characteristics,
            "competitive_position": self.competitive_position,
        }

    def to_dict(self) -> dict[str, float]:
        return self.as_dict()


DEFAULT_BUSINESS_QUALITY_WEIGHTS = BusinessQualityWeights()


@dataclass(frozen=True, slots=True)
class AggregatedFlag:
    """One deduplicated flag contributed by a module."""

    name: str
    source: str
    severity: FlagSeverity
    value: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "source": self.source,
            "severity": self.severity.value,
            "value": self.value,
        }


@dataclass(frozen=True, slots=True)
class AggregatedFlags:
    """Critical / positive / warning flag buckets, severity-sorted."""

    critical: tuple[AggregatedFlag, ...] = ()
    warning: tuple[AggregatedFlag, ...] = ()
    positive: tuple[AggregatedFlag, ...] = ()
    all_sorted: tuple[AggregatedFlag, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "critical": [f.to_dict() for f in self.critical],
            "warning": [f.to_dict() for f in self.warning],
            "positive": [f.to_dict() for f in self.positive],
            "all_sorted": [f.to_dict() for f in self.all_sorted],
        }


@dataclass(frozen=True, slots=True)
class OverallAssessment:
    """Narrative overall assessment derived from module composition."""

    headline: str = ""
    strengths: tuple[str, ...] = ()
    weaknesses: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()
    evidence_summary: tuple[str, ...] = ()
    module_references: tuple[str, ...] = ()
    reasoning: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "headline": self.headline,
            "strengths": list(self.strengths),
            "weaknesses": list(self.weaknesses),
            "limitations": list(self.limitations),
            "evidence_summary": list(self.evidence_summary),
            "module_references": list(self.module_references),
            "reasoning": self.reasoning,
        }


@dataclass(frozen=True, slots=True)
class BusinessQualityScore:
    """Top-level score envelope (framework + F3.6 composition)."""

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
    """Narrative summary for display / backward-compatible consumers."""

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
    """Canonical Business Quality analysis — F3.6 orchestration artifact.

    Nested module analyses are optional so the F3.1 shell remains valid.
    Legacy fields (``score``, ``summary``, ``quality_flags``, ``validation``)
    are preserved for backward compatibility.
    """

    metadata: BusinessQualityMetadata
    validation: BusinessQualityValidation
    score: BusinessQualityScore | None
    summary: BusinessQualitySummary
    quality_flags: tuple[BusinessQualityFlag, ...]
    explainability: tuple[BusinessQualityExplainability, ...]
    research_disclaimer: str
    overall_score: Score | None = None
    overall_rating: OverallRating | None = None
    overall_confidence: Confidence = Confidence.INSUFFICIENT
    overall_assessment: OverallAssessment | None = None
    overall_flags: AggregatedFlags | None = None
    earnings_quality: EarningsQualityAnalysis | None = None
    capital_allocation: CapitalAllocationAnalysis | None = None
    business_characteristics: BusinessCharacteristicsAnalysis | None = None
    competitive_position: CompetitivePositionAnalysis | None = None
    weights_used: BusinessQualityWeights | None = None

    @property
    def validation_summary(self) -> BusinessQualityValidation:
        """Alias for ``validation`` (F3.6 naming)."""
        return self.validation

    def to_dict(self) -> dict[str, Any]:
        return {
            "metadata": self.metadata.to_dict(),
            "validation": self.validation.to_dict(),
            "validation_summary": self.validation.to_dict(),
            "score": self.score.to_dict() if self.score is not None else None,
            "summary": self.summary.to_dict(),
            "quality_flags": [f.value for f in self.quality_flags],
            "explainability": [e.to_dict() for e in self.explainability],
            "research_disclaimer": self.research_disclaimer,
            "overall_score": (
                self.overall_score.to_dict() if self.overall_score is not None else None
            ),
            "overall_rating": (
                self.overall_rating.value if self.overall_rating is not None else None
            ),
            "overall_confidence": self.overall_confidence.value,
            "overall_assessment": (
                self.overall_assessment.to_dict()
                if self.overall_assessment is not None
                else None
            ),
            "overall_flags": (
                self.overall_flags.to_dict() if self.overall_flags is not None else None
            ),
            "earnings_quality": (
                self.earnings_quality.to_dict()
                if self.earnings_quality is not None
                else None
            ),
            "capital_allocation": (
                self.capital_allocation.to_dict()
                if self.capital_allocation is not None
                else None
            ),
            "business_characteristics": (
                self.business_characteristics.to_dict()
                if self.business_characteristics is not None
                else None
            ),
            "competitive_position": (
                self.competitive_position.to_dict()
                if self.competitive_position is not None
                else None
            ),
            "weights_used": (
                self.weights_used.to_dict() if self.weights_used is not None else None
            ),
        }
