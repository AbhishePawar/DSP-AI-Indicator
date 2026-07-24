"""Immutable models for Earnings Quality Intelligence (F3.2)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from business_quality.explainability import BusinessQualityExplainability
from business_quality.metadata import BusinessQualityMetadata
from business_quality.scoring import Assessment, Confidence, Rating, Score
from business_quality.validation import BusinessQualityValidation

__all__ = [
    "EarningsQualityFlag",
    "EarningsQualityAnalysis",
]


class EarningsQualityFlag(str, Enum):
    """Standardized earnings-quality research flags."""

    HIGH_EARNINGS_QUALITY = "high_earnings_quality"
    CASH_SUPPORTED_EARNINGS = "cash_supported_earnings"
    RECURRING_EARNINGS = "recurring_earnings"
    STABLE_MARGINS = "stable_margins"
    AGGRESSIVE_ACCOUNTING_RISK = "aggressive_accounting_risk"
    WEAK_CASH_SUPPORT = "weak_cash_support"
    VOLATILE_EARNINGS = "volatile_earnings"
    HIGH_ACCRUAL_RISK = "high_accrual_risk"


@dataclass(frozen=True, slots=True)
class EarningsQualityAnalysis:
    """Earnings Quality Intelligence result composed from FinancialAnalysis."""

    metadata: BusinessQualityMetadata
    validation: BusinessQualityValidation
    assessments: tuple[Assessment, ...]
    overall_score: Score | None
    overall_rating: Rating
    confidence: Confidence
    quality_flags: tuple[EarningsQualityFlag, ...]
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
