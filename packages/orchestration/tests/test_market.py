"""Unit tests for market-cap → MarketSnapshot resolution."""

from __future__ import annotations

from datetime import date

import pytest

from contracts.domain.fundamental_statement import FundamentalStatement
from contracts.domain.instrument import Instrument
from contracts.domain.margin_of_safety import MARKET_CAPITALIZATION_KEY
from contracts.enums import AssetClass, StatementPeriodType
from fundamental.models import FinancialSnapshot
from orchestration.market import resolve_market_snapshot
from orchestration.models import AnalysisRequest


@pytest.fixture
def instrument() -> Instrument:
    return Instrument(symbol="AAPL", asset_class=AssetClass.EQUITY, currency="USD")


def _snapshot(
    instrument: Instrument, *, market_cap: float | None = None
) -> FinancialSnapshot:
    extras: tuple[tuple[str, float], ...] = ()
    if market_cap is not None:
        extras = ((MARKET_CAPITALIZATION_KEY, market_cap),)
    statement = FundamentalStatement(
        instrument=instrument,
        period_end=date(2023, 12, 31),
        period_type=StatementPeriodType.ANNUAL,
        fiscal_year=2023,
        currency="USD",
        revenue=100.0,
        extra_line_items=extras,
    )
    return FinancialSnapshot(instrument=instrument, statements=(statement,))


class TestResolveMarketSnapshot:
    def test_request_override_wins(self, instrument: Instrument) -> None:
        request = AnalysisRequest(
            instrument=instrument,
            start=date(2024, 1, 1),
            end=date(2024, 6, 1),
            market_cap=123.0,
        )
        market = resolve_market_snapshot(request, _snapshot(instrument, market_cap=999.0))
        assert market is not None
        assert market.market_cap == pytest.approx(123.0)

    def test_reads_extras(self, instrument: Instrument) -> None:
        request = AnalysisRequest(
            instrument=instrument,
            start=date(2024, 1, 1),
            end=date(2024, 6, 1),
        )
        market = resolve_market_snapshot(request, _snapshot(instrument, market_cap=456.0))
        assert market is not None
        assert market.market_cap == pytest.approx(456.0)

    def test_missing_returns_none(self, instrument: Instrument) -> None:
        request = AnalysisRequest(
            instrument=instrument,
            start=date(2024, 1, 1),
            end=date(2024, 6, 1),
        )
        assert resolve_market_snapshot(request, _snapshot(instrument)) is None
