"""Explainability for Earnings Quality Intelligence (F3.2)."""

from __future__ import annotations

from business_quality.explainability import (
    RESEARCH_DISCLAIMER as FRAMEWORK_DISCLAIMER,
    BusinessQualityExplainability,
    build_explainability,
)
from business_quality.scoring import Confidence

__all__ = [
    "EARNINGS_QUALITY_DISCLAIMER",
    "BusinessQualityExplainability",
    "build_explainability",
    "eq_explanation",
]

EARNINGS_QUALITY_DISCLAIMER = (
    "Earnings Quality Intelligence evaluates the durability and cash support "
    "of reported earnings using FinancialAnalysis outputs only. It is not "
    "investment advice, a forecast, or a valuation. Missing financial "
    "evidence reduces coverage and confidence."
)


def eq_explanation(
    *,
    title: str,
    description: str,
    evidence: tuple[str, ...] | list[str],
    reasoning: str,
    confidence: Confidence,
    limitations: str,
    references: tuple[str, ...] | list[str],
) -> BusinessQualityExplainability:
    """Build an earnings-quality explainability record."""
    return build_explainability(
        title=title,
        description=description,
        evidence=evidence,
        reasoning=reasoning,
        confidence=confidence,
        limitations=limitations,
        references=references,
    )


# Re-export framework disclaimer for shell compatibility
__framework_disclaimer__ = FRAMEWORK_DISCLAIMER
