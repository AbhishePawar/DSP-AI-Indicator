"""Explainability for Business Quality report aggregation (F3.7)."""

from __future__ import annotations

from business_quality.business_quality_models import BusinessQualityAnalysis
from business_quality.business_quality_report_models import (
    ConfidenceSummary,
    ModuleBreakdownEntry,
)
from business_quality.explainability import (
    BusinessQualityExplainability,
    build_explainability,
)
from business_quality.scoring import Confidence

__all__ = [
    "BUSINESS_QUALITY_AGGREGATOR_DISCLAIMER",
    "build_report_explainability",
    "report_explanation",
]

BUSINESS_QUALITY_AGGREGATOR_DISCLAIMER = (
    "Business Quality Aggregator packages an existing BusinessQualityAnalysis "
    "into a consumer-facing report. It does not compute new financial metrics, "
    "valuations, forecasts, or peer comparisons."
)


def report_explanation(
    *,
    title: str,
    description: str,
    evidence: tuple[str, ...] | list[str],
    reasoning: str,
    confidence: Confidence,
    limitations: str,
    references: tuple[str, ...] | list[str],
) -> BusinessQualityExplainability:
    """Build one report-level explainability record."""
    return build_explainability(
        title=title,
        description=description,
        evidence=evidence,
        reasoning=reasoning,
        confidence=confidence,
        limitations=limitations,
        references=references,
    )


def build_report_explainability(
    analysis: BusinessQualityAnalysis,
    *,
    confidence_summary: ConfidenceSummary,
    module_breakdown: tuple[ModuleBreakdownEntry, ...],
    evidence_summary: tuple[str, ...],
    limitations: tuple[str, ...],
) -> tuple[BusinessQualityExplainability, ...]:
    """Compose report explainability from analysis + aggregated summaries."""
    present = [m for m in module_breakdown if m.present]
    contribution = "; ".join(
        f"{m.label} rating={m.rating} score={m.score} weight={m.weight}"
        for m in present
    ) or "No module outputs present."

    overall = report_explanation(
        title="Business Quality Report Summary",
        description="Aggregated reporting view of BusinessQualityAnalysis.",
        evidence=evidence_summary[:12],
        reasoning=(
            f"Executive packaging of composed Business Quality modules. "
            f"{confidence_summary.explanation} Module contribution: {contribution}"
        ),
        confidence=confidence_summary.overall,
        limitations="; ".join(limitations) if limitations else BUSINESS_QUALITY_AGGREGATOR_DISCLAIMER,
        references=(
            "BusinessQualityAnalysis",
            "BusinessQualityAnalysis.overall_assessment",
            "BusinessQualityAnalysis.overall_flags",
            "BusinessQualityAnalysis.earnings_quality",
            "BusinessQualityAnalysis.capital_allocation",
            "BusinessQualityAnalysis.business_characteristics",
            "BusinessQualityAnalysis.competitive_position",
        ),
    )

    confidence_exp = report_explanation(
        title="Confidence Explanation",
        description="How overall report confidence was packaged from modules.",
        evidence=tuple(f"{m}={c}" for m, c in confidence_summary.module_confidences),
        reasoning=confidence_summary.explanation,
        confidence=confidence_summary.overall,
        limitations="Confidence is inherited from module analyses; not recalculated.",
        references=("BusinessQualityAnalysis.overall_confidence",),
    )

    module_exp = report_explanation(
        title="Module Contribution Summary",
        description="Deterministic module breakdown for report consumers.",
        evidence=tuple(
            f"{m.name}:present={m.present}:rating={m.rating}:score={m.score}"
            for m in module_breakdown
        ),
        reasoning=contribution,
        confidence=confidence_summary.overall,
        limitations="Weights shown are those used by the Business Quality Engine.",
        references=tuple(m.name for m in present) or ("BusinessQualityAnalysis",),
    )

    # Preserve a truncated view of source explainability (packaging only)
    source = tuple(analysis.explainability[:4])
    return (overall, confidence_exp, module_exp) + source
