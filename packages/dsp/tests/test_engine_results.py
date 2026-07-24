"""Tests for dsp.engine.results (IndicatorAnalysis, AnalysisResult)."""

from datetime import UTC, datetime

from contracts.domain.evidence import Evidence
from contracts.domain.explanation import Explanation
from contracts.domain.instrument import Instrument
from contracts.domain.signal import Signal
from contracts.enums import AssetClass, BarFrequency, EngineSource, SignalDirection
from dsp.engine.models import IndicatorResult
from dsp.engine.results import AnalysisResult, IndicatorAnalysis

_INSTRUMENT = Instrument(symbol="AAPL", asset_class=AssetClass.EQUITY, currency="USD")
_NOW = datetime(2024, 1, 5, tzinfo=UTC)


def _analysis(name: str) -> IndicatorAnalysis:
    result = IndicatorResult(
        instrument=_INSTRUMENT,
        name=name,
        period=14,
        frequency=BarFrequency.DAILY,
        source_values=(1.0, 2.0),
        values=(1.0, 2.0),
        latest_value=2.0,
        as_of=_NOW,
        computed_at=_NOW,
    )
    signal = Signal(
        instrument=_INSTRUMENT,
        source_engine=EngineSource.INDICATOR_ENGINE,
        name=f"{name}_14",
        direction=SignalDirection.NEUTRAL,
        timestamp=_NOW,
    )
    explanation = Explanation(
        source_engine=EngineSource.INDICATOR_ENGINE, summary=f"{name} explanation"
    )
    evidence = Evidence(
        source_engine=EngineSource.INDICATOR_ENGINE, claim=f"{name} claim"
    )
    return IndicatorAnalysis(
        result=result, signal=signal, explanation=explanation, evidence=evidence
    )


class TestAnalysisResult:
    """Tests for AnalysisResult's flattening convenience properties."""

    def test_signals_preserves_request_order(self) -> None:
        analyses = (_analysis("sma"), _analysis("rsi"))
        analysis_result = AnalysisResult(instrument=_INSTRUMENT, analyses=analyses)
        assert [s.name for s in analysis_result.signals] == ["sma_14", "rsi_14"]

    def test_explanations_match_analyses(self) -> None:
        analyses = (_analysis("sma"), _analysis("rsi"))
        analysis_result = AnalysisResult(instrument=_INSTRUMENT, analyses=analyses)
        summaries = [e.summary for e in analysis_result.explanations]
        assert summaries == ["sma explanation", "rsi explanation"]

    def test_evidence_matches_analyses(self) -> None:
        analyses = (_analysis("sma"), _analysis("rsi"))
        analysis_result = AnalysisResult(instrument=_INSTRUMENT, analyses=analyses)
        claims = [e.claim for e in analysis_result.evidence]
        assert claims == ["sma claim", "rsi claim"]

    def test_empty_analyses(self) -> None:
        analysis_result = AnalysisResult(instrument=_INSTRUMENT, analyses=())
        assert analysis_result.signals == ()
        assert analysis_result.explanations == ()
        assert analysis_result.evidence == ()
