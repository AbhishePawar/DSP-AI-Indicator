"""Map engine-native results onto committee contracts DTOs.

This module is the only place in the pipeline that knows both engine
assessment shapes and committee context DTOs. The Investment Committee
never imports engine packages.
"""

from __future__ import annotations

from contracts import (
    AnalyticalStance,
    EconomicContext,
    FundamentalContext,
    TechnicalContext,
    ValuationConfidence,
    ValuationContext,
)
from dsp import AnalysisResult
from economic import EconomicAssessment
from fundamental import CompanyAnalysis
from valuation import ValuationAssessment

__all__ = [
    "to_economic_context",
    "to_fundamental_context",
    "to_technical_context",
    "to_valuation_context",
]

_STANCE_BY_VALUE: dict[str, AnalyticalStance] = {
    stance.value: stance for stance in AnalyticalStance
}


def to_technical_context(result: AnalysisResult) -> TechnicalContext:
    """Map Indicator Engine output onto :class:`TechnicalContext`."""
    return TechnicalContext(
        instrument=result.instrument,
        signals=result.signals,
        evidence=result.evidence,
    )


def to_fundamental_context(analysis: CompanyAnalysis) -> FundamentalContext:
    """Map Fundamental Engine output onto :class:`FundamentalContext`."""
    return FundamentalContext(
        instrument=analysis.instrument,
        signals=analysis.signals,
        evidence=analysis.evidence,
    )


def to_economic_context(assessment: EconomicAssessment) -> EconomicContext:
    """Map Economic Engine output onto :class:`EconomicContext`."""
    stance = _STANCE_BY_VALUE[assessment.recommendation.value]
    return EconomicContext(
        stance=stance,
        overall_condition=assessment.overall_condition.value,
        country=assessment.country,
        reasoning=assessment.reasoning,
        evidence=assessment.evidence,
    )


def to_valuation_context(assessment: ValuationAssessment) -> ValuationContext:
    """Map Valuation Engine output onto :class:`ValuationContext`.

    Margin of Safety and Valuation Summary are copied by reference —
    never recalculated (Phase A1).
    """
    return ValuationContext(
        instrument=assessment.instrument,
        margin_of_safety=assessment.margin_of_safety,
        valuation_summary=assessment.summary,
        confidence=ValuationConfidence(assessment.confidence.value),
        reasoning=assessment.reasoning,
        evidence=assessment.evidence,
    )
