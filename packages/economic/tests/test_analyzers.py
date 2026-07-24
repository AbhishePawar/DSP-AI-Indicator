"""Tests for individual economic analyzers."""

from __future__ import annotations

from contracts.enums import SignalDirection

from economic.analyzers import (
    GdpAnalyzer,
    InflationAnalyzer,
    InterestRateAnalyzer,
    LiquidityAnalyzer,
    PmiAnalyzer,
)


class TestGdpAnalyzer:
    """GDP growth rules."""

    def test_name(self) -> None:
        assert GdpAnalyzer().name == "gdp"

    def test_strong_is_bullish(self, snapshot_factory) -> None:
        signal = GdpAnalyzer().analyze(
            snapshot_factory(gdp_growth=0.04)
        )[0]
        assert signal.direction is SignalDirection.BULLISH
        assert signal.observation == "Strong GDP Growth"

    def test_moderate_is_neutral(self, snapshot_factory) -> None:
        signal = GdpAnalyzer().analyze(
            snapshot_factory(gdp_growth=0.02)
        )[0]
        assert signal.direction is SignalDirection.NEUTRAL

    def test_weak_is_bearish(self, snapshot_factory) -> None:
        signal = GdpAnalyzer().analyze(
            snapshot_factory(gdp_growth=0.005)
        )[0]
        assert signal.direction is SignalDirection.BEARISH

    def test_missing_is_neutral(self, snapshot_factory) -> None:
        signal = GdpAnalyzer().analyze(
            snapshot_factory(gdp_growth=None)
        )[0]
        assert signal.direction is SignalDirection.NEUTRAL


class TestInflationAnalyzer:
    """CPI inflation rules."""

    def test_name(self) -> None:
        assert InflationAnalyzer().name == "inflation"

    def test_missing_is_neutral(self, snapshot_factory) -> None:
        signal = InflationAnalyzer().analyze(
            snapshot_factory(cpi_inflation=None)
        )[0]
        assert signal.direction is SignalDirection.NEUTRAL

    def test_low_is_bullish(self, snapshot_factory) -> None:
        signal = InflationAnalyzer().analyze(
            snapshot_factory(cpi_inflation=0.015)
        )[0]
        assert signal.direction is SignalDirection.BULLISH
        assert signal.observation == "Low Inflation"

    def test_moderate_is_neutral(self, snapshot_factory) -> None:
        signal = InflationAnalyzer().analyze(
            snapshot_factory(cpi_inflation=0.03)
        )[0]
        assert signal.direction is SignalDirection.NEUTRAL

    def test_high_is_bearish(self, snapshot_factory) -> None:
        signal = InflationAnalyzer().analyze(
            snapshot_factory(cpi_inflation=0.06)
        )[0]
        assert signal.direction is SignalDirection.BEARISH
        assert signal.observation == "High Inflation"


class TestInterestRateAnalyzer:
    """Interest-rate level and change rules."""

    def test_name(self) -> None:
        assert InterestRateAnalyzer().name == "interest_rate"

    def test_missing_rate_is_neutral(self, snapshot_factory) -> None:
        signal = InterestRateAnalyzer().analyze(
            snapshot_factory(
                interest_rate=None,
                interest_rate_change=None,
            )
        )[0]
        assert signal.direction is SignalDirection.NEUTRAL

    def test_rapid_hike_is_bearish(self, snapshot_factory) -> None:
        signal = InterestRateAnalyzer().analyze(
            snapshot_factory(
                interest_rate=0.03,
                interest_rate_change=0.01,
            )
        )[0]
        assert signal.direction is SignalDirection.BEARISH
        assert signal.observation == "Rapid Rate Hikes"

    def test_easing_is_bullish(self, snapshot_factory) -> None:
        signal = InterestRateAnalyzer().analyze(
            snapshot_factory(interest_rate_change=-0.005)
        )[0]
        assert signal.direction is SignalDirection.BULLISH

    def test_accommodative_level_is_bullish(self, snapshot_factory) -> None:
        signal = InterestRateAnalyzer().analyze(
            snapshot_factory(
                interest_rate=0.02,
                interest_rate_change=0.0,
            )
        )[0]
        assert signal.direction is SignalDirection.BULLISH

    def test_stable_rates_are_neutral(self, snapshot_factory) -> None:
        signal = InterestRateAnalyzer().analyze(
            snapshot_factory(
                interest_rate=0.04,
                interest_rate_change=0.0,
            )
        )[0]
        assert signal.direction is SignalDirection.NEUTRAL
        assert signal.observation == "Stable Rates"

    def test_restrictive_is_bearish(self, snapshot_factory) -> None:
        signal = InterestRateAnalyzer().analyze(
            snapshot_factory(
                interest_rate=0.07,
                interest_rate_change=0.0,
            )
        )[0]
        assert signal.direction is SignalDirection.BEARISH


class TestPmiAnalyzer:
    """PMI index rules."""

    def test_name(self) -> None:
        assert PmiAnalyzer().name == "pmi"

    def test_missing_is_neutral(self, snapshot_factory) -> None:
        signal = PmiAnalyzer().analyze(snapshot_factory(pmi=None))[0]
        assert signal.direction is SignalDirection.NEUTRAL

    def test_strong_expansion(self, snapshot_factory) -> None:
        signal = PmiAnalyzer().analyze(snapshot_factory(pmi=58.0))[0]
        assert signal.direction is SignalDirection.BULLISH

    def test_expansion(self, snapshot_factory) -> None:
        signal = PmiAnalyzer().analyze(snapshot_factory(pmi=51.0))[0]
        assert signal.direction is SignalDirection.BULLISH

    def test_soft(self, snapshot_factory) -> None:
        signal = PmiAnalyzer().analyze(snapshot_factory(pmi=47.0))[0]
        assert signal.direction is SignalDirection.NEUTRAL

    def test_contraction(self, snapshot_factory) -> None:
        signal = PmiAnalyzer().analyze(snapshot_factory(pmi=42.0))[0]
        assert signal.direction is SignalDirection.BEARISH


class TestLiquidityAnalyzer:
    """Liquidity indicator rules."""

    def test_name(self) -> None:
        assert LiquidityAnalyzer().name == "liquidity"

    def test_missing_is_neutral(self, snapshot_factory) -> None:
        signal = LiquidityAnalyzer().analyze(
            snapshot_factory(liquidity_indicator=None)
        )[0]
        assert signal.direction is SignalDirection.NEUTRAL

    def test_ample(self, snapshot_factory) -> None:
        signal = LiquidityAnalyzer().analyze(
            snapshot_factory(liquidity_indicator=0.8)
        )[0]
        assert signal.direction is SignalDirection.BULLISH

    def test_adequate(self, snapshot_factory) -> None:
        signal = LiquidityAnalyzer().analyze(
            snapshot_factory(liquidity_indicator=0.5)
        )[0]
        assert signal.direction is SignalDirection.NEUTRAL

    def test_tight(self, snapshot_factory) -> None:
        signal = LiquidityAnalyzer().analyze(
            snapshot_factory(liquidity_indicator=0.2)
        )[0]
        assert signal.direction is SignalDirection.BEARISH
