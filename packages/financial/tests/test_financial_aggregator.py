"""Financial Statement Aggregator tests — target 100% module coverage."""

from __future__ import annotations

import time
from datetime import date
from types import SimpleNamespace

import pytest

from financial import (
    FINANCIAL_VERSION,
    AggregatedQualityFlag,
    BalanceSheet,
    CashFlowStatement,
    CurrencyCode,
    CurrencyRef,
    FinancialAggregationError,
    FinancialAggregatorEngine,
    FinancialAnalysis,
    FinancialEngine,
    FinancialPeriod,
    FinancialStatements,
    FinancialStatementsHistory,
    IncomeStatement,
    PeriodType,
    UnitScale,
    validate_aggregation_inputs,
)
from financial.intelligence.aggregator_engine import AGGREGATOR_VERSION
from financial.intelligence.aggregator_explainability import (
    AGGREGATOR_RESEARCH_DISCLAIMER,
)
from financial.intelligence.aggregator_models import (
    FinancialAnalysisMetadata,
    OverallFinancialSummary,
)
from financial.intelligence.aggregator_validation import coerce_aggregation_source
from financial.intelligence.balance_models import BalanceQualityFlag
from financial.intelligence.cashflow_models import CashFlowQualityFlag
from financial.intelligence.income_models import QualityFlag
from financial.intelligence.ratio_models import RatioQualityFlag
from financial.intelligence.trend_models import TrendQualityFlag
from financial.metadata import StatementMetadata
from financial.validation import ValidationResult


def _period(*, end: date = date(2024, 12, 31), fy: int | None = 2024) -> FinancialPeriod:
    return FinancialPeriod(
        period_type=PeriodType.ANNUAL,
        period_end=end,
        fiscal_year=fy,
        currency=CurrencyRef(CurrencyCode.USD),
    )


def _full(*, year: int = 2024, scale: float = 1.0, **kwargs) -> FinancialStatements:
    income = kwargs.pop("income", None) or IncomeStatement(
        revenue=1000.0 * scale,
        cogs=400.0 * scale,
        gross_profit=600.0 * scale,
        ebit=300.0 * scale,
        ebitda=350.0 * scale,
        interest_expense=20.0 * scale,
        pretax_income=280.0 * scale,
        tax=70.0 * scale,
        net_income=210.0 * scale,
        weighted_shares=100.0,
        eps=2.1 * scale,
    )
    balance = kwargs.pop("balance", None) or BalanceSheet(
        cash=150.0 * scale,
        short_term_investments=50.0 * scale,
        accounts_receivable=120.0 * scale,
        inventory=80.0 * scale,
        current_assets=450.0 * scale,
        ppe=400.0 * scale,
        goodwill=50.0 * scale,
        intangibles=50.0 * scale,
        total_assets=1000.0 * scale,
        accounts_payable=60.0 * scale,
        short_term_debt=50.0 * scale,
        current_liabilities=200.0 * scale,
        long_term_debt=200.0 * scale,
        total_liabilities=400.0 * scale,
        retained_earnings=300.0 * scale,
        equity=600.0 * scale,
        total_equity=600.0 * scale,
    )
    cash = kwargs.pop("cash", None) or CashFlowStatement(
        operating_cash_flow=250.0 * scale,
        capex=-80.0 * scale,
        free_cash_flow=170.0 * scale,
        dividends_paid=-50.0 * scale,
        share_buybacks=-30.0 * scale,
        debt_issued=10.0 * scale,
        debt_repaid=-40.0 * scale,
    )
    period = kwargs.pop("period", None) or _period(end=date(year, 12, 31), fy=year)
    return FinancialStatements(
        period=period,
        income_statement=income,
        balance_sheet=balance,
        cash_flow=cash,
        statement_metadata=StatementMetadata(unit_scale=UnitScale.MILLIONS),
    )


def _history(*scales: float, start_year: int = 2020) -> list[FinancialStatements]:
    return [_full(year=start_year + i, scale=s) for i, s in enumerate(scales)]


class TestValidation:
    def test_empty_history(self) -> None:
        with pytest.raises(FinancialAggregationError, match="empty"):
            coerce_aggregation_source(FinancialStatementsHistory(statements=()))
        with pytest.raises(FinancialAggregationError, match="empty"):
            validate_aggregation_inputs([])

    def test_reject_non_statements(self) -> None:
        with pytest.raises(FinancialAggregationError, match="Accept ONLY"):
            coerce_aggregation_source("bad")  # type: ignore[arg-type]
        with pytest.raises(FinancialAggregationError, match="must be"):
            coerce_aggregation_source([1, 2])  # type: ignore[list-item]
        with pytest.raises(FinancialAggregationError, match="empty"):
            coerce_aggregation_source([])

    def test_duplicate_periods(self) -> None:
        a = _full(year=2023)
        b = _full(year=2023)
        with pytest.raises(FinancialAggregationError, match="duplicate"):
            coerce_aggregation_source([a, b])

    def test_missing_income(self) -> None:
        stmt = _full(income=IncomeStatement())
        with pytest.raises(FinancialAggregationError, match="income"):
            validate_aggregation_inputs([stmt])

    def test_missing_balance(self) -> None:
        stmt = _full(balance=BalanceSheet())
        with pytest.raises(FinancialAggregationError, match="balance"):
            validate_aggregation_inputs([stmt])

    def test_missing_cash(self) -> None:
        stmt = _full(cash=CashFlowStatement())
        with pytest.raises(FinancialAggregationError, match="cash flow"):
            validate_aggregation_inputs([stmt])

    def test_incompatible_accounting(self) -> None:
        bad = _full(
            year=2022,
            balance=BalanceSheet(
                total_assets=100.0,
                total_liabilities=10.0,
                total_equity=10.0,
                equity=10.0,
            ),
        )
        with pytest.raises(FinancialAggregationError, match="incompatible"):
            validate_aggregation_inputs([bad])

    def test_single_period_warning(self) -> None:
        result = validate_aggregation_inputs([_full()])
        assert result.ok
        assert any("Trend" in w for w in result.warnings)


class TestAggregator:
    def test_single_period(self) -> None:
        eng = FinancialAggregatorEngine()
        result = eng.analyze(_full())
        assert isinstance(result, FinancialAnalysis)
        assert result.trends is None
        assert result.metadata.periods_used == 1
        assert result.metadata.trend_included is False
        assert result.research_disclaimer == AGGREGATOR_RESEARCH_DISCLAIMER
        assert result.metadata.engine_version == AGGREGATOR_VERSION
        assert result.income is not None
        assert result.balance_sheet is not None
        assert result.cash_flow is not None
        assert result.ratios is not None
        payload = result.to_dict()
        assert payload["trends"] is None
        assert "overall_summary" in payload

    def test_multi_period_history(self) -> None:
        stmts = _history(1.0, 1.1, 1.25, 1.4)
        hist = FinancialStatementsHistory(statements=tuple(stmts))
        result = FinancialAggregatorEngine().analyze(hist)
        assert result.trends is not None
        assert result.metadata.trend_included is True
        assert result.metadata.periods_used == 4
        assert result.explainability
        # Provenance: module explainability preserved
        names = {e.name for e in result.explainability}
        assert "aggregated_quality_flags" in names
        assert "overall_financial_summary" in names
        assert len(result.explainability) > 2

    def test_sequence_input(self) -> None:
        result = FinancialAggregatorEngine().analyze(_history(1.0, 1.15))
        assert result.metadata.periods_used == 2
        assert result.trends is not None

    def test_facade_primary_entry(self) -> None:
        engine = FinancialEngine()
        result = engine.analyze_financials(_full())
        assert isinstance(result, FinancialAnalysis)
        # Backward compatibility: prior entry points still work
        assert engine.analyze_income_statement(_full()).revenue.revenue is not None
        assert engine.analyze_financial_ratios(_full()).profitability
        assert FINANCIAL_VERSION.startswith("0.7.0")

    def test_summary_and_flags_present(self) -> None:
        result = FinancialAggregatorEngine().analyze(_history(1.0, 1.2, 1.4))
        assert isinstance(result.overall_summary, OverallFinancialSummary)
        assert result.overall_summary.data_completeness in {
            "complete",
            "mostly_complete",
            "partial",
        }
        assert result.overall_summary.confidence_summary in {
            "high",
            "medium",
            "low",
            "insufficient",
        }
        assert result.overall_summary.to_dict()["health_label"]
        assert FinancialAnalysisMetadata(
            engine_version="t", periods_used=1, period_ends=("2024-12-31",)
        ).to_dict()["periods_used"] == 1

    def test_performance_multi_period(self) -> None:
        scales = [1.0 + i * 0.06 for i in range(5)]
        eng = FinancialAggregatorEngine()
        hist = FinancialStatementsHistory(statements=tuple(_history(*scales)))
        eng.analyze(hist)
        samples: list[float] = []
        for _ in range(5):
            t0 = time.perf_counter()
            eng.analyze(hist)
            samples.append((time.perf_counter() - t0) * 1000)
        elapsed = min(samples)
        try:
            from coverage import Coverage

            under_cov = Coverage.current() is not None
        except Exception:  # pragma: no cover
            under_cov = False
        limit = 150.0 if under_cov else 50.0
        assert elapsed < limit, f"aggregation best-of-5 {elapsed:.1f} ms"


class TestFlagComposition:
    def _ns(self, *flags):
        return SimpleNamespace(quality_flags=tuple(flags))

    def test_concern_and_excellent_paths(self) -> None:
        eng = FinancialAggregatorEngine()
        # Liquidity / leverage / cash concerns
        flags = eng._aggregate_flags(
            self._ns(QualityFlag.WEAK_EARNINGS_QUALITY),
            self._ns(
                BalanceQualityFlag.WEAK_LIQUIDITY,
                BalanceQualityFlag.EXCESSIVE_LEVERAGE,
                BalanceQualityFlag.BALANCE_SHEET_WARNING,
            ),
            self._ns(CashFlowQualityFlag.NEGATIVE_FREE_CASH_FLOW),
            self._ns(RatioQualityFlag.WEAK_LIQUIDITY, RatioQualityFlag.HIGH_LEVERAGE),
            SimpleNamespace(
                quality_flags=(TrendQualityFlag.DEBT_INCREASING,)
            ),
        )
        assert AggregatedQualityFlag.LIQUIDITY_CONCERN in flags
        assert AggregatedQualityFlag.LEVERAGE_CONCERN in flags
        assert AggregatedQualityFlag.CASH_FLOW_CONCERN in flags
        assert AggregatedQualityFlag.NEEDS_ATTENTION in flags

        # Excellent / healthy / compounder / improving
        flags2 = eng._aggregate_flags(
            self._ns(
                QualityFlag.STRONG_EARNINGS_QUALITY,
                QualityFlag.HEALTHY_GROWTH,
                QualityFlag.MARGIN_EXPANSION,
            ),
            self._ns(
                BalanceQualityFlag.HEALTHY_BALANCE_SHEET,
                BalanceQualityFlag.STRONG_LIQUIDITY,
                BalanceQualityFlag.STRONG_EQUITY_BASE,
            ),
            self._ns(
                CashFlowQualityFlag.STRONG_CASH_GENERATION,
                CashFlowQualityFlag.EXCELLENT_CASH_QUALITY,
                CashFlowQualityFlag.HEALTHY_CAPITAL_ALLOCATION,
            ),
            self._ns(
                RatioQualityFlag.EXCELLENT_PROFITABILITY,
                RatioQualityFlag.STRONG_LIQUIDITY,
                RatioQualityFlag.STRONG_CASH_GENERATION,
                RatioQualityFlag.LOW_LEVERAGE,
            ),
            SimpleNamespace(
                quality_flags=(
                    TrendQualityFlag.CONSISTENT_COMPOUNDER,
                    TrendQualityFlag.STABLE_COMPOUND_GROWTH,
                    TrendQualityFlag.IMPROVING_BUSINESS,
                    TrendQualityFlag.CASH_FLOW_IMPROVING,
                    TrendQualityFlag.MARGIN_EXPANSION,
                )
            ),
        )
        assert AggregatedQualityFlag.EXCELLENT_FINANCIAL_HEALTH in flags2
        assert AggregatedQualityFlag.CONSISTENT_COMPOUNDER in flags2
        assert AggregatedQualityFlag.IMPROVING_FUNDAMENTALS in flags2

        # Deterioration overrides improving
        flags3 = eng._aggregate_flags(
            self._ns(QualityFlag.DECLINING_REVENUE, QualityFlag.MARGIN_COMPRESSION),
            self._ns(BalanceQualityFlag.HEALTHY_BALANCE_SHEET),
            self._ns(CashFlowQualityFlag.HEALTHY_CAPITAL_ALLOCATION),
            self._ns(RatioQualityFlag.LOW_LEVERAGE),
            SimpleNamespace(
                quality_flags=(
                    TrendQualityFlag.DETERIORATING_BUSINESS,
                    TrendQualityFlag.MARGIN_COMPRESSION,
                )
            ),
        )
        assert AggregatedQualityFlag.FINANCIAL_DETERIORATION in flags3
        assert AggregatedQualityFlag.IMPROVING_FUNDAMENTALS not in flags3

        # Healthy without excellent
        flags4 = eng._aggregate_flags(
            self._ns(),
            self._ns(BalanceQualityFlag.STRONG_EQUITY_BASE),
            self._ns(CashFlowQualityFlag.HEALTHY_CAPITAL_ALLOCATION),
            self._ns(RatioQualityFlag.LOW_LEVERAGE),
            None,
        )
        assert AggregatedQualityFlag.HEALTHY_FINANCIAL_POSITION in flags4

    def test_summary_branches(self) -> None:
        eng = FinancialAggregatorEngine()
        # Use real analysis then override flags for summary paths
        base = eng.analyze(_history(1.0, 1.1, 1.2))
        for flag_tuple, expect_health in (
            (
                (AggregatedQualityFlag.EXCELLENT_FINANCIAL_HEALTH,),
                "excellent_financial_health",
            ),
            (
                (AggregatedQualityFlag.HEALTHY_FINANCIAL_POSITION,),
                "healthy_financial_position",
            ),
            (
                (AggregatedQualityFlag.FINANCIAL_DETERIORATION,),
                "financial_deterioration",
            ),
            ((AggregatedQualityFlag.NEEDS_ATTENTION,), "needs_attention"),
        ):
            summary = eng._summary(
                base.income,
                base.balance_sheet,
                base.cash_flow,
                base.ratios,
                base.trends,
                ValidationResult(ok=True, checks=(), errors=(), warnings=()),
                flag_tuple,
            )
            assert summary.health_label == expect_health

        # Completeness / confidence branches
        many_warn = ValidationResult(
            ok=True,
            checks=(),
            errors=(),
            warnings=("a", "b", "c"),
        )
        s2 = eng._summary(
            base.income,
            base.balance_sheet,
            base.cash_flow,
            base.ratios,
            None,
            many_warn,
            (),
        )
        assert s2.data_completeness == "partial"
        assert s2.confidence_summary in {"medium", "low", "insufficient", "high"}

        # Force confidence ranking via fake metadata confidence attrs
        income = SimpleNamespace(
            revenue=base.income.revenue,
            quality_flags=(),
            metadata=SimpleNamespace(confidence="high"),
            explainability=(),
        )
        balance = SimpleNamespace(
            trend_summary=base.balance_sheet.trend_summary,
            quality_flags=(),
            metadata=SimpleNamespace(confidence="high"),
            explainability=(),
        )
        cash = SimpleNamespace(
            quality_flags=(),
            metadata=SimpleNamespace(confidence="medium"),
            explainability=(),
        )
        ratios = SimpleNamespace(
            quality_flags=(),
            metadata=SimpleNamespace(confidence="low"),
            explainability=(),
        )
        s3 = eng._summary(
            income,
            balance,
            cash,
            ratios,
            None,
            ValidationResult(ok=True, checks=(), errors=(), warnings=()),
            (AggregatedQualityFlag.CONSISTENT_COMPOUNDER,),
        )
        assert s3.confidence_summary in {"high", "medium"}
        assert s3.strengths

        s4 = eng._summary(
            SimpleNamespace(
                revenue=base.income.revenue,
                quality_flags=(),
                metadata=SimpleNamespace(confidence="insufficient"),
            ),
            SimpleNamespace(
                trend_summary=base.balance_sheet.trend_summary,
                quality_flags=(),
                metadata=SimpleNamespace(confidence="insufficient"),
            ),
            SimpleNamespace(quality_flags=(), metadata=SimpleNamespace()),
            SimpleNamespace(quality_flags=(), metadata=SimpleNamespace()),
            None,
            ValidationResult(ok=True, checks=(), errors=(), warnings=("x",)),
            (),
        )
        assert s4.confidence_summary in {"insufficient", "low"}


class TestExports:
    def test_package_surface(self) -> None:
        import financial

        assert financial.__version__ == "0.7.0"
        assert hasattr(financial, "analyze_financials") is False  # method on engine
        assert hasattr(financial.FinancialEngine, "analyze_financials")
        assert hasattr(financial, "FinancialAnalysis")
        assert hasattr(financial, "AGGREGATOR_RESEARCH_DISCLAIMER")
