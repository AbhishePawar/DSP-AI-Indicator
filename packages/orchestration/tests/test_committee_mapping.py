"""Tests for engine → committee DTO mapping."""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from contracts import (
    AnalyticalStance,
    AssetClass,
    EngineSource,
    Evidence,
    Instrument,
    MarginOfSafety,
    Signal,
    SignalDirection,
    ValuationConfidence,
    ValuationSummary,
)
from contracts.enums import BarFrequency
from dsp.engine.models import IndicatorResult
from dsp.engine.results import AnalysisResult, IndicatorAnalysis
from economic import EconomicAssessment
from economic.enums import EconomicCondition
from economic.enums import Recommendation as EcoRecommendation
from economic.models import EconomicSignal
from fundamental.engine.results import CompanyAnalysis, MetricAnalysis
from fundamental.enums import MetricUnit
from fundamental.models import FundamentalMetric, FundamentalResult
from orchestration.committee_mapping import (
    to_economic_context,
    to_fundamental_context,
    to_technical_context,
    to_valuation_context,
)
from valuation import (
    IntrinsicValueEstimate,
    ValuationAssessment,
    ValuationConfidence as EngineValConfidence,
    ValuationEvidence,
    ValuationMethod,
    ValuationRange,
)

FIXED_NOW = datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)


@pytest.fixture
def instrument() -> Instrument:
    return Instrument(symbol="AAPL", asset_class=AssetClass.EQUITY, currency="USD")


class TestCommitteeMapping:
    def test_technical_mapping(self, instrument: Instrument) -> None:
        signal = Signal(
            instrument=instrument,
            source_engine=EngineSource.INDICATOR_ENGINE,
            name="rsi",
            direction=SignalDirection.BULLISH,
            timestamp=FIXED_NOW,
            value=1.0,
            strength=0.5,
        )
        evidence = Evidence(
            source_engine=EngineSource.INDICATOR_ENGINE,
            claim="rsi evidence",
            value=1.0,
            reference="test",
            weight=0.5,
        )
        from contracts import Explanation

        explanation = Explanation(
            source_engine=EngineSource.INDICATOR_ENGINE,
            summary="rsi bullish",
            inputs_used=("close",),
            generated_at=FIXED_NOW,
        )
        result = IndicatorResult(
            instrument=instrument,
            name="rsi",
            period=14,
            frequency=BarFrequency.DAILY,
            source_values=(1.0, 2.0, 3.0),
            values=(float("nan"), float("nan"), 50.0),
            latest_value=50.0,
            as_of=FIXED_NOW,
            computed_at=FIXED_NOW,
        )
        analysis = AnalysisResult(
            instrument=instrument,
            analyses=(
                IndicatorAnalysis(
                    result=result,
                    signal=signal,
                    explanation=explanation,
                    evidence=evidence,
                ),
            ),
        )
        ctx = to_technical_context(analysis)
        assert ctx.instrument is instrument
        assert ctx.signals == (signal,)
        assert ctx.evidence == (evidence,)

    def test_fundamental_mapping(self, instrument: Instrument) -> None:
        signal = Signal(
            instrument=instrument,
            source_engine=EngineSource.FUNDAMENTAL_ENGINE,
            name="roe",
            direction=SignalDirection.BEARISH,
            timestamp=FIXED_NOW,
            value=0.1,
            strength=0.5,
        )
        evidence = Evidence(
            source_engine=EngineSource.FUNDAMENTAL_ENGINE,
            claim="roe evidence",
            value=0.1,
            reference="test",
            weight=0.5,
        )
        from contracts import Explanation

        explanation = Explanation(
            source_engine=EngineSource.FUNDAMENTAL_ENGINE,
            summary="roe weak",
            inputs_used=("net_income",),
            generated_at=FIXED_NOW,
        )
        metric = FundamentalMetric(
            instrument=instrument,
            name="roe",
            value=0.1,
            unit=MetricUnit.RATIO,
            period_end=date(2023, 12, 31),
        )
        company = CompanyAnalysis(
            instrument=instrument,
            results=(
                FundamentalResult(
                    instrument=instrument,
                    analyzer_name="profitability",
                    metrics=(metric,),
                    computed_at=FIXED_NOW,
                ),
            ),
            analyses=(
                MetricAnalysis(
                    metric=metric,
                    signal=signal,
                    explanation=explanation,
                    evidence=evidence,
                ),
            ),
        )
        ctx = to_fundamental_context(company)
        assert ctx.signals == (signal,)
        assert ctx.evidence == (evidence,)

    def test_economic_mapping(self) -> None:
        evidence = Evidence(
            source_engine=EngineSource.ECONOMIC_ENGINE,
            claim="gdp strong",
            value=0.03,
            reference="gdp",
            weight=0.5,
        )
        assessment = EconomicAssessment(
            overall_condition=EconomicCondition.EXPANSION,
            recommendation=EcoRecommendation.BUY,
            reasoning="Growth is strong.",
            evidence=(evidence,),
            detected_signals=(
                EconomicSignal(
                    name="gdp",
                    direction=SignalDirection.BULLISH,
                    observation="Strong GDP",
                    reasoning="Growth is strong.",
                    value=0.03,
                ),
            ),
            as_of=date(2024, 6, 1),
            assessed_at=FIXED_NOW,
            country="US",
        )
        ctx = to_economic_context(assessment)
        assert ctx.stance is AnalyticalStance.BUY
        assert ctx.overall_condition == "expansion"
        assert ctx.country == "US"
        assert ctx.reasoning == "Growth is strong."
        assert ctx.evidence == (evidence,)

    def test_valuation_mapping_preserves_mos(
        self, instrument: Instrument
    ) -> None:
        mos = MarginOfSafety(
            ratio=0.25,
            intrinsic_value=1000.0,
            market_value=750.0,
            available=True,
        )
        summary = ValuationSummary(
            intrinsic_low=1000.0,
            intrinsic_mid=1000.0,
            intrinsic_high=1000.0,
            margin_of_safety=mos,
            confidence="high",
            currency="USD",
            as_of=date(2023, 12, 31),
        )
        evidence = Evidence(
            source_engine=EngineSource.VALUATION_ENGINE,
            claim="undervalued",
            value=0.25,
            reference="mos",
            weight=0.5,
        )
        assessment = ValuationAssessment(
            instrument=instrument,
            estimates=(
                IntrinsicValueEstimate(
                    method=ValuationMethod.BOOK_VALUE,
                    intrinsic_value=1000.0,
                    applicable=True,
                    formula="IV = E",
                    rationale="book",
                ),
            ),
            valuation_range=ValuationRange(low=1000.0, mid=1000.0, high=1000.0),
            margin_of_safety=mos,
            summary=summary,
            confidence=EngineValConfidence.HIGH,
            evidence=(evidence,),
            method_evidence=(
                ValuationEvidence(
                    method=ValuationMethod.BOOK_VALUE,
                    claim="book",
                    value=1000.0,
                    reference="IV = E",
                ),
            ),
            reasoning="Trading below intrinsic value.",
            currency="USD",
            as_of=date(2023, 12, 31),
            assessed_at=FIXED_NOW,
        )
        ctx = to_valuation_context(assessment)
        assert ctx.margin_of_safety is mos
        assert ctx.valuation_summary is summary
        assert ctx.confidence is ValuationConfidence.HIGH
        assert ctx.evidence == (evidence,)
        assert ctx.reasoning == assessment.reasoning
