"""Explainability for the canonical Business Quality Engine (F3.6)."""

from __future__ import annotations

from business_quality.explainability import (
    RESEARCH_DISCLAIMER,
    BusinessQualityExplainability,
    build_explainability,
)
from business_quality.scoring import Confidence

__all__ = [
    "BUSINESS_QUALITY_ENGINE_DISCLAIMER",
    "BusinessQualityExplainability",
    "RESEARCH_DISCLAIMER",
    "build_explainability",
    "bq_explanation",
    "merge_module_explainability",
]

BUSINESS_QUALITY_ENGINE_DISCLAIMER = (
    "Business Quality Engine composes Earnings Quality, Capital Allocation, "
    "Business Characteristics, and Competitive Position from FinancialAnalysis "
    "outputs only. It performs no new financial calculations, valuation, "
    "forecasting, peer comparison, or provider integrations."
)


def bq_explanation(
    *,
    title: str,
    description: str,
    evidence: tuple[str, ...] | list[str],
    reasoning: str,
    confidence: Confidence,
    limitations: str,
    references: tuple[str, ...] | list[str],
) -> BusinessQualityExplainability:
    """Build a top-level Business Quality explainability record."""
    return build_explainability(
        title=title,
        description=description,
        evidence=evidence,
        reasoning=reasoning,
        confidence=confidence,
        limitations=limitations,
        references=references,
    )


def merge_module_explainability(
    *module_explainability: tuple[BusinessQualityExplainability, ...],
    overall: BusinessQualityExplainability | None = None,
) -> tuple[BusinessQualityExplainability, ...]:
    """Concatenate module explainability records; overall first when provided."""
    merged: list[BusinessQualityExplainability] = []
    if overall is not None:
        merged.append(overall)
    for block in module_explainability:
        merged.extend(block)
    return tuple(merged)
