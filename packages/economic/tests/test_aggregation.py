"""Tests for signal aggregation rules."""

from __future__ import annotations

import pytest

from contracts.enums import SignalDirection

from economic.aggregation import aggregate_signals
from economic.enums import EconomicCondition, Recommendation
from economic.models import EconomicSignal


def _signal(direction: SignalDirection, name: str = "x") -> EconomicSignal:
    return EconomicSignal(
        name=name,
        direction=direction,
        observation=f"{name}-{direction.value}",
        reasoning="test",
        value=1.0,
    )


class TestAggregateSignals:
    """Condition / recommendation aggregation."""

    def test_broad_bullish_is_expansion_buy(self) -> None:
        signals = (
            _signal(SignalDirection.BULLISH, "a"),
            _signal(SignalDirection.BULLISH, "b"),
            _signal(SignalDirection.BULLISH, "c"),
            _signal(SignalDirection.NEUTRAL, "d"),
        )
        condition, rec, reasoning = aggregate_signals(signals)
        assert condition is EconomicCondition.EXPANSION
        assert rec is Recommendation.BUY
        assert "bullish" in reasoning.lower()

    def test_mild_bullish_is_recovery_buy(self) -> None:
        signals = (
            _signal(SignalDirection.BULLISH, "a"),
            _signal(SignalDirection.BULLISH, "b"),
            _signal(SignalDirection.BEARISH, "c"),
            _signal(SignalDirection.NEUTRAL, "d"),
        )
        condition, rec, _ = aggregate_signals(signals)
        assert condition is EconomicCondition.RECOVERY
        assert rec is Recommendation.BUY

    def test_broad_bearish_is_contraction_sell(self) -> None:
        signals = (
            _signal(SignalDirection.BEARISH, "a"),
            _signal(SignalDirection.BEARISH, "b"),
            _signal(SignalDirection.BEARISH, "c"),
        )
        condition, rec, _ = aggregate_signals(signals)
        assert condition is EconomicCondition.CONTRACTION
        assert rec is Recommendation.SELL

    def test_mild_bearish_is_slowing_sell(self) -> None:
        signals = (
            _signal(SignalDirection.BEARISH, "a"),
            _signal(SignalDirection.BEARISH, "b"),
            _signal(SignalDirection.BULLISH, "c"),
        )
        condition, rec, _ = aggregate_signals(signals)
        assert condition is EconomicCondition.SLOWING
        assert rec is Recommendation.SELL

    def test_mixed_is_hold_slowing(self) -> None:
        signals = (
            _signal(SignalDirection.BULLISH, "a"),
            _signal(SignalDirection.BEARISH, "b"),
            _signal(SignalDirection.NEUTRAL, "c"),
        )
        condition, rec, reasoning = aggregate_signals(signals)
        assert condition is EconomicCondition.SLOWING
        assert rec is Recommendation.HOLD
        assert "mixed" in reasoning.lower()

    def test_empty_raises(self) -> None:
        with pytest.raises(ValueError, match="empty"):
            aggregate_signals(())
