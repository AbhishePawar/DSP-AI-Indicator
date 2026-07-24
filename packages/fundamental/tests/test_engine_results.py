"""Tests for fundamental.engine.results."""

from datetime import UTC, date, datetime

from contracts.domain.evidence import Evidence
from contracts.domain.explanation import Explanation
from contracts.domain.instrument import Instrument
from contracts.domain.signal import Signal
from contracts.enums import AssetClass, EngineSource, SignalDirection
from fundamental.engine.results import CompanyAnalysis, MetricAnalysis
from fundamental.enums import MetricUnit
from fundamental.models import FundamentalMetric, FundamentalResult

_INSTRUMENT = Instrument(symbol="TEST", asset_class=AssetClass.EQUITY, currency="USD")
_NOW = datetime(2024, 6, 1, tzinfo=UTC)


def _metric_analysis(name: str) -> MetricAnalysis:
    metric = FundamentalMetric(
        instrument=_INSTRUMENT,
        name=name,
        value=0.2,
        unit=MetricUnit.PERCENT,
        period_end=date(2024, 12, 31),
    )
    explanation = Explanation(
        source_engine=EngineSource.FUNDAMENTAL_ENGINE,
        summary=f"{name} reading",
        generated_at=_NOW,
    )
    signal = Signal(
        instrument=_INSTRUMENT,
        source_engine=EngineSource.FUNDAMENTAL_ENGINE,
        name=name,
        direction=SignalDirection.BULLISH,
        timestamp=_NOW,
        value=0.2,
        explanation=explanation,
    )
    evidence = Evidence(
        source_engine=EngineSource.FUNDAMENTAL_ENGINE,
        claim=f"{name} reading",
        value=0.2,
        explanation=explanation,
    )
    return MetricAnalysis(
        metric=metric, signal=signal, explanation=explanation, evidence=evidence
    )


class TestCompanyAnalysis:
    """Tests for the CompanyAnalysis convenience properties."""

    def test_signals_explanations_evidence_preserve_order(self) -> None:
        analyses = (_metric_analysis("roe"), _metric_analysis("debt_to_equity"))
        result = FundamentalResult(
            instrument=_INSTRUMENT,
            analyzer_name="profitability",
            metrics=tuple(a.metric for a in analyses),
            computed_at=_NOW,
        )
        analysis = CompanyAnalysis(
            instrument=_INSTRUMENT, results=(result,), analyses=analyses
        )
        assert analysis.signals == tuple(a.signal for a in analyses)
        assert analysis.explanations == tuple(a.explanation for a in analyses)
        assert analysis.evidence == tuple(a.evidence for a in analyses)

    def test_empty_analyses_produce_empty_tuples(self) -> None:
        analysis = CompanyAnalysis(instrument=_INSTRUMENT, results=(), analyses=())
        assert analysis.signals == ()
        assert analysis.explanations == ()
        assert analysis.evidence == ()
