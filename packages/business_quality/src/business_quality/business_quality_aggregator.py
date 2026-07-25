"""Business Quality Aggregator — F3.7 reporting / packaging layer.

Accepts ONLY BusinessQualityAnalysis. Produces immutable report models.
No new analytics, ratios, valuation, or forecasting.
"""

from __future__ import annotations

from typing import Any

from business_quality.business_quality_report_explainability import (
    BUSINESS_QUALITY_AGGREGATOR_DISCLAIMER,
    build_report_explainability,
)
from business_quality.business_quality_report_models import BusinessQualityReport
from business_quality.business_quality_report_validation import (
    validate_business_quality_analysis,
    validate_report_object,
)
from business_quality.business_quality_summary import (
    build_confidence_summary,
    build_executive_summary,
    build_module_breakdown,
    build_recommended_interpretation,
    extract_evidence,
    extract_limitations,
    extract_signals,
    extract_strengths,
    extract_weaknesses,
    source_module_names,
)
from business_quality.metadata import (
    BUSINESS_QUALITY_VERSION,
    FRAMEWORK_VERSION,
    BusinessQualityMetadata,
)
from business_quality.validation import merge_validation_results

__all__ = [
    "BUSINESS_QUALITY_AGGREGATOR_VERSION",
    "BusinessQualityAggregator",
]

BUSINESS_QUALITY_AGGREGATOR_VERSION = "0.7.0-business-quality-aggregator"


class BusinessQualityAggregator:
    """Package BusinessQualityAnalysis into a consumer-facing report."""

    def __init__(self) -> None:
        self._version = BUSINESS_QUALITY_AGGREGATOR_VERSION

    @property
    def version(self) -> str:
        return self._version

    def aggregate(self, analysis: Any) -> BusinessQualityReport:
        """Build a deterministic ``BusinessQualityReport`` from analysis."""
        input_validation = validate_business_quality_analysis(analysis)

        strengths = extract_strengths(analysis)
        weaknesses = extract_weaknesses(analysis)
        key_risks, positive_signals, warning_signals = extract_signals(analysis)
        evidence_summary = extract_evidence(analysis)
        limitations = extract_limitations(analysis)
        module_breakdown = build_module_breakdown(analysis)
        confidence_summary = build_confidence_summary(analysis)
        executive_summary = build_executive_summary(analysis)
        recommended = build_recommended_interpretation(analysis)
        explainability = build_report_explainability(
            analysis,
            confidence_summary=confidence_summary,
            module_breakdown=module_breakdown,
            evidence_summary=evidence_summary,
            limitations=limitations,
        )

        meta = analysis.metadata
        report_metadata = BusinessQualityMetadata(
            engine_version=BUSINESS_QUALITY_VERSION,
            framework_version=getattr(meta, "framework_version", FRAMEWORK_VERSION)
            or FRAMEWORK_VERSION,
            company=str(getattr(meta, "company", "") or ""),
            ticker=str(getattr(meta, "ticker", "") or ""),
            modules_composed=tuple(
                dict.fromkeys(
                    list(getattr(meta, "modules_composed", ()) or ())
                    + ["business_quality_aggregator"]
                )
            ),
            schema_version=str(getattr(meta, "schema_version", "1") or "1"),
        )

        report = BusinessQualityReport(
            metadata=report_metadata,
            validation=input_validation,
            executive_summary=executive_summary,
            business_quality_rating=analysis.overall_rating,
            overall_score=analysis.overall_score,
            strengths=strengths,
            weaknesses=weaknesses,
            key_risks=key_risks,
            positive_signals=positive_signals,
            warning_signals=warning_signals,
            confidence_summary=confidence_summary,
            evidence_summary=evidence_summary,
            module_breakdown=module_breakdown,
            recommended_interpretation=recommended,
            limitations=limitations,
            explainability=explainability,
            research_disclaimer=(
                f"{BUSINESS_QUALITY_AGGREGATOR_DISCLAIMER} "
                f"{getattr(analysis, 'research_disclaimer', '')}"
            ).strip(),
            source_modules=source_module_names(analysis),
        )
        report_validation = validate_report_object(report)
        # Re-seal with merged validation (input + report checks)
        return BusinessQualityReport(
            metadata=report.metadata,
            validation=merge_validation_results([input_validation, report_validation]),
            executive_summary=report.executive_summary,
            business_quality_rating=report.business_quality_rating,
            overall_score=report.overall_score,
            strengths=report.strengths,
            weaknesses=report.weaknesses,
            key_risks=report.key_risks,
            positive_signals=report.positive_signals,
            warning_signals=report.warning_signals,
            confidence_summary=report.confidence_summary,
            evidence_summary=report.evidence_summary,
            module_breakdown=report.module_breakdown,
            recommended_interpretation=report.recommended_interpretation,
            limitations=report.limitations,
            explainability=report.explainability,
            research_disclaimer=report.research_disclaimer,
            source_modules=report.source_modules,
        )

    def summarize(self, analysis: Any) -> BusinessQualityReport:
        """Alias for ``aggregate`` — primary reporting entry."""
        return self.aggregate(analysis)
