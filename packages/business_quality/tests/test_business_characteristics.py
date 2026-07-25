"""Business Characteristics Intelligence tests — target 100% module coverage."""

from __future__ import annotations

from datetime import date
from types import SimpleNamespace

import pytest

from business_quality import (
    BUSINESS_QUALITY_VERSION,
    BusinessCharacteristicsEngine,
    BusinessCharacteristicsFlag,
    BusinessQualityEngine,
    BusinessQualityValidationError,
    Rating,
    validate_business_characteristics_input,
)
from business_quality.business_characteristics_engine import (
    BUSINESS_CHARACTERISTICS_VERSION,
    _asset_light,
    _business_simplicity,
    _capital_intensity,
    _cash_generation,
    _clip01,
    _cyclicality,
    _financial_resilience,
    _invert,
    _margin_durability,
    _mean,
    _normalize_op_lev,
    _normalize_turnover,
    _operating_leverage,
    _operational_stability,
    _ratio_metric,
    _scalability,
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
        assert _clip01(-0.2) == 0.0
        assert _invert(None) is None
        assert _invert(0.25) == pytest.approx(0.75)
        assert _mean([]) is None
        assert _mean([None, None]) is None
        assert _mean([0.2, None, 0.4]) == pytest.approx(0.3)

    def test_normalize_and_ratio(self) -> None:
        assert _normalize_turnover(None) is None
        assert _normalize_turnover(1.0) == pytest.approx(0.5)
        assert _normalize_turnover(4.0) == 1.0
        assert _normalize_turnover(1.0, scale=0.0) is None
        assert _normalize_op_lev(None) is None
        assert _normalize_op_lev(1.5) == pytest.approx(0.5)
        assert _normalize_op_lev(-6.0) == 1.0
        assert _ratio_metric(None, "x") is None
        assert _ratio_metric((), "x") is None
        metrics = (SimpleNamespace(name="asset_turnover", value=1.2),)
        assert _ratio_metric(metrics, "asset_turnover") == pytest.approx(1.2)

    def test_dimension_helpers(self) -> None:
        fa = _fa(1.0, 1.1, 1.2)
        income, balance, cash, ratios = (
            fa.income,
            fa.balance_sheet,
            fa.cash_flow,
            fa.ratios,
        )
        assert _business_simplicity(income, balance) is not None
        ci = _capital_intensity(cash, balance)
        assert ci is not None
        assert _asset_light(cash, balance, ci) is not None
        ol = _operating_leverage(income)
        assert _scalability(income, ratios, ol) is not None
        assert _margin_durability(income) is not None
        assert _cash_generation(cash) is not None
        assert _financial_resilience(balance, cash) is not None
        assert _cyclicality(income, fa.trends) is not None
        assert _operational_stability(income) is not None

        # Fallback OL from growth when consistency OL missing
        income_ns = SimpleNamespace(
            consistency=SimpleNamespace(operating_leverage=None),
            growth=SimpleNamespace(operating_leverage=3.0),
        )
        assert _operating_leverage(income_ns) == pytest.approx(1.0)

        # Cyclicality boosts
        volatile_income = SimpleNamespace(
            revenue=SimpleNamespace(
                growth_stability=0.2, trend_class=SimpleNamespace(value="volatile")
            ),
            consistency=SimpleNamespace(earnings_stability=0.3, revenue_consistency=0.4),
        )
        declining_income = SimpleNamespace(
            revenue=SimpleNamespace(
                growth_stability=None, trend_class=SimpleNamespace(value="declining")
            ),
            consistency=SimpleNamespace(earnings_stability=None, revenue_consistency=None),
        )
        trends = SimpleNamespace(
            trend_summary=SimpleNamespace(overall=SimpleNamespace(value="highly_volatile")),
            quality_flags=(SimpleNamespace(value="high_volatility"),),
        )
        assert _cyclicality(volatile_income, trends) is not None
        assert _cyclicality(declining_income, None) == pytest.approx(0.65)

        # Margin expansion branch in scalability
        income_exp = SimpleNamespace(
            profitability=SimpleNamespace(margin_expansion=0.1),
            revenue=SimpleNamespace(growth_stability=0.8),
        )
        ratios_empty = SimpleNamespace(efficiency=())
        assert _scalability(income_exp, ratios_empty, 0.5) is not None


class TestValidation:
    def test_missing_and_wrong_type(self) -> None:
        with pytest.raises(BusinessQualityValidationError, match="Missing"):
            validate_business_characteristics_input(None)
        with pytest.raises(BusinessQualityValidationError, match="ONLY"):
            validate_business_characteristics_input({"x": 1})

        class FinancialAnalysis:
            pass

        with pytest.raises(BusinessQualityValidationError, match="lacks"):
            validate_business_characteristics_input(FinancialAnalysis())

    def test_incomplete_evidence(self) -> None:
        fa = _fa(1.0)

        class FinancialAnalysis:
            pass

        obj = FinancialAnalysis()
        obj.income = SimpleNamespace(revenue=SimpleNamespace(revenue=None), profitability=None)
        obj.balance_sheet = SimpleNamespace(working_capital=None)
        obj.cash_flow = SimpleNamespace(
            quality=None, operating=SimpleNamespace(operating_cash_flow=None)
        )
        obj.ratios = fa.ratios
        obj.validation = fa.validation
        obj.metadata = fa.metadata
        obj.overall_summary = fa.overall_summary
        with pytest.raises(BusinessQualityValidationError, match="characteristic"):
            validate_business_characteristics_input(obj)

    def test_warnings(self) -> None:
        fa = _fa(1.0)

        class FinancialAnalysis:
            pass

        obj = FinancialAnalysis()
        obj.income = SimpleNamespace(
            revenue=SimpleNamespace(revenue=100.0),
            profitability=SimpleNamespace(margin_stability=None),
        )
        obj.balance_sheet = SimpleNamespace(
            working_capital=SimpleNamespace(balance_sheet_strength=None)
        )
        obj.cash_flow = SimpleNamespace(
            quality=SimpleNamespace(cash_sustainability=None),
            operating=SimpleNamespace(operating_cash_flow=50.0),
        )
        obj.ratios = fa.ratios
        obj.validation = SimpleNamespace(ok=False)
        obj.metadata = fa.metadata
        obj.overall_summary = fa.overall_summary
        result = validate_business_characteristics_input(obj)
        assert result.ok
        assert any("margin_stability" in w for w in result.warnings)
        assert any("not ok" in w for w in result.warnings)

    def test_ok(self) -> None:
        assert validate_business_characteristics_input(_fa(1.0, 1.1)).ok


class TestBusinessCharacteristics:
    def test_happy_path_dimensions(self) -> None:
        fa = _fa(1.0, 1.1, 1.2)
        result = BusinessCharacteristicsEngine().analyze(fa)
        assert result.metadata.engine_version == BUSINESS_CHARACTERISTICS_VERSION
        names = {a.name for a in result.assessments}
        assert names == {
            "business_simplicity",
            "capital_intensity",
            "asset_light",
            "operating_leverage",
            "business_scalability",
            "margin_durability",
            "cash_generation",
            "financial_resilience",
            "cyclicality",
            "operational_stability",
        }
        assert result.explainability
        assert result.to_dict()["overall_rating"]
        assert all(e.evidence and e.reasoning and e.limitations for e in result.explainability)
        assert all(e.references for e in result.explainability)

    def test_facade_compose(self) -> None:
        fa = _fa(1.0, 1.15)
        engine = BusinessQualityEngine()
        bc = engine.analyze_business_characteristics(fa)
        assert bc.overall_rating in Rating
        bq = engine.analyze(fa)
        assert bq.score is not None
        assert "EQ=" in bq.summary.headline
        assert "CA=" in bq.summary.headline
        assert "BC=" in bq.summary.headline
        assert BUSINESS_QUALITY_VERSION.startswith("0.7.0")
        assert "business_characteristics_intelligence" in bq.metadata.modules_composed
        assert len(bq.score.assessments) >= 20
        assert "CP=" in bq.summary.headline
        assert bq.earnings_quality is not None
        assert bq.competitive_position is not None

    def test_single_period(self) -> None:
        result = BusinessCharacteristicsEngine().analyze(_fa(1.0))
        assert result.validation.ok
        assert len(result.assessments) == 10

    def test_capital_intensive_path(self) -> None:
        stmts = []
        for i in range(3):
            stmts.append(
                _full(
                    year=2020 + i,
                    balance=BalanceSheet(
                        cash=20.0,
                        current_assets=100.0,
                        ppe=800.0,
                        total_assets=1000.0,
                        current_liabilities=150.0,
                        long_term_debt=400.0,
                        total_liabilities=600.0,
                        equity=400.0,
                        total_equity=400.0,
                    ),
                    cash=CashFlowStatement(
                        operating_cash_flow=120.0,
                        capex=-110.0,
                        free_cash_flow=10.0,
                    ),
                )
            )
        fa = FinancialEngine().analyze_financials(
            FinancialStatementsHistory(statements=tuple(stmts))
        )
        result = BusinessCharacteristicsEngine().analyze(fa)
        assert result.quality_flags or result.overall_rating in Rating

    def test_asset_light_path(self) -> None:
        stmts = []
        for i in range(3):
            stmts.append(
                _full(
                    year=2020 + i,
                    balance=BalanceSheet(
                        cash=400.0,
                        current_assets=800.0,
                        ppe=50.0,
                        goodwill=10.0,
                        intangibles=20.0,
                        total_assets=1000.0,
                        current_liabilities=100.0,
                        long_term_debt=50.0,
                        total_liabilities=200.0,
                        equity=800.0,
                        total_equity=800.0,
                    ),
                    cash=CashFlowStatement(
                        operating_cash_flow=300.0,
                        capex=-20.0,
                        free_cash_flow=280.0,
                    ),
                )
            )
        fa = FinancialEngine().analyze_financials(
            FinancialStatementsHistory(statements=tuple(stmts))
        )
        result = BusinessCharacteristicsEngine().analyze(fa)
        by_name = {a.name: a for a in result.assessments}
        assert by_name["asset_light"].score is not None

    def test_flag_composition(self) -> None:
        eng = BusinessCharacteristicsEngine()
        assessments = [
            Assessment(name="asset_light", rating=Rating.EXCELLENT),
            Assessment(name="capital_intensity", rating=Rating.EXCELLENT),
            Assessment(name="business_scalability", rating=Rating.STRONG),
            Assessment(name="operational_stability", rating=Rating.STRONG),
            Assessment(name="financial_resilience", rating=Rating.STRONG),
            Assessment(name="cyclicality", rating=Rating.STRONG),
            Assessment(name="cash_generation", rating=Rating.STRONG),
            Assessment(name="margin_durability", rating=Rating.EXCELLENT),
            Assessment(name="operating_leverage", rating=Rating.STRONG),
        ]
        income = SimpleNamespace(
            quality_flags=(SimpleNamespace(value="high_operating_leverage"),),
            revenue=SimpleNamespace(trend_class=SimpleNamespace(value="volatile")),
        )
        cash = SimpleNamespace(
            quality_flags=(
                SimpleNamespace(value="heavy_capex"),
                SimpleNamespace(value="strong_cash_generation"),
            )
        )
        balance = SimpleNamespace(
            quality_flags=(SimpleNamespace(value="healthy_balance_sheet"),)
        )
        flags = eng._flags(assessments, income, cash, balance, 0.8)
        assert BusinessCharacteristicsFlag.ASSET_LIGHT in flags
        assert BusinessCharacteristicsFlag.CAPITAL_INTENSIVE in flags
        assert BusinessCharacteristicsFlag.HIGHLY_SCALABLE in flags
        assert BusinessCharacteristicsFlag.OPERATIONALLY_STABLE in flags
        assert BusinessCharacteristicsFlag.RESILIENT_BUSINESS in flags
        assert BusinessCharacteristicsFlag.CYCLICAL_BUSINESS in flags
        assert BusinessCharacteristicsFlag.STRONG_CASH_GENERATOR in flags
        assert BusinessCharacteristicsFlag.MARGIN_DURABLE in flags
        assert BusinessCharacteristicsFlag.HIGH_OPERATING_LEVERAGE in flags

        # Flag append branches when rating-based flag not already set
        flags_b = eng._flags(
            [
                Assessment(name="asset_light", rating=Rating.AVERAGE),
                Assessment(name="capital_intensity", rating=Rating.AVERAGE),
                Assessment(name="business_scalability", rating=Rating.AVERAGE),
                Assessment(name="operational_stability", rating=Rating.AVERAGE),
                Assessment(name="financial_resilience", rating=Rating.AVERAGE),
                Assessment(name="cyclicality", rating=Rating.AVERAGE),
                Assessment(name="cash_generation", rating=Rating.AVERAGE),
                Assessment(name="margin_durability", rating=Rating.AVERAGE),
                Assessment(name="operating_leverage", rating=Rating.AVERAGE),
            ],
            income,
            cash,
            balance,
            None,
        )
        assert BusinessCharacteristicsFlag.CAPITAL_INTENSIVE in flags_b
        assert BusinessCharacteristicsFlag.RESILIENT_BUSINESS in flags_b
        assert BusinessCharacteristicsFlag.CYCLICAL_BUSINESS in flags_b
        assert BusinessCharacteristicsFlag.STRONG_CASH_GENERATOR in flags_b
        assert BusinessCharacteristicsFlag.HIGH_OPERATING_LEVERAGE in flags_b

    def test_assess_confidence_levels(self) -> None:
        eng = BusinessCharacteristicsEngine()
        out: list = []
        evidence: list = []
        a = eng._assess(
            "x",
            "X",
            0.9,
            "ref",
            "reason",
            out,
            evidence,
            extra_evidence="e=1",
        )
        assert a.confidence in Confidence
        assert a.score is not None
        a2 = eng._assess("y", "Y", None, "ref", "reason", out, evidence)
        assert a2.confidence in Confidence

    def test_analyze_with_sparse_fields(self) -> None:
        base = _fa(1.0, 1.1)

        class FinancialAnalysis:
            pass

        obj = FinancialAnalysis()
        obj.income = SimpleNamespace(
            revenue=SimpleNamespace(
                revenue=100.0,
                growth_stability=None,
                trend_class=SimpleNamespace(value="flat"),
            ),
            profitability=SimpleNamespace(
                margin_stability=None,
                margin_expansion=None,
                margin_compression=None,
            ),
            consistency=SimpleNamespace(
                other_income_dependence=None,
                operating_leverage=None,
                margin_consistency=None,
                earnings_stability=None,
                revenue_consistency=None,
            ),
            growth=SimpleNamespace(operating_leverage=None),
            quality_flags=(),
        )
        obj.balance_sheet = SimpleNamespace(
            assets=SimpleNamespace(
                goodwill_pct=None,
                intangible_asset_pct=None,
                asset_quality_score=None,
                non_current_asset_composition=None,
                current_asset_composition=None,
            ),
            working_capital=SimpleNamespace(
                asset_quality=None,
                balance_sheet_strength=0.5,
                financial_flexibility=None,
                debt_burden=None,
            ),
            quality_flags=(),
        )
        obj.cash_flow = SimpleNamespace(
            investing=SimpleNamespace(capex_intensity=None),
            quality=SimpleNamespace(
                cash_sustainability=0.6,
                operating_cash_quality=None,
                debt_sustainability=None,
            ),
            free_cash_flow=SimpleNamespace(fcf_stability=None),
            operating=SimpleNamespace(operating_cash_flow=100.0),
            quality_flags=(),
        )
        obj.ratios = SimpleNamespace(efficiency=())
        obj.validation = base.validation
        obj.metadata = base.metadata
        obj.overall_summary = SimpleNamespace(health_label="ok", strengths=("s1", "s2"))
        obj.trends = None
        result = BusinessCharacteristicsEngine().analyze(obj)
        assert result.assessments
        assert any("financial_summary" in e for e in result.evidence)


class TestPackage:
    def test_exports(self) -> None:
        import business_quality as bq

        assert bq.__version__ == "0.7.0"
        assert hasattr(bq, "BusinessCharacteristicsAnalysis")
        assert hasattr(bq, "BusinessCharacteristicsFlag")
        assert hasattr(bq.BusinessQualityEngine, "analyze_business_characteristics")
        assert bq.BUSINESS_CHARACTERISTICS_VERSION.startswith("0.4.0")

    def test_strength_weakness_helpers(self) -> None:
        from business_quality.engine import _strengths, _weaknesses
        from business_quality.earnings_quality_models import EarningsQualityFlag
        from business_quality.capital_allocation_models import CapitalAllocationFlag

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
                BusinessCharacteristicsFlag.ASSET_LIGHT,
                BusinessCharacteristicsFlag.CYCLICAL_BUSINESS,
                BusinessCharacteristicsFlag.CAPITAL_INTENSIVE,
                BusinessCharacteristicsFlag.HIGHLY_SCALABLE,
            )
        )
        strengths = _strengths(eq, ca, bc, SimpleNamespace(quality_flags=()))
        weaknesses = _weaknesses(eq, ca, bc, SimpleNamespace(quality_flags=()))
        assert any("high_earnings" in s for s in strengths)
        assert any("asset_light" in s for s in strengths)
        assert any("highly_scalable" in s for s in strengths)
        assert any("debt_dependent" in s for s in weaknesses)
        assert any("cyclical" in s for s in weaknesses)
        assert any("capital_intensive" in s for s in weaknesses)
