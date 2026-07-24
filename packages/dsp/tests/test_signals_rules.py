"""Tests for dsp.signals.rules."""

from datetime import UTC, datetime

import pytest

from contracts.domain.instrument import Instrument
from contracts.enums import AssetClass, BarFrequency, SignalDirection
from dsp.engine.models import IndicatorResult
from dsp.signals import rules

_INSTRUMENT = Instrument(symbol="AAPL", asset_class=AssetClass.EQUITY, currency="USD")
_NOW = datetime(2024, 1, 5, tzinfo=UTC)


def _result(
    name: str,
    *,
    values: tuple[float, ...],
    source_values: tuple[float, ...] | None = None,
    period: int = 14,
) -> IndicatorResult:
    return IndicatorResult(
        instrument=_INSTRUMENT,
        name=name,
        period=period,
        frequency=BarFrequency.DAILY,
        source_values=source_values or values,
        values=values,
        latest_value=values[-1] if values else float("nan"),
        as_of=_NOW,
        computed_at=_NOW,
    )


class TestThresholdRule:
    """Tests for evaluate_threshold_rule (RSI-style oscillators)."""

    def test_overbought_is_bearish(self) -> None:
        result = _result("rsi", values=(76.2,))
        outcome = rules.evaluate_threshold_rule(result)
        assert outcome.direction is SignalDirection.BEARISH
        assert outcome.threshold == 70.0
        assert "76.2" in outcome.reasoning
        assert "overbought" in outcome.reasoning

    def test_oversold_is_bullish(self) -> None:
        result = _result("rsi", values=(21.4,))
        outcome = rules.evaluate_threshold_rule(result)
        assert outcome.direction is SignalDirection.BULLISH
        assert outcome.threshold == 30.0
        assert "oversold" in outcome.reasoning

    def test_neutral_between_thresholds(self) -> None:
        result = _result("rsi", values=(50.0,))
        outcome = rules.evaluate_threshold_rule(result)
        assert outcome.direction is SignalDirection.NEUTRAL
        assert outcome.strength is None

    def test_boundary_values_are_not_overbought_or_oversold(self) -> None:
        overbought_edge = rules.evaluate_threshold_rule(_result("rsi", values=(70.0,)))
        oversold_edge = rules.evaluate_threshold_rule(_result("rsi", values=(30.0,)))
        assert overbought_edge.direction is SignalDirection.NEUTRAL
        assert oversold_edge.direction is SignalDirection.NEUTRAL

    def test_insufficient_data_is_neutral(self) -> None:
        result = _result("rsi", values=(float("nan"),))
        outcome = rules.evaluate_threshold_rule(result)
        assert outcome.direction is SignalDirection.NEUTRAL
        assert "insufficient data" in outcome.reasoning

    def test_custom_thresholds(self) -> None:
        result = _result("rsi", values=(65.0,))
        outcome = rules.evaluate_threshold_rule(result, overbought=60.0, oversold=20.0)
        assert outcome.direction is SignalDirection.BEARISH
        assert outcome.threshold == 60.0

    def test_strength_increases_with_distance_from_threshold(self) -> None:
        near = rules.evaluate_threshold_rule(_result("rsi", values=(71.0,)))
        far = rules.evaluate_threshold_rule(_result("rsi", values=(95.0,)))
        assert near.strength is not None
        assert far.strength is not None
        assert far.strength > near.strength


class TestCrossoverRule:
    """Tests for evaluate_crossover_rule (moving-average-style indicators)."""

    def test_bullish_crossover(self) -> None:
        result = _result(
            "ema",
            source_values=(99.0, 101.0),
            values=(100.0, 100.0),
        )
        outcome = rules.evaluate_crossover_rule(result)
        assert outcome.direction is SignalDirection.BULLISH
        assert outcome.threshold == 100.0
        assert "bullish crossover" in outcome.reasoning

    def test_bearish_crossover(self) -> None:
        result = _result(
            "ema",
            source_values=(101.0, 99.0),
            values=(100.0, 100.0),
        )
        outcome = rules.evaluate_crossover_rule(result)
        assert outcome.direction is SignalDirection.BEARISH
        assert "bearish crossover" in outcome.reasoning

    def test_no_crossover_is_neutral(self) -> None:
        result = _result(
            "ema",
            source_values=(102.0, 103.0),
            values=(100.0, 100.0),
        )
        outcome = rules.evaluate_crossover_rule(result)
        assert outcome.direction is SignalDirection.NEUTRAL
        assert outcome.strength is None

    def test_insufficient_data_is_neutral(self) -> None:
        result = _result("ema", source_values=(101.0,), values=(100.0,))
        outcome = rules.evaluate_crossover_rule(result)
        assert outcome.direction is SignalDirection.NEUTRAL

    def test_nan_values_are_insufficient_data(self) -> None:
        result = _result(
            "ema",
            source_values=(99.0, 101.0),
            values=(float("nan"), 100.0),
        )
        outcome = rules.evaluate_crossover_rule(result)
        assert outcome.direction is SignalDirection.NEUTRAL
        assert "insufficient data" in outcome.reasoning


class TestRuleRegistry:
    """Tests for the name -> rule registry and its dispatch."""

    def test_rsi_dispatches_to_threshold_rule(self) -> None:
        result = _result("rsi", values=(80.0,))
        outcome = rules.evaluate(result)
        assert outcome.direction is SignalDirection.BEARISH

    @pytest.mark.parametrize("name", ["sma", "ema", "wma"])
    def test_moving_averages_dispatch_to_crossover_rule(self, name: str) -> None:
        result = _result(name, source_values=(99.0, 101.0), values=(100.0, 100.0))
        outcome = rules.evaluate(result)
        assert outcome.direction is SignalDirection.BULLISH

    def test_unknown_indicator_raises(self) -> None:
        result = _result("macd", values=(1.0,))
        with pytest.raises(KeyError, match="Unknown signal rule"):
            rules.evaluate(result)

    def test_register_rule_adds_new_dispatch(self) -> None:
        def always_bullish(result: IndicatorResult) -> rules.RuleOutcome:
            return rules.RuleOutcome(
                direction=SignalDirection.BULLISH, reasoning="always bullish"
            )

        rules.register_rule("custom_indicator", always_bullish)
        result = _result("custom_indicator", values=(1.0,))
        outcome = rules.evaluate(result)
        assert outcome.direction is SignalDirection.BULLISH
        assert outcome.reasoning == "always bullish"
