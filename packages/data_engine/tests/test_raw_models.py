"""Tests for data_engine.raw_models."""

from data_engine.raw_models import (
    RawAlternativeData,
    RawEconomicDataPoint,
    RawEconomicSeries,
    RawFundamentalData,
    RawMarketBar,
    RawMarketSeries,
)


class TestRawMarketBar:
    """Tests for the RawMarketBar container."""

    def test_accepts_arbitrary_raw_values(self) -> None:
        bar = RawMarketBar(
            provider_id="fake_vendor",
            timestamp="2026-01-02",
            open="100.5",
            high=101,
            low=99.0,
            close=None,
            volume="N/A",
        )
        assert bar.timestamp == "2026-01-02"
        assert bar.open == "100.5"
        assert bar.close is None
        assert bar.volume == "N/A"

    def test_extra_is_read_only(self) -> None:
        bar = RawMarketBar(
            provider_id="fake_vendor",
            timestamp="2026-01-02",
            open=1,
            high=1,
            low=1,
            close=1,
            extra={"note": "adjusted for split"},
        )
        assert bar.extra["note"] == "adjusted for split"
        try:
            bar.extra["note"] = "changed"  # type: ignore[index]
        except TypeError:
            pass
        else:
            raise AssertionError("extra should be read-only")


class TestRawMarketSeries:
    """Tests for the RawMarketSeries container."""

    def test_bars_are_frozen_into_a_tuple(self) -> None:
        bar = RawMarketBar(
            provider_id="fake_vendor",
            timestamp="2026-01-02",
            open=1,
            high=1,
            low=1,
            close=1,
        )
        series = RawMarketSeries(provider_id="fake_vendor", symbol="AAPL", bars=[bar])
        assert series.bars == (bar,)

    def test_permits_out_of_order_and_duplicate_bars(self) -> None:
        bar_a = RawMarketBar(
            provider_id="fake_vendor",
            timestamp="2026-01-02",
            open=1,
            high=1,
            low=1,
            close=1,
        )
        bar_b = RawMarketBar(
            provider_id="fake_vendor",
            timestamp="2026-01-01",
            open=2,
            high=2,
            low=2,
            close=2,
        )
        series = RawMarketSeries(
            provider_id="fake_vendor", symbol="AAPL", bars=(bar_a, bar_b, bar_a)
        )
        assert series.bars == (bar_a, bar_b, bar_a)


class TestRawFundamentalData:
    """Tests for the RawFundamentalData container."""

    def test_line_items_are_read_only(self) -> None:
        raw = RawFundamentalData(
            provider_id="fake_vendor",
            symbol="AAPL",
            period_end="2025-12-31",
            period_type="FY",
            line_items={"totalRevenue": "394328000000"},
        )
        assert raw.line_items["totalRevenue"] == "394328000000"
        try:
            raw.line_items["totalRevenue"] = "0"  # type: ignore[index]
        except TypeError:
            pass
        else:
            raise AssertionError("line_items should be read-only")


class TestRawEconomicSeries:
    """Tests for the RawEconomicSeries container."""

    def test_points_are_frozen_into_a_tuple(self) -> None:
        point = RawEconomicDataPoint(observation_date="2026-01-01", value="3.1")
        series = RawEconomicSeries(
            provider_id="fake_vendor",
            indicator_code="CPI",
            country="US",
            points=[point],
        )
        assert series.points == (point,)


class TestRawAlternativeData:
    """Tests for the RawAlternativeData container."""

    def test_accepts_arbitrary_raw_values(self) -> None:
        raw = RawAlternativeData(
            provider_id="fake_vendor",
            symbol="AAPL",
            signal_name="social_sentiment",
            timestamp="2026-01-02",
            value=0.73,
        )
        assert raw.signal_name == "social_sentiment"
        assert raw.value == 0.73
