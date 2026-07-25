"""Explainability for Business Characteristics Intelligence (F3.4)."""

from __future__ import annotations

from business_quality.explainability import (
    BusinessQualityExplainability,
    build_explainability,
)
from business_quality.scoring import Confidence

__all__ = [
    "BUSINESS_CHARACTERISTICS_DISCLAIMER",
    "BusinessQualityExplainability",
    "build_explainability",
    "bc_explanation",
]

BUSINESS_CHARACTERISTICS_DISCLAIMER = (
    "Business Characteristics Intelligence evaluates structural operating "
    "characteristics using FinancialAnalysis outputs only. It is not investment "
    "advice, a forecast, or a valuation. Missing statement evidence reduces "
    "coverage and confidence."
)


def bc_explanation(
    *,
    title: str,
    description: str,
    evidence: tuple[str, ...] | list[str],
    reasoning: str,
    confidence: Confidence,
    limitations: str,
    references: tuple[str, ...] | list[str],
) -> BusinessQualityExplainability:
    """Build a business-characteristics explainability record."""
    return build_explainability(
        title=title,
        description=description,
        evidence=evidence,
        reasoning=reasoning,
        confidence=confidence,
        limitations=limitations,
        references=references,
    )
