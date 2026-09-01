"""TEST-ONLY deterministic CanonicalAIResearchOutput fixture.

Not a provider adapter. Not production AI. Not an HTTP response.
Does not call OpenAI, Gemini, Claude, or DeepSeek.

Origin: AI_OUTPUT_FIXTURE
"""

from __future__ import annotations

from dsp_platform.research_assembly.models import AI_OUTPUT_FIXTURE
from dsp_platform.research_package.models import ResearchPackage
from dsp_platform.research_report import (
    BUFFETT_METHODOLOGY,
    build_public_research_report,
)
from dsp_platform.research_validation import CanonicalAIResearchOutput

__all__ = [
    "FIXTURE_ORIGIN",
    "TEST_ONLY",
    "build_test_only_ai_output_fixture",
]

TEST_ONLY = True
FIXTURE_ORIGIN = AI_OUTPUT_FIXTURE


def build_test_only_ai_output_fixture(
    research_package: ResearchPackage,
    *,
    copy_dsp_numbers: bool = True,
) -> CanonicalAIResearchOutput:
    """Return a deterministic narrative draft. TEST ONLY.

    Optional numeric copies are DSP values already on ResearchPackage.
    This function does not calculate IV, MoS, scores, or recommendations.
    """
    report = build_public_research_report(research_package)
    evidence_ids = tuple(item.id for item in report.evidence)
    kwargs: dict = {
        "executive_summary": (
            "DSP evidence describes business quality and valuation without "
            "replacing canonical calculations."
        ),
        "valuation_narrative": (
            "The DSP intrinsic value and margin of safety are explained from "
            "supplied evidence only."
        ),
        "business_quality_narrative": (
            "Business quality interpretation follows the canonical DSP score."
        ),
        "economic_moat_narrative": (
            "Moat interpretation uses the canonical economic-moat stage."
        ),
        "management_quality_narrative": (
            "Management interpretation uses the canonical management stage."
        ),
        "financial_strength_narrative": (
            "Financial-strength interpretation uses the canonical stage score."
        ),
        "earnings_quality_narrative": (
            "Earnings-quality interpretation uses the canonical stage score."
        ),
        "growth_quality_narrative": (
            "Growth-quality interpretation uses the canonical stage score."
        ),
        "financials_narrative": (
            "Financial metrics are DSP-owned; this text does not invent values."
        ),
        "buffett_narrative": (
            "Buffett analysis remains existing_pipeline_stages. No new formula."
        ),
        "risk_narrative": (
            "Risk explanation uses DSP ordinal levels. No numeric risk score."
        ),
        "recommendation_narrative": (
            "The DSP recommendation is unchanged and is not replaced."
        ),
        "evidence_ids": evidence_ids[:4] if len(evidence_ids) >= 4 else evidence_ids,
        "buffett_methodology": BUFFETT_METHODOLOGY,
    }
    if copy_dsp_numbers:
        if report.valuation.current_price.value is not None:
            kwargs["current_price"] = report.valuation.current_price.value
        if report.valuation.intrinsic_value_per_share.value is not None:
            kwargs["intrinsic_value"] = (
                report.valuation.intrinsic_value_per_share.value
            )
        if report.valuation.margin_of_safety.value is not None:
            kwargs["margin_of_safety"] = report.valuation.margin_of_safety.value
        if report.valuation.valuation_range.low is not None:
            kwargs["valuation_range_low"] = report.valuation.valuation_range.low
        if report.valuation.valuation_range.mid is not None:
            kwargs["valuation_range_mid"] = report.valuation.valuation_range.mid
        if report.valuation.valuation_range.high is not None:
            kwargs["valuation_range_high"] = report.valuation.valuation_range.high
        if report.business_quality.score_100 is not None:
            kwargs["quality_scores"] = {
                "business_quality": report.business_quality.score_100,
            }
        if report.buffett_analysis.buffett_overall_score_100 is not None:
            kwargs["buffett_overall_score_100"] = (
                report.buffett_analysis.buffett_overall_score_100
            )
        if report.recommendation.action is not None:
            kwargs["recommendation_action"] = report.recommendation.action
        if report.recommendation.recommendation_score_100 is not None:
            kwargs["recommendation_score_100"] = (
                report.recommendation.recommendation_score_100
            )
        metrics = {
            row.name: row.value
            for row in report.financials.metrics
            if row.value is not None
        }
        if metrics:
            kwargs["financial_metrics"] = metrics
    return CanonicalAIResearchOutput(**kwargs)
