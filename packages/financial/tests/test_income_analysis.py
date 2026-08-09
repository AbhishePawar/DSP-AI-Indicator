"""Income Statement Intelligence tests — target 100% module coverage."""

from __future__ import annotations

import time
from datetime import date

import pytest

from financial import (
    FINANCIAL_VERSION,
    CompanyMetadata,
    CurrencyCode,
    CurrencyRef,
    FinancialEngine,
    FinancialPeriod,
    FinancialSnapshot,
    FinancialStatements,
    IncomeAnalysisError,
    IncomeStatement,
    IncomeStatementAnalysis,
    IncomeStatementEngine,
    PeriodType,
    QualityFlag,
    RevenueTrendClass,
    TrendDirection,
    UnitScale,
    build_explanation,
    validate_income_for_analysis,
)
from financial.intelligence.income_engine import (
    INCOME_INTELLIGENCE_VERSION,
    _cagr,
    _growth,
    _safe_div,
    _stability,
)
from financial.intelligence.income_explainability import RESEARCH_DISCLAIMER
from financial.intelligence.income_validation import coerce_income_series
from financial.metadata import StatementMetadata


def _period(
    *,
    end: date = date(2024, 12, 31),
    period_type: PeriodType = PeriodType.ANNUAL,
    fy: int | None = 2024,
    fq: int | None = None,
) -> FinancialPeriod:
    return FinancialPeriod(
        period_type=period_type,
        period_end=end,
        fiscal_year=fy,
        fiscal_quarter=fq,
        currency=CurrencyRef(CurrencyCode.USD),
    )


def _income(**kwargs) -> IncomeStatement:
    data = dict(
        revenue=1000.0,
        cogs=400.0,
        gross_profit=600.0,
        operating_expenses=200.0,
        rd=50.0,
        sga=150.0,
        ebit=400.0,
        ebitda=450.0,
        depreciation=40.0,
        amortization=10.0,
        interest_expense=20.0,
        other_income=5.0,
        pretax_income=385.0,
        tax=77.0,
        net_income=308.0,
        eps=3.08,
        diluted_eps=3.00,
        weighted_shares=100.0,
    )
    data.update(kwargs)
    return IncomeStatement(**data)


def _stmt(income: IncomeStatement, period: FinancialPeriod | None = None) -> FinancialStatements:
    return FinancialStatements(
        period=period or _period(),
        income_statement=income,
        statement_metadata=StatementMetadata(unit_scale=UnitScale.MILLIONS),
    )


def _snapshot(*incomes_and_periods: tuple[IncomeStatement, FinancialPeriod]) -> FinancialSnapshot:
    stmts = tuple(_stmt(inc, per) for inc, per in incomes_and_periods)
    return FinancialSnapshot(
        company=CompanyMetadata(company="Acme", ticker="ACM"),
        statements=stmts,
    )


class TestExplainability:
    def test_build_explanation_defaults(self) -> None:
        exp = build_explanation(
            name="gross_margin",
            formula="gp/rev",
            inputs={"a": 1},
            result=0.5,
            interpretation="ok",
        )
        assert exp.confidence == "medium"
        assert exp.to_dict()["result"] == 0.5

    def test_invalid_confidence_normalized(self) -> None:
        exp = build_explanation(
            name="x",
            formula="y",
            inputs={},
            result=None,
            confidence="NOPE",
            interpretation="n/a",
        )
        assert exp.confidence == "medium"


class TestValidation:
    def test_missing_revenue(self) -> None:
        with pytest.raises(IncomeAnalysisError, match="Missing Revenue"):
            validate_income_for_analysis(IncomeStatement(net_income=1.0))

    def test_zero_revenue(self) -> None:
        with pytest.raises(IncomeAnalysisError, match="Divide-by-zero"):
            validate_income_for_analysis(IncomeStatement(revenue=0.0))

    def test_nan_rejected(self) -> None:
        with pytest.raises(IncomeAnalysisError, match="NaN"):
            validate_income_for_analysis(IncomeStatement(revenue=float("nan")))

    def test_inf_rejected(self) -> None:
        with pytest.raises(IncomeAnalysisError, match="infinite"):
            validate_income_for_analysis(IncomeStatement(revenue=float("inf")))

    def test_negative_shares(self) -> None:
        with pytest.raises(IncomeAnalysisError, match="Negative Shares"):
            validate_income_for_analysis(
                IncomeStatement(revenue=100.0, weighted_shares=-1.0)
            )

    def test_invalid_eps_zero_shares(self) -> None:
        with pytest.raises(IncomeAnalysisError, match="Invalid EPS"):
            validate_income_for_analysis(
                IncomeStatement(revenue=100.0, eps=1.0, weighted_shares=0.0)
            )

    def test_diluted_exceeds_basic(self) -> None:
        with pytest.raises(IncomeAnalysisError, match="diluted EPS"):
            validate_income_for_analysis(
                IncomeStatement(revenue=100.0, eps=1.0, diluted_eps=2.0)
            )

    def test_impossible_margin(self) -> None:
        with pytest.raises(IncomeAnalysisError, match="Impossible Margins"):
            validate_income_for_analysis(
                IncomeStatement(revenue=100.0, net_income=1000.0)
            )

    def test_negative_revenue_warning(self) -> None:
        result = validate_income_for_analysis(IncomeStatement(revenue=-50.0, net_income=-10.0))
        assert "negative revenue" in result.warnings

    def test_with_statements_ok(self) -> None:
        stmt = _stmt(_income())
        result = validate_income_for_analysis(stmt.income_statement, statements=stmt)
        assert result.ok

    def test_with_statements_propagates_domain_error(self) -> None:
        from financial.balance_sheet import BalanceSheet

        bad = FinancialStatements(
            period=_period(),
            income_statement=_income(),
            balance_sheet=BalanceSheet(
                total_assets=100.0, total_liabilities=10.0, total_equity=10.0
            ),
        )
        with pytest.raises(IncomeAnalysisError, match="accounting equation"):
            validate_income_for_analysis(bad.income_statement, statements=bad)


class TestCoerce:
    def test_income_only(self) -> None:
        incomes, stmts, meta = coerce_income_series(_income())
        assert len(incomes) == 1
        assert stmts[0] is None

    def test_statements(self) -> None:
        incomes, stmts, meta = coerce_income_series(_stmt(_income()))
        assert meta["period_end"] == "2024-12-31"
        assert stmts[0] is not None

    def test_snapshot_sorted(self) -> None:
        snap = _snapshot(
            (_income(revenue=800.0), _period(end=date(2023, 12, 31), fy=2023)),
            (_income(revenue=1000.0), _period(end=date(2024, 12, 31), fy=2024)),
        )
        # reverse order in construction — coerce sorts
        snap2 = FinancialSnapshot(
            company=snap.company,
            statements=(snap.statements[1], snap.statements[0]),
        )
        incomes, _, meta = coerce_income_series(snap2)
        assert incomes[0].revenue == 800.0
        assert incomes[-1].revenue == 1000.0
        assert meta["ticker"] == "ACM"

    def test_empty_snapshot(self) -> None:
        with pytest.raises(IncomeAnalysisError, match="Empty"):
            coerce_income_series(FinancialSnapshot())

    def test_dict_snapshot(self) -> None:
        snap = _snapshot((_income(), _period()))
        incomes, _, _ = coerce_income_series(snap.to_dict())
        assert incomes[0].revenue == 1000.0

    def test_dict_statements(self) -> None:
        incomes, _, _ = coerce_income_series(_stmt(_income()).to_dict())
        assert len(incomes) == 1

    def test_dict_income(self) -> None:
        incomes, _, _ = coerce_income_series({"revenue": 10.0, "net_income": 1.0})
        assert incomes[0].revenue == 10.0

    def test_bad_dict(self) -> None:
        with pytest.raises(IncomeAnalysisError, match="Unsupported"):
            coerce_income_series({"foo": 1})

    def test_sequence_mixed(self) -> None:
        incomes, stmts, _ = coerce_income_series(
            [
                _stmt(_income(revenue=500.0), _period(end=date(2023, 12, 31), fy=2023)),
                _income(revenue=600.0),
            ]
        )
        assert len(incomes) == 2
        assert stmts[1] is None

    def test_empty_sequence(self) -> None:
        with pytest.raises(IncomeAnalysisError, match="Empty history"):
            coerce_income_series([])

    def test_bad_sequence_item(self) -> None:
        with pytest.raises(IncomeAnalysisError, match="History items"):
            coerce_income_series([object()])  # type: ignore[list-item]

    def test_sorted_statement_sequence(self) -> None:
        series = [
            _stmt(_income(revenue=900.0), _period(end=date(2024, 12, 31), fy=2024)),
            _stmt(_income(revenue=700.0), _period(end=date(2023, 12, 31), fy=2023)),
        ]
        incomes, _, meta = coerce_income_series(series)
        assert incomes[0].revenue == 700.0
        assert meta["period_end"] == "2024-12-31"

    def test_reject_provider_object(self) -> None:
        with pytest.raises(IncomeAnalysisError, match="Accept ONLY"):
            coerce_income_series(object())  # type: ignore[arg-type]


class TestAnalysisCore:
    def test_single_statement_margins(self) -> None:
        eng = IncomeStatementEngine()
        result = eng.analyze(_income())
        assert isinstance(result, IncomeStatementAnalysis)
        assert result.margins.gross_margin == pytest.approx(0.6)
        assert result.margins.net_margin == pytest.approx(0.308)
        assert result.expenses.cogs_pct == pytest.approx(0.4)
        assert result.trend_summary is TrendDirection.STABLE
        assert result.revenue.trend_class is RevenueTrendClass.INSUFFICIENT_HISTORY
        assert RESEARCH_DISCLAIMER in result.research_disclaimer
        assert result.metadata.engine_version == INCOME_INTELLIGENCE_VERSION
        d = result.to_dict()
        assert "quality_flags" in d
        assert d["margins"]["gross_margin"] == pytest.approx(0.6)

    def test_operating_margin_fallback(self) -> None:
        eng = IncomeStatementEngine()
        inc = IncomeStatement(revenue=100.0, operating_expenses=30.0, net_income=10.0)
        result = eng.analyze(inc)
        assert result.margins.operating_margin == pytest.approx(0.7)

    def test_multi_year_growth_and_flags(self) -> None:
        eng = IncomeStatementEngine()
        snap = _snapshot(
            (
                _income(revenue=800.0, ebit=200.0, net_income=150.0, eps=1.5, pretax_income=180.0, tax=30.0),
                _period(end=date(2022, 12, 31), fy=2022),
            ),
            (
                _income(revenue=900.0, ebit=270.0, net_income=200.0, eps=2.0, pretax_income=240.0, tax=40.0),
                _period(end=date(2023, 12, 31), fy=2023),
            ),
            (
                _income(
                    revenue=1080.0,
                    ebit=400.0,
                    net_income=300.0,
                    eps=3.0,
                    diluted_eps=2.9,
                    pretax_income=360.0,
                    tax=60.0,
                    interest_expense=10.0,
                    other_income=2.0,
                ),
                _period(end=date(2024, 12, 31), fy=2024),
            ),
        )
        result = eng.analyze(snap)
        assert result.revenue.revenue_growth == pytest.approx(0.2)
        assert result.revenue.yoy_growth == pytest.approx(0.2)
        assert result.revenue.cagr is not None
        assert result.growth.operating_leverage is not None
        assert QualityFlag.HEALTHY_GROWTH in result.quality_flags
        assert QualityFlag.MARGIN_EXPANSION in result.quality_flags
        assert result.trend_summary is TrendDirection.IMPROVING
        assert result.metadata.company == "Acme"
        assert result.consistency.revenue_consistency is not None
        assert any(e.name == "operating_leverage" for e in result.explainability)

    def test_declining_and_compression(self) -> None:
        eng = IncomeStatementEngine()
        snap = _snapshot(
            (
                _income(revenue=1000.0, net_income=200.0, ebit=250.0, eps=2.0),
                _period(end=date(2023, 12, 31), fy=2023),
            ),
            (
                _income(
                    revenue=800.0,
                    net_income=80.0,
                    ebit=100.0,
                    eps=0.8,
                    diluted_eps=0.75,
                    other_income=50.0,
                    pretax_income=90.0,
                ),
                _period(end=date(2024, 12, 31), fy=2024),
            ),
        )
        result = eng.analyze(snap)
        assert QualityFlag.DECLINING_REVENUE in result.quality_flags
        assert QualityFlag.MARGIN_COMPRESSION in result.quality_flags
        assert QualityFlag.WEAK_EARNINGS_QUALITY in result.quality_flags
        assert result.trend_summary is TrendDirection.WEAKENING
        assert result.consistency.one_time_items_detected is True

    def test_high_burdens_and_leverage(self) -> None:
        eng = IncomeStatementEngine()
        snap = _snapshot(
            (
                _income(revenue=1000.0, ebit=100.0, net_income=50.0, interest_expense=5.0, tax=20.0, pretax_income=80.0),
                _period(end=date(2023, 12, 31), fy=2023),
            ),
            (
                _income(
                    revenue=1100.0,
                    ebit=200.0,
                    net_income=60.0,
                    interest_expense=40.0,
                    tax=50.0,
                    pretax_income=100.0,
                    other_income=1.0,
                ),
                _period(end=date(2024, 12, 31), fy=2024),
            ),
        )
        result = eng.analyze(snap)
        assert QualityFlag.HIGH_OPERATING_LEVERAGE in result.quality_flags
        assert QualityFlag.HIGH_INTEREST_BURDEN in result.quality_flags
        assert QualityFlag.HIGH_TAX_BURDEN in result.quality_flags

    def test_qoq_and_yoy_quarterly(self) -> None:
        eng = IncomeStatementEngine()
        snap = _snapshot(
            (
                _income(revenue=200.0),
                _period(
                    end=date(2023, 3, 31),
                    period_type=PeriodType.QUARTERLY,
                    fy=2023,
                    fq=1,
                ),
            ),
            (
                _income(revenue=220.0),
                _period(
                    end=date(2023, 12, 31),
                    period_type=PeriodType.QUARTERLY,
                    fy=2023,
                    fq=4,
                ),
            ),
            (
                _income(revenue=250.0),
                _period(
                    end=date(2024, 3, 31),
                    period_type=PeriodType.QUARTERLY,
                    fy=2024,
                    fq=1,
                ),
            ),
        )
        result = eng.analyze(snap)
        assert result.revenue.qoq_growth == pytest.approx((250 - 220) / 220)
        assert result.revenue.yoy_growth == pytest.approx((250 - 200) / 200)

    def test_history_kwarg(self) -> None:
        eng = IncomeStatementEngine()
        result = eng.analyze(
            _income(revenue=1100.0),
            history=[_income(revenue=1000.0)],
        )
        assert result.revenue.revenue_growth == pytest.approx(0.1)

    def test_expense_trend(self) -> None:
        eng = IncomeStatementEngine()
        result = eng.analyze(
            [
                _income(revenue=1000.0, operating_expenses=300.0),
                _income(revenue=1000.0, operating_expenses=200.0),
            ]
        )
        assert result.expenses.expense_trend is TrendDirection.IMPROVING

    def test_expense_trend_weakening(self) -> None:
        eng = IncomeStatementEngine()
        result = eng.analyze(
            [
                _income(revenue=1000.0, operating_expenses=100.0),
                _income(revenue=1000.0, operating_expenses=250.0),
            ]
        )
        assert result.expenses.expense_trend is TrendDirection.WEAKENING

    def test_expense_trend_stable(self) -> None:
        eng = IncomeStatementEngine()
        result = eng.analyze(
            [
                _income(revenue=1000.0, operating_expenses=200.0),
                _income(revenue=1000.0, operating_expenses=205.0),
            ]
        )
        assert result.expenses.expense_trend is TrendDirection.STABLE

    def test_volatile_and_flat_trends(self) -> None:
        eng = IncomeStatementEngine()
        # volatile growth rates — revenue-only statements avoid default GP mismatch
        vols = [
            IncomeStatement(revenue=100.0, net_income=10.0),
            IncomeStatement(revenue=200.0, net_income=20.0),
            IncomeStatement(revenue=50.0, net_income=5.0),
            IncomeStatement(revenue=180.0, net_income=18.0),
        ]
        r = eng.analyze(vols)
        assert r.revenue.trend_class in (
            RevenueTrendClass.VOLATILE,
            RevenueTrendClass.ACCELERATING,
            RevenueTrendClass.DECELERATING,
            RevenueTrendClass.STEADY_GROWTH,
            RevenueTrendClass.DECLINING,
        )
        flat = eng.analyze(
            [
                IncomeStatement(revenue=100.0, net_income=10.0),
                IncomeStatement(revenue=100.5, net_income=10.0),
            ]
        )
        assert flat.revenue.trend_class is RevenueTrendClass.FLAT

    def test_accelerating_decelerating(self) -> None:
        eng = IncomeStatementEngine()
        acc = eng.analyze(
            [
                IncomeStatement(revenue=100.0, net_income=10.0),
                IncomeStatement(revenue=105.0, net_income=11.0),
                IncomeStatement(revenue=130.0, net_income=15.0),
            ]
        )
        assert acc.revenue.trend_class is RevenueTrendClass.ACCELERATING
        dec = eng.analyze(
            [
                IncomeStatement(revenue=100.0, net_income=10.0),
                IncomeStatement(revenue=130.0, net_income=15.0),
                IncomeStatement(revenue=135.0, net_income=16.0),
            ]
        )
        assert dec.revenue.trend_class is RevenueTrendClass.DECELERATING

    def test_strong_earnings_quality(self) -> None:
        eng = IncomeStatementEngine()
        snap = _snapshot(
            (
                _income(revenue=1000.0, net_income=200.0, other_income=1.0, pretax_income=250.0, tax=50.0),
                _period(end=date(2023, 12, 31), fy=2023),
            ),
            (
                _income(revenue=1100.0, net_income=220.0, other_income=1.0, pretax_income=275.0, tax=55.0),
                _period(end=date(2024, 12, 31), fy=2024),
            ),
        )
        result = eng.analyze(snap)
        assert QualityFlag.STRONG_EARNINGS_QUALITY in result.quality_flags

    def test_tax_one_time_heuristic(self) -> None:
        eng = IncomeStatementEngine()
        result = eng.analyze(
            _income(revenue=1000.0, pretax_income=100.0, tax=70.0, net_income=30.0, other_income=0.0)
        )
        assert result.consistency.one_time_items_detected is True

    def test_stability_zero_mean_edge(self) -> None:
        eng = IncomeStatementEngine()
        # revenue growth from positive to force paths; net income oscillating around zero
        result = eng.analyze(
            [
                _income(revenue=100.0, net_income=-10.0, eps=-0.1),
                _income(revenue=110.0, net_income=10.0, eps=0.1),
                _income(revenue=120.0, net_income=-10.0, eps=-0.1),
            ]
        )
        assert result.profitability.earnings_consistency is not None

    def test_cagr_skips_non_positive(self) -> None:
        eng = IncomeStatementEngine()
        result = eng.analyze(
            [
                IncomeStatement(revenue=-100.0, net_income=-1.0),
                IncomeStatement(revenue=100.0, net_income=1.0),
            ]
        )
        # first period fails validation on primary... primary is last so ok
        # but cagr None due to start <= 0
        assert result.revenue.cagr is None

    def test_interest_tax_fallback_to_revenue(self) -> None:
        eng = IncomeStatementEngine()
        result = eng.analyze(
            IncomeStatement(
                revenue=1000.0,
                interest_expense=50.0,
                tax=40.0,
                net_income=100.0,
            )
        )
        assert result.consistency.interest_burden == pytest.approx(0.05)
        assert result.consistency.tax_burden == pytest.approx(0.04)


class TestFinancialEngineIntegration:
    def test_analyze_income_statement_facade(self) -> None:
        engine = FinancialEngine()
        result = engine.analyze_income_statement(_income())
        assert result.margins.gross_margin == pytest.approx(0.6)
        # F2.1 APIs still work
        snap = _snapshot((_income(), _period()))
        engine.validate(snap)
        assert engine.serialize(snap)["version"] == FINANCIAL_VERSION

    def test_performance_under_20ms(self) -> None:
        engine = FinancialEngine()
        snap = _snapshot(
            *[
                (
                    _income(revenue=800.0 + i * 50),
                    _period(end=date(2020 + i, 12, 31), fy=2020 + i),
                )
                for i in range(5)
            ]
        )
        # warm-up
        engine.analyze_income_statement(snap)
        start = time.perf_counter()
        for _ in range(50):
            engine.analyze_income_statement(snap)
        elapsed_ms = (time.perf_counter() - start) / 50 * 1000
        assert elapsed_ms < 20.0, f"avg {elapsed_ms:.2f} ms"


class TestHelpersAndEdges:
    def test_safe_div_and_growth_edges(self) -> None:
        assert _safe_div(None, 1.0) is None
        assert _safe_div(1.0, 0.0) is None
        assert _safe_div(1e308, 1e-308) is None  # overflow → inf → None
        assert _growth(10.0, 0.0) is None
        assert _cagr(100.0, 200.0, 0) is None
        assert _cagr(None, 200.0, 1) is None
        assert _stability([0.0, 0.0, 0.0]) == 1.0
        assert _stability([1.0]) is None

    def test_classify_edge_paths(self) -> None:
        assert (
            IncomeStatementEngine._classify_revenue_trend([0.1, 0.2], None)
            is RevenueTrendClass.INSUFFICIENT_HISTORY
        )
        assert (
            IncomeStatementEngine._classify_revenue_trend([0.05], -0.015)
            is RevenueTrendClass.DECLINING
        )
        # Extreme oscillation → low stability → VOLATILE
        assert (
            IncomeStatementEngine._classify_revenue_trend(
                [1.0, -1.0, 1.0, -1.0, 1.0, -1.0], 1.0
            )
            is RevenueTrendClass.VOLATILE
        )

    def test_prior_zero_revenue_growth_none(self) -> None:
        eng = IncomeStatementEngine()
        result = eng.analyze(
            [
                IncomeStatement(revenue=0.0, net_income=0.0),
                IncomeStatement(revenue=100.0, net_income=10.0),
            ]
        )
        assert result.revenue.revenue_growth is None

    def test_yoy_skips_none_stmt_slots(self) -> None:
        eng = IncomeStatementEngine()
        result = eng.analyze(
            [
                _stmt(
                    IncomeStatement(revenue=400.0, net_income=40.0),
                    _period(end=date(2021, 12, 31), fy=2021),
                ),
                IncomeStatement(revenue=500.0, net_income=50.0),  # None period slot
                _stmt(
                    IncomeStatement(revenue=700.0, net_income=70.0),
                    _period(end=date(2022, 12, 31), fy=2022),
                ),
                _stmt(
                    IncomeStatement(revenue=1000.0, net_income=100.0),
                    _period(end=date(2024, 12, 31), fy=2024),
                ),
            ]
        )
        # YoY scan walks past the None slot (no FY-1=2023 peer).
        # Sequential period growth must not silently fill YoY (CV-001).
        assert result.revenue.revenue == 1000.0
        assert result.revenue.yoy_growth is None
        assert result.revenue.revenue_growth is not None

    def test_other_income_vs_revenue_fallback(self) -> None:
        eng = IncomeStatementEngine()
        result = eng.analyze(
            IncomeStatement(revenue=1000.0, other_income=50.0, net_income=100.0)
        )
        assert result.consistency.other_income_dependence == pytest.approx(0.05)

    def test_margin_overflow_non_finite(self) -> None:
        with pytest.raises(IncomeAnalysisError, match="non-finite"):
            validate_income_for_analysis(
                IncomeStatement(revenue=1e-308, net_income=1e308)
            )


class TestMetricModelsDict:
    def test_all_metric_to_dict(self) -> None:
        eng = IncomeStatementEngine()
        result = eng.analyze(
            _snapshot(
                (_income(revenue=900.0), _period(end=date(2023, 12, 31), fy=2023)),
                (_income(revenue=1000.0), _period(end=date(2024, 12, 31), fy=2024)),
            )
        )
        assert result.revenue.to_dict()["trend_class"]
        assert "gross_margin" in result.margins.to_dict()
        assert "cogs_pct" in result.expenses.to_dict()
        assert "eps" in result.profitability.to_dict()
        assert "operating_leverage" in result.growth.to_dict()
        assert "one_time_items_detected" in result.consistency.to_dict()
        assert result.metadata.to_dict()["periods_used"] == 2
