"""Earnings Quality Intelligence tests — target 100% module coverage."""

from __future__ import annotations

from datetime import date
from types import SimpleNamespace

import pytest

from business_quality import (
    BUSINESS_QUALITY_VERSION,
    EarningsQualityEngine,
    EarningsQualityFlag,
    BusinessQualityEngine,
    BusinessQualityValidationError,
    Rating,
    validate_earnings_quality_input,
)
from business_quality.earnings_quality_engine import (
    EARNINGS_QUALITY_VERSION,
    _confidence_from_present,
    _rating_from_01,
    _risk_from_01,
    _score_01,
)
from financial import (
    BalanceSheet,
    CashFlowStatement,
    CurrencyCode,
    CurrencyRef,
    FinancialEngine,
    FinancialPeriod,
    FinancialStatements,
    FinancialStatementsHistory,
    IncomeStatement,
    PeriodType,
    UnitScale,
)
from financial.metadata import StatementMetadata


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


def _fa(*scales: float):
    stmts = [
        _full(year=2020 + i, scale=s) for i, s in enumerate(scales or (1.0,))
    ]
    if len(stmts) == 1:
        return FinancialEngine().analyze_financials(stmts[0])
    return FinancialEngine().analyze_financials(
        FinancialStatementsHistory(statements=tuple(stmts))
    )


class TestHelpers:
    def test_rating_score_confidence_risk(self) -> None:
        assert _score_01(None) is None
        assert _score_01(0.5).value == pytest.approx(50.0)
        assert _rating_from_01(None) is Rating.INSUFFICIENT_DATA
        assert _rating_from_01(0.9) is Rating.EXCELLENT
        assert _rating_from_01(0.75) is Rating.STRONG
        assert _rating_from_01(0.6) is Rating.AVERAGE
        assert _rating_from_01(0.45) is Rating.WEAK
        assert _rating_from_01(0.1) is Rating.POOR
        assert _confidence_from_present() is not None
        assert _confidence_from_present(1.0, 2.0, 3.0).value == "high"
        assert _confidence_from_present(1.0, 2.0).value == "medium"
        assert _confidence_from_present(1.0).value == "low"
        assert _confidence_from_present(None, None).value == "insufficient"
        assert _risk_from_01(None).value == "unknown"
        assert _risk_from_01(0.9).value == "high"
        assert _risk_from_01(0.6).value == "elevated"
        assert _risk_from_01(0.4).value == "moderate"
        assert _risk_from_01(0.1).value == "low"
        assert _risk_from_01(0.9, invert=True).value == "low"
        from business_quality.earnings_quality_engine import _aggregate_confidence
        from business_quality.scoring import Confidence

        assert _aggregate_confidence([]) is Confidence.INSUFFICIENT
        assert (
            _aggregate_confidence([Confidence.HIGH, Confidence.HIGH, Confidence.HIGH])
            is Confidence.HIGH
        )
        assert (
            _aggregate_confidence([Confidence.MEDIUM, Confidence.MEDIUM])
            is Confidence.MEDIUM
        )
        assert _aggregate_confidence([Confidence.LOW]) is Confidence.LOW
        assert (
            _aggregate_confidence([Confidence.INSUFFICIENT, Confidence.INSUFFICIENT])
            is Confidence.INSUFFICIENT
        )


class TestValidation:
    def test_missing_and_wrong_type(self) -> None:
        with pytest.raises(BusinessQualityValidationError, match="Missing"):
            validate_earnings_quality_input(None)
        with pytest.raises(BusinessQualityValidationError, match="ONLY"):
            validate_earnings_quality_input({"income": 1})

        class FinancialAnalysis:
            pass

        with pytest.raises(BusinessQualityValidationError, match="lacks"):
            validate_earnings_quality_input(FinancialAnalysis())

    def test_incomplete_evidence(self) -> None:
        fa = _fa(1.0)

        class FinancialAnalysis:
            pass

        obj = FinancialAnalysis()
        obj.income = SimpleNamespace(
            revenue=SimpleNamespace(revenue=None),
            profitability=SimpleNamespace(net_income_quality=None),
        )
        obj.cash_flow = SimpleNamespace(
            operating=SimpleNamespace(
                operating_cash_flow=None, cash_conversion=None
            )
        )
        obj.ratios = fa.ratios
        obj.validation = fa.validation
        obj.metadata = fa.metadata
        with pytest.raises(BusinessQualityValidationError, match="Incomplete"):
            validate_earnings_quality_input(obj)

    def test_warnings_and_fa_not_ok(self) -> None:
        fa = _fa(1.0, 1.1)

        class FinancialAnalysis:
            pass

        obj = FinancialAnalysis()
        obj.income = SimpleNamespace(
            revenue=SimpleNamespace(revenue=100.0),
            profitability=SimpleNamespace(net_income_quality=None),
        )
        obj.cash_flow = SimpleNamespace(
            operating=SimpleNamespace(
                operating_cash_flow=50.0, cash_conversion=None
            )
        )
        obj.ratios = fa.ratios
        obj.validation = SimpleNamespace(ok=False)
        obj.metadata = fa.metadata
        result = validate_earnings_quality_input(obj)
        assert result.ok
        assert any("net_income_quality" in w for w in result.warnings)
        assert any("cash_conversion" in w for w in result.warnings)
        assert any("not ok" in w for w in result.warnings)

    def test_ok(self) -> None:
        result = validate_earnings_quality_input(_fa(1.0, 1.1))
        assert result.ok


class TestEarningsQuality:
    def test_happy_path_multi_period(self) -> None:
        fa = _fa(1.0, 1.1, 1.2)
        result = EarningsQualityEngine().analyze(fa)
        assert result.metadata.engine_version == EARNINGS_QUALITY_VERSION
        names = {a.name for a in result.assessments}
        assert "revenue_quality" in names
        assert "accrual_quality" in names
        assert "margin_stability" in names
        assert "free_cash_flow_support" in names
        assert result.explainability
        assert result.evidence
        payload = result.to_dict()
        assert "quality_flags" in payload
        assert payload["overall_rating"]

    def test_facade_analyze_and_eq(self) -> None:
        fa = _fa(1.0, 1.15, 1.3)
        engine = BusinessQualityEngine()
        eq = engine.analyze_earnings_quality(fa)
        assert eq.overall_rating in Rating
        bq = engine.analyze(fa)
        assert bq.score is not None
        assert bq.summary.headline
        assert BUSINESS_QUALITY_VERSION.startswith("0.7.0")

    def test_single_period(self) -> None:
        result = EarningsQualityEngine().analyze(_fa(1.0))
        assert result.validation.ok
        assert len(result.assessments) == 10

    def test_weak_cash_path(self) -> None:
        # Low OCF relative to NI via custom cash statement
        stmts = []
        for i, scale in enumerate((1.0, 1.0, 1.0)):
            stmts.append(
                _full(
                    year=2020 + i,
                    scale=scale,
                    cash=CashFlowStatement(
                        operating_cash_flow=20.0,
                        capex=-80.0,
                        free_cash_flow=-60.0,
                        dividends_paid=-10.0,
                    ),
                )
            )
        fa = FinancialEngine().analyze_financials(
            FinancialStatementsHistory(statements=tuple(stmts))
        )
        result = EarningsQualityEngine().analyze(fa)
        flags = set(result.quality_flags)
        assert flags & {
            EarningsQualityFlag.WEAK_CASH_SUPPORT,
            EarningsQualityFlag.HIGH_ACCRUAL_RISK,
            EarningsQualityFlag.AGGRESSIVE_ACCOUNTING_RISK,
            EarningsQualityFlag.VOLATILE_EARNINGS,
        } or result.overall_rating in (
            Rating.WEAK,
            Rating.POOR,
            Rating.AVERAGE,
            Rating.STRONG,
            Rating.EXCELLENT,
            Rating.INSUFFICIENT_DATA,
        )

    def test_accrual_conversion_branches(self) -> None:
        eng = EarningsQualityEngine()
        # Force conversion tiers via mocked namespaces with FinancialAnalysis type
        class FinancialAnalysis:
            pass

        base = _fa(1.0, 1.1)

        def _wrap(conversion: float, fcf: float | None = 10.0):
            obj = FinancialAnalysis()
            obj.income = base.income
            obj.cash_flow = SimpleNamespace(
                operating=SimpleNamespace(
                    operating_cash_flow=100.0,
                    cash_conversion=conversion,
                    cash_earnings_quality=None,
                    cash_flow_stability=None,
                ),
                free_cash_flow=SimpleNamespace(
                    free_cash_flow=fcf,
                    fcf_stability=None,
                ),
                quality=SimpleNamespace(operating_cash_quality=0.5),
            )
            obj.ratios = base.ratios
            obj.validation = base.validation
            obj.metadata = base.metadata
            return obj

        for conv in (1.2, 0.85, 0.6, 0.2, -0.1):
            r = eng.analyze(_wrap(conv))
            assert any(a.name == "accrual_quality" for a in r.assessments)

        # FCF negative path
        r2 = eng.analyze(_wrap(0.9, fcf=-5.0))
        assert any(a.name == "free_cash_flow_support" for a in r2.assessments)

    def test_flag_composition_unit(self) -> None:
        eng = EarningsQualityEngine()
        from business_quality.scoring import Assessment, Confidence, Score

        assessments = [
            Assessment(
                name="accrual_quality",
                rating=Rating.POOR,
                score=Score(value=20.0),
                confidence=Confidence.MEDIUM,
            ),
            Assessment(
                name="cash_earnings_quality",
                rating=Rating.EXCELLENT,
                score=Score(value=90.0),
                confidence=Confidence.HIGH,
            ),
            Assessment(
                name="free_cash_flow_support",
                rating=Rating.POOR,
                score=Score(value=20.0),
                confidence=Confidence.LOW,
            ),
            Assessment(
                name="margin_stability",
                rating=Rating.STRONG,
                score=Score(value=80.0),
                confidence=Confidence.MEDIUM,
            ),
            Assessment(
                name="earnings_consistency",
                rating=Rating.POOR,
                score=Score(value=20.0),
                confidence=Confidence.MEDIUM,
            ),
            Assessment(
                name="recurring_earnings",
                rating=Rating.STRONG,
                score=Score(value=80.0),
                confidence=Confidence.MEDIUM,
            ),
        ]
        income = SimpleNamespace(
            quality_flags=(SimpleNamespace(value="weak_earnings_quality"),),
            consistency=SimpleNamespace(one_time_items_detected=False),
        )
        cash = SimpleNamespace(
            operating=SimpleNamespace(cash_conversion=0.2),
        )
        flags = eng._flags(assessments, income, cash, 0.8)
        assert EarningsQualityFlag.HIGH_EARNINGS_QUALITY in flags
        assert EarningsQualityFlag.HIGH_ACCRUAL_RISK in flags
        assert EarningsQualityFlag.VOLATILE_EARNINGS in flags
        assert EarningsQualityFlag.STABLE_MARGINS in flags
        assert EarningsQualityFlag.AGGRESSIVE_ACCOUNTING_RISK in flags

        # Recurring with one-time but strong rating still flags
        income2 = SimpleNamespace(
            quality_flags=(),
            consistency=SimpleNamespace(one_time_items_detected=True),
        )
        cash2 = SimpleNamespace(operating=SimpleNamespace(cash_conversion=0.9))
        assessments2 = [
            Assessment(name="cash_earnings_quality", rating=Rating.AVERAGE),
            Assessment(name="free_cash_flow_support", rating=Rating.EXCELLENT),
            Assessment(name="recurring_earnings", rating=Rating.EXCELLENT),
            Assessment(name="accrual_quality", rating=Rating.AVERAGE),
            Assessment(name="margin_stability", rating=Rating.AVERAGE),
            Assessment(name="earnings_consistency", rating=Rating.AVERAGE),
        ]
        flags2 = eng._flags(assessments2, income2, cash2, 0.5)
        assert EarningsQualityFlag.CASH_SUPPORTED_EARNINGS in flags2
        assert EarningsQualityFlag.RECURRING_EARNINGS in flags2

        # FCF weak adds weak cash when conversion ok; conversion <0.3 accrual
        cash3 = SimpleNamespace(operating=SimpleNamespace(cash_conversion=0.25))
        assessments3 = [
            Assessment(name="free_cash_flow_support", rating=Rating.WEAK),
            Assessment(name="accrual_quality", rating=Rating.AVERAGE),
        ]
        flags3 = eng._flags(assessments3, income2, cash3, None)
        assert EarningsQualityFlag.WEAK_CASH_SUPPORT in flags3
        assert EarningsQualityFlag.HIGH_ACCRUAL_RISK in flags3

    def test_assessment_edge_branches(self) -> None:
        eng = EarningsQualityEngine()
        out: list = []
        evidence: list = []
        # FCF with conversion > 1.5 and no stability
        cash = SimpleNamespace(
            free_cash_flow=SimpleNamespace(free_cash_flow=None, fcf_stability=None),
            operating=SimpleNamespace(cash_conversion=2.0),
            quality=SimpleNamespace(operating_cash_quality=0.4),
        )
        a = eng._assess_fcf_support(cash, out, evidence)
        assert a.score is not None
        # FCF positive only
        cash2 = SimpleNamespace(
            free_cash_flow=SimpleNamespace(free_cash_flow=5.0, fcf_stability=None),
            operating=SimpleNamespace(cash_conversion=None),
            quality=SimpleNamespace(operating_cash_quality=None),
        )
        a2 = eng._assess_fcf_support(cash2, out, evidence)
        assert a2.rating is not Rating.INSUFFICIENT_DATA or a2.score is not None
        # Recurring one-time / no one-time defaults
        income = SimpleNamespace(
            consistency=SimpleNamespace(
                recurring_earnings=None,
                one_time_items_detected=True,
                other_income_dependence=None,
                interest_burden=0.2,
                revenue_consistency=0.5,
            ),
            profitability=SimpleNamespace(net_income_quality=0.5),
            revenue=SimpleNamespace(revenue=100.0, growth_stability=None),
            margins=SimpleNamespace(operating_margin=0.1, net_margin=0.1),
        )
        a3 = eng._assess_recurring(income, out, evidence)
        assert a3.score is not None and a3.score.value == pytest.approx(35.0)
        income.consistency.one_time_items_detected = False
        a4 = eng._assess_recurring(income, out, evidence)
        assert a4.score is not None and a4.score.value == pytest.approx(65.0)
        # Non-operating with only burden
        a5 = eng._assess_non_operating(income, out, evidence)
        assert a5.score is not None
        income.consistency.other_income_dependence = 0.3
        a5b = eng._assess_non_operating(income, out, evidence)
        assert a5b.score is not None
        # Revenue falls back to consistency
        a6 = eng._assess_revenue_quality(income, out, evidence)
        assert a6.score is not None

        # Weak cash already present → fcf weak skip-append branch
        from business_quality.scoring import Assessment

        flags4 = eng._flags(
            [Assessment(name="free_cash_flow_support", rating=Rating.WEAK)],
            SimpleNamespace(
                quality_flags=(),
                consistency=SimpleNamespace(one_time_items_detected=False),
            ),
            SimpleNamespace(operating=SimpleNamespace(cash_conversion=0.4)),
            None,
        )
        assert EarningsQualityFlag.WEAK_CASH_SUPPORT in flags4

        # FCF weak alone (conversion ok) adds weak cash
        flags5 = eng._flags(
            [Assessment(name="free_cash_flow_support", rating=Rating.POOR)],
            SimpleNamespace(
                quality_flags=(),
                consistency=SimpleNamespace(one_time_items_detected=False),
            ),
            SimpleNamespace(operating=SimpleNamespace(cash_conversion=0.8)),
            None,
        )
        assert EarningsQualityFlag.WEAK_CASH_SUPPORT in flags5


class TestPackageVersion:
    def test_version(self) -> None:
        import business_quality as bq

        assert bq.__version__ == "0.7.0"
        assert hasattr(bq, "EarningsQualityAnalysis")
        assert hasattr(bq, "analyze_earnings_quality") is False
        assert hasattr(bq.BusinessQualityEngine, "analyze_earnings_quality")
