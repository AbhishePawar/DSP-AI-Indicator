"""Cash Flow Intelligence tests — target 100% module coverage."""

from __future__ import annotations

import time
from datetime import date

import pytest

from financial import (
    FINANCIAL_VERSION,
    CashFlowAnalysis,
    CashFlowAnalysisError,
    CashFlowEngine,
    CashFlowQualityFlag,
    CashFlowStatement,
    CompanyMetadata,
    CurrencyCode,
    CurrencyRef,
    FinancialEngine,
    FinancialPeriod,
    FinancialSnapshot,
    FinancialStatements,
    GrowthInvestmentClass,
    IncomeStatement,
    PeriodType,
    TrendDirection,
    UnitScale,
    validate_cashflow_for_analysis,
)
from financial.intelligence.cashflow_engine import (
    CASHFLOW_INTELLIGENCE_VERSION,
    _clip01,
    _growth,
    _safe_div,
    _stability,
    _trend_from_delta,
)
from financial.intelligence.cashflow_explainability import CASHFLOW_RESEARCH_DISCLAIMER
from financial.intelligence.cashflow_validation import (
    _computed_fcf,
    coerce_cashflow_series,
)
from financial.metadata import StatementMetadata


def _period(*, end: date = date(2024, 12, 31), fy: int | None = 2024) -> FinancialPeriod:
    return FinancialPeriod(
        period_type=PeriodType.ANNUAL,
        period_end=end,
        fiscal_year=fy,
        currency=CurrencyRef(CurrencyCode.USD),
    )


def _cf(**kwargs) -> CashFlowStatement:
    data = dict(
        operating_cash_flow=200.0,
        capex=-50.0,
        acquisitions=-10.0,
        investments=-5.0,
        asset_sales=5.0,
        investing_cash_flow=-60.0,
        debt_issued=20.0,
        debt_repaid=-30.0,
        dividends_paid=-40.0,
        share_buybacks=-20.0,
        share_issuance=0.0,
        financing_cash_flow=-70.0,
        fx_effects=0.0,
        net_cash_change=70.0,
        free_cash_flow=150.0,
        owner_earnings=140.0,
    )
    data.update(kwargs)
    return CashFlowStatement(**data)


def _stmt(
    cf: CashFlowStatement,
    period: FinancialPeriod | None = None,
    *,
    revenue: float | None = 1000.0,
) -> FinancialStatements:
    return FinancialStatements(
        period=period or _period(),
        income_statement=IncomeStatement(revenue=revenue, net_income=100.0),
        cash_flow=cf,
        statement_metadata=StatementMetadata(unit_scale=UnitScale.MILLIONS),
    )


def _snap(*items: tuple[CashFlowStatement, FinancialPeriod]) -> FinancialSnapshot:
    return FinancialSnapshot(
        company=CompanyMetadata(company="Acme", ticker="ACM"),
        statements=tuple(_stmt(cf, per) for cf, per in items),
    )


class TestValidation:
    def test_missing_ocf(self) -> None:
        with pytest.raises(CashFlowAnalysisError, match="Missing operating_cash_flow"):
            validate_cashflow_for_analysis(CashFlowStatement(capex=-1.0))

    def test_nan_inf(self) -> None:
        with pytest.raises(CashFlowAnalysisError, match="NaN"):
            validate_cashflow_for_analysis(
                CashFlowStatement(operating_cash_flow=float("nan"))
            )
        with pytest.raises(CashFlowAnalysisError, match="infinite"):
            validate_cashflow_for_analysis(
                CashFlowStatement(operating_cash_flow=float("inf"))
            )

    def test_invalid_fcf(self) -> None:
        with pytest.raises(CashFlowAnalysisError, match="Invalid FCF"):
            validate_cashflow_for_analysis(
                CashFlowStatement(
                    operating_cash_flow=100.0,
                    capex=-20.0,
                    free_cash_flow=500.0,
                )
            )

    def test_all_zero_warning(self) -> None:
        result = validate_cashflow_for_analysis(
            CashFlowStatement(
                operating_cash_flow=0.0,
                capex=0.0,
                free_cash_flow=0.0,
            )
        )
        assert "all cash-flow line items are zero" in result.warnings

    def test_with_statements_ok(self) -> None:
        stmt = _stmt(_cf())
        assert validate_cashflow_for_analysis(stmt.cash_flow, statements=stmt).ok

    def test_statements_domain_error(self) -> None:
        from financial.balance_sheet import BalanceSheet

        bad = FinancialStatements(
            period=_period(),
            income_statement=IncomeStatement(revenue=float("nan")),
            cash_flow=_cf(),
            balance_sheet=BalanceSheet(
                total_assets=100.0, total_liabilities=40.0, total_equity=60.0
            ),
        )
        with pytest.raises(CashFlowAnalysisError, match="NaN"):
            validate_cashflow_for_analysis(bad.cash_flow, statements=bad)


class TestCoerce:
    def test_cf_only(self) -> None:
        f, s, _ = coerce_cashflow_series(_cf())
        assert len(f) == 1 and s[0] is None

    def test_statements_snapshot_dicts(self) -> None:
        assert coerce_cashflow_series(_stmt(_cf()))[2]["period_end"] == "2024-12-31"
        assert coerce_cashflow_series(_stmt(_cf()))[2]["revenue"] == 1000.0
        snap = _snap(
            (_cf(operating_cash_flow=100.0, free_cash_flow=50.0, capex=-50.0), _period(end=date(2023, 12, 31), fy=2023)),
            (_cf(), _period()),
        )
        snap2 = FinancialSnapshot(company=snap.company, statements=(snap.statements[1], snap.statements[0]))
        flows, _, meta = coerce_cashflow_series(snap2)
        assert flows[0].operating_cash_flow == 100.0
        assert meta["ticker"] == "ACM"
        assert coerce_cashflow_series(_cf().to_dict())[0][0].operating_cash_flow == 200.0
        assert coerce_cashflow_series(_stmt(_cf()).to_dict())[0][0].operating_cash_flow == 200.0
        assert coerce_cashflow_series(snap.to_dict())[0][-1].operating_cash_flow == 200.0

    def test_empty_and_dupes(self) -> None:
        with pytest.raises(CashFlowAnalysisError, match="Empty"):
            coerce_cashflow_series(FinancialSnapshot())
        with pytest.raises(CashFlowAnalysisError, match="Duplicate"):
            coerce_cashflow_series(
                FinancialSnapshot(statements=(_stmt(_cf()), _stmt(_cf(capex=-1.0))))
            )
        with pytest.raises(CashFlowAnalysisError, match="Unsupported"):
            coerce_cashflow_series({"foo": 1})
        with pytest.raises(CashFlowAnalysisError, match="Empty history"):
            coerce_cashflow_series([])
        with pytest.raises(CashFlowAnalysisError, match="History items"):
            coerce_cashflow_series([object()])  # type: ignore[list-item]
        with pytest.raises(CashFlowAnalysisError, match="Accept ONLY"):
            coerce_cashflow_series(object())  # type: ignore[arg-type]

    def test_sequence_sort_dupes(self) -> None:
        series = [
            _stmt(_cf(), _period(end=date(2024, 12, 31), fy=2024)),
            _stmt(
                _cf(operating_cash_flow=100.0, free_cash_flow=50.0, capex=-50.0),
                _period(end=date(2023, 12, 31), fy=2023),
            ),
        ]
        flows, _, meta = coerce_cashflow_series(series)
        assert flows[0].operating_cash_flow == 100.0
        assert meta["period_end"] == "2024-12-31"
        with pytest.raises(CashFlowAnalysisError, match="Duplicate"):
            coerce_cashflow_series([_stmt(_cf()), _stmt(_cf(capex=-2.0))])

    def test_mixed_sequence(self) -> None:
        flows, stmts, _ = coerce_cashflow_series([_cf(operating_cash_flow=50.0), _stmt(_cf())])
        assert len(flows) == 2 and stmts[0] is None


class TestAnalysis:
    def test_single_strong(self) -> None:
        eng = CashFlowEngine()
        result = eng.analyze(_cf())
        assert isinstance(result, CashFlowAnalysis)
        assert result.operating.operating_cash_flow == 200.0
        assert result.free_cash_flow.free_cash_flow == 150.0
        assert result.free_cash_flow.fcf_source == "reported"
        assert result.free_cash_flow.owner_earnings == 140.0
        assert result.investing.growth_investment_class is GrowthInvestmentClass.MAINTENANCE
        assert CASHFLOW_RESEARCH_DISCLAIMER in result.research_disclaimer
        assert result.metadata.engine_version == CASHFLOW_INTELLIGENCE_VERSION
        d = result.to_dict()
        assert "operating" in d and d["quality_flags"] is not None

    def test_computed_fcf(self) -> None:
        eng = CashFlowEngine()
        result = eng.analyze(
            CashFlowStatement(operating_cash_flow=100.0, capex=-30.0)
        )
        assert result.free_cash_flow.free_cash_flow == pytest.approx(70.0)
        assert result.free_cash_flow.fcf_source == "computed_ocf_minus_abs_capex"

    def test_multi_period_growth_and_trends(self) -> None:
        eng = CashFlowEngine()
        snap = _snap(
            (
                CashFlowStatement(
                    operating_cash_flow=100.0,
                    capex=-40.0,
                    free_cash_flow=60.0,
                    debt_issued=80.0,
                    debt_repaid=-10.0,
                    dividends_paid=0.0,
                ),
                _period(end=date(2023, 12, 31), fy=2023),
            ),
            (
                _cf(),
                _period(end=date(2024, 12, 31), fy=2024),
            ),
        )
        result = eng.analyze(snap)
        assert result.operating.operating_cash_flow_growth == pytest.approx(1.0)
        assert result.free_cash_flow.fcf_growth is not None
        assert result.free_cash_flow.fcf_margin == pytest.approx(0.15)
        assert result.metadata.company == "Acme"
        assert result.trend_summary.operating_cash_flow is TrendDirection.IMPROVING
        assert CashFlowQualityFlag.STRONG_CASH_GENERATION in result.quality_flags
        assert CashFlowQualityFlag.SHAREHOLDER_FRIENDLY in result.quality_flags

    def test_warning_flags(self) -> None:
        eng = CashFlowEngine()
        result = eng.analyze(
            CashFlowStatement(
                operating_cash_flow=-50.0,
                capex=-80.0,
                free_cash_flow=-130.0,
                debt_issued=200.0,
                debt_repaid=0.0,
                dividends_paid=-10.0,
            )
        )
        assert CashFlowQualityFlag.WEAK_CASH_GENERATION in result.quality_flags
        assert CashFlowQualityFlag.NEGATIVE_FREE_CASH_FLOW in result.quality_flags
        assert CashFlowQualityFlag.HEAVY_CAPEX in result.quality_flags
        assert CashFlowQualityFlag.AGGRESSIVE_DEBT_FUNDING in result.quality_flags
        assert CashFlowQualityFlag.CASH_FLOW_WARNING in result.quality_flags

    def test_growth_classes(self) -> None:
        eng = CashFlowEngine()
        maint = eng.analyze(CashFlowStatement(operating_cash_flow=100.0, capex=-20.0))
        assert maint.investing.growth_investment_class is GrowthInvestmentClass.MAINTENANCE
        growth = eng.analyze(CashFlowStatement(operating_cash_flow=100.0, capex=-50.0))
        assert growth.investing.growth_investment_class is GrowthInvestmentClass.GROWTH
        agg = eng.analyze(CashFlowStatement(operating_cash_flow=100.0, capex=-90.0))
        assert agg.investing.growth_investment_class is GrowthInvestmentClass.AGGRESSIVE_GROWTH
        divest = eng.analyze(
            CashFlowStatement(
                operating_cash_flow=100.0,
                capex=-10.0,
                investing_cash_flow=40.0,
            )
        )
        assert divest.investing.growth_investment_class is GrowthInvestmentClass.NET_DIVESTING

    def test_history_and_composed_investing(self) -> None:
        eng = CashFlowEngine()
        result = eng.analyze(
            CashFlowStatement(
                operating_cash_flow=120.0,
                capex=-30.0,
                acquisitions=-5.0,
                free_cash_flow=90.0,
            ),
            history=[
                CashFlowStatement(operating_cash_flow=100.0, capex=-25.0, free_cash_flow=75.0)
            ],
        )
        assert result.metadata.periods_used == 2
        assert result.investing.investment_activity == pytest.approx(-35.0)

    def test_excellent_quality(self) -> None:
        eng = CashFlowEngine()
        snap = _snap(
            (
                CashFlowStatement(
                    operating_cash_flow=180.0,
                    capex=-40.0,
                    free_cash_flow=140.0,
                    dividends_paid=-30.0,
                    share_buybacks=-20.0,
                    debt_issued=0.0,
                    debt_repaid=-10.0,
                ),
                _period(end=date(2023, 12, 31), fy=2023),
            ),
            (
                CashFlowStatement(
                    operating_cash_flow=220.0,
                    capex=-45.0,
                    free_cash_flow=175.0,
                    dividends_paid=-35.0,
                    share_buybacks=-25.0,
                    debt_issued=0.0,
                    debt_repaid=-15.0,
                    owner_earnings=160.0,
                ),
                _period(),
            ),
        )
        result = eng.analyze(snap)
        assert CashFlowQualityFlag.EXCELLENT_CASH_QUALITY in result.quality_flags
        assert CashFlowQualityFlag.HEALTHY_CAPITAL_ALLOCATION in result.quality_flags

    def test_sustainability_zero_div_buyback(self) -> None:
        eng = CashFlowEngine()
        result = eng.analyze(
            CashFlowStatement(
                operating_cash_flow=100.0,
                capex=-20.0,
                free_cash_flow=80.0,
                dividends_paid=0.0,
                share_buybacks=0.0,
            )
        )
        assert result.quality.dividend_sustainability == 1.0
        assert result.quality.buyback_sustainability == 1.0

    def test_debt_sust_repay(self) -> None:
        eng = CashFlowEngine()
        result = eng.analyze(
            CashFlowStatement(
                operating_cash_flow=100.0,
                free_cash_flow=80.0,
                capex=-20.0,
                debt_repaid=-50.0,
            )
        )
        # Net debt raise <= 0 → dependence 0 → sustainability 1.0
        assert result.quality.debt_sustainability == pytest.approx(1.0)

    def test_alloc_quality_branches(self) -> None:
        eng = CashFlowEngine()
        retain = eng.analyze(
            CashFlowStatement(operating_cash_flow=100.0, capex=-20.0, free_cash_flow=80.0)
        )
        assert retain.financing.capital_allocation_quality == pytest.approx(0.7)
        weak = eng.analyze(
            CashFlowStatement(
                operating_cash_flow=50.0,
                capex=-80.0,
                free_cash_flow=-30.0,
                dividends_paid=-30.0,
            )
        )
        assert weak.financing.capital_allocation_quality == pytest.approx(0.2)

    def test_fcf_unavailable_and_intensity_zero_ocf(self) -> None:
        eng = CashFlowEngine()
        no_fcf = eng.analyze(CashFlowStatement(operating_cash_flow=100.0))
        assert no_fcf.free_cash_flow.fcf_source == "unavailable"
        assert no_fcf.free_cash_flow.free_cash_flow is None
        zero_ocf = eng.analyze(
            CashFlowStatement(operating_cash_flow=0.0, capex=-10.0)
        )
        assert (
            zero_ocf.investing.growth_investment_class
            is GrowthInvestmentClass.INSUFFICIENT_DATA
        )


class TestHelpers:
    def test_math_helpers(self) -> None:
        assert _safe_div(None, 1) is None
        assert _safe_div(1, 0) is None
        assert _safe_div(1e308, 1e-308) is None
        assert _growth(10, 0) is None
        assert _clip01(None) is None
        assert _clip01(2.0) == 1.0
        assert _stability([0.0, 0.0]) == 1.0
        assert _stability([1.0, -1.0]) == 0.0
        assert _stability([1.0]) is None
        assert _trend_from_delta(None) is TrendDirection.STABLE
        assert _trend_from_delta(0.01) is TrendDirection.STABLE
        assert _trend_from_delta(0.05, improve_when_up=False) is TrendDirection.WEAKENING
        assert _computed_fcf(CashFlowStatement(operating_cash_flow=10.0)) is None
        assert _computed_fcf(
            CashFlowStatement(operating_cash_flow=10.0, capex=-3.0)
        ) == pytest.approx(7.0)

    def test_revenue_from_statement_not_meta(self) -> None:
        """History path still picks up revenue from primary FinancialStatements."""
        eng = CashFlowEngine()
        result = eng.analyze(
            _stmt(_cf(), revenue=2000.0),
            history=[CashFlowStatement(operating_cash_flow=150.0, free_cash_flow=100.0, capex=-50.0)],
        )
        assert result.free_cash_flow.fcf_margin == pytest.approx(150 / 2000)


class TestEngineFacade:
    def test_analyze_cash_flow(self) -> None:
        engine = FinancialEngine()
        result = engine.analyze_cash_flow(_cf())
        assert result.operating.operating_cash_flow == 200.0
        snap = _snap((_cf(), _period()))
        engine.validate(snap)
        assert engine.serialize(snap)["version"] == FINANCIAL_VERSION
        # prior APIs still work
        from financial.balance_sheet import BalanceSheet

        bal = engine.analyze_balance_sheet(
            BalanceSheet(
                total_assets=100.0,
                total_liabilities=40.0,
                total_equity=60.0,
                equity=60.0,
                current_assets=50.0,
                current_liabilities=20.0,
            )
        )
        assert bal.equity.book_value == 60.0

    def test_performance(self) -> None:
        engine = FinancialEngine()
        snap = _snap(
            *[
                (
                    _cf(operating_cash_flow=100.0 + i * 10, free_cash_flow=70.0 + i * 5),
                    _period(end=date(2020 + i, 12, 31), fy=2020 + i),
                )
                for i in range(4)
            ]
        )
        engine.analyze_cash_flow(snap)
        start = time.perf_counter()
        for _ in range(50):
            engine.analyze_cash_flow(snap)
        avg_ms = (time.perf_counter() - start) / 50 * 1000
        assert avg_ms < 20.0, f"avg {avg_ms:.2f} ms"

    def test_metric_dicts(self) -> None:
        result = CashFlowEngine().analyze(
            _snap(
                (
                    CashFlowStatement(
                        operating_cash_flow=90.0,
                        capex=-30.0,
                        free_cash_flow=60.0,
                        debt_issued=40.0,
                        debt_repaid=-5.0,
                    ),
                    _period(end=date(2023, 12, 31), fy=2023),
                ),
                (_cf(), _period()),
            )
        )
        assert result.operating.to_dict()["operating_cash_flow"] == 200.0
        assert result.investing.to_dict()["capex"] == -50.0
        assert result.financing.to_dict()["dividends_paid"] == -40.0
        assert result.free_cash_flow.to_dict()["fcf_source"] == "reported"
        assert result.quality.to_dict()["cash_sustainability"] is not None
        assert result.trend_summary.to_dict()["debt_activity"]
        assert result.metadata.to_dict()["periods_used"] == 2
