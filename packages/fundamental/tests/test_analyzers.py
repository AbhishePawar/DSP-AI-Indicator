"""Tests for the concrete analyzer implementations."""

from collections.abc import Callable
from datetime import date

import pytest

from contracts.domain.fundamental_statement import FundamentalStatement
from fundamental.analyzers.growth import GrowthAnalyzer
from fundamental.analyzers.leverage import LeverageAnalyzer
from fundamental.analyzers.profitability import ProfitabilityAnalyzer
from fundamental.analyzers.quality import QualityAnalyzer
from fundamental.models import FinancialSnapshot

StatementFactory = Callable[..., FundamentalStatement]
SnapshotFactory = Callable[..., FinancialSnapshot]


def _by_name(metrics, name):
    return next(metric for metric in metrics if metric.name == name)


class TestProfitabilityAnalyzer:
    """Tests for ProfitabilityAnalyzer's ROE, ROCE, and operating margin."""

    def test_name(self) -> None:
        assert ProfitabilityAnalyzer().name == "profitability"

    def test_computes_three_metrics(
        self, statement_factory: StatementFactory, snapshot_factory: SnapshotFactory
    ) -> None:
        snapshot = snapshot_factory([statement_factory()])
        metrics = ProfitabilityAnalyzer().analyze(snapshot)
        assert {metric.name for metric in metrics} == {
            "roe",
            "roce",
            "operating_margin",
        }

    def test_roe_is_net_income_over_equity(
        self, statement_factory: StatementFactory, snapshot_factory: SnapshotFactory
    ) -> None:
        statement = statement_factory(net_income=100.0, total_equity=500.0)
        snapshot = snapshot_factory([statement])
        metrics = ProfitabilityAnalyzer().analyze(snapshot)
        assert _by_name(metrics, "roe").value == pytest.approx(0.2)

    def test_roce_uses_equity_plus_debt_as_capital_employed(
        self, statement_factory: StatementFactory, snapshot_factory: SnapshotFactory
    ) -> None:
        statement = statement_factory(
            operating_income=150.0, total_equity=500.0, total_debt=250.0
        )
        snapshot = snapshot_factory([statement])
        metrics = ProfitabilityAnalyzer().analyze(snapshot)
        assert _by_name(metrics, "roce").value == pytest.approx(150.0 / 750.0)

    def test_operating_margin_is_operating_income_over_revenue(
        self, statement_factory: StatementFactory, snapshot_factory: SnapshotFactory
    ) -> None:
        statement = statement_factory(operating_income=150.0, revenue=1_000.0)
        snapshot = snapshot_factory([statement])
        metrics = ProfitabilityAnalyzer().analyze(snapshot)
        assert _by_name(metrics, "operating_margin").value == pytest.approx(0.15)

    def test_missing_equity_yields_none_roe_and_roce(
        self, statement_factory: StatementFactory, snapshot_factory: SnapshotFactory
    ) -> None:
        statement = statement_factory(total_equity=None, total_debt=None)
        snapshot = snapshot_factory([statement])
        metrics = ProfitabilityAnalyzer().analyze(snapshot)
        assert _by_name(metrics, "roe").value is None
        assert _by_name(metrics, "roce").value is None


class TestGrowthAnalyzer:
    """Tests for GrowthAnalyzer's revenue and EPS growth."""

    def test_name(self) -> None:
        assert GrowthAnalyzer().name == "growth"

    def test_revenue_and_eps_growth_between_two_periods(
        self, statement_factory: StatementFactory, snapshot_factory: SnapshotFactory
    ) -> None:
        latest = statement_factory(
            fiscal_year=2024,
            period_end=date(2024, 12, 31),
            revenue=1_100.0,
            eps_diluted=2.2,
        )
        previous = statement_factory(
            fiscal_year=2023,
            period_end=date(2023, 12, 31),
            revenue=1_000.0,
            eps_diluted=2.0,
        )
        snapshot = snapshot_factory([latest, previous])
        metrics = GrowthAnalyzer().analyze(snapshot)
        assert _by_name(metrics, "revenue_growth").value == pytest.approx(0.10)
        assert _by_name(metrics, "eps_growth").value == pytest.approx(0.10)

    def test_single_period_snapshot_yields_none_growth(
        self, statement_factory: StatementFactory, snapshot_factory: SnapshotFactory
    ) -> None:
        snapshot = snapshot_factory([statement_factory()])
        metrics = GrowthAnalyzer().analyze(snapshot)
        assert _by_name(metrics, "revenue_growth").value is None
        assert _by_name(metrics, "eps_growth").value is None


class TestLeverageAnalyzer:
    """Tests for LeverageAnalyzer's debt-to-equity metric."""

    def test_name(self) -> None:
        assert LeverageAnalyzer().name == "leverage"

    def test_debt_to_equity(
        self, statement_factory: StatementFactory, snapshot_factory: SnapshotFactory
    ) -> None:
        statement = statement_factory(total_debt=250.0, total_equity=500.0)
        snapshot = snapshot_factory([statement])
        metrics = LeverageAnalyzer().analyze(snapshot)
        assert _by_name(metrics, "debt_to_equity").value == pytest.approx(0.5)

    def test_zero_equity_yields_none(
        self, statement_factory: StatementFactory, snapshot_factory: SnapshotFactory
    ) -> None:
        statement = statement_factory(total_debt=250.0, total_equity=0.0)
        snapshot = snapshot_factory([statement])
        metrics = LeverageAnalyzer().analyze(snapshot)
        assert _by_name(metrics, "debt_to_equity").value is None


class TestQualityAnalyzer:
    """Tests for QualityAnalyzer's free cash flow metric."""

    def test_name(self) -> None:
        assert QualityAnalyzer().name == "quality"

    def test_free_cash_flow_is_ocf_minus_capex(
        self, statement_factory: StatementFactory, snapshot_factory: SnapshotFactory
    ) -> None:
        statement = statement_factory(
            operating_cash_flow=180.0, capital_expenditures=40.0
        )
        snapshot = snapshot_factory([statement])
        metrics = QualityAnalyzer().analyze(snapshot)
        assert _by_name(metrics, "free_cash_flow").value == pytest.approx(140.0)

    def test_missing_capex_yields_none(
        self, statement_factory: StatementFactory, snapshot_factory: SnapshotFactory
    ) -> None:
        statement = statement_factory(
            operating_cash_flow=180.0, capital_expenditures=None
        )
        snapshot = snapshot_factory([statement])
        metrics = QualityAnalyzer().analyze(snapshot)
        assert _by_name(metrics, "free_cash_flow").value is None
