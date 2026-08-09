"""Working-capital + cash-conversion quality — fail-closed evidence signals."""

from __future__ import annotations

from datetime import date

import pytest

from financial import (
    BalanceSheet,
    CashFlowStatement,
    CurrencyCode,
    CurrencyRef,
    FinancialPeriod,
    FinancialStatements,
    IncomeStatement,
    PeriodType,
    UnitScale,
)
from financial.intelligence.balance_engine import BalanceSheetEngine
from financial.intelligence.cashflow_engine import CashFlowEngine
from financial.intelligence.quality_signals import (
    days_from_turnover,
    growth_gap,
    ocf_to_earnings_ratio,
    operating_working_capital,
    period_change_rate,
)
from financial.intelligence.ratio_engine import FinancialRatioEngine
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
    *,
    period: FinancialPeriod,
    income: IncomeStatement | None = None,
    balance: BalanceSheet | None = None,
    cash: CashFlowStatement | None = None,
) -> FinancialStatements:
    return FinancialStatements(
        period=period,
        income_statement=income or IncomeStatement(revenue=100.0, net_income=20.0),
        balance_sheet=balance or BalanceSheet(total_assets=200.0, total_liabilities=80.0, equity=120.0),
        cash_flow=cash or CashFlowStatement(),
        statement_metadata=StatementMetadata(unit_scale=UnitScale.MILLIONS),
    )


class TestCashConversionFcfOcf:
    def test_fcf_gt_ocf(self) -> None:
        stmt = _stmt(
            period=_period(end=date(2024, 12, 31), fy=2024),
            cash=CashFlowStatement(
                operating_cash_flow=80.0, free_cash_flow=100.0, capex=-10.0
            ),
        )
        result = CashFlowEngine().analyze(stmt)
        assert result.operating.cash_conversion == pytest.approx(1.25)

    def test_fcf_lt_ocf(self) -> None:
        stmt = _stmt(
            period=_period(end=date(2024, 12, 31), fy=2024),
            cash=CashFlowStatement(
                operating_cash_flow=100.0, free_cash_flow=60.0, capex=-40.0
            ),
        )
        result = CashFlowEngine().analyze(stmt)
        assert result.operating.cash_conversion == pytest.approx(0.6)

    def test_fcf_eq_ocf(self) -> None:
        stmt = _stmt(
            period=_period(end=date(2024, 12, 31), fy=2024),
            cash=CashFlowStatement(
                operating_cash_flow=50.0, free_cash_flow=50.0, capex=0.0
            ),
        )
        result = CashFlowEngine().analyze(stmt)
        assert result.operating.cash_conversion == pytest.approx(1.0)

    def test_ocf_zero_unavailable(self) -> None:
        # Consistent reported FCF when OCF is zero (capex=0 → computed FCF=0).
        stmt = _stmt(
            period=_period(end=date(2024, 12, 31), fy=2024),
            cash=CashFlowStatement(
                operating_cash_flow=0.0, free_cash_flow=0.0, capex=0.0
            ),
        )
        result = CashFlowEngine().analyze(stmt)
        assert result.operating.cash_conversion is None

    def test_negative_ocf_preserves_ratio(self) -> None:
        stmt = _stmt(
            period=_period(end=date(2024, 12, 31), fy=2024),
            cash=CashFlowStatement(
                operating_cash_flow=-40.0, free_cash_flow=-45.0, capex=-5.0
            ),
        )
        result = CashFlowEngine().analyze(stmt)
        assert result.operating.cash_conversion == pytest.approx(1.125)

    def test_missing_fcf_unavailable(self) -> None:
        stmt = _stmt(
            period=_period(end=date(2024, 12, 31), fy=2024),
            cash=CashFlowStatement(operating_cash_flow=80.0, free_cash_flow=None, capex=None),
        )
        result = CashFlowEngine().analyze(stmt)
        assert result.operating.cash_conversion is None

    def test_missing_ocf_rejected_by_validation(self) -> None:
        # Hard validation rejects missing OCF — conversion never invented.
        from financial.exceptions import CashFlowAnalysisError

        stmt = _stmt(
            period=_period(end=date(2024, 12, 31), fy=2024),
            cash=CashFlowStatement(operating_cash_flow=None, free_cash_flow=40.0),
        )
        with pytest.raises(CashFlowAnalysisError, match="operating_cash_flow"):
            CashFlowEngine().analyze(stmt)


class TestOcfToEarnings:
    def test_strong_conversion(self) -> None:
        assert ocf_to_earnings_ratio(120.0, 100.0) == pytest.approx(1.2)

    def test_zero_ni_unavailable(self) -> None:
        assert ocf_to_earnings_ratio(50.0, 0.0) is None

    def test_negative_ni_unavailable(self) -> None:
        assert ocf_to_earnings_ratio(50.0, -10.0) is None

    def test_negative_ocf(self) -> None:
        assert ocf_to_earnings_ratio(-20.0, 100.0) == pytest.approx(-0.2)

    def test_missing_inputs(self) -> None:
        assert ocf_to_earnings_ratio(None, 100.0) is None
        assert ocf_to_earnings_ratio(50.0, None) is None

    def test_engine_surfaces_distinct_from_cash_conversion(self) -> None:
        stmt = _stmt(
            period=_period(end=date(2024, 12, 31), fy=2024),
            income=IncomeStatement(revenue=200.0, net_income=50.0),
            cash=CashFlowStatement(
                operating_cash_flow=80.0, free_cash_flow=60.0, capex=-20.0
            ),
        )
        result = CashFlowEngine().analyze(stmt)
        assert result.operating.ocf_to_earnings == pytest.approx(1.6)
        assert result.operating.cash_conversion == pytest.approx(0.75)
        assert result.free_cash_flow.fcf_to_earnings == pytest.approx(1.2)


class TestOperatingWorkingCapital:
    def test_owc_requires_all_three(self) -> None:
        assert operating_working_capital(100.0, 50.0, 40.0) == pytest.approx(110.0)
        assert operating_working_capital(100.0, None, 40.0) is None
        assert operating_working_capital(None, 50.0, 40.0) is None
        assert operating_working_capital(100.0, 50.0, None) is None

    def test_balance_engine_owc_and_growth_gaps(self) -> None:
        prior = _stmt(
            period=_period(end=date(2023, 12, 31), fy=2023),
            income=IncomeStatement(revenue=100.0, cogs=40.0, net_income=20.0),
            balance=BalanceSheet(
                accounts_receivable=20.0,
                inventory=10.0,
                accounts_payable=5.0,
                current_assets=50.0,
                current_liabilities=15.0,
                total_assets=200.0,
                total_liabilities=80.0,
                equity=120.0,
            ),
        )
        current = _stmt(
            period=_period(end=date(2024, 12, 31), fy=2024),
            income=IncomeStatement(revenue=110.0, cogs=44.0, net_income=22.0),
            balance=BalanceSheet(
                accounts_receivable=30.0,
                inventory=15.0,
                accounts_payable=6.0,
                current_assets=70.0,
                current_liabilities=20.0,
                total_assets=220.0,
                total_liabilities=90.0,
                equity=130.0,
            ),
        )
        result = BalanceSheetEngine().analyze([prior, current])
        wc = result.working_capital
        assert wc.operating_working_capital == pytest.approx(39.0)  # 30+15-6
        assert wc.operating_working_capital_change == pytest.approx(14.0)  # 39-25
        assert wc.receivables_growth == pytest.approx(0.5)
        assert wc.inventory_growth == pytest.approx(0.5)
        assert wc.payables_growth == pytest.approx(0.2)
        # revenue growth = 10%
        assert wc.receivables_vs_revenue_growth == pytest.approx(0.4)
        assert wc.inventory_vs_revenue_growth == pytest.approx(0.4)
        # cogs growth = 10%; payables 20% → gap 0.1
        assert wc.payables_vs_cogs_growth == pytest.approx(0.1)

    def test_missing_ar_makes_owc_unavailable(self) -> None:
        stmt = _stmt(
            period=_period(end=date(2024, 12, 31), fy=2024),
            balance=BalanceSheet(
                inventory=10.0,
                accounts_payable=5.0,
                current_assets=40.0,
                current_liabilities=10.0,
                total_assets=100.0,
                total_liabilities=40.0,
                equity=60.0,
            ),
        )
        result = BalanceSheetEngine().analyze(stmt)
        assert result.working_capital.operating_working_capital is None
        assert result.working_capital.receivables_growth is None

    def test_quarterly_history_does_not_compute_growth_gaps(self) -> None:
        q1 = _stmt(
            period=_period(
                end=date(2024, 3, 31), fy=2024, period_type=PeriodType.QUARTERLY, fq=1
            ),
            income=IncomeStatement(revenue=100.0, cogs=40.0),
            balance=BalanceSheet(
                accounts_receivable=20.0,
                inventory=10.0,
                accounts_payable=5.0,
                current_assets=50.0,
                current_liabilities=15.0,
                total_assets=200.0,
                total_liabilities=80.0,
                equity=120.0,
            ),
        )
        q2 = _stmt(
            period=_period(
                end=date(2024, 6, 30), fy=2024, period_type=PeriodType.QUARTERLY, fq=2
            ),
            income=IncomeStatement(revenue=120.0, cogs=48.0),
            balance=BalanceSheet(
                accounts_receivable=40.0,
                inventory=20.0,
                accounts_payable=8.0,
                current_assets=80.0,
                current_liabilities=25.0,
                total_assets=220.0,
                total_liabilities=90.0,
                equity=130.0,
            ),
        )
        result = BalanceSheetEngine().analyze([q1, q2])
        # Stock OWC still available (point-in-time)
        assert result.working_capital.operating_working_capital == pytest.approx(52.0)
        # Growth gaps require annual FY span
        assert result.working_capital.receivables_growth is None
        assert result.working_capital.receivables_vs_revenue_growth is None

    def test_one_year_history_no_growth(self) -> None:
        stmt = _stmt(
            period=_period(end=date(2024, 12, 31), fy=2024),
            balance=BalanceSheet(
                accounts_receivable=20.0,
                inventory=10.0,
                accounts_payable=5.0,
                current_assets=50.0,
                current_liabilities=15.0,
                total_assets=200.0,
                total_liabilities=80.0,
                equity=120.0,
            ),
        )
        result = BalanceSheetEngine().analyze(stmt)
        assert result.working_capital.operating_working_capital == pytest.approx(25.0)
        assert result.working_capital.operating_working_capital_change is None


class TestDaysAndHelpers:
    def test_days_from_turnover(self) -> None:
        assert days_from_turnover(365.0 / 45.0) == pytest.approx(45.0)
        assert days_from_turnover(0.0) is None
        assert days_from_turnover(None) is None

    def test_period_change_and_gap_edge_cases(self) -> None:
        assert period_change_rate(110.0, 100.0) == pytest.approx(0.1)
        assert period_change_rate(10.0, 0.0) is None
        assert period_change_rate(None, 100.0) is None
        assert growth_gap(0.5, 0.1) == pytest.approx(0.4)
        assert growth_gap(None, 0.1) is None

    def test_ratio_engine_ccc_from_turnovers(self) -> None:
        stmt = _stmt(
            period=_period(end=date(2024, 12, 31), fy=2024),
            income=IncomeStatement(revenue=365.0, cogs=365.0, net_income=50.0),
            balance=BalanceSheet(
                accounts_receivable=45.0,
                inventory=30.0,
                accounts_payable=20.0,
                current_assets=100.0,
                current_liabilities=40.0,
                total_assets=400.0,
                total_liabilities=150.0,
                equity=250.0,
                ppe=100.0,
            ),
            cash=CashFlowStatement(operating_cash_flow=80.0, free_cash_flow=60.0, capex=-20.0),
        )
        result = FinancialRatioEngine().analyze(stmt)
        by_name = {m.name: m.value for m in result.efficiency}
        # turnover AR = 365/45 → DSO ≈ 45
        assert by_name["days_sales_outstanding"] == pytest.approx(45.0)
        assert by_name["days_inventory_outstanding"] == pytest.approx(30.0)
        assert by_name["days_payables_outstanding"] == pytest.approx(20.0)
        assert by_name["cash_conversion_cycle"] == pytest.approx(55.0)

    def test_zero_revenue_growth_gap_unavailable_via_engine(self) -> None:
        prior = _stmt(
            period=_period(end=date(2023, 12, 31), fy=2023),
            income=IncomeStatement(revenue=0.0, cogs=40.0),
            balance=BalanceSheet(
                accounts_receivable=20.0,
                inventory=10.0,
                accounts_payable=5.0,
                current_assets=50.0,
                current_liabilities=15.0,
                total_assets=200.0,
                total_liabilities=80.0,
                equity=120.0,
            ),
        )
        current = _stmt(
            period=_period(end=date(2024, 12, 31), fy=2024),
            income=IncomeStatement(revenue=100.0, cogs=44.0),
            balance=BalanceSheet(
                accounts_receivable=30.0,
                inventory=15.0,
                accounts_payable=6.0,
                current_assets=70.0,
                current_liabilities=20.0,
                total_assets=220.0,
                total_liabilities=90.0,
                equity=130.0,
            ),
        )
        result = BalanceSheetEngine().analyze([prior, current])
        # revenue prior 0 → rev growth unavailable → AR vs revenue gap unavailable
        assert result.working_capital.receivables_vs_revenue_growth is None
