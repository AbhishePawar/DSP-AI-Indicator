"""Tests for ai_committee.voting helpers."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from contracts.domain.instrument import Instrument
from contracts.domain.signal import Signal
from contracts.enums import AssetClass, EngineSource, SignalDirection

from ai_committee.enums import Decision
from ai_committee.voting import (
    aggregate_recommendations,
    collapse_signals,
    signal_direction_to_decision,
)

FIXED_NOW = datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)


def _signal(direction: SignalDirection) -> Signal:
    instrument = Instrument(
        symbol="T", asset_class=AssetClass.EQUITY, currency="USD"
    )
    return Signal(
        instrument=instrument,
        source_engine=EngineSource.INDICATOR_ENGINE,
        name="x",
        direction=direction,
        timestamp=FIXED_NOW,
    )


class TestSignalDirectionToDecision:
    """Tests for SignalDirection → Decision mapping."""

    def test_bullish_is_buy(self) -> None:
        assert (
            signal_direction_to_decision(SignalDirection.BULLISH)
            is Decision.BUY
        )

    def test_bearish_is_sell(self) -> None:
        assert (
            signal_direction_to_decision(SignalDirection.BEARISH)
            is Decision.SELL
        )

    def test_neutral_is_hold(self) -> None:
        assert (
            signal_direction_to_decision(SignalDirection.NEUTRAL)
            is Decision.HOLD
        )


class TestCollapseSignals:
    """Tests for collapse_signals majority logic."""

    def test_more_bullish_is_buy(self) -> None:
        signals = (
            _signal(SignalDirection.BULLISH),
            _signal(SignalDirection.BULLISH),
            _signal(SignalDirection.BEARISH),
        )
        assert collapse_signals(signals) is Decision.BUY

    def test_more_bearish_is_sell(self) -> None:
        signals = (
            _signal(SignalDirection.BEARISH),
            _signal(SignalDirection.BEARISH),
            _signal(SignalDirection.BULLISH),
        )
        assert collapse_signals(signals) is Decision.SELL

    def test_tie_is_hold(self) -> None:
        signals = (
            _signal(SignalDirection.BULLISH),
            _signal(SignalDirection.BEARISH),
        )
        assert collapse_signals(signals) is Decision.HOLD

    def test_all_neutral_is_hold(self) -> None:
        signals = (
            _signal(SignalDirection.NEUTRAL),
            _signal(SignalDirection.NEUTRAL),
        )
        assert collapse_signals(signals) is Decision.HOLD

    def test_empty_is_hold(self) -> None:
        assert collapse_signals(()) is Decision.HOLD


class TestAggregateRecommendations:
    """Equal-weight plurality voting (2- and 3-member)."""

    def test_buy_buy_is_buy(self) -> None:
        assert (
            aggregate_recommendations((Decision.BUY, Decision.BUY))
            is Decision.BUY
        )

    def test_sell_sell_is_sell(self) -> None:
        assert (
            aggregate_recommendations((Decision.SELL, Decision.SELL))
            is Decision.SELL
        )

    def test_hold_hold_is_hold(self) -> None:
        assert (
            aggregate_recommendations((Decision.HOLD, Decision.HOLD))
            is Decision.HOLD
        )

    def test_buy_sell_is_neutral(self) -> None:
        assert (
            aggregate_recommendations((Decision.BUY, Decision.SELL))
            is Decision.NEUTRAL
        )

    def test_buy_hold_is_hold(self) -> None:
        assert (
            aggregate_recommendations((Decision.BUY, Decision.HOLD))
            is Decision.HOLD
        )

    def test_sell_hold_is_hold(self) -> None:
        assert (
            aggregate_recommendations((Decision.SELL, Decision.HOLD))
            is Decision.HOLD
        )

    def test_buy_buy_buy(self) -> None:
        assert (
            aggregate_recommendations(
                (Decision.BUY, Decision.BUY, Decision.BUY)
            )
            is Decision.BUY
        )

    def test_buy_buy_hold_is_buy(self) -> None:
        assert (
            aggregate_recommendations(
                (Decision.BUY, Decision.BUY, Decision.HOLD)
            )
            is Decision.BUY
        )

    def test_sell_sell_hold_is_sell(self) -> None:
        assert (
            aggregate_recommendations(
                (Decision.SELL, Decision.SELL, Decision.HOLD)
            )
            is Decision.SELL
        )

    def test_buy_hold_hold_is_hold(self) -> None:
        assert (
            aggregate_recommendations(
                (Decision.BUY, Decision.HOLD, Decision.HOLD)
            )
            is Decision.HOLD
        )

    def test_sell_hold_hold_is_hold(self) -> None:
        assert (
            aggregate_recommendations(
                (Decision.SELL, Decision.HOLD, Decision.HOLD)
            )
            is Decision.HOLD
        )

    def test_buy_buy_sell_is_buy(self) -> None:
        assert (
            aggregate_recommendations(
                (Decision.BUY, Decision.BUY, Decision.SELL)
            )
            is Decision.BUY
        )

    def test_sell_sell_buy_is_sell(self) -> None:
        assert (
            aggregate_recommendations(
                (Decision.SELL, Decision.SELL, Decision.BUY)
            )
            is Decision.SELL
        )

    def test_buy_sell_hold_is_neutral(self) -> None:
        assert (
            aggregate_recommendations(
                (Decision.BUY, Decision.SELL, Decision.HOLD)
            )
            is Decision.NEUTRAL
        )

    def test_buy_sell_sell_is_sell(self) -> None:
        assert (
            aggregate_recommendations(
                (Decision.BUY, Decision.SELL, Decision.SELL)
            )
            is Decision.SELL
        )

    def test_empty_raises(self) -> None:
        with pytest.raises(ValueError, match="empty"):
            aggregate_recommendations(())

    def test_neutral_member_vote_raises(self) -> None:
        with pytest.raises(ValueError, match="NEUTRAL"):
            aggregate_recommendations((Decision.BUY, Decision.NEUTRAL))
