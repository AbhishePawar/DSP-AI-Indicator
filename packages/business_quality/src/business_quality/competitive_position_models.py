"""Immutable models for Competitive Position Indicators (F3.5)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from business_quality.explainability import BusinessQualityExplainability
from business_quality.metadata import BusinessQualityMetadata
from business_quality.scoring import Assessment, Confidence, Rating, Score
from business_quality.validation import BusinessQualityValidation

__all__ = [
    "CompetitivePositionFlag",
    "CompetitivePositionAnalysis",
]


class CompetitivePositionFlag(str, Enum):
    """Standardized competitive-position research flags."""

    STRONG_PRICING_POWER = "strong_pricing_power"
    DURABLE_MARGINS = "durable_margins"
    HIGH_CAPITAL_EFFICIENCY = "high_capital_efficiency"
    OPERATIONAL_EXCELLENCE = "operational_excellence"
    STRONG_COMPETITIVE_POSITION = "strong_competitive_position"
    WEAK_COMPETITIVE_POSITION = "weak_competitive_position"
    MARGIN_PRESSURE = "margin_pressure"
    WEAK_CAPITAL_EFFICIENCY = "weak_capital_efficiency"
    DECLINING_PROFITABILITY = "declining_profitability"


@dataclass(frozen=True, slots=True)
class CompetitivePositionAnalysis:
    """Competitive Position Indicators result from FinancialAnalysis."""

    metadata: BusinessQualityMetadata
    validation: BusinessQualityValidation
    assessments: tuple[Assessment, ...]
    overall_score: Score | None
    overall_rating: Rating
    confidence: Confidence
    quality_flags: tuple[CompetitivePositionFlag, ...]
    evidence: tuple[str, ...]
    explainability: tuple[BusinessQualityExplainability, ...]
    research_disclaimer: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "metadata": self.metadata.to_dict(),
            "validation": self.validation.to_dict(),
            "assessments": [a.to_dict() for a in self.assessments],
            "overall_score": (
                self.overall_score.to_dict() if self.overall_score is not None else None
            ),
            "overall_rating": self.overall_rating.value,
            "confidence": self.confidence.value,
            "quality_flags": [f.value for f in self.quality_flags],
            "evidence": list(self.evidence),
            "explainability": [e.to_dict() for e in self.explainability],
            "research_disclaimer": self.research_disclaimer,
        }
