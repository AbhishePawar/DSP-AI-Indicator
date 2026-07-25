"""Explainability for Competitive Position Indicators (F3.5)."""

from __future__ import annotations

from business_quality.explainability import (
    BusinessQualityExplainability,
    build_explainability,
)
from business_quality.scoring import Confidence

__all__ = [
    "COMPETITIVE_POSITION_DISCLAIMER",
    "BusinessQualityExplainability",
    "build_explainability",
    "cp_explanation",
]

COMPETITIVE_POSITION_DISCLAIMER = (
    "Competitive Position Indicators evaluate structural competitive "
    "characteristics inferred from FinancialAnalysis outputs only. They do "
    "not use peer comparisons, industry datasets, market share, forecasts, "
    "or valuations. Missing evidence reduces coverage and confidence."
)


def cp_explanation(
    *,
    title: str,
    description: str,
    evidence: tuple[str, ...] | list[str],
    reasoning: str,
    confidence: Confidence,
    limitations: str,
    references: tuple[str, ...] | list[str],
) -> BusinessQualityExplainability:
    """Build a competitive-position explainability record."""
    return build_explainability(
        title=title,
        description=description,
        evidence=evidence,
        reasoning=reasoning,
        confidence=confidence,
        limitations=limitations,
        references=references,
    )
