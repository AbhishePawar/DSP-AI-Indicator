"""Tests for the PriceBar domain contract."""

from datetime import UTC, datetime

import pytest

from contracts.domain.price_bar import PriceBar
from contracts.exceptions import ContractValidationError


class TestPriceBar:
    """Tests for PriceBar construction and structural validation."""

    def test_valid_bar(self, utc_now: datetime) -> None:
        bar = PriceBar(
            timestamp=utc_now,
            open=100.0,
            high=105.0,
            low=99.0,
            close=103.0,
            volume=1_000_000.0,
        )
        assert bar.close == 103.0
        assert bar.adjusted_close is None

    def test_adjusted_close_optional(self, utc_now: datetime) -> None:
        bar = PriceBar(
            timestamp=utc_now,
            open=100.0,
            high=105.0,
            low=99.0,
            close=103.0,
            volume=1_000_000.0,
            adjusted_close=102.5,
        )
        assert bar.adjusted_close == 102.5

    def test_negative_adjusted_close_raises(self, utc_now: datetime) -> None:
        with pytest.raises(ContractValidationError, match="adjusted_close"):
            PriceBar(
                timestamp=utc_now,
                open=100.0,
                high=105.0,
                low=99.0,
                close=103.0,
                volume=1_000_000.0,
                adjusted_close=-1.0,
            )

    def test_low_greater_than_high_raises(self, utc_now: datetime) -> None:
        with pytest.raises(ContractValidationError, match="low"):
            PriceBar(
                timestamp=utc_now,
                open=100.0,
                high=90.0,
                low=95.0,
                close=92.0,
                volume=1.0,
            )

    def test_open_outside_range_raises(self, utc_now: datetime) -> None:
        with pytest.raises(ContractValidationError, match="open"):
            PriceBar(
                timestamp=utc_now,
                open=110.0,
                high=105.0,
                low=99.0,
                close=103.0,
                volume=1.0,
            )

    def test_close_outside_range_raises(self, utc_now: datetime) -> None:
        with pytest.raises(ContractValidationError, match="close"):
            PriceBar(
                timestamp=utc_now,
                open=100.0,
                high=105.0,
                low=99.0,
                close=110.0,
                volume=1.0,
            )

    def test_negative_volume_raises(self, utc_now: datetime) -> None:
        with pytest.raises(ContractValidationError, match="volume"):
            PriceBar(
                timestamp=utc_now,
                open=100.0,
                high=105.0,
                low=99.0,
                close=103.0,
                volume=-5.0,
            )

    def test_negative_price_raises(self, utc_now: datetime) -> None:
        with pytest.raises(ContractValidationError, match="non-negative"):
            PriceBar(
                timestamp=utc_now,
                open=-1.0,
                high=105.0,
                low=-2.0,
                close=103.0,
                volume=1.0,
            )

    def test_naive_timestamp_raises(self) -> None:
        naive = datetime(2026, 1, 15, 12, 0)
        with pytest.raises(ContractValidationError, match="timezone-aware"):
            PriceBar(
                timestamp=naive,
                open=100.0,
                high=105.0,
                low=99.0,
                close=103.0,
                volume=1.0,
            )

    def test_non_finite_price_raises(self, utc_now: datetime) -> None:
        with pytest.raises(ContractValidationError, match="finite"):
            PriceBar(
                timestamp=utc_now,
                open=float("nan"),
                high=105.0,
                low=99.0,
                close=103.0,
                volume=1.0,
            )

    def test_immutable(self, utc_now: datetime) -> None:
        bar = PriceBar(
            timestamp=utc_now,
            open=100.0,
            high=105.0,
            low=99.0,
            close=103.0,
            volume=1.0,
        )
        with pytest.raises(AttributeError):
            bar.close = 200.0  # type: ignore[misc]

    def test_flat_bar_where_all_prices_equal(self, utc_now: datetime) -> None:
        bar = PriceBar(
            timestamp=utc_now, open=50.0, high=50.0, low=50.0, close=50.0, volume=0.0
        )
        assert bar.high == bar.low == bar.open == bar.close == 50.0
        assert bar.volume == 0.0

    def test_timestamp_defaults_to_utc_fixture(self, utc_now: datetime) -> None:
        assert utc_now.tzinfo is UTC
