"""Competitive Position Indicators tests — target 100% module coverage."""

from __future__ import annotations

from datetime import date
from types import SimpleNamespace

import pytest

from business_quality import (
    BUSINESS_QUALITY_VERSION,
    BusinessQualityEngine,
    BusinessQualityValidationError,
    CompetitivePositionEngine,
    CompetitivePositionFlag,
    Rating,
    validate_competitive_position_input,
)
from business_quality.competitive_position_engine import (
    COMPETITIVE_POSITION_VERSION,
    _benchmark_score,
    _capital_efficiency,
    _cash_conversion,
    _clip01,
    _competitive_resilience,
    _financial_competitive_strength,
    _invert,
    _margin_defensibility,
    _mean,
    _normalize_turnover,
    _operational_efficiency,
    _pricing_power,
    _profitability_persistence,
    _ratio_metric,
    _return_on_capital,
    _revenue_stability,
)
from business_quality.scoring import Assessment, Confidence
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
    def test_clip_invert_mean(self) -> None:
        assert _clip01(None) is None
        assert _clip01(1.5) == 1.0
        assert _invert(None) is None
        assert _invert(0.2) == pytest.approx(0.8)
        assert _mean([]) is None
        assert _mean([0.4, None, 0.6]) == pytest.approx(0.5)
        assert _normalize_turnover(None) is None
        assert _normalize_turnover(1.0, scale=0.0) is None
        assert _normalize_turnover(2.0) == 1.0
        assert _ratio_metric(None, "x") is None
        assert _benchmark_score(None) is None
        assert _benchmark_score(SimpleNamespace(benchmark=SimpleNamespace(value="excellent"))) == 1.0
        assert _benchmark_score(SimpleNamespace(benchmark=SimpleNamespace(value="unknown"))) is None

    def test_dimension_helpers(self) -> None:
        fa = _fa(1.0, 1.1, 1.2)
        income, balance, cash, ratios = (
            fa.income,
            fa.balance_sheet,
            fa.cash_flow,
            fa.ratios,
        )
        assert _pricing_power(income) is not None
        assert _margin_defensibility(income) is not None
        assert _return_on_capital(ratios) is not None
        assert _cash_conversion(cash, ratios) is not None
        assert _operational_efficiency(ratios, balance) is not None
        assert _revenue_stability(income) is not None
        assert _profitability_persistence(income, fa.trends) is not None
        assert _capital_efficiency(ratios, cash) is not None
        assert _competitive_resilience(income, balance, cash) is not None
        assert _financial_competitive_strength(
            income, ratios, cash, fa.overall_summary
        ) is not None

        # Pricing expansion branch
        income_exp = SimpleNamespace(
            margins=SimpleNamespace(gross_margin=0.5, operating_margin=0.2),
            profitability=SimpleNamespace(margin_expansion=0.1, margin_compression=0.0),
        )
        assert _pricing_power(income_exp) is not None

        # Persistence trend branches
        income_p = SimpleNamespace(
            profitability=SimpleNamespace(
                earnings_consistency=0.7, margin_stability=0.6
            ),
            consistency=SimpleNamespace(earnings_stability=0.7, recurring_earnings=0.8),
        )
        trends_up = SimpleNamespace(
            consistency=SimpleNamespace(persistence_score=0.8, consistency_score=0.7),
            trend_summary=SimpleNamespace(
                profitability=SimpleNamespace(value="improving")
            ),
        )
        trends_down = SimpleNamespace(
            consistency=SimpleNamespace(persistence_score=None, consistency_score=None),
            trend_summary=SimpleNamespace(
                profitability=SimpleNamespace(value="weakening")
            ),
        )
        trends_stable = SimpleNamespace(
            consistency=None,
            trend_summary=SimpleNamespace(
                profitability=SimpleNamespace(value="stable")
            ),
        )
        assert _profitability_persistence(income_p, trends_up) is not None
        assert _profitability_persistence(income_p, trends_down) is not None
        assert _profitability_persistence(income_p, trends_stable) is not None
        assert _profitability_persistence(income_p, None) is not None

        # Financial competitive strength flag/health branches
        ratios_ex = SimpleNamespace(
            profitability=(),
            quality_flags=(SimpleNamespace(value="excellent_profitability"),),
        )
        ratios_wk = SimpleNamespace(
            profitability=(),
            quality_flags=(SimpleNamespace(value="weak_profitability"),),
        )
        cash_ns = SimpleNamespace(quality=SimpleNamespace(cash_sustainability=0.5))
        income_ns = SimpleNamespace(
            profitability=SimpleNamespace(
                operating_profit_quality=0.6, net_income_quality=0.5
            )
        )
        assert (
            _financial_competitive_strength(
                income_ns,
                ratios_ex,
                cash_ns,
                SimpleNamespace(health_label="excellent_financial_health"),
            )
            is not None
        )
        assert (
            _financial_competitive_strength(
                income_ns,
                ratios_wk,
                cash_ns,
                SimpleNamespace(health_label="financial_deterioration"),
            )
            is not None
        )


class TestValidation:
    def test_missing_and_wrong_type(self) -> None:
        with pytest.raises(BusinessQualityValidationError, match="Missing"):
            validate_competitive_position_input(None)
        with pytest.raises(BusinessQualityValidationError, match="ONLY"):
            validate_competitive_position_input({"x": 1})

        class FinancialAnalysis:
            pass

        with pytest.raises(BusinessQualityValidationError, match="lacks"):
            validate_competitive_position_input(FinancialAnalysis())

    def test_incomplete_evidence(self) -> None:
        fa = _fa(1.0)

        class FinancialAnalysis:
            pass

        obj = FinancialAnalysis()
        obj.income = SimpleNamespace(
            revenue=SimpleNamespace(revenue=None),
            margins=None,
            profitability=None,
        )
        obj.balance_sheet = fa.balance_sheet
        obj.cash_flow = SimpleNamespace(
            operating=SimpleNamespace(operating_cash_flow=None)
        )
        obj.ratios = SimpleNamespace(profitability=())
        obj.validation = fa.validation
        obj.metadata = fa.metadata
        obj.overall_summary = fa.overall_summary
        with pytest.raises(BusinessQualityValidationError, match="competitive"):
            validate_competitive_position_input(obj)

    def test_warnings(self) -> None:
        fa = _fa(1.0)

        class FinancialAnalysis:
            pass

        obj = FinancialAnalysis()
        obj.income = SimpleNamespace(
            revenue=SimpleNamespace(revenue=100.0),
            margins=SimpleNamespace(gross_margin=None),
            profitability=SimpleNamespace(margin_stability=None),
        )
        obj.balance_sheet = fa.balance_sheet
        obj.cash_flow = SimpleNamespace(
            operating=SimpleNamespace(operating_cash_flow=50.0)
        )
        obj.ratios = SimpleNamespace(profitability=None)
        obj.validation = SimpleNamespace(ok=False)
        obj.metadata = fa.metadata
        obj.overall_summary = fa.overall_summary
        result = validate_competitive_position_input(obj)
        assert result.ok
        assert any("gross_margin" in w for w in result.warnings)
        assert any("return-on-capital" in w for w in result.warnings)
        assert any("not ok" in w for w in result.warnings)

        # Cover _ratio_value when profitability metrics is None (already) and
        # when present but name missing — also exercise found-path via real FA
        assert validate_competitive_position_input(_fa(1.0)).ok

    def test_ok(self) -> None:
        assert validate_competitive_position_input(_fa(1.0, 1.1)).ok


class TestCompetitivePosition:
    def test_happy_path_dimensions(self) -> None:
        fa = _fa(1.0, 1.1, 1.2)
        result = CompetitivePositionEngine().analyze(fa)
        assert result.metadata.engine_version == COMPETITIVE_POSITION_VERSION
        names = {a.name for a in result.assessments}
        assert names == {
            "pricing_power",
            "margin_defensibility",
            "return_on_capital_strength",
            "cash_conversion_advantage",
            "operational_efficiency",
            "revenue_stability",
            "profitability_persistence",
            "capital_efficiency",
            "competitive_resilience",
            "financial_competitive_strength",
        }
        assert result.explainability
        assert result.to_dict()["overall_rating"]
        assert all(
            e.evidence and e.reasoning and e.limitations and e.references
            for e in result.explainability
        )

    def test_facade_compose(self) -> None:
        fa = _fa(1.0, 1.15)
        engine = BusinessQualityEngine()
        cp = engine.analyze_competitive_position(fa)
        assert cp.overall_rating in Rating
        bq = engine.analyze(fa)
        assert bq.score is not None
        assert "EQ=" in bq.summary.headline
        assert "CA=" in bq.summary.headline
        assert "BC=" in bq.summary.headline
        assert "CP=" in bq.summary.headline
        assert BUSINESS_QUALITY_VERSION.startswith("0.7.0")
        assert "competitive_position_indicators" in bq.metadata.modules_composed
        assert len(bq.score.assessments) >= 30
        assert bq.overall_rating is not None
        assert bq.weights_used is not None

    def test_single_period(self) -> None:
        result = CompetitivePositionEngine().analyze(_fa(1.0))
        assert result.validation.ok
        assert len(result.assessments) == 10

    def test_flag_composition(self) -> None:
        eng = CompetitivePositionEngine()
        assessments = [
            Assessment(name="pricing_power", rating=Rating.EXCELLENT),
            Assessment(name="margin_defensibility", rating=Rating.STRONG),
            Assessment(name="capital_efficiency", rating=Rating.STRONG),
            Assessment(name="operational_efficiency", rating=Rating.STRONG),
            Assessment(name="profitability_persistence", rating=Rating.AVERAGE),
        ]
        income = SimpleNamespace(
            quality_flags=(
                SimpleNamespace(value="margin_expansion"),
                SimpleNamespace(value="margin_compression"),
            )
        )
        ratios = SimpleNamespace(
            quality_flags=(
                SimpleNamespace(value="poor_efficiency"),
                SimpleNamespace(value="efficient_operations"),
                SimpleNamespace(value="weak_profitability"),
            )
        )
        trends = SimpleNamespace(
            trend_summary=SimpleNamespace(
                profitability=SimpleNamespace(value="strongly_weakening")
            )
        )
        flags = eng._flags(assessments, income, ratios, trends, 0.8)
        assert CompetitivePositionFlag.STRONG_COMPETITIVE_POSITION in flags
        assert CompetitivePositionFlag.STRONG_PRICING_POWER in flags
        assert CompetitivePositionFlag.DURABLE_MARGINS in flags
        assert CompetitivePositionFlag.MARGIN_PRESSURE in flags
        assert CompetitivePositionFlag.HIGH_CAPITAL_EFFICIENCY in flags
        assert CompetitivePositionFlag.OPERATIONAL_EXCELLENCE in flags
        assert CompetitivePositionFlag.DECLINING_PROFITABILITY in flags

        flags_weak = eng._flags(
            [
                Assessment(name="pricing_power", rating=Rating.AVERAGE),
                Assessment(name="margin_defensibility", rating=Rating.POOR),
                Assessment(name="capital_efficiency", rating=Rating.WEAK),
                Assessment(name="operational_efficiency", rating=Rating.AVERAGE),
                Assessment(name="profitability_persistence", rating=Rating.POOR),
            ],
            SimpleNamespace(quality_flags=()),
            SimpleNamespace(quality_flags=()),
            None,
            0.3,
        )
        assert CompetitivePositionFlag.WEAK_COMPETITIVE_POSITION in flags_weak
        assert CompetitivePositionFlag.MARGIN_PRESSURE in flags_weak
        assert CompetitivePositionFlag.WEAK_CAPITAL_EFFICIENCY in flags_weak
        assert CompetitivePositionFlag.DECLINING_PROFITABILITY in flags_weak

        # Append branches when rating-based flags absent
        flags_b = eng._flags(
            [
                Assessment(name="pricing_power", rating=Rating.AVERAGE),
                Assessment(name="margin_defensibility", rating=Rating.AVERAGE),
                Assessment(name="capital_efficiency", rating=Rating.AVERAGE),
                Assessment(name="operational_efficiency", rating=Rating.AVERAGE),
                Assessment(name="profitability_persistence", rating=Rating.AVERAGE),
            ],
            income,
            ratios,
            trends,
            None,
        )
        assert CompetitivePositionFlag.STRONG_PRICING_POWER in flags_b
        assert CompetitivePositionFlag.MARGIN_PRESSURE in flags_b
        assert CompetitivePositionFlag.WEAK_CAPITAL_EFFICIENCY in flags_b
        assert CompetitivePositionFlag.OPERATIONAL_EXCELLENCE in flags_b
        assert CompetitivePositionFlag.DECLINING_PROFITABILITY in flags_b

        # Volatile profitability trend branch
        flags_v = eng._flags(
            assessments,
            SimpleNamespace(quality_flags=()),
            SimpleNamespace(quality_flags=()),
            SimpleNamespace(
                trend_summary=SimpleNamespace(
                    profitability=SimpleNamespace(value="highly_volatile")
                )
            ),
            0.5,
        )
        assert CompetitivePositionFlag.DECLINING_PROFITABILITY in flags_v

    def test_assess_and_sparse(self) -> None:
        eng = CompetitivePositionEngine()
        out: list = []
        evidence: list = []
        a = eng._assess(
            "x", "X", 0.9, "ref", "reason", out, evidence, extra_evidence="e=1"
        )
        assert a.confidence in Confidence
        assert a.score is not None
        a2 = eng._assess("y", "Y", None, "ref", "reason", out, evidence)
        assert a2.confidence in Confidence

        base = _fa(1.0, 1.1)

        class FinancialAnalysis:
            pass

        obj = FinancialAnalysis()
        obj.income = SimpleNamespace(
            revenue=SimpleNamespace(revenue=100.0, growth_stability=None),
            margins=SimpleNamespace(gross_margin=None, operating_margin=None),
            profitability=SimpleNamespace(
                margin_stability=None,
                margin_expansion=None,
                margin_compression=None,
                earnings_consistency=None,
                operating_profit_quality=None,
                net_income_quality=None,
            ),
            consistency=SimpleNamespace(
                margin_consistency=None,
                earnings_stability=None,
                recurring_earnings=None,
                revenue_consistency=None,
            ),
            quality_flags=(),
        )
        obj.balance_sheet = SimpleNamespace(
            working_capital=SimpleNamespace(
                inventory_efficiency=None,
                balance_sheet_strength=0.5,
                financial_flexibility=None,
                debt_burden=None,
            )
        )
        obj.cash_flow = SimpleNamespace(
            operating=SimpleNamespace(cash_conversion=None, operating_cash_flow=100.0),
            free_cash_flow=SimpleNamespace(fcf_margin=None),
            quality=SimpleNamespace(
                operating_cash_quality=None, cash_sustainability=0.5
            ),
            investing=SimpleNamespace(capex_intensity=None),
            quality_flags=(),
        )
        obj.ratios = SimpleNamespace(
            profitability=(),
            efficiency=(),
            cash_flow=(),
            quality_flags=(),
        )
        obj.validation = base.validation
        obj.metadata = base.metadata
        obj.overall_summary = SimpleNamespace(
            health_label="needs_attention", strengths=("s1",)
        )
        obj.trends = None
        result = CompetitivePositionEngine().analyze(obj)
        assert result.assessments
        assert any("financial_summary" in e for e in result.evidence)


class TestPackage:
    def test_exports(self) -> None:
        import business_quality as bq

        assert bq.__version__ == "0.7.0"
        assert hasattr(bq, "CompetitivePositionAnalysis")
        assert hasattr(bq, "CompetitivePositionFlag")
        assert hasattr(bq.BusinessQualityEngine, "analyze_competitive_position")
        assert bq.COMPETITIVE_POSITION_VERSION.startswith("0.5.0")

    def test_strength_weakness_helpers(self) -> None:
        from business_quality.engine import _strengths, _weaknesses
        from business_quality.earnings_quality_models import EarningsQualityFlag
        from business_quality.capital_allocation_models import CapitalAllocationFlag
        from business_quality.business_characteristics_models import (
            BusinessCharacteristicsFlag,
        )

        eq = SimpleNamespace(
            quality_flags=(EarningsQualityFlag.HIGH_EARNINGS_QUALITY,)
        )
        ca = SimpleNamespace(
            quality_flags=(CapitalAllocationFlag.EXCELLENT_CAPITAL_ALLOCATION,)
        )
        bc = SimpleNamespace(
            quality_flags=(BusinessCharacteristicsFlag.ASSET_LIGHT,)
        )
        cp = SimpleNamespace(
            quality_flags=(
                CompetitivePositionFlag.STRONG_COMPETITIVE_POSITION,
                CompetitivePositionFlag.MARGIN_PRESSURE,
                CompetitivePositionFlag.WEAK_COMPETITIVE_POSITION,
            )
        )
        strengths = _strengths(eq, ca, bc, cp)
        weaknesses = _weaknesses(eq, ca, bc, cp)
        assert any("strong_competitive" in s for s in strengths)
        assert any("margin_pressure" in s for s in weaknesses)
        assert any("weak_competitive" in s for s in weaknesses)
