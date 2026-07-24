"""Tests for AnalysisRequest and public API."""

from __future__ import annotations

from datetime import date

import pytest

from contracts.domain.instrument import Instrument
from contracts.enums import AssetClass
from orchestration import (
    AnalysisRequest,
    InvestmentAnalysisService,
    OrchestrationError,
)


@pytest.fixture
def instrument() -> Instrument:
    return Instrument(symbol="AAPL", asset_class=AssetClass.EQUITY, currency="USD")


class TestPublicApi:
    def test_exports(self) -> None:
        assert AnalysisRequest is not None
        assert InvestmentAnalysisService is not None
        assert issubclass(OrchestrationError, Exception)


class TestAnalysisRequest:
    def test_valid(self, instrument: Instrument) -> None:
        request = AnalysisRequest(
            instrument=instrument,
            start=date(2024, 1, 1),
            end=date(2024, 6, 1),
        )
        assert request.include_fundamentals is True
        assert request.allow_partial is True

    def test_start_after_end_raises(self, instrument: Instrument) -> None:
        with pytest.raises(OrchestrationError, match="start"):
            AnalysisRequest(
                instrument=instrument,
                start=date(2024, 6, 1),
                end=date(2024, 1, 1),
            )

    def test_negative_limit_raises(self, instrument: Instrument) -> None:
        with pytest.raises(OrchestrationError, match="fundamentals_limit"):
            AnalysisRequest(
                instrument=instrument,
                start=date(2024, 1, 1),
                end=date(2024, 6, 1),
                fundamentals_limit=-1,
            )

    def test_negative_market_cap_raises(self, instrument: Instrument) -> None:
        with pytest.raises(OrchestrationError, match="market_cap"):
            AnalysisRequest(
                instrument=instrument,
                start=date(2024, 1, 1),
                end=date(2024, 6, 1),
                market_cap=-1.0,
            )
