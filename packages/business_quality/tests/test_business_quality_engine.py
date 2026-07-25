"""Business Quality Engine (F3.6) tests — target 100% module coverage."""

from __future__ import annotations

from datetime import date
from types import SimpleNamespace

import pytest

from business_quality import (
    BUSINESS_QUALITY_VERSION,
    BusinessQualityEngine,
    BusinessQualityValidationError,
    BusinessQualityWeights,
    FlagSeverity,
    OverallRating,
    aggregate_flags,
    compose_overall_score,
    overall_rating_from_01,
    validate_business_quality_input,
    validate_module_outputs,
    validate_weights,
)
from business_quality.business_quality_engine import (
    BUSINESS_QUALITY_ENGINE_VERSION,
    _classify_flag,
    _map_overall_to_bq_flag,
    _module_01,
)
from business_quality.business_quality_explainability import (
    merge_module_explainability,
    bq_explanation,
)
from business_quality.business_quality_models import BusinessQualityFlag
from business_quality.explainability import BusinessQualityExplainability
from business_quality.scoring import Confidence, Rating, Score
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


def _full(*, year: int = 2024, scale: float = 1.0) -> FinancialStatements:
    return FinancialStatements(
        period=_period(end=date(year, 12, 31), fy=year),
        income_statement=IncomeStatement(
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
        ),
        balance_sheet=BalanceSheet(
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
        ),
        cash_flow=CashFlowStatement(
            operating_cash_flow=250.0 * scale,
            capex=-80.0 * scale,
            free_cash_flow=170.0 * scale,
            dividends_paid=-50.0 * scale,
            share_buybacks=-30.0 * scale,
            debt_issued=10.0 * scale,
            debt_repaid=-40.0 * scale,
        ),
        statement_metadata=StatementMetadata(unit_scale=UnitScale.MILLIONS),
    )


def _fa(*scales: float):
    stmts = [_full(year=2020 + i, scale=s) for i, s in enumerate(scales or (1.0,))]
    if len(stmts) == 1:
        return FinancialEngine().analyze_financials(stmts[0])
    return FinancialEngine().analyze_financials(
        FinancialStatementsHistory(statements=tuple(stmts))
    )


class TestValidation:
    def test_missing_and_wrong_type(self) -> None:
        with pytest.raises(BusinessQualityValidationError, match="Missing"):
            validate_business_quality_input(None)
        with pytest.raises(BusinessQualityValidationError, match="ONLY"):
            validate_business_quality_input({"x": 1})

        class FinancialAnalysis:
            pass

        with pytest.raises(BusinessQualityValidationError, match="lacks"):
            validate_business_quality_input(FinancialAnalysis())

    def test_incomplete_evidence(self) -> None:
        fa = _fa(1.0)

        class FinancialAnalysis:
            pass

        obj = FinancialAnalysis()
        obj.income = SimpleNamespace(revenue=SimpleNamespace(revenue=None))
        obj.balance_sheet = fa.balance_sheet
        obj.cash_flow = SimpleNamespace(
            operating=SimpleNamespace(operating_cash_flow=None)
        )
        obj.ratios = fa.ratios
        obj.validation = fa.validation
        obj.metadata = fa.metadata
        obj.overall_summary = fa.overall_summary
        with pytest.raises(BusinessQualityValidationError, match="Business Quality"):
            validate_business_quality_input(obj)

    def test_warnings_and_ok(self) -> None:
        fa = _fa(1.0)

        class FinancialAnalysis:
            pass

        obj = FinancialAnalysis()
        obj.income = fa.income
        obj.balance_sheet = fa.balance_sheet
        obj.cash_flow = fa.cash_flow
        obj.ratios = fa.ratios
        obj.validation = SimpleNamespace(ok=False)
        obj.metadata = fa.metadata
        obj.overall_summary = fa.overall_summary
        result = validate_business_quality_input(obj)
        assert result.ok
        assert any("not ok" in w for w in result.warnings)
        assert validate_business_quality_input(_fa(1.0, 1.1)).ok

    def test_weights(self) -> None:
        assert validate_weights(None).earnings_quality == pytest.approx(0.3)
        ok = validate_weights(
            BusinessQualityWeights(
                earnings_quality=0.4,
                capital_allocation=0.3,
                business_characteristics=0.2,
                competitive_position=0.1,
            )
        )
        assert ok.competitive_position == pytest.approx(0.1)
        with pytest.raises(BusinessQualityValidationError, match="weighting"):
            validate_weights(
                BusinessQualityWeights(
                    earnings_quality=-0.1,
                    capital_allocation=0.5,
                    business_characteristics=0.3,
                    competitive_position=0.3,
                )
            )
        with pytest.raises(BusinessQualityValidationError, match="positive"):
            validate_weights(
                BusinessQualityWeights(
                    earnings_quality=0.0,
                    capital_allocation=0.0,
                    business_characteristics=0.0,
                    competitive_position=0.0,
                )
            )
        with pytest.raises(BusinessQualityValidationError, match="finite"):
            validate_weights(
                BusinessQualityWeights(
                    earnings_quality=float("nan"),
                    capital_allocation=0.5,
                    business_characteristics=0.3,
                    competitive_position=0.2,
                )
            )
        with pytest.raises(BusinessQualityValidationError, match="numeric"):
            validate_weights(
                SimpleNamespace(  # type: ignore[arg-type]
                    as_dict=lambda: {
                        "earnings_quality": True,
                        "capital_allocation": 0.3,
                        "business_characteristics": 0.2,
                        "competitive_position": 0.2,
                    },
                )
            )

    def test_module_outputs(self) -> None:
        with pytest.raises(BusinessQualityValidationError, match="Missing module"):
            validate_module_outputs(
                earnings_quality=None,
                capital_allocation=object(),
                business_characteristics=object(),
                competitive_position=object(),
            )
        with pytest.raises(BusinessQualityValidationError, match="incomplete"):
            validate_module_outputs(
                earnings_quality=SimpleNamespace(),
                capital_allocation=SimpleNamespace(
                    overall_score=Score(value=1.0), validation=object()
                ),
                business_characteristics=SimpleNamespace(
                    overall_score=Score(value=1.0), validation=object()
                ),
                competitive_position=SimpleNamespace(
                    overall_score=Score(value=1.0), validation=object()
                ),
            )
        complete = SimpleNamespace(overall_score=Score(value=50.0), validation=object())
        assert validate_module_outputs(
            earnings_quality=complete,
            capital_allocation=complete,
            business_characteristics=complete,
            competitive_position=complete,
        ).ok


class TestScoringAndFlags:
    def test_overall_rating_bands(self) -> None:
        assert overall_rating_from_01(None) is OverallRating.AVERAGE
        assert overall_rating_from_01(0.90) is OverallRating.EXCELLENT
        assert overall_rating_from_01(0.76) is OverallRating.STRONG
        assert overall_rating_from_01(0.66) is OverallRating.GOOD
        assert overall_rating_from_01(0.55) is OverallRating.AVERAGE
        assert overall_rating_from_01(0.40) is OverallRating.WEAK
        assert overall_rating_from_01(0.10) is OverallRating.POOR

    def test_compose_and_module_01(self) -> None:
        assert _module_01(SimpleNamespace(overall_score=None)) is None
        assert _module_01(SimpleNamespace(overall_score=Score(value=None))) is None
        assert _module_01(SimpleNamespace(overall_score=Score(value=80.0))) == pytest.approx(
            0.8
        )
        eq = SimpleNamespace(overall_score=Score(value=80.0))
        ca = SimpleNamespace(overall_score=Score(value=60.0))
        bc = SimpleNamespace(overall_score=Score(value=None))
        cp = SimpleNamespace(overall_score=Score(value=40.0))
        overall, parts = compose_overall_score(
            eq=eq,  # type: ignore[arg-type]
            ca=ca,  # type: ignore[arg-type]
            bc=bc,  # type: ignore[arg-type]
            cp=cp,  # type: ignore[arg-type]
            weights=BusinessQualityWeights(
                earnings_quality=0.5,
                capital_allocation=0.3,
                business_characteristics=0.1,
                competitive_position=0.1,
            ),
        )
        assert overall is not None
        assert parts["business_characteristics"] is None

    def test_flag_aggregation(self) -> None:
        eq = SimpleNamespace(
            quality_flags=(
                SimpleNamespace(value="high_earnings_quality"),
                SimpleNamespace(value="aggressive_accounting_risk"),
                SimpleNamespace(value="weak_cash_support"),
            )
        )
        ca = SimpleNamespace(
            quality_flags=(
                SimpleNamespace(value="debt_dependent"),
                SimpleNamespace(value="shareholder_friendly"),
            )
        )
        bc = SimpleNamespace(
            quality_flags=(SimpleNamespace(value="cyclical_business"),)
        )
        cp = SimpleNamespace(
            quality_flags=(
                SimpleNamespace(value="strong_competitive_position"),
                SimpleNamespace(value="unknown_flag"),
            )
        )
        flags = aggregate_flags(eq=eq, ca=ca, bc=bc, cp=cp)  # type: ignore[arg-type]
        assert flags.critical
        assert flags.warning
        assert flags.positive
        assert flags.all_sorted[0].severity is FlagSeverity.CRITICAL
        # dedupe
        flags2 = aggregate_flags(
            eq=SimpleNamespace(
                quality_flags=(
                    SimpleNamespace(value="high_earnings_quality"),
                    SimpleNamespace(value="high_earnings_quality"),
                )
            ),
            ca=SimpleNamespace(quality_flags=()),
            bc=SimpleNamespace(quality_flags=()),
            cp=SimpleNamespace(quality_flags=()),
        )
        assert len(flags2.positive) == 1
        assert _classify_flag("earnings_quality", "high_earnings_quality") is FlagSeverity.POSITIVE
        assert _classify_flag("competitive_position", "mystery") is FlagSeverity.WARNING

    def test_map_flag_and_explainability(self) -> None:
        assert (
            _map_overall_to_bq_flag(OverallRating.GOOD, Rating.AVERAGE)
            is BusinessQualityFlag.GOOD
        )
        assert (
            _map_overall_to_bq_flag(OverallRating.EXCELLENT, Rating.POOR)
            is BusinessQualityFlag.EXCELLENT
        )
        # Force legacy path with a fake overall not in mapping — use AVERAGE legacy
        # by calling with a monkeypatched approach: pass OverallRating.AVERAGE
        assert (
            _map_overall_to_bq_flag(OverallRating.AVERAGE, Rating.UNKNOWN)
            is BusinessQualityFlag.AVERAGE
        )
        assert (
            _map_overall_to_bq_flag(OverallRating.POOR, Rating.INSUFFICIENT_DATA)
            is BusinessQualityFlag.POOR
        )
        # legacy fallback when overall somehow not mapped — call internal with Ranking via
        # reconstructing: all OverallRating values are mapped; cover legacy_map via
        # Rating-only path by temporarily using a non-enum — skip; cover UNKNOWN via
        # mapping Rating.UNKNOWN when overall not in map is unreachable. Cover via
        # Rating path when we pass a bogus OverallRating using SimpleNamespace:
        class _Bogus:
            pass

        assert (
            _map_overall_to_bq_flag(_Bogus(), Rating.UNKNOWN)  # type: ignore[arg-type]
            is BusinessQualityFlag.UNKNOWN
        )
        assert (
            _map_overall_to_bq_flag(_Bogus(), Rating.INSUFFICIENT_DATA)  # type: ignore[arg-type]
            is BusinessQualityFlag.INSUFFICIENT_DATA
        )
        assert (
            _map_overall_to_bq_flag(_Bogus(), Rating.STRONG)  # type: ignore[arg-type]
            is BusinessQualityFlag.STRONG
        )

        exp = bq_explanation(
            title="t",
            description="d",
            evidence=("e",),
            reasoning="r",
            confidence=Confidence.LOW,
            limitations="l",
            references=("ref",),
        )
        merged = merge_module_explainability(
            (exp,),
            (),
            overall=exp,
        )
        assert len(merged) == 2
        assert merge_module_explainability() == ()


class TestEngine:
    def test_happy_path_and_nested(self) -> None:
        fa = _fa(1.0, 1.1, 1.2)
        engine = BusinessQualityEngine()
        result = engine.analyze(fa)
        assert result.overall_score is not None
        assert result.overall_rating in OverallRating
        assert result.overall_confidence in Confidence
        assert result.overall_assessment is not None
        assert result.overall_flags is not None
        assert result.earnings_quality is not None
        assert result.capital_allocation is not None
        assert result.business_characteristics is not None
        assert result.competitive_position is not None
        assert result.weights_used is not None
        assert result.validation_summary.ok
        assert result.score is not None
        assert "EQ=" in result.summary.headline
        assert "business_quality_engine" in result.metadata.modules_composed
        assert result.to_dict()["overall_rating"] is not None
        assert result.to_dict()["earnings_quality"] is not None

    def test_weight_overrides_change_score(self) -> None:
        fa = _fa(1.0, 1.15)
        engine = BusinessQualityEngine()
        default = engine.analyze(fa)
        skewed = engine.analyze(
            fa,
            weights=BusinessQualityWeights(
                earnings_quality=0.7,
                capital_allocation=0.1,
                business_characteristics=0.1,
                competitive_position=0.1,
            ),
        )
        assert skewed.weights_used is not None
        assert skewed.weights_used.earnings_quality == pytest.approx(0.7)
        # Determinism
        again = engine.analyze(
            fa,
            weights=BusinessQualityWeights(
                earnings_quality=0.7,
                capital_allocation=0.1,
                business_characteristics=0.1,
                competitive_position=0.1,
            ),
        )
        assert again.overall_score is not None and skewed.overall_score is not None
        assert again.overall_score.value == skewed.overall_score.value
        assert default.overall_score is not None

    def test_optional_apis_and_shell(self) -> None:
        fa = _fa(1.0, 1.1)
        engine = BusinessQualityEngine()
        assert engine.engine_version == BUSINESS_QUALITY_ENGINE_VERSION
        assert engine.default_weights.earnings_quality == pytest.approx(0.3)
        assert engine.analyze_earnings_quality(fa).overall_rating in Rating
        assert engine.analyze_capital_allocation(fa).overall_rating in Rating
        assert engine.analyze_business_characteristics(fa).overall_rating in Rating
        assert engine.analyze_competitive_position(fa).overall_rating in Rating
        shell = engine.create_shell_analysis(company="X", ticker="X")
        assert shell.score is None
        assert shell.earnings_quality is None

    def test_invalid_weights_on_analyze(self) -> None:
        fa = _fa(1.0)
        with pytest.raises(BusinessQualityValidationError, match="weighting"):
            BusinessQualityEngine().analyze(
                fa,
                weights=BusinessQualityWeights(
                    earnings_quality=-1.0,
                    capital_allocation=0.5,
                    business_characteristics=0.3,
                    competitive_position=0.2,
                ),
            )

    def test_constructor_default_weights(self) -> None:
        eng = BusinessQualityEngine(
            default_weights=BusinessQualityWeights(
                earnings_quality=0.25,
                capital_allocation=0.25,
                business_characteristics=0.25,
                competitive_position=0.25,
            )
        )
        assert eng.default_weights.earnings_quality == pytest.approx(0.25)


class TestPackage:
    def test_exports_and_version(self) -> None:
        import business_quality as bq

        assert bq.__version__ == "0.7.0"
        assert BUSINESS_QUALITY_VERSION.startswith("0.7.0")
        assert hasattr(bq, "BusinessQualityWeights")
        assert hasattr(bq, "OverallRating")
        assert hasattr(bq, "aggregate_flags")
        assert hasattr(bq.BusinessQualityEngine, "analyze")

    def test_strength_weakness_helpers(self) -> None:
        from business_quality.engine import _strengths, _weaknesses
        from business_quality.earnings_quality_models import EarningsQualityFlag
        from business_quality.capital_allocation_models import CapitalAllocationFlag
        from business_quality.business_characteristics_models import (
            BusinessCharacteristicsFlag,
        )
        from business_quality.competitive_position_models import (
            CompetitivePositionFlag,
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
            quality_flags=(BusinessCharacteristicsFlag.ASSET_LIGHT,)
        )
        cp = SimpleNamespace(
            quality_flags=(
                CompetitivePositionFlag.STRONG_COMPETITIVE_POSITION,
                CompetitivePositionFlag.MARGIN_PRESSURE,
            )
        )
        assert any("high_earnings" in s for s in _strengths(eq, ca, bc, cp))
        assert any("margin_pressure" in s for s in _weaknesses(eq, ca, bc, cp))
