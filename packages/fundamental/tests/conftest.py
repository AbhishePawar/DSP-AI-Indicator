"""Shared pytest fixtures for fundamental engine tests."""

from collections.abc import Sequence
from datetime import date

import pytest

from contracts.domain.fundamental_statement import FundamentalStatement
from contracts.domain.instrument import Instrument
from contracts.enums import AssetClass, StatementPeriodType
from fundamental.models import FinancialSnapshot


def make_statement(
    *,
    symbol: str = "TEST",
    fiscal_year: int = 2024,
    period_end: date = date(2024, 12, 31),
    revenue: float | None = 1_000.0,
    cost_of_revenue: float | None = None,
    gross_profit: float | None = None,
    operating_income: float | None = 150.0,
    net_income: float | None = 100.0,
    eps_basic: float | None = None,
    eps_diluted: float | None = 2.0,
    total_assets: float | None = None,
    total_liabilities: float | None = None,
    total_equity: float | None = 500.0,
    cash_and_equivalents: float | None = None,
    total_debt: float | None = 250.0,
    operating_cash_flow: float | None = 180.0,
    investing_cash_flow: float | None = None,
    financing_cash_flow: float | None = None,
    capital_expenditures: float | None = 40.0,
) -> FundamentalStatement:
    """Build a ``FundamentalStatement`` with sensible, overridable defaults.

    Every monetary default is chosen so every metric in this sprint
    (ROE, ROCE, operating margin, debt-to-equity, free cash flow) is
    computable out of the box; individual fields can be overridden
    (including set to ``None``) to exercise "insufficient data" paths.
    """
    instrument = Instrument(
        symbol=symbol, asset_class=AssetClass.EQUITY, currency="USD"
    )
    return FundamentalStatement(
        instrument=instrument,
        period_end=period_end,
        period_type=StatementPeriodType.ANNUAL,
        fiscal_year=fiscal_year,
        currency="USD",
        revenue=revenue,
        cost_of_revenue=cost_of_revenue,
        gross_profit=gross_profit,
        operating_income=operating_income,
        net_income=net_income,
        eps_basic=eps_basic,
        eps_diluted=eps_diluted,
        total_assets=total_assets,
        total_liabilities=total_liabilities,
        total_equity=total_equity,
        cash_and_equivalents=cash_and_equivalents,
        total_debt=total_debt,
        operating_cash_flow=operating_cash_flow,
        investing_cash_flow=investing_cash_flow,
        financing_cash_flow=financing_cash_flow,
        capital_expenditures=capital_expenditures,
    )


def make_snapshot(statements: Sequence[FundamentalStatement]) -> FinancialSnapshot:
    """Build a ``FinancialSnapshot`` from statements ordered most-recent-first."""
    statements = tuple(statements)
    return FinancialSnapshot(
        instrument=statements[0].instrument, statements=statements
    )


@pytest.fixture
def statement_factory():
    """Return :func:`make_statement` as an injectable pytest fixture."""
    return make_statement


@pytest.fixture
def snapshot_factory():
    """Return :func:`make_snapshot` as an injectable pytest fixture."""
    return make_snapshot
