"""Tests for InvestmentAnalysisService pipeline composition."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

import pytest

from ai_committee import CommitteeReport, Decision
from contracts.domain.evidence import Evidence
from contracts.domain.explanation import Explanation
from contracts.domain.instrument import Instrument
from contracts.domain.margin_of_safety import MarginOfSafety
from contracts.domain.price_bar import PriceBar
from contracts.domain.price_series import PriceSeries
from contracts.domain.signal import Signal
from contracts.domain.valuation_summary import ValuationSummary
from contracts.enums import (
    AssetClass,
    BarFrequency,
    EngineSource,
    SignalDirection,
)
from data_engine.exceptions import DataEngineError
from data_engine.models import PriceSeriesRequest
from dsp.engine.models import IndicatorResult
from dsp.engine.results import AnalysisResult, IndicatorAnalysis
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
from orchestration import (
    AnalysisRequest,
    InvestmentAnalysisService,
    OrchestrationError,
)
from snapshot_bridge.exceptions import SnapshotBridgeError
from valuation.enums import ValuationConfidence, ValuationMethod
from valuation.models import (
    IntrinsicValueEstimate,
    ValuationAssessment,
    ValuationEvidence,
    ValuationRange,
)

FIXED_NOW = datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)


@pytest.fixture
def instrument() -> Instrument:
    return Instrument(symbol="AAPL", asset_class=AssetClass.EQUITY, currency="USD")


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


def _technical(instrument: Instrument) -> AnalysisResult:
    explanation = Explanation(
        source_engine=EngineSource.INDICATOR_ENGINE,
        summary="rsi bullish",
        inputs_used=("rsi",),
        generated_at=FIXED_NOW,
    )
    evidence = Evidence(
        source_engine=EngineSource.INDICATOR_ENGINE,
        claim="rsi evidence",
        value=1.0,
        reference="test",
        weight=0.5,
    )
    signal = _signal(
        instrument,
        name="rsi",
        direction=SignalDirection.BULLISH,
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


def _fundamental(instrument: Instrument) -> CompanyAnalysis:
    metric = FundamentalMetric(
        instrument=instrument,
        name="roe",
        value=0.18,
        unit=MetricUnit.PERCENT,
        period_end=date(2023, 12, 31),
    )
    explanation = Explanation(
        source_engine=EngineSource.FUNDAMENTAL_ENGINE,
        summary="roe strong",
        inputs_used=("roe",),
        generated_at=FIXED_NOW,
    )
    evidence = Evidence(
        source_engine=EngineSource.FUNDAMENTAL_ENGINE,
        claim="roe evidence",
        value=0.18,
        reference="test",
        weight=0.5,
    )
    signal = _signal(
        instrument,
        name="roe",
        direction=SignalDirection.BULLISH,
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


def _economic() -> EconomicAssessment:
    signal = EconomicSignal(
        name="gdp",
        direction=SignalDirection.BULLISH,
        observation="Strong GDP Growth",
        reasoning="Growth is strong.",
        value=0.03,
    )
    return EconomicAssessment(
        overall_condition=EconomicCondition.EXPANSION,
        recommendation=EcoRecommendation.BUY,
        reasoning="Macro backdrop is expansionary.",
        evidence=(),
        detected_signals=(signal,),
        as_of=date(2024, 6, 1),
        assessed_at=FIXED_NOW,
        country="US",
    )


def _valuation(instrument: Instrument) -> ValuationAssessment:
    reasoning = "Trading 25% below intrinsic value."
    mos = MarginOfSafety(
        ratio=0.25,
        intrinsic_value=1000.0,
        market_value=750.0,
        available=True,
    )
    return ValuationAssessment(
        instrument=instrument,
        estimates=(
            IntrinsicValueEstimate(
                method=ValuationMethod.BOOK_VALUE,
                intrinsic_value=1000.0,
                applicable=True,
                formula="IV = total_equity",
                rationale=reasoning,
            ),
        ),
        valuation_range=ValuationRange(low=1000.0, mid=1000.0, high=1000.0),
        margin_of_safety=mos,
        summary=ValuationSummary(
            intrinsic_low=1000.0,
            intrinsic_mid=1000.0,
            intrinsic_high=1000.0,
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
                value=0.25,
                reference="mos",
                weight=0.5,
            ),
        ),
        method_evidence=(
            ValuationEvidence(
                method=ValuationMethod.BOOK_VALUE,
                claim=reasoning,
                value=1000.0,
                reference="IV = total_equity",
            ),
        ),
        reasoning=reasoning,
        currency="USD",
        as_of=date(2023, 12, 31),
        assessed_at=FIXED_NOW,
    )


def _price_series(instrument: Instrument) -> PriceSeries:
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


class _FakeMarket:
    def __init__(
        self,
        series: PriceSeries | None = None,
        *,
        error: Exception | None = None,
    ) -> None:
        self._series = series
        self._error = error
        self.calls = 0

    def get_price_series(self, request: PriceSeriesRequest) -> PriceSeries:
        self.calls += 1
        if self._error is not None:
            raise self._error
        assert self._series is not None
        return self._series


class _FakeFinancialBridge:
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


class _FakeEconomicBridge:
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


class _FakeIndicatorEngine:
    def __init__(self, result: AnalysisResult) -> None:
        self._result = result
        self.calls = 0

    def analyze(self, price_series: PriceSeries, **kwargs: Any) -> AnalysisResult:
        self.calls += 1
        return self._result


class _FakeFundamentalEngine:
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


class _FakeEconomicEngine:
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


class _FakeValuationEngine:
    def __init__(
        self,
        result: ValuationAssessment | None = None,
        *,
        error: Exception | None = None,
    ) -> None:
        self._result = result
        self._error = error
        self.calls = 0
        self.last_market: Any = None

    def analyze(
        self, snapshot: FinancialSnapshot, market: Any = None, **kwargs: Any
    ) -> ValuationAssessment:
        self.calls += 1
        self.last_market = market
        if self._error is not None:
            raise self._error
        assert self._result is not None
        return self._result


def _service(
    instrument: Instrument,
    *,
    market_error: Exception | None = None,
    fund_error: Exception | None = None,
    eco_error: Exception | None = None,
    val_error: Exception | None = None,
    market_cap_in_extras: float | None = None,
) -> tuple[InvestmentAnalysisService, _FakeValuationEngine]:
    from contracts.domain.fundamental_statement import FundamentalStatement
    from contracts.domain.margin_of_safety import MARKET_CAPITALIZATION_KEY
    from contracts.enums import StatementPeriodType

    extras: tuple[tuple[str, float], ...] = ()
    if market_cap_in_extras is not None:
        extras = ((MARKET_CAPITALIZATION_KEY, market_cap_in_extras),)

    statement = FundamentalStatement(
        instrument=instrument,
        period_end=date(2023, 12, 31),
        period_type=StatementPeriodType.ANNUAL,
        fiscal_year=2023,
        currency="USD",
        revenue=100.0,
        extra_line_items=extras,
    )
    fin_snap = FinancialSnapshot(instrument=instrument, statements=(statement,))
    eco_snap = EconomicSnapshot(as_of=date(2024, 6, 1), country="US", pmi=52.0)

    valuation_engine = _FakeValuationEngine(
        None if (fund_error or val_error) else _valuation(instrument),
        error=val_error or fund_error,
    )
    service = InvestmentAnalysisService(
        market_data=_FakeMarket(  # type: ignore[arg-type]
            None if market_error else _price_series(instrument),
            error=market_error,
        ),
        financial_bridge=_FakeFinancialBridge(  # type: ignore[arg-type]
            None if fund_error else fin_snap,
            error=fund_error,
        ),
        economic_bridge=_FakeEconomicBridge(  # type: ignore[arg-type]
            None if eco_error else eco_snap,
            error=eco_error,
        ),
        indicator_engine=_FakeIndicatorEngine(_technical(instrument)),  # type: ignore[arg-type]
        fundamental_engine=_FakeFundamentalEngine(  # type: ignore[arg-type]
            None if fund_error else _fundamental(instrument),
            error=fund_error,
        ),
        economic_engine=_FakeEconomicEngine(_economic()),  # type: ignore[arg-type]
        valuation_engine=valuation_engine,  # type: ignore[arg-type]
    )
    return service


class TestHappyPath:
    def test_returns_committee_report(self, instrument: Instrument) -> None:
        service = _service(instrument)
        request = AnalysisRequest(
            instrument=instrument,
            start=date(2024, 1, 1),
            end=date(2024, 6, 1),
        )
        report = service.analyze(request)

        assert isinstance(report, CommitteeReport)
        assert report.instrument == instrument
        assert report.decision.decision is Decision.BUY
        assert len(report.votes) == 4
        assert {vote.source for vote in report.votes} == {
            "technical",
            "fundamental",
            "economic",
            "valuation",
        }

    def test_recommendation_includes_valuation_evidence(
        self, instrument: Instrument
    ) -> None:
        service = _service(instrument)
        recommendation = service.analyze_recommendation(
            AnalysisRequest(
                instrument=instrument,
                start=date(2024, 1, 1),
                end=date(2024, 6, 1),
            )
        )
        claims = " ".join(
            e.claim for e in recommendation.supporting_evidence
        )
        assert "intrinsic" in claims.lower() or "25%" in claims or "Trading" in claims

    def test_deterministic(self, instrument: Instrument) -> None:
        service = _service(instrument)
        request = AnalysisRequest(
            instrument=instrument,
            start=date(2024, 1, 1),
            end=date(2024, 6, 1),
        )
        first = service.analyze(request)
        second = service.analyze(request)
        assert first.decision.decision is second.decision.decision
        assert first.voting_summary == second.voting_summary


class TestMissingEconomics:
    def test_skips_economic_member_when_include_false(
        self, instrument: Instrument
    ) -> None:
        service = _service(instrument)
        report = service.analyze(
            AnalysisRequest(
                instrument=instrument,
                start=date(2024, 1, 1),
                end=date(2024, 6, 1),
                include_economic=False,
            )
        )
        assert {vote.source for vote in report.votes} == {
            "technical",
            "fundamental",
            "valuation",
        }

    def test_partial_economic_failure_skips_member(
        self, instrument: Instrument
    ) -> None:
        service = _service(
            instrument, eco_error=SnapshotBridgeError("no series")
        )
        report = service.analyze(
            AnalysisRequest(
                instrument=instrument,
                start=date(2024, 1, 1),
                end=date(2024, 6, 1),
                allow_partial=True,
            )
        )
        assert "economic" not in {vote.source for vote in report.votes}
        assert "technical" in {vote.source for vote in report.votes}
        assert "valuation" in {vote.source for vote in report.votes}


class TestMissingFundamentals:
    def test_skips_when_include_false(self, instrument: Instrument) -> None:
        service = _service(instrument)
        report = service.analyze(
            AnalysisRequest(
                instrument=instrument,
                start=date(2024, 1, 1),
                end=date(2024, 6, 1),
                include_fundamentals=False,
            )
        )
        assert {vote.source for vote in report.votes} == {
            "technical",
            "economic",
            "valuation",
        }

    def test_partial_failure_skips_member(self, instrument: Instrument) -> None:
        service = _service(
            instrument, fund_error=DataEngineError("fundamentals down")
        )
        report = service.analyze(
            AnalysisRequest(
                instrument=instrument,
                start=date(2024, 1, 1),
                end=date(2024, 6, 1),
                allow_partial=True,
            )
        )
        assert "fundamental" not in {vote.source for vote in report.votes}
        assert "valuation" not in {vote.source for vote in report.votes}

    def test_strict_mode_raises(self, instrument: Instrument) -> None:
        service = _service(
            instrument, fund_error=DataEngineError("fundamentals down")
        )
        with pytest.raises(OrchestrationError, match="financial snapshot"):
            service.analyze(
                AnalysisRequest(
                    instrument=instrument,
                    start=date(2024, 1, 1),
                    end=date(2024, 6, 1),
                    allow_partial=False,
                )
            )


class TestMissingValuation:
    def test_skips_when_include_false(self, instrument: Instrument) -> None:
        service = _service(instrument)
        report = service.analyze(
            AnalysisRequest(
                instrument=instrument,
                start=date(2024, 1, 1),
                end=date(2024, 6, 1),
                include_valuation=False,
            )
        )
        assert {vote.source for vote in report.votes} == {
            "technical",
            "fundamental",
            "economic",
        }

    def test_partial_failure_skips_member(self, instrument: Instrument) -> None:
        service = _service(
            instrument, val_error=OrchestrationError("valuation boom")
        )
        # val_error on engine after successful snapshot fetch
        report = service.analyze(
            AnalysisRequest(
                instrument=instrument,
                start=date(2024, 1, 1),
                end=date(2024, 6, 1),
                allow_partial=True,
            )
        )
        assert "valuation" not in {vote.source for vote in report.votes}
        assert "fundamental" in {vote.source for vote in report.votes}


class TestProviderFailures:
    def test_market_failure_raises(self, instrument: Instrument) -> None:
        service = _service(
            instrument, market_error=DataEngineError("yahoo down")
        )
        with pytest.raises(OrchestrationError, match="technical"):
            service.analyze(
                AnalysisRequest(
                    instrument=instrument,
                    start=date(2024, 1, 1),
                    end=date(2024, 6, 1),
                )
            )

    def test_does_not_leak_provider_exception_type(
        self, instrument: Instrument
    ) -> None:
        service = _service(
            instrument, market_error=DataEngineError("yahoo down")
        )
        with pytest.raises(OrchestrationError) as exc_info:
            service.analyze(
                AnalysisRequest(
                    instrument=instrument,
                    start=date(2024, 1, 1),
                    end=date(2024, 6, 1),
                )
            )
        assert not isinstance(exc_info.value, DataEngineError)


class TestMarginOfSafetyWiring:
    def test_passes_market_cap_override_to_valuation(
        self, instrument: Instrument
    ) -> None:
        service = _service(instrument)
        service.analyze(
            AnalysisRequest(
                instrument=instrument,
                start=date(2024, 1, 1),
                end=date(2024, 6, 1),
                market_cap=500.0,
            )
        )
        market = service._valuation_engine.last_market  # type: ignore[attr-defined]
        assert market is not None
        assert market.market_cap == pytest.approx(500.0)

    def test_reads_market_capitalization_from_extras(
        self, instrument: Instrument
    ) -> None:
        service = _service(instrument, market_cap_in_extras=800.0)
        service.analyze(
            AnalysisRequest(
                instrument=instrument,
                start=date(2024, 1, 1),
                end=date(2024, 6, 1),
            )
        )
        market = service._valuation_engine.last_market  # type: ignore[attr-defined]
        assert market is not None
        assert market.market_cap == pytest.approx(800.0)

    def test_recommendation_propagates_mos(
        self, instrument: Instrument
    ) -> None:
        service = _service(instrument)
        recommendation = service.analyze_recommendation(
            AnalysisRequest(
                instrument=instrument,
                start=date(2024, 1, 1),
                end=date(2024, 6, 1),
            )
        )
        assert recommendation.margin_of_safety is not None
        assert recommendation.margin_of_safety.available is True
        assert recommendation.margin_of_safety.ratio == pytest.approx(0.25)
        assert recommendation.valuation_summary is not None
        assert recommendation.valuation_summary.intrinsic_mid == pytest.approx(
            1000.0
        )
