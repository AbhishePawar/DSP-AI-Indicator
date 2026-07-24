"""Shared pytest fixtures for indicator tests."""

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

import numpy as np
import pytest

from contracts.domain.instrument import Instrument
from contracts.domain.price_bar import PriceBar
from contracts.domain.price_series import PriceSeries
from contracts.enums import AssetClass, BarFrequency


def make_price_series(
    closes: Sequence[float], *, symbol: str = "TEST"
) -> PriceSeries:
    """Build a daily ``PriceSeries`` whose closes are exactly ``closes``.

    Each bar's open/high/low are derived from the close so every bar
    passes ``PriceBar``'s OHLC structural validation, and volume is a
    fixed placeholder since no test in this package depends on it.
    """
    instrument = Instrument(
        symbol=symbol, asset_class=AssetClass.EQUITY, currency="USD"
    )
    start = datetime(2024, 1, 1, tzinfo=UTC)
    bars = tuple(
        PriceBar(
            timestamp=start + timedelta(days=index),
            open=close,
            high=close,
            low=close,
            close=close,
            volume=1_000.0,
        )
        for index, close in enumerate(closes)
    )
    return PriceSeries(instrument=instrument, frequency=BarFrequency.DAILY, bars=bars)


@pytest.fixture
def price_series_factory():
    """Return ``make_price_series`` as an injectable pytest fixture.

    Exposed as a fixture (rather than requiring test modules to import
    ``conftest`` directly) so every test file can build a
    ``contracts.PriceSeries`` without depending on cross-test-file
    imports.
    """
    return make_price_series


@pytest.fixture
def sample_prices() -> np.ndarray:
    """Return a representative price series for indicator testing."""
    return np.array(
        [44.0, 44.34, 44.09, 43.61, 44.33, 44.83, 45.10, 45.42, 45.84, 46.08],
        dtype=np.float64,
    )


@pytest.fixture
def monotonic_up() -> np.ndarray:
    """Return a strictly increasing price series."""
    return np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0], dtype=np.float64)


@pytest.fixture
def monotonic_down() -> np.ndarray:
    """Return a strictly decreasing price series."""
    return np.array([8.0, 7.0, 6.0, 5.0, 4.0, 3.0, 2.0, 1.0], dtype=np.float64)


@pytest.fixture
def constant_prices() -> np.ndarray:
    """Return a flat price series."""
    return np.array([50.0, 50.0, 50.0, 50.0, 50.0], dtype=np.float64)


@pytest.fixture
def simple_prices() -> np.ndarray:
    """Return a small integer price series for hand-verified calculations."""
    return np.array([1.0, 2.0, 3.0, 4.0, 5.0], dtype=np.float64)
