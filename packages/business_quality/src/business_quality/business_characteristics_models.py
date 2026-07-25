"""Immutable models for Business Characteristics Intelligence (F3.4)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from business_quality.explainability import BusinessQualityExplainability
from business_quality.metadata import BusinessQualityMetadata
from business_quality.scoring import Assessment, Confidence, Rating, Score
from business_quality.validation import BusinessQualityValidation

__all__ = [
    "BusinessCharacteristicsFlag",
    "BusinessCharacteristicsAnalysis",
]


class BusinessCharacteristicsFlag(str, Enum):
    """Standardized business-characteristics research flags."""

    ASSET_LIGHT = "asset_light"
    CAPITAL_INTENSIVE = "capital_intensive"
    HIGHLY_SCALABLE = "highly_scalable"
    OPERATIONALLY_STABLE = "operationally_stable"
    RESILIENT_BUSINESS = "resilient_business"
    CYCLICAL_BUSINESS = "cyclical_business"
    STRONG_CASH_GENERATOR = "strong_cash_generator"
    MARGIN_DURABLE = "margin_durable"
    HIGH_OPERATING_LEVERAGE = "high_operating_leverage"


@dataclass(frozen=True, slots=True)
class BusinessCharacteristicsAnalysis:
    """Business Characteristics Intelligence result from FinancialAnalysis."""

    metadata: BusinessQualityMetadata
    validation: BusinessQualityValidation
    assessments: tuple[Assessment, ...]
    overall_score: Score | None
    overall_rating: Rating
    confidence: Confidence
    quality_flags: tuple[BusinessCharacteristicsFlag, ...]
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
