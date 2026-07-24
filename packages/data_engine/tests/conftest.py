"""Shared pytest fixtures for Data Engine tests."""

from datetime import UTC, date, datetime

import pytest

from contracts.domain.instrument import Instrument
from contracts.domain.price_bar import PriceBar
from contracts.domain.price_series import PriceSeries
from contracts.enums import AssetClass, BarFrequency


@pytest.fixture
def instrument() -> Instrument:
    """Return a representative equity instrument."""
    return Instrument(symbol="aapl", asset_class=AssetClass.EQUITY, currency="usd")


@pytest.fixture
def sample_price_series(instrument: Instrument) -> PriceSeries:
    """Return a minimal, valid price series for the sample instrument."""
    bar = PriceBar(
        timestamp=datetime(2026, 1, 2, tzinfo=UTC),
        open=100.0,
        high=101.0,
        low=99.0,
        close=100.5,
        volume=1_000.0,
    )
    return PriceSeries(
        instrument=instrument, frequency=BarFrequency.DAILY, bars=(bar,)
    )


@pytest.fixture
def date_range() -> tuple[date, date]:
    """Return a representative (start, end) date range."""
    return date(2026, 1, 1), date(2026, 1, 31)
