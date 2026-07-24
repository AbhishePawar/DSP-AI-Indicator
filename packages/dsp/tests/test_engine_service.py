"""Tests for dsp.engine.service.IndicatorEngine."""

from collections.abc import Callable, Sequence
from datetime import UTC, datetime

import pytest

from contracts.domain.price_series import PriceSeries
from contracts.domain.signal import Signal
from contracts.enums import SignalDirection
from dsp.engine.models import IndicatorSpec
from dsp.engine.service import DEFAULT_INDICATOR_SPECS, IndicatorEngine
from dsp.exceptions import IndicatorError
from dsp.indicators.base import Indicator

_FIXED_NOW = datetime(2024, 6, 1, tzinfo=UTC)
PriceSeriesFactory = Callable[[Sequence[float]], PriceSeries]


class TestIndicatorEngineAnalyze:
    """Tests for IndicatorEngine.analyze end-to-end behavior."""

    @pytest.fixture(autouse=True)
    def _setup(self, price_series_factory: PriceSeriesFactory) -> None:
        # A steady linear ramp drives a deterministic RSI reading (100.0
        # rising / 0.0 falling, since every delta has the same sign) —
        # crossover-rule behavior is covered directly in
        # test_signals_rules.py with hand-crafted IndicatorResults.
        length = 40
        self.rising = price_series_factory([100.0 + i for i in range(length)])
        self.falling = price_series_factory([100.0 - i for i in range(length)])

    def test_default_specs_produce_one_analysis_each(self) -> None:
        engine = IndicatorEngine()
        result = engine.analyze(self.rising)
        assert len(result.analyses) == len(DEFAULT_INDICATOR_SPECS)

    def test_returns_analysis_result_for_the_series_instrument(self) -> None:
        engine = IndicatorEngine()
        result = engine.analyze(self.rising)
        assert result.instrument is self.rising.instrument

    def test_custom_specs_are_honored_in_order(self) -> None:
        engine = IndicatorEngine()
        specs = (IndicatorSpec("rsi", 5), IndicatorSpec("sma", 10))
        result = engine.analyze(self.rising, specs=specs)
        assert [a.result.name for a in result.analyses] == ["rsi", "sma"]
        assert [a.result.period for a in result.analyses] == [5, 10]

    def test_rising_series_produces_rsi_overbought_signal(self) -> None:
        engine = IndicatorEngine()
        result = engine.analyze(self.rising, specs=(IndicatorSpec("rsi", 14),))
        signal = result.signals[0]
        assert signal.direction is SignalDirection.BEARISH
        assert "overbought" in result.explanations[0].summary

    def test_falling_series_produces_rsi_oversold_signal(self) -> None:
        engine = IndicatorEngine()
        result = engine.analyze(self.falling, specs=(IndicatorSpec("rsi", 14),))
        signal = result.signals[0]
        assert signal.direction is SignalDirection.BULLISH
        assert "oversold" in result.explanations[0].summary

    def test_every_analysis_has_matching_signal_explanation_evidence(self) -> None:
        engine = IndicatorEngine()
        result = engine.analyze(self.rising)
        for analysis in result.analyses:
            assert analysis.explanation.summary == analysis.evidence.claim
            assert analysis.signal.explanation is analysis.explanation

    def test_no_numpy_array_in_public_result(self) -> None:
        import numpy as np

        engine = IndicatorEngine()
        result = engine.analyze(self.rising)
        for analysis in result.analyses:
            assert isinstance(analysis.result.values, tuple)
            assert isinstance(analysis.result.source_values, tuple)
            assert not isinstance(analysis.signal.value, np.ndarray)
            for value in analysis.result.values:
                assert isinstance(value, float)

    def test_unknown_indicator_raises_indicator_error(self) -> None:
        engine = IndicatorEngine()
        with pytest.raises(IndicatorError, match="unknown indicator"):
            engine.analyze(self.rising, specs=(IndicatorSpec("macd", 12),))

    def test_deterministic_given_identical_inputs_and_clock(self) -> None:
        engine = IndicatorEngine(clock=lambda: _FIXED_NOW)
        first = engine.analyze(self.rising)
        second = engine.analyze(self.rising)
        assert first.signals == second.signals
        assert first.explanations == second.explanations
        assert first.evidence == second.evidence

    def test_injected_resolver_is_used_instead_of_default_registry(self) -> None:
        calls: list[tuple[str, int]] = []

        class _FakeRsiLikeIndicator(Indicator):
            """A fake indicator whose name ("rsi") has a registered rule."""

            @property
            def name(self) -> str:
                return "rsi"

            def compute(self, prices: object) -> object:
                import numpy as np

                return np.zeros(len(prices))

        def fake_resolver(name: str, period: int) -> Indicator:
            calls.append((name, period))
            return _FakeRsiLikeIndicator(period)

        engine = IndicatorEngine(resolve_indicator=fake_resolver)
        engine.analyze(self.rising, specs=(IndicatorSpec("anything", 7),))
        assert calls == [("anything", 7)]

    def test_indicator_without_a_registered_rule_raises_indicator_error(
        self,
    ) -> None:
        class _NamelessIndicator(Indicator):
            """A fake indicator whose name has no registered signal rule."""

            @property
            def name(self) -> str:
                return "totally_custom_indicator"

            def compute(self, prices: object) -> object:
                import numpy as np

                return np.zeros(len(prices))

        engine = IndicatorEngine(
            resolve_indicator=lambda name, period: _NamelessIndicator(period)
        )
        with pytest.raises(IndicatorError, match="No signal rule registered"):
            engine.analyze(self.rising, specs=(IndicatorSpec("custom", 7),))

    def test_signal_returned_for_every_analysis_is_a_contract_type(self) -> None:
        engine = IndicatorEngine()
        result = engine.analyze(self.rising)
        assert all(isinstance(signal, Signal) for signal in result.signals)
