"""Shared fixtures and offline platform factory for dsp_platform tests."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

import pytest

from contracts.domain.evidence import Evidence
from contracts.domain.explanation import Explanation
from contracts.domain.fundamental_statement import FundamentalStatement
from contracts.domain.instrument import Instrument
from contracts.domain.price_bar import PriceBar
from contracts.domain.price_series import PriceSeries
from contracts.domain.signal import Signal
from contracts.enums import (
    AssetClass,
    BarFrequency,
    EngineSource,
    SignalDirection,
    StatementPeriodType,
)
from dsp.engine.models import IndicatorResult
from dsp.engine.results import AnalysisResult, IndicatorAnalysis
from dsp_platform import DSPPlatform, FeatureFlags
from economic.enums import EconomicCondition
from economic.enums import Recommendation as EcoRecommendation
from economic.models import EconomicAssessment, EconomicSignal, EconomicSnapshot
from fundamental.engine.results import CompanyAnalysis, MetricAnalysis
from fundamental.enums import MetricUnit
from fundamental.models import (
    FinancialSnapshot,
    FundamentalMetric,
    FundamentalResult,
)
from orchestration import InvestmentAnalysisService

FIXED_NOW = datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)


@pytest.fixture
def instrument() -> Instrument:
    return Instrument(symbol="AAPL", asset_class=AssetClass.EQUITY, currency="USD")


def price_series(instrument: Instrument) -> PriceSeries:
    bar = PriceBar(
        timestamp=datetime(2024, 1, 2, tzinfo=UTC),
        open=100.0,
        high=101.0,
        low=99.0,
        close=100.5,
        volume=1_000.0,
    )
    return PriceSeries(
        instrument=instrument, frequency=BarFrequency.DAILY, bars=(bar,)
    )


def financial_snapshot(instrument: Instrument) -> FinancialSnapshot:
    statement = FundamentalStatement(
        instrument=instrument,
        period_end=date(2023, 12, 31),
        period_type=StatementPeriodType.ANNUAL,
        fiscal_year=2023,
        currency="USD",
        revenue=100.0,
    )
    return FinancialSnapshot(instrument=instrument, statements=(statement,))


def economic_snapshot(*, pmi: float | None = 52.0) -> EconomicSnapshot:
    return EconomicSnapshot(as_of=date(2024, 6, 1), country="US", pmi=pmi)


def _signal(
    instrument: Instrument,
    *,
    name: str,
    direction: SignalDirection,
    source: EngineSource,
) -> Signal:
    return Signal(
        instrument=instrument,
        source_engine=source,
        name=name,
        direction=direction,
        timestamp=FIXED_NOW,
        value=1.0,
        strength=0.5,
    )


def technical_result(
    instrument: Instrument,
    *,
    direction: SignalDirection = SignalDirection.BULLISH,
) -> AnalysisResult:
    explanation = Explanation(
        source_engine=EngineSource.INDICATOR_ENGINE,
        summary=f"rsi {direction.value}",
        inputs_used=("rsi",),
        generated_at=FIXED_NOW,
    )
    evidence = Evidence(
        source_engine=EngineSource.INDICATOR_ENGINE,
        claim="rsi evidence",
        value=1.0,
        reference="e2e",
        weight=0.5,
    )
    signal = _signal(
        instrument,
        name="rsi",
        direction=direction,
        source=EngineSource.INDICATOR_ENGINE,
    )
    result = IndicatorResult(
        instrument=instrument,
        name="rsi",
        period=14,
        frequency=BarFrequency.DAILY,
        source_values=(1.0, 2.0, 3.0),
        values=(float("nan"), float("nan"), 55.0),
        latest_value=55.0,
        as_of=FIXED_NOW,
        computed_at=FIXED_NOW,
    )
    return AnalysisResult(
        instrument=instrument,
        analyses=(
            IndicatorAnalysis(
                result=result, signal=signal, explanation=explanation, evidence=evidence
            ),
        ),
    )


def fundamental_result(
    instrument: Instrument,
    *,
    direction: SignalDirection = SignalDirection.BULLISH,
) -> CompanyAnalysis:
    metric = FundamentalMetric(
        instrument=instrument,
        name="roe",
        value=0.18,
        unit=MetricUnit.PERCENT,
        period_end=date(2023, 12, 31),
    )
    explanation = Explanation(
        source_engine=EngineSource.FUNDAMENTAL_ENGINE,
        summary=f"roe {direction.value}",
        inputs_used=("roe",),
        generated_at=FIXED_NOW,
    )
    evidence = Evidence(
        source_engine=EngineSource.FUNDAMENTAL_ENGINE,
        claim="roe evidence",
        value=0.18,
        reference="e2e",
        weight=0.5,
    )
    signal = _signal(
        instrument,
        name="roe",
        direction=direction,
        source=EngineSource.FUNDAMENTAL_ENGINE,
    )
    return CompanyAnalysis(
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
                metric=metric, signal=signal, explanation=explanation, evidence=evidence
            ),
        ),
    )


def economic_result(
    *,
    recommendation: EcoRecommendation = EcoRecommendation.BUY,
) -> EconomicAssessment:
    direction = {
        EcoRecommendation.BUY: SignalDirection.BULLISH,
        EcoRecommendation.HOLD: SignalDirection.NEUTRAL,
        EcoRecommendation.SELL: SignalDirection.BEARISH,
    }[recommendation]
    signal = EconomicSignal(
        name="gdp",
        direction=direction,
        observation="Macro observation",
        reasoning="E2E fixture.",
        value=0.03,
    )
    condition = {
        EcoRecommendation.BUY: EconomicCondition.EXPANSION,
        EcoRecommendation.HOLD: EconomicCondition.SLOWING,
        EcoRecommendation.SELL: EconomicCondition.CONTRACTION,
    }[recommendation]
    return EconomicAssessment(
        overall_condition=condition,
        recommendation=recommendation,
        reasoning="E2E macro fixture.",
        evidence=(),
        detected_signals=(signal,),
        as_of=date(2024, 6, 1),
        assessed_at=FIXED_NOW,
        country="US",
    )


class FakeMarket:
    def __init__(
        self,
        series: PriceSeries | None = None,
        *,
        error: Exception | None = None,
    ) -> None:
        self._series = series
        self._error = error
        self.calls = 0

    def get_price_series(self, request: Any) -> PriceSeries:
        self.calls += 1
        if self._error is not None:
            raise self._error
        assert self._series is not None
        return self._series


class FakeFinancialBridge:
    def __init__(
        self,
        snapshot: FinancialSnapshot | None = None,
        *,
        error: Exception | None = None,
    ) -> None:
        self._snapshot = snapshot
        self._error = error
        self.calls = 0

    def get_snapshot(self, request: Any) -> FinancialSnapshot:
        self.calls += 1
        if self._error is not None:
            raise self._error
        assert self._snapshot is not None
        return self._snapshot


class FakeEconomicBridge:
    def __init__(
        self,
        snapshot: EconomicSnapshot | None = None,
        *,
        error: Exception | None = None,
    ) -> None:
        self._snapshot = snapshot
        self._error = error
        self.calls = 0

    def get_snapshot(self, **kwargs: Any) -> EconomicSnapshot:
        self.calls += 1
        if self._error is not None:
            raise self._error
        assert self._snapshot is not None
        return self._snapshot


class FakeIndicatorEngine:
    def __init__(self, result: AnalysisResult) -> None:
        self._result = result
        self.calls = 0

    def analyze(self, price_series: PriceSeries, **kwargs: Any) -> AnalysisResult:
        self.calls += 1
        return self._result


class FakeFundamentalEngine:
    def __init__(
        self,
        result: CompanyAnalysis | None = None,
        *,
        error: Exception | None = None,
    ) -> None:
        self._result = result
        self._error = error
        self.calls = 0

    def analyze(self, snapshot: FinancialSnapshot, **kwargs: Any) -> CompanyAnalysis:
        self.calls += 1
        if self._error is not None:
            raise self._error
        assert self._result is not None
        return self._result


class FakeEconomicEngine:
    def __init__(
        self,
        result: EconomicAssessment | None = None,
        *,
        error: Exception | None = None,
    ) -> None:
        self._result = result
        self._error = error
        self.calls = 0

    def analyze(self, snapshot: EconomicSnapshot, **kwargs: Any) -> EconomicAssessment:
        self.calls += 1
        if self._error is not None:
            raise self._error
        assert self._result is not None
        return self._result


class FakeValuationEngine:
    def __init__(
        self,
        result: Any | None = None,
        *,
        error: Exception | None = None,
    ) -> None:
        self._result = result
        self._error = error
        self.calls = 0

    def analyze(self, snapshot: FinancialSnapshot, market: Any = None, **kwargs: Any) -> Any:
        self.calls += 1
        if self._error is not None:
            raise self._error
        assert self._result is not None
        return self._result


def build_offline_platform(
    instrument: Instrument,
    *,
    technical: SignalDirection = SignalDirection.BULLISH,
    fundamental: SignalDirection = SignalDirection.BULLISH,
    economic: EcoRecommendation = EcoRecommendation.BUY,
    valuation_mos: float | None = 0.25,
    market_error: Exception | None = None,
    fund_error: Exception | None = None,
    eco_error: Exception | None = None,
    features: FeatureFlags | None = None,
) -> DSPPlatform:
    """Wire ``DSPPlatform`` through the real orchestrator with fakes."""
    from contracts.domain.evidence import Evidence
    from contracts.domain.margin_of_safety import MarginOfSafety
    from contracts.domain.valuation_summary import ValuationSummary
    from contracts.enums import EngineSource
    from valuation.enums import ValuationConfidence, ValuationMethod
    from valuation.models import (
        IntrinsicValueEstimate,
        ValuationAssessment,
        ValuationEvidence,
        ValuationRange,
    )

    reasoning = (
        "Trading below intrinsic value."
        if valuation_mos is None or valuation_mos >= 0
        else "Trading above intrinsic value."
    )
    mid = 1000.0
    market_value = (
        mid * (1.0 - valuation_mos) if valuation_mos is not None else None
    )
    mos = MarginOfSafety(
        ratio=valuation_mos,
        intrinsic_value=mid,
        market_value=market_value,
        available=valuation_mos is not None,
    )
    valuation = ValuationAssessment(
        instrument=instrument,
        estimates=(
            IntrinsicValueEstimate(
                method=ValuationMethod.BOOK_VALUE,
                intrinsic_value=mid,
                applicable=True,
                formula="IV = total_equity",
                rationale=reasoning,
            ),
        ),
        valuation_range=ValuationRange(low=mid, mid=mid, high=mid),
        margin_of_safety=mos,
        summary=ValuationSummary(
            intrinsic_low=mid,
            intrinsic_mid=mid,
            intrinsic_high=mid,
            margin_of_safety=mos,
            confidence=ValuationConfidence.HIGH.value,
            currency="USD",
            as_of=date(2023, 12, 31),
        ),
        confidence=ValuationConfidence.HIGH,
        evidence=(
            Evidence(
                source_engine=EngineSource.VALUATION_ENGINE,
                claim=reasoning,
                value=valuation_mos,
                reference="mos",
                weight=0.5,
            ),
        ),
        method_evidence=(
            ValuationEvidence(
                method=ValuationMethod.BOOK_VALUE,
                claim=reasoning,
                value=mid,
                reference="IV = total_equity",
            ),
        ),
        reasoning=reasoning,
        currency="USD",
        as_of=date(2023, 12, 31),
        assessed_at=FIXED_NOW,
    )

    service = InvestmentAnalysisService(
        market_data=FakeMarket(  # type: ignore[arg-type]
            None if market_error else price_series(instrument),
            error=market_error,
        ),
        financial_bridge=FakeFinancialBridge(  # type: ignore[arg-type]
            None if fund_error else financial_snapshot(instrument),
            error=fund_error,
        ),
        economic_bridge=FakeEconomicBridge(  # type: ignore[arg-type]
            None if eco_error else economic_snapshot(),
            error=eco_error,
        ),
        indicator_engine=FakeIndicatorEngine(  # type: ignore[arg-type]
            technical_result(instrument, direction=technical)
        ),
        fundamental_engine=FakeFundamentalEngine(  # type: ignore[arg-type]
            (
                None
                if fund_error
                else fundamental_result(instrument, direction=fundamental)
            ),
            error=fund_error,
        ),
        economic_engine=FakeEconomicEngine(  # type: ignore[arg-type]
            None if eco_error else economic_result(recommendation=economic),
            error=eco_error,
        ),
        valuation_engine=FakeValuationEngine(  # type: ignore[arg-type]
            None if fund_error else valuation,
            error=fund_error,
        ),
    )
    return DSPPlatform(analysis_service=service, features=features)


@pytest.fixture
def build_platform(instrument: Instrument):
    """Factory fixture — avoids importing conftest under importlib mode."""

    def _factory(**kwargs: Any) -> DSPPlatform:
        return build_offline_platform(instrument, **kwargs)

    return _factory
