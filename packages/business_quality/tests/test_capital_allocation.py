"""Capital Allocation Intelligence tests — target 100% module coverage."""

from __future__ import annotations

from datetime import date
from types import SimpleNamespace

import pytest

from business_quality import (
    BUSINESS_QUALITY_VERSION,
    CapitalAllocationEngine,
    CapitalAllocationFlag,
    BusinessQualityEngine,
    BusinessQualityValidationError,
    Rating,
    validate_capital_allocation_input,
)
from business_quality.capital_allocation_engine import (
    CAPITAL_ALLOCATION_VERSION,
    _capex_from_intensity,
    _flexibility,
)
from business_quality.scoring import Assessment, Confidence, Score
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
    stmts = [_full(year=2020 + i, scale=s) for i, s in enumerate(scales or (1.0,))]
    if len(stmts) == 1:
        return FinancialEngine().analyze_financials(stmts[0])
    return FinancialEngine().analyze_financials(
        FinancialStatementsHistory(statements=tuple(stmts))
    )


class TestHelpers:
    def test_capex_and_flexibility(self) -> None:
        assert _capex_from_intensity(None) is None
        assert _capex_from_intensity(0.2) == pytest.approx(0.8)
        assert _capex_from_intensity(1.5) == pytest.approx(0.0)
        assert _flexibility(None, None) is None
        assert _flexibility(0.2, None) == pytest.approx(0.8)
        assert _flexibility(None, 0.6) == pytest.approx(0.6)
        assert _flexibility(0.5, 0.5) == pytest.approx(0.5)


class TestValidation:
    def test_missing_and_wrong_type(self) -> None:
        with pytest.raises(BusinessQualityValidationError, match="Missing"):
            validate_capital_allocation_input(None)
        with pytest.raises(BusinessQualityValidationError, match="ONLY"):
            validate_capital_allocation_input({"x": 1})

        class FinancialAnalysis:
            pass

        with pytest.raises(BusinessQualityValidationError, match="lacks"):
            validate_capital_allocation_input(FinancialAnalysis())

    def test_incomplete_evidence(self) -> None:
        fa = _fa(1.0)

        class FinancialAnalysis:
            pass

        obj = FinancialAnalysis()
        obj.cash_flow = SimpleNamespace(
            operating=SimpleNamespace(operating_cash_flow=None),
            investing=SimpleNamespace(investment_discipline=None),
        )
        obj.ratios = SimpleNamespace(
            capital_allocation=SimpleNamespace(
                capital_allocation_score=None, capex_discipline=None
            )
        )
        obj.validation = fa.validation
        obj.metadata = fa.metadata
        obj.overall_summary = fa.overall_summary
        with pytest.raises(BusinessQualityValidationError, match="capital allocation"):
            validate_capital_allocation_input(obj)

    def test_warnings(self) -> None:
        fa = _fa(1.0)

        class FinancialAnalysis:
            pass

        obj = FinancialAnalysis()
        obj.cash_flow = SimpleNamespace(
            operating=SimpleNamespace(operating_cash_flow=100.0),
            investing=SimpleNamespace(investment_discipline=None),
        )
        obj.ratios = SimpleNamespace(
            capital_allocation=SimpleNamespace(
                capital_allocation_score=None, capex_discipline=None
            )
        )
        obj.validation = SimpleNamespace(ok=False)
        obj.metadata = fa.metadata
        obj.overall_summary = fa.overall_summary
        result = validate_capital_allocation_input(obj)
        assert result.ok
        assert any("capital_allocation_score" in w for w in result.warnings)
        assert any("not ok" in w for w in result.warnings)

    def test_ok(self) -> None:
        assert validate_capital_allocation_input(_fa(1.0, 1.1)).ok


class TestCapitalAllocation:
    def test_happy_path(self) -> None:
        fa = _fa(1.0, 1.1, 1.2)
        result = CapitalAllocationEngine().analyze(fa)
        assert result.metadata.engine_version == CAPITAL_ALLOCATION_VERSION
        names = {a.name for a in result.assessments}
        assert "capex_discipline" in names
        assert "debt_reduction_discipline" in names
        assert "dilution_discipline" in names
        assert "shareholder_capital_stewardship" in names
        assert result.explainability
        assert result.to_dict()["overall_rating"]

    def test_facade_compose(self) -> None:
        fa = _fa(1.0, 1.15)
        engine = BusinessQualityEngine()
        ca = engine.analyze_capital_allocation(fa)
        assert ca.overall_rating in Rating
        bq = engine.analyze(fa)
        assert bq.score is not None
        assert "EQ=" in bq.summary.headline
        assert "CA=" in bq.summary.headline
        assert BUSINESS_QUALITY_VERSION.startswith("0.7.0")
        assert len(bq.score.assessments) >= 10
        assert "BC=" in bq.summary.headline
        assert "CP=" in bq.summary.headline
        assert bq.capital_allocation is not None

    def test_single_period(self) -> None:
        result = CapitalAllocationEngine().analyze(_fa(1.0))
        assert result.validation.ok
        assert len(result.assessments) == 11

    def test_heavy_capex_path(self) -> None:
        stmts = []
        for i in range(3):
            stmts.append(
                _full(
                    year=2020 + i,
                    cash=CashFlowStatement(
                        operating_cash_flow=100.0,
                        capex=-95.0,
                        free_cash_flow=5.0,
                        dividends_paid=-80.0,
                        share_buybacks=-10.0,
                        debt_issued=50.0,
                        debt_repaid=-5.0,
                    ),
                )
            )
        fa = FinancialEngine().analyze_financials(
            FinancialStatementsHistory(statements=tuple(stmts))
        )
        result = CapitalAllocationEngine().analyze(fa)
        assert result.quality_flags or result.overall_rating in Rating

    def test_flag_composition(self) -> None:
        eng = CapitalAllocationEngine()
        assessments = [
            Assessment(name="reinvestment_quality", rating=Rating.EXCELLENT),
            Assessment(name="capex_discipline", rating=Rating.POOR),
            Assessment(name="shareholder_capital_stewardship", rating=Rating.STRONG),
            Assessment(name="cash_deployment_quality", rating=Rating.STRONG),
            Assessment(name="dividend_allocation_quality", rating=Rating.POOR),
            Assessment(name="capital_allocation_consistency", rating=Rating.WEAK),
        ]
        cash = SimpleNamespace(
            quality_flags=(
                SimpleNamespace(value="heavy_capex"),
                SimpleNamespace(value="shareholder_friendly"),
                SimpleNamespace(value="healthy_capital_allocation"),
            ),
            financing=SimpleNamespace(financing_dependence=0.7),
        )
        ratios = SimpleNamespace(
            quality_flags=(SimpleNamespace(value="capital_allocation_warning"),),
            capital_allocation=SimpleNamespace(dividend_sustainability=0.2),
        )
        trends = SimpleNamespace(
            ratio_trends=(
                SimpleNamespace(
                    name="capital_allocation_score",
                    classification=SimpleNamespace(value="highly_volatile"),
                    consistency=0.2,
                ),
            )
        )
        flags = eng._flags(assessments, cash, ratios, trends, 0.8)
        assert CapitalAllocationFlag.EXCELLENT_CAPITAL_ALLOCATION in flags
        assert CapitalAllocationFlag.DISCIPLINED_REINVESTMENT in flags
        assert CapitalAllocationFlag.EXCESSIVE_CAPITAL_SPENDING in flags
        assert CapitalAllocationFlag.SHAREHOLDER_FRIENDLY in flags
        assert CapitalAllocationFlag.HEALTHY_CASH_DEPLOYMENT in flags
        assert CapitalAllocationFlag.DEBT_DEPENDENT in flags
        assert CapitalAllocationFlag.DIVIDEND_AT_RISK in flags
        assert CapitalAllocationFlag.INCONSISTENT_ALLOCATION in flags

        flags2 = eng._flags(assessments, cash, ratios, None, 0.3)
        assert CapitalAllocationFlag.WEAK_CAPITAL_ALLOCATION in flags2

        # Flag append branches when rating-based flag not already set
        cash_b = SimpleNamespace(
            quality_flags=(
                SimpleNamespace(value="heavy_capex"),
                SimpleNamespace(value="shareholder_friendly"),
                SimpleNamespace(value="healthy_capital_allocation"),
            ),
            financing=SimpleNamespace(financing_dependence=0.1),
        )
        ratios_b = SimpleNamespace(
            quality_flags=(),
            capital_allocation=SimpleNamespace(dividend_sustainability=0.2),
        )
        trends_b = SimpleNamespace(
            ratio_trends=(
                SimpleNamespace(
                    name="capital_allocation_score",
                    classification=SimpleNamespace(value="strongly_weakening"),
                    consistency=0.1,
                ),
            )
        )
        flags_b = eng._flags(
            [
                Assessment(name="reinvestment_quality", rating=Rating.AVERAGE),
                Assessment(name="capex_discipline", rating=Rating.AVERAGE),
                Assessment(name="shareholder_capital_stewardship", rating=Rating.AVERAGE),
                Assessment(name="cash_deployment_quality", rating=Rating.AVERAGE),
                Assessment(name="dividend_allocation_quality", rating=Rating.AVERAGE),
                Assessment(name="capital_allocation_consistency", rating=Rating.AVERAGE),
            ],
            cash_b,
            ratios_b,
            trends_b,
            0.5,
        )
        assert CapitalAllocationFlag.EXCESSIVE_CAPITAL_SPENDING in flags_b
        assert CapitalAllocationFlag.SHAREHOLDER_FRIENDLY in flags_b
        assert CapitalAllocationFlag.HEALTHY_CASH_DEPLOYMENT in flags_b
        assert CapitalAllocationFlag.DIVIDEND_AT_RISK in flags_b
        assert CapitalAllocationFlag.INCONSISTENT_ALLOCATION in flags_b

    def test_fallbacks_and_stewardship(self) -> None:
        eng = CapitalAllocationEngine()
        out: list = []
        evidence: list = []
        # Fallback intensity → capex
        a = eng._assess(
            "capex_discipline",
            "Capex",
            _capex_from_intensity(0.4),
            "ref",
            "reason",
            out,
            evidence,
            extra_evidence="x=1",
        )
        assert a.score is not None
        # Consistency without trends uses score
        a2 = eng._consistency(None, 0.7, out, evidence)
        assert a2.score is not None
        # Consistency with trends
        trends = SimpleNamespace(
            ratio_trends=(
                SimpleNamespace(
                    name="capital_allocation_score",
                    classification=SimpleNamespace(value="improving"),
                    consistency=0.85,
                ),
            )
        )
        a3 = eng._consistency(trends, 0.5, out, evidence)
        assert a3.score is not None and a3.score.value == pytest.approx(85.0)
        # Stewardship from shareholder flag only
        cash = SimpleNamespace(
            quality_flags=(SimpleNamespace(value="shareholder_friendly"),),
            financing=SimpleNamespace(capital_allocation_quality=None),
        )
        cap = SimpleNamespace(
            dividend_sustainability=None, buyback_sustainability=None
        )
        a4 = eng._stewardship(cash, cap, out, evidence)
        assert a4.score is not None and a4.score.value == pytest.approx(75.0)
        # Stewardship with parts
        cap2 = SimpleNamespace(
            dividend_sustainability=0.8, buyback_sustainability=0.6
        )
        cash2 = SimpleNamespace(
            quality_flags=(),
            financing=SimpleNamespace(capital_allocation_quality=0.7),
        )
        a5 = eng._stewardship(cash2, cap2, out, evidence)
        assert a5.score is not None

    def test_analyze_with_minimal_namespaces(self) -> None:
        """Drive fallbacks when ratio capital fields are None."""
        base = _fa(1.0, 1.1)

        class FinancialAnalysis:
            pass

        obj = FinancialAnalysis()
        obj.income = base.income
        obj.cash_flow = base.cash_flow
        obj.ratios = SimpleNamespace(
            capital_allocation=SimpleNamespace(
                capital_allocation_score=None,
                capex_discipline=None,
                dividend_sustainability=None,
                buyback_sustainability=None,
                debt_reduction_quality=None,
            ),
            quality_flags=(),
        )
        obj.validation = base.validation
        obj.metadata = base.metadata
        obj.overall_summary = base.overall_summary
        obj.trends = base.trends
        result = CapitalAllocationEngine().analyze(obj)
        assert result.assessments


class TestPackage:
    def test_exports(self) -> None:
        import business_quality as bq

        assert bq.__version__ == "0.7.0"
        assert hasattr(bq, "CapitalAllocationAnalysis")
        assert hasattr(bq.BusinessQualityEngine, "analyze_capital_allocation")

    def test_strength_weakness_helpers(self) -> None:
        from business_quality.engine import _strengths, _weaknesses
        from business_quality.earnings_quality_models import EarningsQualityFlag
        from business_quality.capital_allocation_models import CapitalAllocationFlag
        from business_quality.business_characteristics_models import (
            BusinessCharacteristicsFlag,
        )

        eq = SimpleNamespace(
            quality_flags=(
                EarningsQualityFlag.HIGH_EARNINGS_QUALITY,
                EarningsQualityFlag.WEAK_CASH_SUPPORT,
            )
        )
        ca = SimpleNamespace(
            quality_flags=(
                CapitalAllocationFlag.EXCELLENT_CAPITAL_ALLOCATION,
                CapitalAllocationFlag.DEBT_DEPENDENT,
            )
        )
        bc = SimpleNamespace(
            quality_flags=(
                BusinessCharacteristicsFlag.MARGIN_DURABLE,
                BusinessCharacteristicsFlag.CYCLICAL_BUSINESS,
            )
        )
        assert any("high_earnings" in s for s in _strengths(eq, ca, bc, SimpleNamespace(quality_flags=())))
        assert any("debt_dependent" in s for s in _weaknesses(eq, ca, bc, SimpleNamespace(quality_flags=())))
        assert any("excellent_capital" in s for s in _strengths(eq, ca, bc, SimpleNamespace(quality_flags=())))
        assert any("weak_cash" in s for s in _weaknesses(eq, ca, bc, SimpleNamespace(quality_flags=())))
        assert any("margin_durable" in s for s in _strengths(eq, ca, bc, SimpleNamespace(quality_flags=())))
        assert any("cyclical" in s for s in _weaknesses(eq, ca, bc, SimpleNamespace(quality_flags=())))
