"""Financial Ratio Engine tests — target 100% module coverage."""

from __future__ import annotations

import time
from datetime import date

import pytest

from financial import (
    FINANCIAL_VERSION,
    BalanceSheet,
    BenchmarkClass,
    CashFlowStatement,
    CompanyMetadata,
    CurrencyCode,
    CurrencyRef,
    FinancialEngine,
    FinancialPeriod,
    FinancialRatioAnalysis,
    FinancialRatioEngine,
    FinancialRatioError,
    FinancialSnapshot,
    FinancialStatements,
    IncomeStatement,
    PeriodType,
    RatioQualityFlag,
    TrendDirection,
    UnitScale,
    validate_ratio_inputs,
)
from financial.intelligence.ratio_engine import (
    RATIO_INTELLIGENCE_VERSION,
    _benchmark_margin,
    _benchmark_ratio,
    _clip01,
    _confidence,
    _safe_div,
    _trend,
)
from financial.intelligence.ratio_explainability import RATIO_RESEARCH_DISCLAIMER
from financial.intelligence.ratio_validation import coerce_ratio_series
from financial.metadata import StatementMetadata
from financial.derivation import (
    FORMULA_ASSET_TURNOVER,
    FORMULA_AVERAGE_BALANCE,
    FORMULA_CASH_RATIO,
    FORMULA_CURRENT_RATIO,
    FORMULA_DEBT_COVERAGE,
    FORMULA_DEBT_TO_ASSETS,
    FORMULA_DEBT_TO_EQUITY,
    FORMULA_DIVIDEND_COVERAGE,
    FORMULA_FCF_MARGIN,
    FORMULA_GROSS_MARGIN,
    FORMULA_NET_DEBT,
    FORMULA_NET_MARGIN,
    FORMULA_OPERATING_MARGIN,
    FORMULA_QUICK_RATIO,
    FORMULA_ROA,
    FORMULA_ROE,
    FORMULA_ROIC,
    FORMULA_WORKING_CAPITAL_RATIO,
    FORMULA_WORKING_CAPITAL_TURNOVER,
    DerivationInput,
    FinancialValueStatus,
    as_reported,
)


def _period(*, end: date = date(2024, 12, 31), fy: int | None = 2024) -> FinancialPeriod:
    return FinancialPeriod(
        period_type=PeriodType.ANNUAL,
        period_end=end,
        fiscal_year=fy,
        currency=CurrencyRef(CurrencyCode.USD),
    )


def _full(**kwargs) -> FinancialStatements:
    income = kwargs.pop("income", None) or IncomeStatement(
        revenue=1000.0,
        cogs=400.0,
        gross_profit=600.0,
        ebit=300.0,
        ebitda=350.0,
        interest_expense=20.0,
        pretax_income=280.0,
        tax=70.0,
        net_income=210.0,
        weighted_shares=100.0,
        eps=2.1,
    )
    balance = kwargs.pop("balance", None) or BalanceSheet(
        cash=150.0,
        short_term_investments=50.0,
        accounts_receivable=120.0,
        inventory=80.0,
        current_assets=450.0,
        ppe=400.0,
        goodwill=50.0,
        intangibles=50.0,
        total_assets=1000.0,
        accounts_payable=60.0,
        short_term_debt=50.0,
        current_liabilities=200.0,
        long_term_debt=200.0,
        total_liabilities=400.0,
        retained_earnings=300.0,
        equity=600.0,
        total_equity=600.0,
    )
    cash = kwargs.pop("cash", None) or CashFlowStatement(
        operating_cash_flow=250.0,
        capex=-80.0,
        free_cash_flow=170.0,
        dividends_paid=-50.0,
        share_buybacks=-30.0,
        debt_issued=10.0,
        debt_repaid=-40.0,
    )
    period = kwargs.pop("period", None) or _period()
    return FinancialStatements(
        period=period,
        income_statement=income,
        balance_sheet=balance,
        cash_flow=cash,
        statement_metadata=StatementMetadata(unit_scale=UnitScale.MILLIONS),
    )


def _bs(**overrides) -> BalanceSheet:
    """Full-fixture balance sheet with explicit field overrides (including None)."""
    fields = dict(
        cash=150.0,
        short_term_investments=50.0,
        accounts_receivable=120.0,
        inventory=80.0,
        current_assets=450.0,
        ppe=400.0,
        goodwill=50.0,
        intangibles=50.0,
        total_assets=1000.0,
        accounts_payable=60.0,
        short_term_debt=50.0,
        current_liabilities=200.0,
        long_term_debt=200.0,
        total_liabilities=400.0,
        retained_earnings=300.0,
        equity=600.0,
        total_equity=600.0,
    )
    fields.update(overrides)
    return BalanceSheet(**fields)


def _snap(*stmts: FinancialStatements) -> FinancialSnapshot:
    return FinancialSnapshot(
        company=CompanyMetadata(company="Acme", ticker="ACM"),
        statements=stmts,
    )


class TestValidation:
    def test_missing_revenue(self) -> None:
        stmt = _full(income=IncomeStatement(net_income=10.0))
        with pytest.raises(FinancialRatioError, match="revenue"):
            validate_ratio_inputs(stmt)

    def test_zero_revenue(self) -> None:
        stmt = _full(income=IncomeStatement(revenue=0.0, net_income=0.0))
        with pytest.raises(FinancialRatioError, match="Divide-by-zero"):
            validate_ratio_inputs(stmt)

    def test_zero_assets(self) -> None:
        stmt = _full(
            balance=BalanceSheet(total_assets=0.0, total_liabilities=0.0, total_equity=0.0)
        )
        with pytest.raises(FinancialRatioError, match="total_assets"):
            validate_ratio_inputs(stmt)

    def test_impossible_margin(self) -> None:
        stmt = _full(income=IncomeStatement(revenue=100.0, net_income=900.0))
        with pytest.raises(FinancialRatioError, match="Impossible"):
            validate_ratio_inputs(stmt)

    def test_nan(self) -> None:
        stmt = _full(income=IncomeStatement(revenue=float("nan")))
        with pytest.raises(FinancialRatioError, match="NaN"):
            validate_ratio_inputs(stmt)

    def test_domain_error(self) -> None:
        stmt = _full(
            balance=BalanceSheet(
                total_assets=100.0, total_liabilities=10.0, total_equity=10.0, equity=10.0
            )
        )
        with pytest.raises(FinancialRatioError):
            validate_ratio_inputs(stmt)

    def test_ok(self) -> None:
        assert validate_ratio_inputs(_full()).ok


class TestCoerce:
    def test_statements_snapshot_dicts(self) -> None:
        stmts, meta = coerce_ratio_series(_full())
        assert meta["period_end"] == "2024-12-31"
        snap = _snap(
            _full(period=_period(end=date(2023, 12, 31), fy=2023)),
            _full(),
        )
        # reverse
        snap2 = FinancialSnapshot(company=snap.company, statements=(snap.statements[1], snap.statements[0]))
        ordered, meta = coerce_ratio_series(snap2)
        assert ordered[0].period.fiscal_year == 2023
        assert meta["ticker"] == "ACM"
        assert coerce_ratio_series(_full().to_dict())[0][0].income_statement.revenue == 1000.0
        assert coerce_ratio_series(snap.to_dict())[1]["company"] == "Acme"

    def test_errors(self) -> None:
        with pytest.raises(FinancialRatioError, match="Unsupported"):
            coerce_ratio_series({"foo": 1})
        with pytest.raises(FinancialRatioError, match="Empty"):
            coerce_ratio_series(FinancialSnapshot())
        with pytest.raises(FinancialRatioError, match="Duplicate"):
            coerce_ratio_series(_snap(_full(), _full(income=IncomeStatement(revenue=900.0, net_income=100.0))))
        with pytest.raises(FinancialRatioError, match="Empty history"):
            coerce_ratio_series([])
        with pytest.raises(FinancialRatioError, match="History items"):
            coerce_ratio_series([object()])  # type: ignore[list-item]
        with pytest.raises(FinancialRatioError, match="Accept ONLY"):
            coerce_ratio_series(object())  # type: ignore[arg-type]

    def test_sequence_sort_dupes(self) -> None:
        series = [
            _full(period=_period(end=date(2024, 12, 31), fy=2024)),
            _full(period=_period(end=date(2023, 12, 31), fy=2023)),
        ]
        stmts, meta = coerce_ratio_series(series)
        assert stmts[0].period.fiscal_year == 2023
        assert meta["period_end"] == "2024-12-31"
        with pytest.raises(FinancialRatioError, match="Duplicate"):
            coerce_ratio_series([_full(), _full()])


class TestAnalysis:
    def test_single_period(self) -> None:
        eng = FinancialRatioEngine()
        result = eng.analyze(_full())
        assert isinstance(result, FinancialRatioAnalysis)
        names = {m.name for m in result.profitability}
        assert {"gross_margin", "roa", "roe", "roic"}.issubset(names)
        assert any(m.name == "current_ratio" for m in result.liquidity)
        assert any(m.name == "debt_to_equity" for m in result.leverage)
        assert any(m.name == "asset_turnover" for m in result.efficiency)
        assert any(m.name == "free_cash_flow_margin" for m in result.cash_flow)
        assert any(m.name == "book_value_per_share" for m in result.shareholder)
        assert result.capital_allocation.capital_allocation_score is not None
        assert RATIO_RESEARCH_DISCLAIMER in result.research_disclaimer
        assert result.metadata.engine_version == RATIO_INTELLIGENCE_VERSION
        d = result.to_dict()
        assert "profitability" in d and d["metadata"]["composed_from"]

    def test_multi_period_flags(self) -> None:
        eng = FinancialRatioEngine()
        prior = _full(
            period=_period(end=date(2023, 12, 31), fy=2023),
            income=IncomeStatement(
                revenue=900.0,
                cogs=400.0,
                gross_profit=500.0,
                ebit=200.0,
                ebitda=240.0,
                interest_expense=30.0,
                pretax_income=170.0,
                tax=40.0,
                net_income=130.0,
                weighted_shares=100.0,
            ),
        )
        result = eng.analyze(_snap(prior, _full()))
        assert result.metadata.periods_used == 2
        assert result.metadata.company == "Acme"
        assert RatioQualityFlag.EXCELLENT_PROFITABILITY in result.quality_flags
        assert RatioQualityFlag.STRONG_LIQUIDITY in result.quality_flags
        assert RatioQualityFlag.LOW_LEVERAGE in result.quality_flags
        assert RatioQualityFlag.STRONG_CASH_GENERATION in result.quality_flags
        assert RatioQualityFlag.SHAREHOLDER_FRIENDLY in result.quality_flags
        assert any(m.trend is not None for m in result.profitability)

    def test_weak_flags(self) -> None:
        eng = FinancialRatioEngine()
        weak = _full(
            income=IncomeStatement(
                revenue=1000.0,
                cogs=900.0,
                gross_profit=100.0,
                ebit=20.0,
                ebitda=30.0,
                interest_expense=40.0,
                pretax_income=10.0,
                tax=2.0,
                net_income=8.0,
                weighted_shares=100.0,
            ),
            balance=BalanceSheet(
                cash=10.0,
                inventory=200.0,
                accounts_receivable=300.0,
                current_assets=400.0,
                ppe=200.0,
                total_assets=1000.0,
                current_liabilities=500.0,
                short_term_debt=300.0,
                long_term_debt=400.0,
                total_liabilities=800.0,
                equity=200.0,
                total_equity=200.0,
                accounts_payable=100.0,
            ),
            cash=CashFlowStatement(
                operating_cash_flow=20.0,
                capex=-90.0,
                free_cash_flow=-70.0,
                dividends_paid=-40.0,
                debt_issued=200.0,
            ),
        )
        result = eng.analyze(weak)
        assert RatioQualityFlag.WEAK_PROFITABILITY in result.quality_flags
        assert RatioQualityFlag.WEAK_LIQUIDITY in result.quality_flags
        assert RatioQualityFlag.HIGH_LEVERAGE in result.quality_flags
        assert RatioQualityFlag.WEAK_CASH_GENERATION in result.quality_flags
        assert RatioQualityFlag.CAPITAL_ALLOCATION_WARNING in result.quality_flags

    def test_edge_helpers_coverage(self) -> None:
        eng = FinancialRatioEngine()
        stmt = _full(
            balance=BalanceSheet(
                total_assets=1000.0,
                total_liabilities=400.0,
                equity=600.0,
                total_equity=600.0,
                current_liabilities=200.0,
            ),
            cash=CashFlowStatement(
                operating_cash_flow=200.0,
                capex=-50.0,
            ),
        )
        prior1 = _full(period=_period(end=date(2022, 12, 31), fy=2022))
        prior2 = _full(period=_period(end=date(2023, 12, 31), fy=2023))
        result = eng.analyze([prior1, prior2, stmt])
        assert any(m.confidence == "medium" for m in result.profitability)
        fcf_m = next(m for m in result.cash_flow if m.name == "free_cash_flow_margin")
        assert fcf_m.value == pytest.approx(0.15)
        eng._flags((), (), (), (), (), result.capital_allocation, eng._cash.analyze(stmt))
        assert _confidence(5, has_value=False) == "insufficient"
        assert _confidence(3, has_value=True) == "high"

    def test_inf_and_no_dividends_fallback(self) -> None:
        with pytest.raises(FinancialRatioError, match="infinite"):
            validate_ratio_inputs(
                _full(income=IncomeStatement(revenue=float("inf"), net_income=1.0))
            )
        eng = FinancialRatioEngine()
        result = eng.analyze(
            _full(
                cash=CashFlowStatement(
                    operating_cash_flow=200.0,
                    capex=-40.0,
                    free_cash_flow=160.0,
                )
            )
        )
        # No dividend/buyback activity fields → sustainability unavailable
        # (never invent perfect 1.0 merely because FCF exists).
        assert result.capital_allocation.dividend_sustainability is None
        assert result.capital_allocation.buyback_sustainability is None

    def test_missing_total_assets(self) -> None:
        with pytest.raises(FinancialRatioError, match="total_assets"):
            validate_ratio_inputs(
                _full(balance=BalanceSheet(cash=1.0, total_liabilities=0.0, equity=1.0))
            )

    def test_history_kwarg(self) -> None:
        eng = FinancialRatioEngine()
        result = eng.analyze(
            _full(),
            history=[_full(period=_period(end=date(2023, 12, 31), fy=2023))],
        )
        assert result.metadata.periods_used == 2

    def test_composed_current_assets(self) -> None:
        # Fail-closed: component cash/AR/inventory cannot substitute for
        # unreported current_assets (CV-001 — no or-0 composition).
        eng = FinancialRatioEngine()
        stmt = _full(
            balance=_bs(
                current_assets=None,
                cash=100.0,
                accounts_receivable=50.0,
                inventory=50.0,
                current_liabilities=100.0,
            )
        )
        result = eng.analyze(stmt)
        cr = next(m for m in result.liquidity if m.name == "current_ratio")
        assert cr.value is None
        assert cr.status == FinancialValueStatus.UNAVAILABLE.value
        assert cr.formula_id == FORMULA_CURRENT_RATIO

    def test_efficiency_and_poor(self) -> None:
        eng = FinancialRatioEngine()
        low_rev = IncomeStatement(
            revenue=100.0,
            cogs=50.0,
            gross_profit=50.0,
            ebit=20.0,
            ebitda=25.0,
            interest_expense=5.0,
            pretax_income=15.0,
            tax=3.0,
            net_income=12.0,
            weighted_shares=10.0,
        )
        prior = _full(
            period=_period(end=date(2023, 12, 31), fy=2023),
            income=low_rev,
        )
        current = _full(income=low_rev)
        result = eng.analyze(_snap(prior, current))
        assert RatioQualityFlag.POOR_EFFICIENCY in result.quality_flags


class TestHelpers:
    def test_helpers(self) -> None:
        assert _safe_div(None, 1) is None
        assert _safe_div(1, 0) is None
        assert _safe_div(1e308, 1e-308) is None
        assert _clip01(None) is None
        assert _clip01(2) == 1.0
        assert _benchmark_margin(None) is BenchmarkClass.INSUFFICIENT
        assert _benchmark_margin(0.3) is BenchmarkClass.EXCELLENT
        assert _benchmark_margin(0.2) is BenchmarkClass.STRONG
        assert _benchmark_margin(0.1) is BenchmarkClass.ADEQUATE
        assert _benchmark_margin(0.01) is BenchmarkClass.WEAK
        assert _benchmark_margin(-0.1) is BenchmarkClass.POOR
        assert _benchmark_ratio(None, excellent=1, strong=0.5, adequate=0.2) is BenchmarkClass.INSUFFICIENT
        assert _benchmark_ratio(2, excellent=1, strong=0.5, adequate=0.2) is BenchmarkClass.EXCELLENT
        assert _benchmark_ratio(0.6, excellent=1, strong=0.5, adequate=0.2) is BenchmarkClass.STRONG
        assert _benchmark_ratio(0.3, excellent=1, strong=0.5, adequate=0.2) is BenchmarkClass.ADEQUATE
        assert _benchmark_ratio(0.1, excellent=1, strong=0.5, adequate=0.2) is BenchmarkClass.WEAK
        assert _benchmark_ratio(-1, excellent=1, strong=0.5, adequate=0.2) is BenchmarkClass.POOR
        assert _benchmark_ratio(0.1, excellent=0.3, strong=0.5, adequate=0.8, higher_better=False) is BenchmarkClass.EXCELLENT
        assert _benchmark_ratio(0.4, excellent=0.3, strong=0.5, adequate=0.8, higher_better=False) is BenchmarkClass.STRONG
        assert _benchmark_ratio(0.6, excellent=0.3, strong=0.5, adequate=0.8, higher_better=False) is BenchmarkClass.ADEQUATE
        assert _benchmark_ratio(1.0, excellent=0.3, strong=0.5, adequate=0.8, higher_better=False) is BenchmarkClass.WEAK
        assert _trend(None, 1.0) is None
        assert _trend(1.0, 1.0) is TrendDirection.STABLE
        assert _trend(1.1, 1.0) is TrendDirection.IMPROVING
        assert _trend(0.9, 1.0) is TrendDirection.WEAKENING
        assert _trend(1.1, 1.0, higher_better=False) is TrendDirection.WEAKENING
        assert _trend(0.9, 1.0, higher_better=False) is TrendDirection.IMPROVING


class TestEngineFacade:
    def test_analyze_financial_ratios(self) -> None:
        engine = FinancialEngine()
        result = engine.analyze_financial_ratios(_full())
        assert result.profitability[0].value is not None
        snap = _snap(_full())
        engine.validate(snap)
        assert engine.serialize(snap)["version"] == FINANCIAL_VERSION

    def test_performance(self) -> None:
        engine = FinancialEngine()
        snap = _snap(
            _full(period=_period(end=date(2022, 12, 31), fy=2022)),
            _full(period=_period(end=date(2023, 12, 31), fy=2023)),
            _full(),
        )
        engine.analyze_financial_ratios(snap)
        start = time.perf_counter()
        for _ in range(20):
            engine.analyze_financial_ratios(snap)
        avg_ms = (time.perf_counter() - start) / 20 * 1000
        assert avg_ms < 30.0, f"avg {avg_ms:.2f} ms"

    def test_metric_dicts(self) -> None:
        result = FinancialRatioEngine().analyze(
            _snap(
                _full(period=_period(end=date(2023, 12, 31), fy=2023)),
                _full(),
            )
        )
        assert result.profitability[0].to_dict()["name"]
        assert result.capital_allocation.to_dict()["capital_allocation_score"] is not None
        assert result.trend_summary.to_dict()["profitability"]
        assert result.metadata.to_dict()["periods_used"] == 2


def _by_name(result: FinancialRatioAnalysis, name: str):
    return next(m for m in result.profitability if m.name == name)


class TestPhase1DerivedMargins:
    """F2.5 Phase 1: gross / operating / net margin via financial.derivation."""

    def test_gross_margin_valid_is_calculated(self) -> None:
        result = FinancialRatioEngine().analyze(_full())
        gm = _by_name(result, "gross_margin")
        assert gm.value == pytest.approx(0.6)
        assert gm.status == FinancialValueStatus.CALCULATED.value
        assert gm.formula_id == FORMULA_GROSS_MARGIN
        assert gm.formula == "gross_profit / revenue"
        assert gm.inputs["gross_profit"] == 600.0
        assert gm.inputs["revenue"] == 1000.0

    def test_operating_margin_valid_is_calculated(self) -> None:
        result = FinancialRatioEngine().analyze(_full())
        om = _by_name(result, "operating_margin")
        assert om.value == pytest.approx(0.3)
        assert om.status == FinancialValueStatus.CALCULATED.value
        assert om.formula_id == FORMULA_OPERATING_MARGIN
        assert om.formula == "ebit / revenue"

    def test_net_margin_valid_is_calculated(self) -> None:
        result = FinancialRatioEngine().analyze(_full())
        nm = _by_name(result, "net_margin")
        assert nm.value == pytest.approx(0.21)
        assert nm.status == FinancialValueStatus.CALCULATED.value
        assert nm.formula_id == FORMULA_NET_MARGIN
        assert nm.formula == "net_income / revenue"

    def test_missing_gross_profit_is_unavailable(self) -> None:
        stmt = _full(
            income=IncomeStatement(
                revenue=1000.0,
                ebit=300.0,
                ebitda=350.0,
                net_income=210.0,
            )
        )
        gm = _by_name(FinancialRatioEngine().analyze(stmt), "gross_margin")
        assert gm.value is None
        assert gm.status == FinancialValueStatus.UNAVAILABLE.value
        assert gm.formula_id == FORMULA_GROSS_MARGIN

    def test_missing_ebit_operating_margin_unavailable(self) -> None:
        stmt = _full(
            income=IncomeStatement(
                revenue=1000.0,
                gross_profit=600.0,
                net_income=210.0,
            )
        )
        om = _by_name(FinancialRatioEngine().analyze(stmt), "operating_margin")
        assert om.value is None
        assert om.status == FinancialValueStatus.UNAVAILABLE.value
        assert om.formula_id == FORMULA_OPERATING_MARGIN

    def test_missing_net_income_net_margin_unavailable(self) -> None:
        stmt = _full(
            income=IncomeStatement(
                revenue=1000.0,
                gross_profit=600.0,
                ebit=300.0,
            )
        )
        nm = _by_name(FinancialRatioEngine().analyze(stmt), "net_margin")
        assert nm.value is None
        assert nm.status == FinancialValueStatus.UNAVAILABLE.value
        assert nm.formula_id == FORMULA_NET_MARGIN

    def test_zero_revenue_never_fabricates(self) -> None:
        stmt = _full(income=IncomeStatement(revenue=0.0, net_income=0.0))
        with pytest.raises(FinancialRatioError, match="Divide-by-zero"):
            FinancialRatioEngine().analyze(stmt)

    def test_provenance_and_calculated_not_reported(self) -> None:
        gm = _by_name(FinancialRatioEngine().analyze(_full()), "gross_margin")
        payload = gm.to_dict()
        assert payload["formula_id"] == FORMULA_GROSS_MARGIN
        assert payload["formula"] == "gross_profit / revenue"
        assert payload["inputs"]["gross_profit"] == 600.0
        assert payload["inputs"]["revenue"] == 1000.0
        refs = payload["intermediates"]["derivation_inputs"]
        assert {item["field_id"] for item in refs} == {"gross_profit", "revenue"}
        assert payload["status"] == FinancialValueStatus.CALCULATED.value
        assert payload["status"] != FinancialValueStatus.REPORTED.value
        relabeled = as_reported(
            DerivationInput(
                field_id="gross_margin",
                value=gm.value,
                status=FinancialValueStatus.CALCULATED,
            )
        )
        assert relabeled.status is FinancialValueStatus.UNAVAILABLE
        assert relabeled.unavailable_reason == "calculated_cannot_be_reported"

    def test_unmigrated_ebit_margins_have_no_phase1_status(self) -> None:
        result = FinancialRatioEngine().analyze(_full())
        ebit = _by_name(result, "ebit_margin")
        ebitda = _by_name(result, "ebitda_margin")
        assert ebit.status is None
        assert ebit.formula_id is None
        assert ebitda.status is None
        assert ebit.value == pytest.approx(0.3)
        assert ebitda.value == pytest.approx(0.35)

    def test_no_cogs_fallback_for_gross_margin(self) -> None:
        stmt = _full(
            income=IncomeStatement(
                revenue=1000.0,
                cogs=400.0,
                ebit=300.0,
                net_income=210.0,
            )
        )
        gm = _by_name(FinancialRatioEngine().analyze(stmt), "gross_margin")
        assert gm.value is None
        assert gm.status == FinancialValueStatus.UNAVAILABLE.value


def _lev(result: FinancialRatioAnalysis, name: str):
    return next(m for m in result.leverage if m.name == name)


class TestPhase2DerivedRoeAndDebtToEquity:
    """F2.5 Phase 2: ROE (average equity) and fail-closed debt/equity."""

    def test_roe_valid_two_period_is_calculated(self) -> None:
        prior = _full(
            period=_period(end=date(2023, 12, 31), fy=2023),
            balance=BalanceSheet(
                cash=150.0,
                current_assets=450.0,
                total_assets=1000.0,
                current_liabilities=200.0,
                short_term_debt=50.0,
                long_term_debt=200.0,
                total_liabilities=400.0,
                equity=400.0,
                total_equity=400.0,
            ),
        )
        current = _full()
        roe = _by_name(FinancialRatioEngine().analyze(_snap(prior, current)), "roe")
        assert roe.value == pytest.approx(210.0 / 500.0)
        assert roe.status == FinancialValueStatus.CALCULATED.value
        assert roe.formula_id == FORMULA_ROE
        assert roe.formula == "net_income / ((beginning_equity + ending_equity) / 2)"
        assert roe.inputs["beginning_equity"] == 400.0
        assert roe.inputs["ending_equity"] == 600.0
        assert roe.status != FinancialValueStatus.REPORTED.value

    def test_roe_missing_beginning_equity_unavailable(self) -> None:
        roe = _by_name(FinancialRatioEngine().analyze(_full()), "roe")
        assert roe.value is None
        assert roe.status == FinancialValueStatus.UNAVAILABLE.value
        assert roe.formula_id == FORMULA_ROE

    def test_roe_period_type_mismatch_unavailable(self) -> None:
        prior = _full(
            period=FinancialPeriod(
                period_type=PeriodType.QUARTERLY,
                period_end=date(2023, 12, 31),
                fiscal_year=2023,
                fiscal_quarter=4,
                currency=CurrencyRef(CurrencyCode.USD),
            )
        )
        roe = _by_name(FinancialRatioEngine().analyze(_snap(prior, _full())), "roe")
        assert roe.value is None
        assert roe.status == FinancialValueStatus.UNAVAILABLE.value
        assert roe.intermediates["unavailable_reason"] == "period_mismatch"

    def test_roe_currency_mismatch_unavailable(self) -> None:
        prior = _full(
            period=FinancialPeriod(
                period_type=PeriodType.ANNUAL,
                period_end=date(2023, 12, 31),
                fiscal_year=2023,
                currency=CurrencyRef(CurrencyCode.INR),
            )
        )
        roe = _by_name(FinancialRatioEngine().analyze(_snap(prior, _full())), "roe")
        assert roe.value is None
        assert roe.status == FinancialValueStatus.UNAVAILABLE.value
        assert roe.intermediates["unavailable_reason"] == "currency_mismatch"

    def test_roe_unknown_unit_unavailable(self) -> None:
        prior = FinancialStatements(
            period=_period(end=date(2023, 12, 31), fy=2023),
            income_statement=_full().income_statement,
            balance_sheet=_full().balance_sheet,
            cash_flow=_full().cash_flow,
            statement_metadata=StatementMetadata(unit_scale="widgets"),
        )
        roe = _by_name(FinancialRatioEngine().analyze(_snap(prior, _full())), "roe")
        assert roe.value is None
        assert roe.status == FinancialValueStatus.UNAVAILABLE.value
        assert roe.intermediates["unavailable_reason"] == "unit_mismatch"

    def test_roe_calculated_cannot_be_reported(self) -> None:
        prior = _full(period=_period(end=date(2023, 12, 31), fy=2023))
        roe = _by_name(FinancialRatioEngine().analyze(_snap(prior, _full())), "roe")
        assert roe.status == FinancialValueStatus.CALCULATED.value
        relabeled = as_reported(
            DerivationInput(
                field_id="roe",
                value=roe.value,
                status=FinancialValueStatus.CALCULATED,
            )
        )
        assert relabeled.status is FinancialValueStatus.UNAVAILABLE
        assert relabeled.unavailable_reason == "calculated_cannot_be_reported"

    def test_debt_to_equity_valid_is_calculated(self) -> None:
        dte = _lev(FinancialRatioEngine().analyze(_full()), "debt_to_equity")
        assert dte.value == pytest.approx(250.0 / 600.0)
        assert dte.status == FinancialValueStatus.CALCULATED.value
        assert dte.formula_id == FORMULA_DEBT_TO_EQUITY
        assert dte.formula == "total_debt / equity"
        assert dte.inputs["short_term_debt"] == 50.0
        assert dte.inputs["long_term_debt"] == 200.0
        assert dte.status != FinancialValueStatus.REPORTED.value

    def test_debt_to_equity_missing_long_term_unavailable(self) -> None:
        stmt = _full(
            balance=BalanceSheet(
                cash=150.0,
                current_assets=450.0,
                total_assets=1000.0,
                current_liabilities=200.0,
                short_term_debt=50.0,
                total_liabilities=400.0,
                equity=600.0,
                total_equity=600.0,
            )
        )
        dte = _lev(FinancialRatioEngine().analyze(stmt), "debt_to_equity")
        assert dte.value is None
        assert dte.status == FinancialValueStatus.UNAVAILABLE.value
        assert dte.formula_id == FORMULA_DEBT_TO_EQUITY

    def test_debt_to_equity_missing_short_term_unavailable(self) -> None:
        stmt = _full(
            balance=BalanceSheet(
                cash=150.0,
                current_assets=450.0,
                total_assets=1000.0,
                current_liabilities=200.0,
                long_term_debt=200.0,
                total_liabilities=400.0,
                equity=600.0,
                total_equity=600.0,
            )
        )
        dte = _lev(FinancialRatioEngine().analyze(stmt), "debt_to_equity")
        assert dte.value is None
        assert dte.status == FinancialValueStatus.UNAVAILABLE.value

    def test_debt_to_equity_missing_equity_unavailable(self) -> None:
        stmt = _full(
            balance=BalanceSheet(
                cash=150.0,
                current_assets=450.0,
                total_assets=1000.0,
                current_liabilities=200.0,
                short_term_debt=50.0,
                long_term_debt=200.0,
                total_liabilities=400.0,
            )
        )
        dte = _lev(FinancialRatioEngine().analyze(stmt), "debt_to_equity")
        assert dte.value is None
        assert dte.status == FinancialValueStatus.UNAVAILABLE.value

    def test_debt_to_equity_calculated_cannot_be_reported(self) -> None:
        dte = _lev(FinancialRatioEngine().analyze(_full()), "debt_to_equity")
        relabeled = as_reported(
            DerivationInput(
                field_id="debt_to_equity",
                value=dte.value,
                status=FinancialValueStatus.CALCULATED,
            )
        )
        assert relabeled.status is FinancialValueStatus.UNAVAILABLE
        assert relabeled.unavailable_reason == "calculated_cannot_be_reported"


def _liq(result: FinancialRatioAnalysis, name: str):
    return next(m for m in result.liquidity if m.name == name)


def _eff(result: FinancialRatioAnalysis, name: str):
    return next(m for m in result.efficiency if m.name == name)


class TestPhase3DerivedLiquidity:
    """F2.5 Phase 3: liquidity ratios via reported current assets, fail-closed."""

    def test_current_ratio_valid_is_calculated(self) -> None:
        cr = _liq(FinancialRatioEngine().analyze(_full()), "current_ratio")
        assert cr.value == pytest.approx(450.0 / 200.0)
        assert cr.status == FinancialValueStatus.CALCULATED.value
        assert cr.formula_id == FORMULA_CURRENT_RATIO
        assert cr.formula == "current_assets / current_liabilities"
        assert cr.inputs["current_assets"] == 450.0
        assert cr.inputs["current_liabilities"] == 200.0
        assert cr.status != FinancialValueStatus.REPORTED.value

    def test_working_capital_ratio_is_ratio_not_amount(self) -> None:
        wcr = _liq(FinancialRatioEngine().analyze(_full()), "working_capital_ratio")
        assert wcr.value == pytest.approx(450.0 / 200.0)
        assert wcr.status == FinancialValueStatus.CALCULATED.value
        assert wcr.formula_id == FORMULA_WORKING_CAPITAL_RATIO
        assert wcr.formula == "current_assets / current_liabilities"
        assert wcr.formula_id != "working_capital"

    def test_quick_ratio_valid_is_calculated(self) -> None:
        qr = _liq(FinancialRatioEngine().analyze(_full()), "quick_ratio")
        assert qr.value == pytest.approx((450.0 - 80.0) / 200.0)
        assert qr.status == FinancialValueStatus.CALCULATED.value
        assert qr.formula_id == FORMULA_QUICK_RATIO
        assert qr.formula == "(current_assets - inventory) / current_liabilities"
        assert qr.inputs["inventory"] == 80.0

    def test_cash_ratio_valid_is_calculated(self) -> None:
        cash_r = _liq(FinancialRatioEngine().analyze(_full()), "cash_ratio")
        assert cash_r.value == pytest.approx((150.0 + 50.0) / 200.0)
        assert cash_r.status == FinancialValueStatus.CALCULATED.value
        assert cash_r.formula_id == FORMULA_CASH_RATIO
        assert cash_r.formula == "(cash + short_term_investments) / current_liabilities"
        assert cash_r.inputs["cash"] == 150.0
        assert cash_r.inputs["sti"] == 50.0

    def test_working_capital_turnover_uses_ending_wc(self) -> None:
        wc_to = _eff(
            FinancialRatioEngine().analyze(_full()), "working_capital_turnover"
        )
        assert wc_to.value == pytest.approx(1000.0 / 250.0)
        assert wc_to.status == FinancialValueStatus.CALCULATED.value
        assert wc_to.formula_id == FORMULA_WORKING_CAPITAL_TURNOVER
        assert wc_to.formula == "revenue / working_capital"
        assert wc_to.inputs["revenue"] == 1000.0
        assert wc_to.inputs["working_capital"] == 250.0

    def test_missing_current_assets_unavailable(self) -> None:
        stmt = _full(balance=_bs(current_assets=None))
        result = FinancialRatioEngine().analyze(stmt)
        for name in ("current_ratio", "quick_ratio", "working_capital_ratio"):
            metric = _liq(result, name)
            assert metric.value is None
            assert metric.status == FinancialValueStatus.UNAVAILABLE.value
        wc_to = _eff(result, "working_capital_turnover")
        assert wc_to.value is None
        assert wc_to.status == FinancialValueStatus.UNAVAILABLE.value

    def test_missing_current_liabilities_unavailable(self) -> None:
        stmt = _full(balance=_bs(current_liabilities=None))
        cr = _liq(FinancialRatioEngine().analyze(stmt), "current_ratio")
        assert cr.value is None
        assert cr.status == FinancialValueStatus.UNAVAILABLE.value
        assert cr.formula_id == FORMULA_CURRENT_RATIO

    def test_missing_inventory_quick_ratio_unavailable(self) -> None:
        stmt = _full(balance=_bs(inventory=None))
        result = FinancialRatioEngine().analyze(stmt)
        qr = _liq(result, "quick_ratio")
        assert qr.value is None
        assert qr.status == FinancialValueStatus.UNAVAILABLE.value
        assert qr.formula_id == FORMULA_QUICK_RATIO
        cr = _liq(result, "current_ratio")
        assert cr.value == pytest.approx(450.0 / 200.0)

    def test_missing_sti_cash_ratio_unavailable(self) -> None:
        stmt = _full(balance=_bs(short_term_investments=None))
        cash_r = _liq(FinancialRatioEngine().analyze(stmt), "cash_ratio")
        assert cash_r.value is None
        assert cash_r.status == FinancialValueStatus.UNAVAILABLE.value
        assert cash_r.formula_id == FORMULA_CASH_RATIO

    def test_missing_cash_cash_ratio_unavailable(self) -> None:
        stmt = _full(balance=_bs(cash=None))
        cash_r = _liq(FinancialRatioEngine().analyze(stmt), "cash_ratio")
        assert cash_r.value is None
        assert cash_r.status == FinancialValueStatus.UNAVAILABLE.value

    def test_reported_zero_current_assets_is_calculated(self) -> None:
        stmt = _full(balance=_bs(current_assets=0.0))
        cr = _liq(FinancialRatioEngine().analyze(stmt), "current_ratio")
        assert cr.value == pytest.approx(0.0)
        assert cr.status == FinancialValueStatus.CALCULATED.value

    def test_reported_zero_inventory_is_calculated(self) -> None:
        stmt = _full(balance=_bs(inventory=0.0))
        qr = _liq(FinancialRatioEngine().analyze(stmt), "quick_ratio")
        assert qr.value == pytest.approx(450.0 / 200.0)
        assert qr.status == FinancialValueStatus.CALCULATED.value

    def test_reported_zero_sti_is_calculated(self) -> None:
        stmt = _full(balance=_bs(short_term_investments=0.0))
        cash_r = _liq(FinancialRatioEngine().analyze(stmt), "cash_ratio")
        assert cash_r.value == pytest.approx(150.0 / 200.0)
        assert cash_r.status == FinancialValueStatus.CALCULATED.value

    def test_zero_current_liabilities_unavailable(self) -> None:
        stmt = _full(balance=_bs(current_liabilities=0.0))
        cr = _liq(FinancialRatioEngine().analyze(stmt), "current_ratio")
        assert cr.value is None
        assert cr.status == FinancialValueStatus.UNAVAILABLE.value
        assert cr.intermediates["unavailable_reason"] == "division_by_zero"

    def test_current_ratio_calculated_cannot_be_reported(self) -> None:
        cr = _liq(FinancialRatioEngine().analyze(_full()), "current_ratio")
        relabeled = as_reported(
            DerivationInput(
                field_id="current_ratio",
                value=cr.value,
                status=FinancialValueStatus.CALCULATED,
            )
        )
        assert relabeled.status is FinancialValueStatus.UNAVAILABLE
        assert relabeled.unavailable_reason == "calculated_cannot_be_reported"

    def test_regression_full_fixture_liquidity(self) -> None:
        result = FinancialRatioEngine().analyze(_full())
        assert _liq(result, "current_ratio").value == pytest.approx(2.25)
        assert _liq(result, "quick_ratio").value == pytest.approx(1.85)
        assert _liq(result, "cash_ratio").value == pytest.approx(1.0)
        assert _liq(result, "working_capital_ratio").value == pytest.approx(2.25)
        assert _eff(result, "working_capital_turnover").value == pytest.approx(4.0)


def _cf(result: FinancialRatioAnalysis, name: str):
    return next(m for m in result.cash_flow if m.name == name)


class TestF25FinalMigration:
    """Remaining F2.5 metrics: averages, debt composition, FCF-derived ratios."""

    def test_asset_turnover_requires_prior_period(self) -> None:
        at = _eff(FinancialRatioEngine().analyze(_full()), "asset_turnover")
        assert at.value is None
        assert at.status == FinancialValueStatus.UNAVAILABLE.value
        assert at.formula_id == FORMULA_ASSET_TURNOVER

    def test_asset_turnover_two_period_calculated(self) -> None:
        prior = _full(period=_period(end=date(2023, 12, 31), fy=2023))
        result = FinancialRatioEngine().analyze(_snap(prior, _full()))
        at = _eff(result, "asset_turnover")
        assert at.value == pytest.approx(1000.0 / 1000.0)
        assert at.status == FinancialValueStatus.CALCULATED.value
        assert at.formula_id == FORMULA_ASSET_TURNOVER

    def test_debt_to_assets_missing_long_term_unavailable(self) -> None:
        stmt = _full(
            balance=_bs(long_term_debt=None),
        )
        dta = next(m for m in FinancialRatioEngine().analyze(stmt).leverage if m.name == "debt_to_assets")
        assert dta.value is None
        assert dta.status == FinancialValueStatus.UNAVAILABLE.value
        assert dta.formula_id == FORMULA_DEBT_TO_ASSETS

    def test_net_debt_missing_cash_unavailable(self) -> None:
        stmt = _full(balance=_bs(cash=None))
        nd = next(m for m in FinancialRatioEngine().analyze(stmt).leverage if m.name == "net_debt")
        assert nd.value is None
        assert nd.status == FinancialValueStatus.UNAVAILABLE.value
        assert nd.formula_id == FORMULA_NET_DEBT

    def test_net_debt_reported_zero_cash(self) -> None:
        stmt = _full(balance=_bs(cash=0.0))
        nd = next(m for m in FinancialRatioEngine().analyze(stmt).leverage if m.name == "net_debt")
        assert nd.value == pytest.approx(250.0)
        assert nd.status == FinancialValueStatus.CALCULATED.value

    def test_roic_missing_cash_unavailable(self) -> None:
        stmt = _full(balance=_bs(cash=None))
        roic = next(m for m in FinancialRatioEngine().analyze(stmt).profitability if m.name == "roic")
        assert roic.value is None
        assert roic.status == FinancialValueStatus.UNAVAILABLE.value
        assert roic.formula_id == FORMULA_ROIC

    def test_roa_calculated(self) -> None:
        roa = next(m for m in FinancialRatioEngine().analyze(_full()).profitability if m.name == "roa")
        assert roa.value == pytest.approx(210.0 / 1000.0)
        assert roa.status == FinancialValueStatus.CALCULATED.value
        assert roa.formula_id == FORMULA_ROA

    def test_fcf_margin_calculated(self) -> None:
        fcfm = _cf(FinancialRatioEngine().analyze(_full()), "free_cash_flow_margin")
        assert fcfm.value == pytest.approx(170.0 / 1000.0)
        assert fcfm.status == FinancialValueStatus.CALCULATED.value
        assert fcfm.formula_id == FORMULA_FCF_MARGIN

    def test_debt_coverage_missing_debt_leg_unavailable(self) -> None:
        stmt = _full(balance=_bs(long_term_debt=None))
        dc = _cf(FinancialRatioEngine().analyze(stmt), "debt_coverage")
        assert dc.value is None
        assert dc.status == FinancialValueStatus.UNAVAILABLE.value
        assert dc.formula_id == FORMULA_DEBT_COVERAGE

    def test_dividend_coverage_missing_dividends_unavailable(self) -> None:
        stmt = _full(
            cash=CashFlowStatement(
                operating_cash_flow=250.0,
                capex=-80.0,
                free_cash_flow=170.0,
            )
        )
        div = _cf(FinancialRatioEngine().analyze(stmt), "dividend_coverage")
        assert div.value is None
        assert div.status == FinancialValueStatus.UNAVAILABLE.value
        assert div.formula_id == FORMULA_DIVIDEND_COVERAGE

    def test_regression_full_fixture_debt_and_fcf(self) -> None:
        prior = _full(period=_period(end=date(2023, 12, 31), fy=2023))
        result = FinancialRatioEngine().analyze(_snap(prior, _full()))
        dte = next(m for m in result.leverage if m.name == "debt_to_equity")
        dta = next(m for m in result.leverage if m.name == "debt_to_assets")
        nd = next(m for m in result.leverage if m.name == "net_debt")
        assert dte.value == pytest.approx(250.0 / 600.0)
        assert dta.value == pytest.approx(250.0 / 1000.0)
        assert nd.value == pytest.approx(100.0)
        assert _cf(result, "free_cash_flow_margin").value == pytest.approx(0.17)
        assert _cf(result, "debt_coverage").value == pytest.approx(250.0 / 250.0)
        assert _eff(result, "asset_turnover").value == pytest.approx(1.0)

    def test_derived_metric_cannot_be_reported(self) -> None:
        roa = next(m for m in FinancialRatioEngine().analyze(_full()).profitability if m.name == "roa")
        relabeled = as_reported(
            DerivationInput(
                field_id="roa",
                value=roa.value,
                status=FinancialValueStatus.CALCULATED,
            )
        )
        assert relabeled.status is FinancialValueStatus.UNAVAILABLE
        assert relabeled.unavailable_reason == "calculated_cannot_be_reported"


