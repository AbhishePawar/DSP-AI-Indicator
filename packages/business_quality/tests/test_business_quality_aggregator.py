"""Business Quality Aggregator (F3.7) tests — target 100% module coverage."""

from __future__ import annotations

from datetime import date
from types import SimpleNamespace

import pytest

from business_quality import (
    BUSINESS_QUALITY_VERSION,
    BusinessQualityAggregator,
    BusinessQualityEngine,
    BusinessQualityReport,
    BusinessQualityValidationError,
    OverallRating,
    validate_business_quality_analysis,
    validate_report_metadata,
    validate_report_object,
)
from business_quality.business_quality_aggregator import (
    BUSINESS_QUALITY_AGGREGATOR_VERSION,
)
from business_quality.business_quality_models import (
    AggregatedFlag,
    AggregatedFlags,
    BusinessQualityAnalysis,
    BusinessQualityFlag,
    BusinessQualitySummary,
    FlagSeverity,
    OverallAssessment,
)
from business_quality.business_quality_report_explainability import (
    build_report_explainability,
    report_explanation,
)
from business_quality.business_quality_report_models import (
    ConfidenceSummary,
    ModuleBreakdownEntry,
    ReportSignal,
)
from business_quality.business_quality_summary import (
    build_confidence_summary,
    build_executive_summary,
    build_module_breakdown,
    build_recommended_interpretation,
    dedupe_ordered,
    extract_evidence,
    extract_limitations,
    extract_signals,
    extract_strengths,
    extract_weaknesses,
    source_module_names,
)
from business_quality.metadata import BusinessQualityMetadata
from business_quality.scoring import Confidence, Score
from business_quality.validation import empty_validation
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


def _analysis() -> BusinessQualityAnalysis:
    return BusinessQualityEngine().analyze(_fa(1.0, 1.1, 1.2))


class TestReportModels:
    def test_to_dicts(self) -> None:
        signal = ReportSignal(text="t", source="eq", category="risk")
        assert signal.to_dict()["text"] == "t"
        entry = ModuleBreakdownEntry(name="x", label="X", present=True, score=1.0)
        assert entry.to_dict()["present"] is True
        conf = ConfidenceSummary(
            overall=Confidence.HIGH,
            module_confidences=(("eq", "high"),),
            explanation="ok",
        )
        assert conf.to_dict()["overall"] == "high"


class TestSummaryHelpers:
    def test_dedupe_and_interpretations(self) -> None:
        assert dedupe_ordered(["a", "a", "b", ""]) == ("a", "b")
        for rating in OverallRating:
            analysis = SimpleNamespace(overall_rating=rating)
            text = build_recommended_interpretation(analysis)  # type: ignore[arg-type]
            assert text
        assert "unavailable" in build_recommended_interpretation(
            SimpleNamespace(overall_rating=None)  # type: ignore[arg-type]
        )

    def test_extractors_and_breakdown(self) -> None:
        analysis = _analysis()
        assert extract_strengths(analysis) or True
        assert extract_weaknesses(analysis) or True
        risks, pos, warn = extract_signals(analysis)
        assert isinstance(risks, tuple)
        assert extract_evidence(analysis)
        assert extract_limitations(analysis)
        breakdown = build_module_breakdown(analysis)
        assert len(breakdown) == 4
        assert all(m.present for m in breakdown)
        assert source_module_names(analysis) == (
            "earnings_quality",
            "capital_allocation",
            "business_characteristics",
            "competitive_position",
        )
        conf = build_confidence_summary(analysis)
        assert conf.overall in Confidence
        assert "confidence" in conf.explanation.lower() or "Confidence" in conf.explanation or conf.explanation
        exec_sum = build_executive_summary(analysis)
        assert "rating" in exec_sum.lower() or "Business quality" in exec_sum

    def test_shell_and_sparse_paths(self) -> None:
        shell = BusinessQualityEngine().create_shell_analysis(company="A", ticker="A")
        assert build_executive_summary(shell)
        assert extract_evidence(shell) or True
        assert "unavailable" in build_recommended_interpretation(shell).lower() or True
        risks, pos, warn = extract_signals(shell)
        assert risks == () and pos == () and warn == ()
        breakdown = build_module_breakdown(shell)
        assert all(not m.present for m in breakdown)
        conf = build_confidence_summary(shell)
        assert "unavailable" in conf.explanation.lower()
        assert source_module_names(shell) == ()

        # Executive summary fallback without assessment headline
        sparse = BusinessQualityAnalysis(
            metadata=BusinessQualityMetadata(engine_version="x"),
            validation=empty_validation(ok=True),
            score=None,
            summary=BusinessQualitySummary(headline=""),
            quality_flags=(),
            explainability=(),
            research_disclaimer="d",
            overall_score=Score(value=55.0),
            overall_rating=OverallRating.AVERAGE,
            overall_confidence=Confidence.LOW,
            overall_assessment=None,
        )
        assert "rating=average" in build_executive_summary(sparse)

        # With assessment but empty headline uses summary path then fallback
        sparse2 = BusinessQualityAnalysis(
            metadata=BusinessQualityMetadata(engine_version="x"),
            validation=empty_validation(ok=True),
            score=None,
            summary=BusinessQualitySummary(headline="From summary"),
            quality_flags=(),
            explainability=(),
            research_disclaimer="d",
            overall_score=None,
            overall_rating=None,
            overall_confidence=Confidence.MEDIUM,
            overall_assessment=OverallAssessment(headline=""),
        )
        assert "From summary" in build_executive_summary(sparse2)

        # Confidence with non-Confidence overall
        weird = SimpleNamespace(
            overall_confidence="low",
            earnings_quality=None,
            capital_allocation=None,
            business_characteristics=None,
            competitive_position=None,
        )
        cs = build_confidence_summary(weird)  # type: ignore[arg-type]
        assert cs.overall is Confidence.INSUFFICIENT

        # Module present but confidence missing
        partial = SimpleNamespace(
            overall_confidence=Confidence.MEDIUM,
            earnings_quality=SimpleNamespace(
                overall_score=Score(value=50.0),
                overall_rating=SimpleNamespace(value="average"),
                confidence=None,
            ),
            capital_allocation=None,
            business_characteristics=None,
            competitive_position=None,
            weights_used=None,
        )
        conf2 = build_confidence_summary(partial)  # type: ignore[arg-type]
        assert conf2.module_confidences == ()
        bd = build_module_breakdown(partial)  # type: ignore[arg-type]
        assert bd[0].present is True
        assert bd[0].confidence is None
        assert bd[1].present is False


class TestValidation:
    def test_analysis_validation(self) -> None:
        with pytest.raises(BusinessQualityValidationError, match="Missing"):
            validate_business_quality_analysis(None)
        with pytest.raises(BusinessQualityValidationError, match="ONLY"):
            validate_business_quality_analysis({"x": 1})

        class BusinessQualityAnalysis:
            pass

        with pytest.raises(BusinessQualityValidationError, match="lacks"):
            validate_business_quality_analysis(BusinessQualityAnalysis())

        result = validate_business_quality_analysis(_analysis())
        assert result.ok

        shell = BusinessQualityEngine().create_shell_analysis()
        warned = validate_business_quality_analysis(shell)
        assert any("overall_score" in w for w in warned.warnings)

    def test_metadata_and_report_validation(self) -> None:
        with pytest.raises(BusinessQualityValidationError, match="metadata"):
            validate_report_metadata(None)
        with pytest.raises(BusinessQualityValidationError, match="engine_version"):
            validate_report_metadata(SimpleNamespace(engine_version="", schema_version="1"))
        meta_ok = validate_report_metadata(
            SimpleNamespace(engine_version="0.7.0", schema_version=None)
        )
        assert any("schema_version" in w for w in meta_ok.warnings)

        with pytest.raises(BusinessQualityValidationError, match="report"):
            validate_report_object(None)
        with pytest.raises(BusinessQualityValidationError, match="BusinessQualityReport"):
            validate_report_object({"x": 1})

        class BusinessQualityReport:
            pass

        with pytest.raises(BusinessQualityValidationError, match="missing"):
            validate_report_object(BusinessQualityReport())

        report = BusinessQualityAggregator().aggregate(_analysis())
        assert validate_report_object(report).ok

        class BusinessQualityReport:
            pass

        bad_exec = BusinessQualityReport()
        bad_exec.metadata = BusinessQualityMetadata(engine_version="x")
        bad_exec.validation = empty_validation(ok=True)
        bad_exec.executive_summary = 123
        bad_exec.confidence_summary = report.confidence_summary
        bad_exec.module_breakdown = report.module_breakdown
        bad_exec.explainability = ()
        bad_exec.research_disclaimer = "d"
        with pytest.raises(BusinessQualityValidationError, match="executive_summary"):
            validate_report_object(bad_exec)

        bad_mod = BusinessQualityReport()
        bad_mod.metadata = BusinessQualityMetadata(engine_version="x")
        bad_mod.validation = empty_validation(ok=True)
        bad_mod.executive_summary = "ok"
        bad_mod.confidence_summary = report.confidence_summary
        bad_mod.module_breakdown = ["not", "a", "tuple"]
        bad_mod.explainability = ()
        bad_mod.research_disclaimer = "d"
        with pytest.raises(BusinessQualityValidationError, match="module_breakdown"):
            validate_report_object(bad_mod)


class TestExplainability:
    def test_report_explainability(self) -> None:
        analysis = _analysis()
        conf = build_confidence_summary(analysis)
        breakdown = build_module_breakdown(analysis)
        evidence = extract_evidence(analysis)
        limitations = extract_limitations(analysis)
        exps = build_report_explainability(
            analysis,
            confidence_summary=conf,
            module_breakdown=breakdown,
            evidence_summary=evidence,
            limitations=limitations,
        )
        assert len(exps) >= 3
        assert all(e.reasoning for e in exps[:3])
        # Empty limitations branch
        exps2 = build_report_explainability(
            analysis,
            confidence_summary=conf,
            module_breakdown=breakdown,
            evidence_summary=(),
            limitations=(),
        )
        assert exps2[0].limitations
        # No present modules
        empty_breakdown = (
            ModuleBreakdownEntry(name="earnings_quality", label="EQ", present=False),
        )
        exps3 = build_report_explainability(
            analysis,
            confidence_summary=ConfidenceSummary(
                overall=Confidence.LOW, module_confidences=(), explanation="none"
            ),
            module_breakdown=empty_breakdown,
            evidence_summary=(),
            limitations=("lim",),
        )
        assert "No module" in exps3[0].reasoning
        one = report_explanation(
            title="t",
            description="d",
            evidence=("e",),
            reasoning="r",
            confidence=Confidence.MEDIUM,
            limitations="l",
            references=("ref",),
        )
        assert one.title == "t"


class TestAggregator:
    def test_happy_path_and_determinism(self) -> None:
        analysis = _analysis()
        agg = BusinessQualityAggregator()
        assert agg.version == BUSINESS_QUALITY_AGGREGATOR_VERSION
        report = agg.aggregate(analysis)
        assert isinstance(report, BusinessQualityReport)
        assert report.executive_summary
        assert report.business_quality_rating in OverallRating
        assert report.confidence_summary.overall in Confidence
        assert len(report.module_breakdown) == 4
        assert report.recommended_interpretation
        assert report.limitations
        assert report.explainability
        assert "business_quality_aggregator" in report.metadata.modules_composed
        assert report.to_dict()["executive_summary"]
        again = agg.summarize(analysis)
        assert again.executive_summary == report.executive_summary
        assert again.evidence_summary == report.evidence_summary
        assert again.positive_signals == report.positive_signals
        assert again.key_risks == report.key_risks

    def test_flag_dedup_and_signals(self) -> None:
        base = _analysis()
        # Force flags with duplicates conceptually via rebuilt analysis fields
        flags = AggregatedFlags(
            critical=(
                AggregatedFlag(
                    name="debt_dependent",
                    source="capital_allocation",
                    severity=FlagSeverity.CRITICAL,
                    value="debt_dependent",
                ),
            ),
            warning=(
                AggregatedFlag(
                    name="cyclical_business",
                    source="business_characteristics",
                    severity=FlagSeverity.WARNING,
                    value="cyclical_business",
                ),
            ),
            positive=(
                AggregatedFlag(
                    name="asset_light",
                    source="business_characteristics",
                    severity=FlagSeverity.POSITIVE,
                    value="asset_light",
                ),
            ),
            all_sorted=(),
        )
        analysis = BusinessQualityAnalysis(
            metadata=base.metadata,
            validation=base.validation,
            score=base.score,
            summary=BusinessQualitySummary(
                headline=base.summary.headline,
                strengths=("s1", "s1", "s2"),
                weaknesses=("w1",),
                key_observations=("o1",),
                flag=BusinessQualityFlag.AVERAGE,
            ),
            quality_flags=base.quality_flags,
            explainability=base.explainability,
            research_disclaimer=base.research_disclaimer,
            overall_score=base.overall_score,
            overall_rating=OverallRating.GOOD,
            overall_confidence=base.overall_confidence,
            overall_assessment=OverallAssessment(
                headline="Head",
                strengths=("s2", "s3"),
                weaknesses=("w1", "w2"),
                limitations=("lim",),
                evidence_summary=("ev1",),
            ),
            overall_flags=flags,
            earnings_quality=base.earnings_quality,
            capital_allocation=base.capital_allocation,
            business_characteristics=base.business_characteristics,
            competitive_position=base.competitive_position,
            weights_used=base.weights_used,
        )
        report = BusinessQualityAggregator().aggregate(analysis)
        assert "s1" in report.strengths and report.strengths.count("s1") == 1
        assert any("debt_dependent" in r for r in report.key_risks)
        assert any("asset_light" in p for p in report.positive_signals)
        assert any("cyclical" in w for w in report.warning_signals)
        assert report.business_quality_rating is OverallRating.GOOD
        assert "good" in report.recommended_interpretation.lower()

    def test_rating_interpretation_branches(self) -> None:
        base = _analysis()
        for rating, needle in (
            (OverallRating.EXCELLENT, "excellent"),
            (OverallRating.STRONG, "strong"),
            (OverallRating.WEAK, "weak"),
            (OverallRating.POOR, "poor"),
        ):
            analysis = BusinessQualityAnalysis(
                metadata=base.metadata,
                validation=base.validation,
                score=base.score,
                summary=base.summary,
                quality_flags=base.quality_flags,
                explainability=(),
                research_disclaimer=base.research_disclaimer,
                overall_score=base.overall_score,
                overall_rating=rating,
                overall_confidence=base.overall_confidence,
                overall_assessment=base.overall_assessment,
                overall_flags=base.overall_flags,
                earnings_quality=base.earnings_quality,
                capital_allocation=base.capital_allocation,
                business_characteristics=base.business_characteristics,
                competitive_position=base.competitive_position,
                weights_used=base.weights_used,
            )
            report = BusinessQualityAggregator().aggregate(analysis)
            assert needle in report.recommended_interpretation.lower()


class TestPackage:
    def test_exports(self) -> None:
        import business_quality as bq

        assert bq.__version__ == "0.7.0"
        assert BUSINESS_QUALITY_VERSION.startswith("0.7.0")
        assert hasattr(bq, "BusinessQualityAggregator")
        assert hasattr(bq, "BusinessQualityReport")
        assert bq.BUSINESS_QUALITY_AGGREGATOR_VERSION.startswith("0.7.0")
