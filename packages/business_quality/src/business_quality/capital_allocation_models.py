"""Immutable models for Capital Allocation Intelligence (F3.3)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from business_quality.explainability import BusinessQualityExplainability
from business_quality.metadata import BusinessQualityMetadata
from business_quality.scoring import Assessment, Confidence, Rating, Score
from business_quality.validation import BusinessQualityValidation

__all__ = [
    "CapitalAllocationFlag",
    "CapitalAllocationAnalysis",
]


class CapitalAllocationFlag(str, Enum):
    """Standardized capital-allocation research flags."""

    EXCELLENT_CAPITAL_ALLOCATION = "excellent_capital_allocation"
    DISCIPLINED_REINVESTMENT = "disciplined_reinvestment"
    SHAREHOLDER_FRIENDLY = "shareholder_friendly"
    HEALTHY_CASH_DEPLOYMENT = "healthy_cash_deployment"
    EXCESSIVE_CAPITAL_SPENDING = "excessive_capital_spending"
    WEAK_CAPITAL_ALLOCATION = "weak_capital_allocation"
    DEBT_DEPENDENT = "debt_dependent"
    DIVIDEND_AT_RISK = "dividend_at_risk"
    INCONSISTENT_ALLOCATION = "inconsistent_allocation"


@dataclass(frozen=True, slots=True)
class CapitalAllocationAnalysis:
    """Capital Allocation Intelligence result from FinancialAnalysis."""

    metadata: BusinessQualityMetadata
    validation: BusinessQualityValidation
    assessments: tuple[Assessment, ...]
    overall_score: Score | None
    overall_rating: Rating
    confidence: Confidence
    quality_flags: tuple[CapitalAllocationFlag, ...]
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
