"""Tests for the PriceSeries domain contract."""

from datetime import UTC, datetime, timedelta

import pytest

from contracts.domain.instrument import Instrument
from contracts.domain.price_bar import PriceBar
from contracts.domain.price_series import PriceSeries
from contracts.enums import BarFrequency
from contracts.exceptions import ContractValidationError


def _bar(day_offset: int) -> PriceBar:
    timestamp = datetime(2026, 1, 1, tzinfo=UTC) + timedelta(days=day_offset)
    price = 100.0 + day_offset
    return PriceBar(
        timestamp=timestamp,
        open=price,
        high=price + 1,
        low=price - 1,
        close=price,
        volume=1.0,
    )


class TestPriceSeries:
    """Tests for PriceSeries construction and ordering validation."""

    def test_valid_series(self, instrument: Instrument) -> None:
        bars = tuple(_bar(i) for i in range(5))
        series = PriceSeries(
            instrument=instrument, frequency=BarFrequency.DAILY, bars=bars
        )
        assert series.length == 5
        assert series.start == bars[0]
        assert series.end == bars[-1]

    def test_empty_bars_raises(self, instrument: Instrument) -> None:
        with pytest.raises(ContractValidationError, match="empty"):
            PriceSeries(instrument=instrument, frequency=BarFrequency.DAILY, bars=())

    def test_unsorted_bars_raises(self, instrument: Instrument) -> None:
        bars = (_bar(1), _bar(0), _bar(2))
        with pytest.raises(ContractValidationError, match="ascending"):
            PriceSeries(
                instrument=instrument, frequency=BarFrequency.DAILY, bars=bars
            )

    def test_duplicate_timestamps_raises(self, instrument: Instrument) -> None:
        bars = (_bar(0), _bar(0))
        with pytest.raises(ContractValidationError, match="duplicate"):
            PriceSeries(
                instrument=instrument, frequency=BarFrequency.DAILY, bars=bars
            )

    def test_bars_stored_as_tuple(self, instrument: Instrument) -> None:
        bars = [_bar(0), _bar(1)]
        series = PriceSeries(
            instrument=instrument, frequency=BarFrequency.DAILY, bars=bars
        )
        assert isinstance(series.bars, tuple)

    def test_immutable(self, instrument: Instrument) -> None:
        bars = (_bar(0), _bar(1))
        series = PriceSeries(
            instrument=instrument, frequency=BarFrequency.DAILY, bars=bars
        )
        with pytest.raises(AttributeError):
            series.bars = ()  # type: ignore[misc]

    def test_single_bar_series_is_valid(self, instrument: Instrument) -> None:
        series = PriceSeries(
            instrument=instrument, frequency=BarFrequency.DAILY, bars=(_bar(0),)
        )
        assert series.length == 1
        assert series.start is series.end
