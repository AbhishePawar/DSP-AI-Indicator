"""Deterministic tests for EPS CAGR, FCF/NI conversion, share dilution."""

from __future__ import annotations

from datetime import date
from types import SimpleNamespace

import pytest

from financial import (
    CurrencyCode,
    CurrencyRef,
    FinancialPeriod,
    FinancialStatements,
    IncomeStatement,
    PeriodType,
    UnitScale,
)
from financial.cash_flow import CashFlowStatement
from financial.intelligence.cashflow_engine import CashFlowEngine
from financial.intelligence.income_engine import IncomeStatementEngine
from financial.intelligence.quality_signals import (
    dilution_discipline_01,
    eps_cagr_from_series,
    fcf_to_earnings_ratio,
    map_fcf_to_earnings_01,
    share_dilution_rate,
)
from financial.metadata import StatementMetadata


def _period(
    *,
    end: date,
    fy: int,
    period_type: PeriodType = PeriodType.ANNUAL,
    fq: int | None = None,
) -> FinancialPeriod:
    return FinancialPeriod(
        period_type=period_type,
        period_end=end,
        fiscal_year=fy,
        fiscal_quarter=fq,
        currency=CurrencyRef(CurrencyCode.USD),
    )


def _stmt(
    income: IncomeStatement,
    period: FinancialPeriod,
    *,
    cash: CashFlowStatement | None = None,
) -> FinancialStatements:
    return FinancialStatements(
        period=period,
        income_statement=income,
        cash_flow=cash or CashFlowStatement(),
        statement_metadata=StatementMetadata(unit_scale=UnitScale.MILLIONS),
    )


class TestEpsCagr:
    def test_positive_diluted_eps_cagr(self) -> None:
        incomes = [
            IncomeStatement(revenue=100.0, eps=1.0, diluted_eps=0.90, weighted_shares=100.0),
            IncomeStatement(revenue=110.0, eps=1.21, diluted_eps=1.089, weighted_shares=100.0),
        ]
        stmts = [
            _stmt(incomes[0], _period(end=date(2022, 12, 31), fy=2022)),
            _stmt(incomes[1], _period(end=date(2024, 12, 31), fy=2024)),
        ]
        cagr, basis = eps_cagr_from_series(incomes, stmts)
        assert basis == "diluted"
        assert cagr is not None
        assert abs(cagr - 0.10) < 1e-6

    def test_falls_back_to_basic_when_diluted_incomplete(self) -> None:
        incomes = [
            IncomeStatement(revenue=100.0, eps=1.0, diluted_eps=None, weighted_shares=100.0),
            IncomeStatement(revenue=110.0, eps=1.21, diluted_eps=1.10, weighted_shares=100.0),
        ]
        stmts = [
            _stmt(incomes[0], _period(end=date(2022, 12, 31), fy=2022)),
            _stmt(incomes[1], _period(end=date(2024, 12, 31), fy=2024)),
        ]
        cagr, basis = eps_cagr_from_series(incomes, stmts)
        assert basis == "basic"
        assert cagr is not None
        assert abs(cagr - 0.10) < 1e-6

    def test_never_mixes_diluted_and_basic(self) -> None:
        # Only one diluted point → diluted CAGR unavailable; uses basic series.
        incomes = [
            IncomeStatement(revenue=100.0, eps=2.0, diluted_eps=1.0, weighted_shares=100.0),
            IncomeStatement(revenue=110.0, eps=2.42, diluted_eps=None, weighted_shares=100.0),
        ]
        stmts = [
            _stmt(incomes[0], _period(end=date(2022, 12, 31), fy=2022)),
            _stmt(incomes[1], _period(end=date(2024, 12, 31), fy=2024)),
        ]
        cagr, basis = eps_cagr_from_series(incomes, stmts)
        assert basis == "basic"
        assert cagr is not None
        assert abs(cagr - 0.10) < 1e-6

    def test_zero_eps_unavailable(self) -> None:
        incomes = [
            IncomeStatement(revenue=100.0, eps=0.0, diluted_eps=0.0),
            IncomeStatement(revenue=110.0, eps=1.0, diluted_eps=1.0),
        ]
        stmts = [
            _stmt(incomes[0], _period(end=date(2022, 12, 31), fy=2022)),
            _stmt(incomes[1], _period(end=date(2024, 12, 31), fy=2024)),
        ]
        cagr, basis = eps_cagr_from_series(incomes, stmts)
        assert cagr is None
        assert basis == "unavailable"

    def test_negative_eps_unavailable(self) -> None:
        incomes = [
            IncomeStatement(revenue=100.0, eps=-1.0, diluted_eps=-1.0),
            IncomeStatement(revenue=110.0, eps=-0.5, diluted_eps=-0.5),
        ]
        stmts = [
            _stmt(incomes[0], _period(end=date(2022, 12, 31), fy=2022)),
            _stmt(incomes[1], _period(end=date(2024, 12, 31), fy=2024)),
        ]
        cagr, basis = eps_cagr_from_series(incomes, stmts)
        assert cagr is None
        assert basis == "unavailable"

    def test_negative_to_positive_unavailable(self) -> None:
        incomes = [
            IncomeStatement(revenue=100.0, eps=-1.0, diluted_eps=-1.0),
            IncomeStatement(revenue=110.0, eps=1.0, diluted_eps=1.0),
        ]
        stmts = [
            _stmt(incomes[0], _period(end=date(2022, 12, 31), fy=2022)),
            _stmt(incomes[1], _period(end=date(2024, 12, 31), fy=2024)),
        ]
        cagr, basis = eps_cagr_from_series(incomes, stmts)
        assert cagr is None
        assert basis == "unavailable"

    def test_quarterly_not_counted_as_years(self) -> None:
        incomes = [
            IncomeStatement(revenue=100.0, eps=1.0, diluted_eps=1.0),
            IncomeStatement(revenue=110.0, eps=1.1, diluted_eps=1.1),
            IncomeStatement(revenue=120.0, eps=1.2, diluted_eps=1.2),
            IncomeStatement(revenue=130.0, eps=1.3, diluted_eps=1.3),
        ]
        stmts = [
            _stmt(
                incomes[i],
                _period(
                    end=date(2024, 3 + i * 3, 28),
                    fy=2024,
                    period_type=PeriodType.QUARTERLY,
                    fq=i + 1,
                ),
            )
            for i in range(4)
        ]
        cagr, basis = eps_cagr_from_series(incomes, stmts)
        assert cagr is None
        assert basis == "unavailable"

    def test_income_engine_surfaces_eps_cagr(self) -> None:
        snap_stmts = [
            _stmt(
                IncomeStatement(
                    revenue=1000.0,
                    cogs=400.0,
                    net_income=100.0,
                    eps=1.0,
                    diluted_eps=0.95,
                    weighted_shares=100.0,
                ),
                _period(end=date(2022, 12, 31), fy=2022),
            ),
            _stmt(
                IncomeStatement(
                    revenue=1210.0,
                    cogs=400.0,
                    net_income=121.0,
                    eps=1.21,
                    diluted_eps=1.1495,
                    weighted_shares=100.0,
                ),
                _period(end=date(2024, 12, 31), fy=2024),
            ),
        ]
        result = IncomeStatementEngine().analyze(snap_stmts)
        assert result.profitability.eps_cagr_basis == "diluted"
        assert result.profitability.eps_cagr is not None
        assert abs(result.profitability.eps_cagr - 0.10) < 1e-5


class TestFcfToEarnings:
    def test_strong_conversion(self) -> None:
        assert fcf_to_earnings_ratio(120.0, 100.0) == pytest.approx(1.2)

    def test_weak_conversion(self) -> None:
        assert fcf_to_earnings_ratio(40.0, 100.0) == pytest.approx(0.4)

    def test_fcf_less_than_ni(self) -> None:
        r = fcf_to_earnings_ratio(80.0, 100.0)
        assert r is not None and r < 1.0

    def test_fcf_greater_than_ni(self) -> None:
        r = fcf_to_earnings_ratio(150.0, 100.0)
        assert r is not None and r > 1.0

    def test_negative_fcf(self) -> None:
        assert fcf_to_earnings_ratio(-20.0, 100.0) == pytest.approx(-0.2)
        assert map_fcf_to_earnings_01(-0.2) == pytest.approx(0.15)

    def test_zero_ni_unavailable(self) -> None:
        assert fcf_to_earnings_ratio(50.0, 0.0) is None

    def test_negative_ni_unavailable(self) -> None:
        assert fcf_to_earnings_ratio(50.0, -10.0) is None

    def test_missing_fcf(self) -> None:
        assert fcf_to_earnings_ratio(None, 100.0) is None

    def test_missing_ni(self) -> None:
        assert fcf_to_earnings_ratio(50.0, None) is None

    def test_does_not_use_ocf_as_fcf(self) -> None:
        # Engine resolves FCF; if FCF missing and OCF present without capex, FCF unavailable.
        stmt = _stmt(
            IncomeStatement(revenue=100.0, net_income=50.0),
            _period(end=date(2024, 12, 31), fy=2024),
            cash=CashFlowStatement(operating_cash_flow=80.0, free_cash_flow=None, capex=None),
        )
        result = CashFlowEngine().analyze(stmt)
        assert result.free_cash_flow.free_cash_flow is None
        assert result.free_cash_flow.fcf_to_earnings is None

    def test_cashflow_engine_computes_fcf_to_earnings(self) -> None:
        stmt = _stmt(
            IncomeStatement(revenue=100.0, net_income=50.0),
            _period(end=date(2024, 12, 31), fy=2024),
            cash=CashFlowStatement(
                operating_cash_flow=80.0,
                free_cash_flow=60.0,
                capex=-20.0,
            ),
        )
        result = CashFlowEngine().analyze(stmt)
        assert result.free_cash_flow.fcf_to_earnings == pytest.approx(1.2)
        # cash_conversion remains FCF/OCF
        assert result.operating.cash_conversion == pytest.approx(0.75)


class TestShareDilution:
    def test_increasing_shares(self) -> None:
        incomes = [
            IncomeStatement(revenue=100.0, weighted_shares=100.0),
            IncomeStatement(revenue=110.0, weighted_shares=110.0),
        ]
        stmts = [
            _stmt(incomes[0], _period(end=date(2022, 12, 31), fy=2022)),
            _stmt(incomes[1], _period(end=date(2024, 12, 31), fy=2024)),
        ]
        rate = share_dilution_rate(incomes, stmts)
        assert rate == pytest.approx(0.10)
        disc = dilution_discipline_01(rate)
        assert disc is not None and disc < 0.85

    def test_decreasing_shares(self) -> None:
        incomes = [
            IncomeStatement(revenue=100.0, weighted_shares=100.0),
            IncomeStatement(revenue=110.0, weighted_shares=90.0),
        ]
        stmts = [
            _stmt(incomes[0], _period(end=date(2022, 12, 31), fy=2022)),
            _stmt(incomes[1], _period(end=date(2024, 12, 31), fy=2024)),
        ]
        rate = share_dilution_rate(incomes, stmts)
        assert rate == pytest.approx(-0.10)
        assert dilution_discipline_01(rate) == pytest.approx(1.0)

    def test_unchanged_shares(self) -> None:
        incomes = [
            IncomeStatement(revenue=100.0, weighted_shares=100.0),
            IncomeStatement(revenue=110.0, weighted_shares=100.0),
        ]
        stmts = [
            _stmt(incomes[0], _period(end=date(2022, 12, 31), fy=2022)),
            _stmt(incomes[1], _period(end=date(2024, 12, 31), fy=2024)),
        ]
        rate = share_dilution_rate(incomes, stmts)
        assert rate == pytest.approx(0.0)
        assert dilution_discipline_01(rate) == pytest.approx(0.85)

    def test_missing_historical_shares(self) -> None:
        incomes = [
            IncomeStatement(revenue=100.0, weighted_shares=None),
            IncomeStatement(revenue=110.0, weighted_shares=100.0),
        ]
        stmts = [
            _stmt(incomes[0], _period(end=date(2022, 12, 31), fy=2022)),
            _stmt(incomes[1], _period(end=date(2024, 12, 31), fy=2024)),
        ]
        assert share_dilution_rate(incomes, stmts) is None
        assert dilution_discipline_01(None) is None

    def test_zero_shares_unavailable(self) -> None:
        incomes = [
            IncomeStatement(revenue=100.0, weighted_shares=0.0),
            IncomeStatement(revenue=110.0, weighted_shares=10.0),
        ]
        stmts = [
            _stmt(incomes[0], _period(end=date(2022, 12, 31), fy=2022)),
            _stmt(incomes[1], _period(end=date(2024, 12, 31), fy=2024)),
        ]
        assert share_dilution_rate(incomes, stmts) is None

    def test_quarterly_ignored_for_dilution(self) -> None:
        incomes = [
            IncomeStatement(revenue=100.0, weighted_shares=100.0),
            IncomeStatement(revenue=110.0, weighted_shares=120.0),
        ]
        stmts = [
            _stmt(
                incomes[0],
                _period(
                    end=date(2024, 3, 31),
                    fy=2024,
                    period_type=PeriodType.QUARTERLY,
                    fq=1,
                ),
            ),
            _stmt(
                incomes[1],
                _period(
                    end=date(2024, 6, 30),
                    fy=2024,
                    period_type=PeriodType.QUARTERLY,
                    fq=2,
                ),
            ),
        ]
        assert share_dilution_rate(incomes, stmts) is None

    def test_not_aliased_from_buybacks(self) -> None:
        # Buyback cash activity must not invent a dilution rate.
        assert share_dilution_rate([], []) is None
        assert dilution_discipline_01(None) is None
        # Explicit namespace without share history stays unavailable.
        fa_profit = SimpleNamespace(
            share_dilution_rate=None,
            dilution_discipline=None,
        )
        assert fa_profit.dilution_discipline is None
