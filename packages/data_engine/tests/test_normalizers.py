"""Tests for data_engine.normalization.normalizers and .defaults."""

from datetime import UTC, datetime

import pytest

from contracts.domain.instrument import Instrument
from contracts.enums import AssetClass, BarFrequency
from data_engine.exceptions import InvalidProviderDataError, MissingFieldError
from data_engine.normalization import (
    AlternativeDataNormalizer,
    DefaultMarketDataNormalizer,
    EconomicDataNormalizer,
    FundamentalNormalizer,
    MarketDataNormalizer,
)
from data_engine.raw_models import RawMarketBar, RawMarketSeries


class TestAbstractNormalizers:
    """Every abstract normalizer interface should refuse direct instantiation."""

    @pytest.mark.parametrize(
        "normalizer_cls",
        [
            MarketDataNormalizer,
            FundamentalNormalizer,
            EconomicDataNormalizer,
            AlternativeDataNormalizer,
        ],
    )
    def test_cannot_be_instantiated_directly(self, normalizer_cls: type) -> None:
        with pytest.raises(TypeError):
            normalizer_cls()  # type: ignore[abstract]


class TestDefaultMarketDataNormalizer:
    """Tests for the concrete, provider-agnostic DefaultMarketDataNormalizer."""

    def _instrument(self) -> Instrument:
        return Instrument(symbol="AAPL", asset_class=AssetClass.EQUITY, currency="USD")

    def _raw_bar(self, **overrides: object) -> RawMarketBar:
        defaults: dict[str, object] = {
            "provider_id": "fake_vendor",
            "timestamp": "2026-01-02T00:00:00+00:00",
            "open": "100.0",
            "high": "101.0",
            "low": "99.0",
            "close": "100.5",
            "volume": "1000",
        }
        defaults.update(overrides)
        return RawMarketBar(**defaults)  # type: ignore[arg-type]

    def test_is_a_market_data_normalizer(self) -> None:
        normalizer = DefaultMarketDataNormalizer(frequency=BarFrequency.DAILY)
        assert isinstance(normalizer, MarketDataNormalizer)

    def test_normalizes_well_formed_raw_series_into_price_series(self) -> None:
        normalizer = DefaultMarketDataNormalizer(frequency=BarFrequency.DAILY)
        raw = RawMarketSeries(
            provider_id="fake_vendor", symbol="AAPL", bars=(self._raw_bar(),)
        )

        series = normalizer.normalize(raw, self._instrument())

        assert series.frequency is BarFrequency.DAILY
        assert series.instrument.symbol == "AAPL"
        assert series.length == 1
        bar = series.bars[0]
        assert bar.timestamp == datetime(2026, 1, 2, tzinfo=UTC)
        assert bar.open == 100.0
        assert bar.high == 101.0
        assert bar.low == 99.0
        assert bar.close == 100.5
        assert bar.volume == 1000.0

    def test_defaults_missing_volume_to_zero(self) -> None:
        normalizer = DefaultMarketDataNormalizer(frequency=BarFrequency.DAILY)
        raw = RawMarketSeries(
            provider_id="fake_vendor",
            symbol="AAPL",
            bars=(self._raw_bar(volume=None),),
        )
        series = normalizer.normalize(raw, self._instrument())
        assert series.bars[0].volume == 0.0

    def test_raises_missing_field_error_for_missing_required_field(self) -> None:
        normalizer = DefaultMarketDataNormalizer(frequency=BarFrequency.DAILY)
        raw = RawMarketSeries(
            provider_id="fake_vendor",
            symbol="AAPL",
            bars=(self._raw_bar(close=None),),
        )
        with pytest.raises(MissingFieldError):
            normalizer.normalize(raw, self._instrument())

    def test_raises_invalid_provider_data_error_for_non_numeric_price(self) -> None:
        normalizer = DefaultMarketDataNormalizer(frequency=BarFrequency.DAILY)
        raw = RawMarketSeries(
            provider_id="fake_vendor",
            symbol="AAPL",
            bars=(self._raw_bar(open="not-a-number"),),
        )
        with pytest.raises(InvalidProviderDataError):
            normalizer.normalize(raw, self._instrument())

    def test_raises_invalid_provider_data_error_for_ohlc_violation(self) -> None:
        normalizer = DefaultMarketDataNormalizer(frequency=BarFrequency.DAILY)
        raw = RawMarketSeries(
            provider_id="fake_vendor",
            symbol="AAPL",
            bars=(self._raw_bar(high="90.0"),),
        )
        with pytest.raises(InvalidProviderDataError):
            normalizer.normalize(raw, self._instrument())

    def test_raises_invalid_provider_data_error_for_duplicate_timestamps(self) -> None:
        normalizer = DefaultMarketDataNormalizer(frequency=BarFrequency.DAILY)
        raw = RawMarketSeries(
            provider_id="fake_vendor",
            symbol="AAPL",
            bars=(self._raw_bar(), self._raw_bar()),
        )
        with pytest.raises(InvalidProviderDataError):
            normalizer.normalize(raw, self._instrument())

    def test_raises_invalid_provider_data_error_for_out_of_order_bars(self) -> None:
        normalizer = DefaultMarketDataNormalizer(frequency=BarFrequency.DAILY)
        raw = RawMarketSeries(
            provider_id="fake_vendor",
            symbol="AAPL",
            bars=(
                self._raw_bar(timestamp="2026-01-02T00:00:00+00:00"),
                self._raw_bar(timestamp="2026-01-01T00:00:00+00:00"),
            ),
        )
        with pytest.raises(InvalidProviderDataError):
            normalizer.normalize(raw, self._instrument())

    def test_raises_invalid_provider_data_error_for_negative_volume(self) -> None:
        normalizer = DefaultMarketDataNormalizer(frequency=BarFrequency.DAILY)
        raw = RawMarketSeries(
            provider_id="fake_vendor",
            symbol="AAPL",
            bars=(self._raw_bar(volume="-5"),),
        )
        with pytest.raises(InvalidProviderDataError):
            normalizer.normalize(raw, self._instrument())

    def test_multi_bar_series_normalizes_in_chronological_order(self) -> None:
        normalizer = DefaultMarketDataNormalizer(frequency=BarFrequency.DAILY)
        raw = RawMarketSeries(
            provider_id="fake_vendor",
            symbol="AAPL",
            bars=(
                self._raw_bar(timestamp="2026-01-01T00:00:00+00:00"),
                self._raw_bar(timestamp="2026-01-02T00:00:00+00:00"),
            ),
        )
        series = normalizer.normalize(raw, self._instrument())
        assert series.length == 2
        assert series.start.timestamp < series.end.timestamp
