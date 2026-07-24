"""Balance Sheet Intelligence tests — target 100% module coverage."""

from __future__ import annotations

import time
from datetime import date

import pytest

from financial import (
    FINANCIAL_VERSION,
    BalanceAnalysisError,
    BalanceQualityFlag,
    BalanceSheet,
    BalanceSheetAnalysis,
    BalanceSheetEngine,
    CompanyMetadata,
    CurrencyCode,
    CurrencyRef,
    FinancialEngine,
    FinancialPeriod,
    FinancialSnapshot,
    FinancialStatements,
    PeriodType,
    TrendDirection,
    UnitScale,
    validate_balance_for_analysis,
)
from financial.intelligence.balance_engine import (
    BALANCE_INTELLIGENCE_VERSION,
    _clip01,
    _growth,
    _safe_div,
    _trend_from_delta,
)
from financial.intelligence.balance_explainability import BALANCE_RESEARCH_DISCLAIMER
from financial.intelligence.balance_validation import coerce_balance_series
from financial.metadata import StatementMetadata


def _period(
    *,
    end: date = date(2024, 12, 31),
    fy: int | None = 2024,
) -> FinancialPeriod:
    return FinancialPeriod(
        period_type=PeriodType.ANNUAL,
        period_end=end,
        fiscal_year=fy,
        currency=CurrencyRef(CurrencyCode.USD),
    )


def _bs(**kwargs) -> BalanceSheet:
    data = dict(
        cash=200.0,
        short_term_investments=50.0,
        accounts_receivable=150.0,
        inventory=100.0,
        other_current_assets=50.0,
        current_assets=550.0,
        ppe=300.0,
        goodwill=50.0,
        intangibles=50.0,
        investments=50.0,
        other_assets=0.0,
        total_assets=1000.0,
        accounts_payable=80.0,
        short_term_debt=70.0,
        current_liabilities=200.0,
        long_term_debt=200.0,
        lease_liabilities=50.0,
        deferred_tax=30.0,
        other_liabilities=20.0,
        total_liabilities=400.0,
        minority_interest=0.0,
        share_capital=200.0,
        reserves=50.0,
        retained_earnings=400.0,
        treasury_shares=-50.0,
        equity=600.0,
        total_equity=600.0,
    )
    data.update(kwargs)
    return BalanceSheet(**data)


def _stmt(bs: BalanceSheet, period: FinancialPeriod | None = None) -> FinancialStatements:
    return FinancialStatements(
        period=period or _period(),
        balance_sheet=bs,
        statement_metadata=StatementMetadata(unit_scale=UnitScale.MILLIONS),
    )


def _snap(*items: tuple[BalanceSheet, FinancialPeriod]) -> FinancialSnapshot:
    return FinancialSnapshot(
        company=CompanyMetadata(company="Acme", ticker="ACM"),
        statements=tuple(_stmt(bs, per) for bs, per in items),
    )


class TestValidation:
    def test_missing_assets(self) -> None:
        with pytest.raises(BalanceAnalysisError, match="Missing total_assets"):
            validate_balance_for_analysis(BalanceSheet(cash=1.0))

    def test_negative_assets(self) -> None:
        with pytest.raises(BalanceAnalysisError, match="Negative Total Assets"):
            validate_balance_for_analysis(BalanceSheet(total_assets=-1.0, total_liabilities=0.0, total_equity=-1.0))

    def test_zero_assets(self) -> None:
        with pytest.raises(BalanceAnalysisError, match="Impossible ratios"):
            validate_balance_for_analysis(BalanceSheet(total_assets=0.0, total_liabilities=0.0, total_equity=0.0))

    def test_negative_equity(self) -> None:
        with pytest.raises(BalanceAnalysisError, match="Negative Equity"):
            validate_balance_for_analysis(
                BalanceSheet(total_assets=100.0, total_liabilities=150.0, total_equity=-50.0)
            )

    def test_allow_negative_equity(self) -> None:
        result = validate_balance_for_analysis(
            BalanceSheet(total_assets=100.0, total_liabilities=150.0, total_equity=-50.0),
            allow_negative_equity=True,
        )
        assert result.ok

    def test_accounting_equation_fail(self) -> None:
        with pytest.raises(BalanceAnalysisError, match="Assets"):
            validate_balance_for_analysis(
                BalanceSheet(total_assets=100.0, total_liabilities=10.0, total_equity=10.0)
            )

    def test_nan_inf(self) -> None:
        with pytest.raises(BalanceAnalysisError, match="NaN"):
            validate_balance_for_analysis(BalanceSheet(total_assets=float("nan")))
        with pytest.raises(BalanceAnalysisError, match="infinite"):
            validate_balance_for_analysis(BalanceSheet(total_assets=float("inf")))

    def test_negative_cash_warning(self) -> None:
        result = validate_balance_for_analysis(
            BalanceSheet(
                cash=-5.0,
                total_assets=100.0,
                total_liabilities=40.0,
                total_equity=60.0,
                current_liabilities=-1.0,
            )
        )
        assert "negative cash" in result.warnings
        assert "negative current_liabilities" in result.warnings

    def test_with_statements_ok(self) -> None:
        stmt = _stmt(_bs())
        assert validate_balance_for_analysis(stmt.balance_sheet, statements=stmt).ok

    def test_with_statements_domain_error(self) -> None:
        bad = FinancialStatements(
            period=_period(),
            balance_sheet=BalanceSheet(
                total_assets=100.0, total_liabilities=10.0, total_equity=10.0
            ),
        )
        # hard check fails before domain validate
        with pytest.raises(BalanceAnalysisError):
            validate_balance_for_analysis(bad.balance_sheet, statements=bad)

    def test_statements_nan_in_income_propagates(self) -> None:
        from financial.income_statement import IncomeStatement

        stmt = FinancialStatements(
            period=_period(),
            income_statement=IncomeStatement(revenue=float("nan")),
            balance_sheet=_bs(),
        )
        with pytest.raises(BalanceAnalysisError, match="NaN"):
            validate_balance_for_analysis(stmt.balance_sheet, statements=stmt)


class TestCoerce:
    def test_balance_only(self) -> None:
        b, s, _ = coerce_balance_series(_bs())
        assert len(b) == 1 and s[0] is None

    def test_statements_and_snapshot(self) -> None:
        b, s, meta = coerce_balance_series(_stmt(_bs()))
        assert meta["period_end"] == "2024-12-31"
        snap = _snap(
            (_bs(total_assets=900.0, total_liabilities=400.0, total_equity=500.0, equity=500.0), _period(end=date(2023, 12, 31), fy=2023)),
            (_bs(), _period(end=date(2024, 12, 31), fy=2024)),
        )
        # reverse order
        snap2 = FinancialSnapshot(company=snap.company, statements=(snap.statements[1], snap.statements[0]))
        balances, _, meta = coerce_balance_series(snap2)
        assert balances[0].total_assets == 900.0
        assert meta["ticker"] == "ACM"

    def test_empty_snapshot(self) -> None:
        with pytest.raises(BalanceAnalysisError, match="Empty"):
            coerce_balance_series(FinancialSnapshot())

    def test_duplicate_periods_snapshot(self) -> None:
        snap = FinancialSnapshot(
            statements=(
                _stmt(_bs(), _period()),
                _stmt(_bs(cash=1.0), _period()),
            )
        )
        with pytest.raises(BalanceAnalysisError, match="Duplicate"):
            coerce_balance_series(snap)

    def test_dicts(self) -> None:
        assert coerce_balance_series(_bs().to_dict())[0][0].total_assets == 1000.0
        assert coerce_balance_series(_stmt(_bs()).to_dict())[0][0].total_assets == 1000.0
        assert coerce_balance_series(_snap((_bs(), _period())).to_dict())[0][0].total_assets == 1000.0

    def test_bad_dict(self) -> None:
        with pytest.raises(BalanceAnalysisError, match="Unsupported"):
            coerce_balance_series({"foo": 1})

    def test_sequence(self) -> None:
        b, s, _ = coerce_balance_series([_bs(cash=1.0), _stmt(_bs())])
        assert len(b) == 2 and s[0] is None

    def test_empty_and_bad_sequence(self) -> None:
        with pytest.raises(BalanceAnalysisError, match="Empty history"):
            coerce_balance_series([])
        with pytest.raises(BalanceAnalysisError, match="History items"):
            coerce_balance_series([object()])  # type: ignore[list-item]
        with pytest.raises(BalanceAnalysisError, match="Accept ONLY"):
            coerce_balance_series(object())  # type: ignore[arg-type]

    def test_sorted_statement_sequence_duplicates(self) -> None:
        series = [
            _stmt(_bs(), _period(end=date(2024, 12, 31), fy=2024)),
            _stmt(_bs(cash=1.0), _period(end=date(2023, 12, 31), fy=2023)),
        ]
        b, _, meta = coerce_balance_series(series)
        assert b[0].cash == 1.0
        assert meta["period_end"] == "2024-12-31"
        with pytest.raises(BalanceAnalysisError, match="Duplicate"):
            coerce_balance_series(
                [
                    _stmt(_bs(), _period()),
                    _stmt(_bs(cash=2.0), _period()),
                ]
            )


class TestAnalysis:
    def test_single_healthy(self) -> None:
        eng = BalanceSheetEngine()
        result = eng.analyze(_bs())
        assert isinstance(result, BalanceSheetAnalysis)
        assert result.liquidity.current_ratio == pytest.approx(550 / 200)
        assert result.liquidity.quick_ratio == pytest.approx(450 / 200)
        assert result.leverage.debt_to_equity == pytest.approx(270 / 600)
        assert result.assets.goodwill_pct == pytest.approx(0.05)
        assert result.equity.book_value == 600.0
        assert result.equity.tangible_book_value == pytest.approx(500.0)
        assert BALANCE_RESEARCH_DISCLAIMER in result.research_disclaimer
        assert result.metadata.engine_version == BALANCE_INTELLIGENCE_VERSION
        d = result.to_dict()
        assert "liquidity" in d and d["leverage"]["capital_structure_summary"]

    def test_composed_current_assets(self) -> None:
        eng = BalanceSheetEngine()
        bs = BalanceSheet(
            cash=100.0,
            accounts_receivable=50.0,
            inventory=50.0,
            total_assets=400.0,
            current_liabilities=100.0,
            total_liabilities=100.0,
            total_equity=300.0,
            equity=300.0,
            short_term_debt=0.0,
            long_term_debt=0.0,
        )
        result = eng.analyze(bs)
        assert result.liquidity.current_ratio == pytest.approx(2.0)

    def test_weak_and_warning_flags(self) -> None:
        eng = BalanceSheetEngine()
        bs = BalanceSheet(
            cash=10.0,
            current_assets=80.0,
            inventory=40.0,
            goodwill=300.0,
            intangibles=350.0,
            total_assets=1000.0,
            current_liabilities=200.0,
            short_term_debt=400.0,
            long_term_debt=400.0,
            total_liabilities=900.0,
            lease_liabilities=50.0,
            deferred_tax=40.0,
            total_equity=100.0,
            equity=100.0,
            retained_earnings=20.0,
        )
        result = eng.analyze(bs)
        assert BalanceQualityFlag.WEAK_LIQUIDITY in result.quality_flags
        assert BalanceQualityFlag.EXCESSIVE_LEVERAGE in result.quality_flags
        assert BalanceQualityFlag.HIGH_GOODWILL in result.quality_flags
        assert BalanceQualityFlag.HIGH_INTANGIBLE_ASSETS in result.quality_flags
        assert BalanceQualityFlag.WORKING_CAPITAL_PRESSURE in result.quality_flags
        assert BalanceQualityFlag.WEAK_EQUITY_BASE in result.quality_flags
        assert BalanceQualityFlag.BALANCE_SHEET_WARNING in result.quality_flags

    def test_healthy_flags(self) -> None:
        eng = BalanceSheetEngine()
        bs = BalanceSheet(
            cash=300.0,
            short_term_investments=100.0,
            current_assets=800.0,
            inventory=50.0,
            goodwill=10.0,
            intangibles=10.0,
            total_assets=1000.0,
            current_liabilities=200.0,
            short_term_debt=20.0,
            long_term_debt=80.0,
            total_liabilities=300.0,
            total_equity=700.0,
            equity=700.0,
            retained_earnings=400.0,
            treasury_shares=-10.0,
        )
        result = eng.analyze(bs)
        assert BalanceQualityFlag.STRONG_LIQUIDITY in result.quality_flags
        assert BalanceQualityFlag.CONSERVATIVE_CAPITAL_STRUCTURE in result.quality_flags
        assert BalanceQualityFlag.STRONG_EQUITY_BASE in result.quality_flags
        assert BalanceQualityFlag.HEALTHY_BALANCE_SHEET in result.quality_flags

    def test_multi_period_trends(self) -> None:
        eng = BalanceSheetEngine()
        snap = _snap(
            (
                BalanceSheet(
                    cash=50.0,
                    current_assets=300.0,
                    inventory=50.0,
                    goodwill=100.0,
                    intangibles=50.0,
                    total_assets=1000.0,
                    current_liabilities=250.0,
                    short_term_debt=200.0,
                    long_term_debt=300.0,
                    total_liabilities=600.0,
                    total_equity=400.0,
                    equity=400.0,
                ),
                _period(end=date(2023, 12, 31), fy=2023),
            ),
            (
                _bs(),
                _period(end=date(2024, 12, 31), fy=2024),
            ),
        )
        result = eng.analyze(snap)
        assert result.liquidity.working_capital_trend is not None
        assert result.equity.equity_growth is not None
        assert result.trend_summary.liquidity in (
            TrendDirection.IMPROVING,
            TrendDirection.STABLE,
            TrendDirection.WEAKENING,
        )
        assert result.metadata.company == "Acme"
        assert result.metadata.periods_used == 2

    def test_history_kwarg(self) -> None:
        eng = BalanceSheetEngine()
        prior = BalanceSheet(
            cash=100.0,
            current_assets=400.0,
            total_assets=1000.0,
            current_liabilities=300.0,
            total_liabilities=500.0,
            total_equity=500.0,
            equity=500.0,
            short_term_debt=100.0,
            long_term_debt=100.0,
        )
        result = eng.analyze(_bs(), history=[prior])
        assert result.metadata.periods_used == 2

    def test_wc_trend_zero_prior(self) -> None:
        eng = BalanceSheetEngine()
        prior = BalanceSheet(
            current_assets=100.0,
            current_liabilities=100.0,
            total_assets=500.0,
            total_liabilities=200.0,
            total_equity=300.0,
            equity=300.0,
        )
        cur = BalanceSheet(
            current_assets=150.0,
            current_liabilities=100.0,
            total_assets=500.0,
            total_liabilities=200.0,
            total_equity=300.0,
            equity=300.0,
        )
        result = eng.analyze([prior, cur])
        assert result.liquidity.working_capital_trend is TrendDirection.IMPROVING

    def test_capital_structure_labels(self) -> None:
        eng = BalanceSheetEngine()
        heavy = eng.analyze(
            BalanceSheet(
                total_assets=1000.0,
                short_term_debt=500.0,
                long_term_debt=500.0,
                total_liabilities=800.0,
                total_equity=200.0,
                equity=200.0,
                current_liabilities=200.0,
                current_assets=300.0,
            )
        )
        assert heavy.leverage.capital_structure_summary == "debt-heavy"
        light = eng.analyze(
            BalanceSheet(
                total_assets=1000.0,
                short_term_debt=50.0,
                long_term_debt=50.0,
                total_liabilities=200.0,
                total_equity=800.0,
                equity=800.0,
                current_liabilities=100.0,
                current_assets=400.0,
            )
        )
        assert light.leverage.capital_structure_summary == "equity-heavy"
        bal = eng.analyze(
            BalanceSheet(
                total_assets=1000.0,
                short_term_debt=200.0,
                long_term_debt=400.0,
                total_liabilities=500.0,
                total_equity=500.0,
                equity=500.0,
                current_liabilities=200.0,
                current_assets=400.0,
                cash=50.0,
            )
        )
        assert bal.leverage.capital_structure_summary == "balanced"

    def test_insufficient_debt_summary(self) -> None:
        eng = BalanceSheetEngine()
        result = eng.analyze(
            BalanceSheet(
                total_assets=100.0,
                total_liabilities=40.0,
                total_equity=60.0,
                equity=60.0,
            )
        )
        assert result.leverage.capital_structure_summary == "insufficient_data"

    def test_asset_quality_without_soft(self) -> None:
        eng = BalanceSheetEngine()
        result = eng.analyze(
            BalanceSheet(
                current_assets=400.0,
                total_assets=1000.0,
                total_liabilities=400.0,
                total_equity=600.0,
                equity=600.0,
                current_liabilities=200.0,
            )
        )
        assert result.assets.asset_quality_score is not None

    def test_equity_fallback_field(self) -> None:
        eng = BalanceSheetEngine()
        result = eng.analyze(
            BalanceSheet(
                total_assets=100.0,
                total_liabilities=40.0,
                equity=60.0,
                current_assets=50.0,
                current_liabilities=20.0,
            )
        )
        assert result.equity.book_value == 60.0


class TestHelpers:
    def test_safe_div_and_growth(self) -> None:
        assert _safe_div(None, 1) is None
        assert _safe_div(1, 0) is None
        assert _safe_div(1e308, 1e-308) is None
        assert _growth(10, 0) is None
        assert _growth(None, 1) is None
        assert _clip01(None) is None
        assert _clip01(1.5) == 1.0
        assert _clip01(-0.2) == 0.0
        assert _trend_from_delta(None) is TrendDirection.STABLE
        assert _trend_from_delta(0.01) is TrendDirection.STABLE
        assert _trend_from_delta(0.05, improve_when_up=False) is TrendDirection.WEAKENING
        assert _trend_from_delta(-0.05, improve_when_up=False) is TrendDirection.IMPROVING

    def test_wc_pressure_via_current_ratio_only(self) -> None:
        """Cash alone composes current assets → WC pressure when CR < 1."""
        eng = BalanceSheetEngine()
        result = eng.analyze(
            BalanceSheet(
                current_liabilities=100.0,
                total_assets=500.0,
                total_liabilities=200.0,
                total_equity=300.0,
                equity=300.0,
                cash=10.0,
            )
        )
        assert result.liquidity.current_ratio == pytest.approx(0.1)
        assert BalanceQualityFlag.WORKING_CAPITAL_PRESSURE in result.quality_flags


class TestEngineFacade:
    def test_analyze_balance_sheet(self) -> None:
        engine = FinancialEngine()
        result = engine.analyze_balance_sheet(_bs())
        assert result.liquidity.current_ratio is not None
        snap = _snap((_bs(), _period()))
        engine.validate(snap)
        assert engine.serialize(snap)["version"] == FINANCIAL_VERSION
        # income still works
        from financial.income_statement import IncomeStatement

        inc = engine.analyze_income_statement(IncomeStatement(revenue=100.0, net_income=10.0))
        assert inc.margins.net_margin == pytest.approx(0.1)

    def test_performance(self) -> None:
        engine = FinancialEngine()
        snap = _snap(
            *[
                (
                    _bs(
                        cash=100.0 + i,
                        total_assets=1000.0,
                        total_liabilities=400.0,
                        total_equity=600.0,
                        equity=600.0,
                    ),
                    _period(end=date(2020 + i, 12, 31), fy=2020 + i),
                )
                for i in range(4)
            ]
        )
        engine.analyze_balance_sheet(snap)
        start = time.perf_counter()
        for _ in range(50):
            engine.analyze_balance_sheet(snap)
        avg_ms = (time.perf_counter() - start) / 50 * 1000
        assert avg_ms < 20.0, f"avg {avg_ms:.2f} ms"

    def test_metric_dicts(self) -> None:
        result = BalanceSheetEngine().analyze(
            _snap(
                (
                    BalanceSheet(
                        cash=50.0,
                        current_assets=300.0,
                        goodwill=80.0,
                        intangibles=40.0,
                        total_assets=1000.0,
                        current_liabilities=250.0,
                        short_term_debt=150.0,
                        long_term_debt=250.0,
                        total_liabilities=550.0,
                        total_equity=450.0,
                        equity=450.0,
                    ),
                    _period(end=date(2023, 12, 31), fy=2023),
                ),
                (_bs(), _period()),
            )
        )
        assert result.liquidity.to_dict()["current_ratio"]
        assert result.leverage.to_dict()["debt_to_equity"] is not None
        assert result.assets.to_dict()["cash_concentration"] is not None
        assert result.liabilities.to_dict()["current_liability_mix"] is not None
        assert result.equity.to_dict()["book_value"] == 600.0
        assert result.working_capital.to_dict()["balance_sheet_strength"] is not None
        assert result.trend_summary.to_dict()["liquidity"]
        assert result.metadata.to_dict()["periods_used"] == 2
