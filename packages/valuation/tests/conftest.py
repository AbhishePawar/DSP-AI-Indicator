"""Shared fixtures for valuation engine tests."""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from contracts.domain.fundamental_statement import FundamentalStatement
from contracts.domain.instrument import Instrument
from contracts.enums import AssetClass, StatementPeriodType
from fundamental.models import FinancialSnapshot

FIXED_NOW = datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)


@pytest.fixture
def instrument() -> Instrument:
    return Instrument(symbol="AAPL", asset_class=AssetClass.EQUITY, currency="USD")


def make_statement(
    instrument: Instrument,
    *,
    fiscal_year: int = 2023,
    period_end: date = date(2023, 12, 31),
    net_income: float | None = 100.0,
    total_equity: float | None = 500.0,
    operating_cash_flow: float | None = 180.0,
    capital_expenditures: float | None = 40.0,
    **kwargs: float | None,
) -> FundamentalStatement:
    return FundamentalStatement(
        instrument=instrument,
        period_end=period_end,
        period_type=StatementPeriodType.ANNUAL,
        fiscal_year=fiscal_year,
        currency="USD",
        net_income=net_income,
        total_equity=total_equity,
        operating_cash_flow=operating_cash_flow,
        capital_expenditures=capital_expenditures,
        **kwargs,
    )


@pytest.fixture
def snapshot(instrument: Instrument) -> FinancialSnapshot:
    return FinancialSnapshot(
        instrument=instrument,
        statements=(make_statement(instrument),),
    )


@pytest.fixture
def sparse_snapshot(instrument: Instrument) -> FinancialSnapshot:
    """Only book equity — most methods should disable gracefully."""
    return FinancialSnapshot(
        instrument=instrument,
        statements=(
            make_statement(
                instrument,
                net_income=None,
                operating_cash_flow=None,
                capital_expenditures=None,
                total_equity=500.0,
            ),
        ),
    )


@pytest.fixture
def empty_inputs_snapshot(instrument: Instrument) -> FinancialSnapshot:
    return FinancialSnapshot(
        instrument=instrument,
        statements=(
            make_statement(
                instrument,
                net_income=None,
                total_equity=None,
                operating_cash_flow=None,
                capital_expenditures=None,
            ),
        ),
    )
