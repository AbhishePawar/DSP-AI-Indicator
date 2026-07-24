"""Shared pytest fixtures for Contracts package tests."""

from datetime import UTC, datetime

import pytest

from contracts.domain.instrument import Instrument
from contracts.enums import AssetClass, EngineSource


@pytest.fixture
def instrument() -> Instrument:
    """Return a representative equity instrument."""
    return Instrument(
        symbol="aapl",
        asset_class=AssetClass.EQUITY,
        currency="usd",
        name="Apple Inc.",
        exchange="NASDAQ",
        sector="Technology",
    )


@pytest.fixture
def utc_now() -> datetime:
    """Return a fixed, timezone-aware reference timestamp."""
    return datetime(2026, 1, 15, 12, 0, tzinfo=UTC)


@pytest.fixture
def source_engine() -> EngineSource:
    """Return a representative source engine tag."""
    return EngineSource.INDICATOR_ENGINE
