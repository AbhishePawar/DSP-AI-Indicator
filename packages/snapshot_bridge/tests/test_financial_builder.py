"""Tests for FinancialSnapshotBuilder."""

from __future__ import annotations

from datetime import date

import pytest

from contracts.domain.fundamental_statement import FundamentalStatement
from contracts.domain.instrument import Instrument
from contracts.enums import AssetClass, StatementPeriodType
from fundamental.models import FinancialSnapshot
from snapshot_bridge import FinancialSnapshotBuilder, SnapshotBridgeError


@pytest.fixture
def instrument() -> Instrument:
    return Instrument(symbol="AAPL", asset_class=AssetClass.EQUITY, currency="USD")


def _statement(
    instrument: Instrument,
    period_end: date,
    *,
    revenue: float | None = 100.0,
    net_income: float | None = 20.0,
    total_assets: float | None = 200.0,
    total_equity: float | None = 80.0,
    operating_income: float | None = 30.0,
    operating_cash_flow: float | None = 25.0,
) -> FundamentalStatement:
    return FundamentalStatement(
        instrument=instrument,
        period_end=period_end,
        period_type=StatementPeriodType.ANNUAL,
        fiscal_year=period_end.year,
        currency="USD",
        revenue=revenue,
        operating_income=operating_income,
        net_income=net_income,
        total_assets=total_assets,
        total_liabilities=120.0,
        total_equity=total_equity,
        operating_cash_flow=operating_cash_flow,
    )


class TestFinancialSnapshotBuilder:
    def test_orders_most_recent_first(self, instrument: Instrument) -> None:
        older = _statement(instrument, date(2022, 12, 31), revenue=90.0)
        newer = _statement(instrument, date(2023, 12, 31), revenue=100.0)
        snapshot = FinancialSnapshotBuilder.build(instrument, (older, newer))

        assert isinstance(snapshot, FinancialSnapshot)
        assert snapshot.latest.period_end == date(2023, 12, 31)
        assert snapshot.previous is not None
        assert snapshot.previous.period_end == date(2022, 12, 31)
        assert snapshot.latest.revenue == pytest.approx(100.0)
        assert snapshot.latest.net_income == pytest.approx(20.0)
        assert snapshot.latest.total_assets == pytest.approx(200.0)
        assert snapshot.latest.operating_cash_flow == pytest.approx(25.0)

    def test_preserves_line_items_for_engine_analyzers(
        self, instrument: Instrument
    ) -> None:
        statement = _statement(instrument, date(2023, 12, 31))
        snapshot = FinancialSnapshotBuilder.build(instrument, (statement,))
        latest = snapshot.latest
        assert latest.operating_income == pytest.approx(30.0)
        assert latest.total_equity == pytest.approx(80.0)
        assert latest.total_liabilities == pytest.approx(120.0)

    def test_empty_raises(self, instrument: Instrument) -> None:
        with pytest.raises(SnapshotBridgeError):
            FinancialSnapshotBuilder.build(instrument, ())

    def test_mismatched_instrument_raises(self, instrument: Instrument) -> None:
        other = Instrument(
            symbol="MSFT", asset_class=AssetClass.EQUITY, currency="USD"
        )
        with pytest.raises(SnapshotBridgeError):
            FinancialSnapshotBuilder.build(
                instrument, (_statement(other, date(2023, 12, 31)),)
            )

    def test_deterministic(self, instrument: Instrument) -> None:
        statements = (
            _statement(instrument, date(2022, 12, 31)),
            _statement(instrument, date(2023, 12, 31)),
        )
        assert FinancialSnapshotBuilder.build(
            instrument, statements
        ) == FinancialSnapshotBuilder.build(instrument, statements)
