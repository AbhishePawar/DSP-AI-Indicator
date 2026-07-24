"""Explainability for Capital Allocation Intelligence (F3.3)."""

from __future__ import annotations

from business_quality.explainability import (
    BusinessQualityExplainability,
    build_explainability,
)
from business_quality.scoring import Confidence

__all__ = [
    "CAPITAL_ALLOCATION_DISCLAIMER",
    "BusinessQualityExplainability",
    "build_explainability",
    "ca_explanation",
]

CAPITAL_ALLOCATION_DISCLAIMER = (
    "Capital Allocation Intelligence evaluates management capital deployment "
    "using FinancialAnalysis outputs only. It is not investment advice, a "
    "forecast, or a valuation. Missing cash-flow / ratio evidence reduces "
    "coverage and confidence."
)


def ca_explanation(
    *,
    title: str,
    description: str,
    evidence: tuple[str, ...] | list[str],
    reasoning: str,
    confidence: Confidence,
    limitations: str,
    references: tuple[str, ...] | list[str],
) -> BusinessQualityExplainability:
    """Build a capital-allocation explainability record."""
    return build_explainability(
        title=title,
        description=description,
        evidence=evidence,
        reasoning=reasoning,
        confidence=confidence,
        limitations=limitations,
        references=references,
    )
