"""Shared fixtures for Economic Engine tests."""

from __future__ import annotations

from datetime import date

import pytest

from economic.models import EconomicSnapshot


@pytest.fixture
def snapshot_factory():
    """Factory for EconomicSnapshot with overridable defaults."""

    def _factory(**overrides) -> EconomicSnapshot:
        values = {
            "as_of": date(2024, 6, 15),
            "gdp_growth": 0.025,
            "cpi_inflation": 0.025,
            "interest_rate": 0.04,
            "interest_rate_change": 0.0,
            "unemployment": 0.04,
            "pmi": 52.0,
            "currency_trend": 0.0,
            "liquidity_indicator": 0.5,
            "country": "US",
        }
        values.update(overrides)
        return EconomicSnapshot(**values)

    return _factory
