"""STEP 4E — public DSP research report contract tests."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import date

import pytest

from dsp_platform import CompositionRequest, PlatformOrchestrator
from dsp_platform.research_package import (
    RESEARCH_PACKAGE_SCHEMA_VERSION,
    ResearchPackage,
    build_research_package,
)
from dsp_platform.research_report import (
    BUFFETT_METHODOLOGY,
    CANONICAL_VALUATION_AUTHORITY,
    FUTURE_VALIDATION_CHECKS,
    PRIVATE_REPORT_FIELD_NAMES,
    PUBLIC_RESEARCH_REPORT_SCHEMA_VERSION,
    PUBLIC_TOP_LEVEL_KEYS,
    SCORE_10_STATUS,
    PublicResearchReport,
    PublicResearchReportError,
    assert_public_report_privacy,
    build_public_research_report,
)
from financial import (
    BalanceSheet,
    CashFlowStatement,
    CurrencyCode,
    CurrencyRef,
    FinancialPeriod,
    FinancialStatements,
    IncomeStatement,
    PeriodType,
    UnitScale,
)
from financial.metadata import StatementMetadata

TICKER = "RELIANCE"


def _statements() -> FinancialStatements:
    period = FinancialPeriod(
        period_type=PeriodType.ANNUAL,
        period_end=date(2024, 12, 31),
        fiscal_year=2024,
        currency=CurrencyRef(CurrencyCode.USD),
    )
    return FinancialStatements(
        period=period,
        income_statement=IncomeStatement(
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
        ),
        balance_sheet=BalanceSheet(
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
        ),
        cash_flow=CashFlowStatement(
            operating_cash_flow=250.0,
            capex=-80.0,
            free_cash_flow=170.0,
            dividends_paid=-50.0,
            share_buybacks=-30.0,
            debt_issued=10.0,
            debt_repaid=-40.0,
        ),
        statement_metadata=StatementMetadata(unit_scale=UnitScale.MILLIONS),
    )


def _compose() -> tuple:
    request = CompositionRequest(
        financial_statements=_statements(),
        current_market_price=70.0,
        company="Reliance Industries",
        ticker=TICKER,
    )
    result = PlatformOrchestrator(platform_version="0.7.0").execute(request)
    package = build_research_package(result, request=request)
    report = build_public_research_report(package)
    return request, result, package, report


def test_report_constructs_from_research_package() -> None:
    _request, _result, package, report = _compose()
    assert isinstance(package, ResearchPackage)
    assert isinstance(report, PublicResearchReport)
    assert report.schema_version == PUBLIC_RESEARCH_REPORT_SCHEMA_VERSION
    assert report.source_pipeline == "compose_intelligence"
    assert report.identity.ticker == TICKER
    assert report.identity.company_name == "Reliance Industries"
    assert report.research_status in {"complete", "degraded", "failed"}
    dumped = report.to_public_dict()
    assert dumped["identity"]["ticker"] == TICKER


def test_missing_valuation_remains_unavailable() -> None:
    request = CompositionRequest(
        financial_statements=_statements(),
        current_market_price=None,
        ticker=TICKER,
        company="Reliance Industries",
    )
    result = PlatformOrchestrator(platform_version="0.7.0").execute(request)
    package = build_research_package(result, request=request)
    report = build_public_research_report(package)
    assert report.research_status == "failed"
    assert report.valuation.intrinsic_value_per_share.value is None
    assert report.valuation.intrinsic_value_per_share.status in {
        "unavailable",
        "failed",
    }
    assert report.valuation.intrinsic_value_per_share.source == "dsp"
    assert report.valuation.margin_of_safety.value is None
    assert report.valuation.authority == CANONICAL_VALUATION_AUTHORITY


def test_missing_mos_remains_unavailable() -> None:
    request = CompositionRequest(
        financial_statements=_statements(),
        current_market_price=None,
        ticker=TICKER,
        company="Reliance Industries",
    )
    result = PlatformOrchestrator(platform_version="0.7.0").execute(request)
    report = build_public_research_report(
        build_research_package(result, request=request)
    )
    mos = report.valuation.margin_of_safety
    assert mos.value is None
    assert mos.status in {"unavailable", "failed"}
    assert mos.unit == "ratio"
    dumped = report.to_public_dict()
    assert dumped["valuation"]["margin_of_safety"]["value"] is None


def test_score_10_remains_not_implemented() -> None:
    _request, _result, _package, report = _compose()
    factors = (
        report.business_quality,
        report.economic_moat,
        report.management_quality,
        report.financial_strength,
        report.earnings_quality,
        report.growth_quality,
    )
    for factor in factors:
        assert factor.score_10 is None
        assert factor.score_10_status == SCORE_10_STATUS
    for row in report.factor_scorecard:
        assert row.score_10 is None
        assert row.score_10_status == SCORE_10_STATUS
    assert report.risk.score_10 is None
    assert report.risk.score_10_status == SCORE_10_STATUS
    assert report.risk.score_100 is None


def test_no_automatic_score_100_to_score_10_conversion() -> None:
    _request, _result, _package, report = _compose()
    score = report.business_quality.score_100
    assert score is not None
    assert report.business_quality.score_10 is None
    assert report.business_quality.score_10 != pytest.approx(score / 10.0)
    for row in report.factor_scorecard:
        if row.score_100 is not None:
            assert row.score_10 is None
            assert row.score_10 != pytest.approx(row.score_100 / 10.0)


def test_entry_exit_remains_not_implemented() -> None:
    _request, _result, _package, report = _compose()
    assert report.entry_exit.entry.status == "not_implemented"
    assert report.entry_exit.exit.status == "not_implemented"
    dumped = report.to_public_dict()["entry_exit"]
    assert dumped["entry"]["status"] == "not_implemented"
    assert dumped["exit"]["status"] == "not_implemented"
    assert "entry_price" not in dumped["entry"]
    assert "exit_price" not in dumped["exit"]


def test_scenarios_remain_unavailable() -> None:
    _request, _result, _package, report = _compose()
    dumped = report.to_public_dict()["scenarios"]
    assert dumped["bear"]["status"] == "unavailable"
    assert dumped["base"]["status"] == "unavailable"
    assert dumped["bull"]["status"] == "unavailable"
    assert "value" not in dumped["bear"]


def test_expected_returns_remain_unavailable() -> None:
    _request, _result, _package, report = _compose()
    assert report.expected_returns.status == "not_implemented"
    assert report.expected_returns.value is None
    dumped = report.to_public_dict()["expected_returns"]
    assert dumped["value"] is None
    assert "cagr" not in dumped


def test_industry_and_competitors_remain_unavailable() -> None:
    _request, _result, _package, report = _compose()
    dumped = report.to_public_dict()["industry"]
    assert dumped["industry"]["status"] == "unavailable"
    assert dumped["competitors"]["status"] == "unavailable"


def test_canonical_recommendation_is_represented() -> None:
    _request, result, package, report = _compose()
    rec = result.investment_recommendation
    assert rec is not None
    expected_action = getattr(rec.recommendation, "value", rec.recommendation)
    assert report.recommendation.action == expected_action
    assert report.recommendation.source == "dsp"
    package_action = package.investment_recommendation.payload["recommendation"]
    assert report.recommendation.action == package_action
    score = report.recommendation.recommendation_score_100
    assert score == pytest.approx(rec.overall_investment_score)
    assert report.recommendation.narrative.source == "ai"
    assert report.recommendation.narrative.text is None


def test_buffett_methodology_is_existing_pipeline_stages() -> None:
    _request, _result, package, report = _compose()
    assert report.buffett_analysis.methodology == BUFFETT_METHODOLOGY
    assert report.buffett_analysis.methodology == "existing_pipeline_stages"
    assert (
        package.buffett_authority.payload["methodology"]
        == "existing_pipeline_stages"
    )


def test_buffett_overall_and_recommendation_scores_are_distinct() -> None:
    _request, _result, package, report = _compose()
    dumped = report.to_public_dict()
    assert "overall_score" not in dumped
    assert "overall_score" not in dumped["buffett_analysis"]
    assert "overall_score" not in dumped["recommendation"]
    buffett = report.buffett_analysis.buffett_overall_score_100
    rec = report.recommendation.recommendation_score_100
    assert buffett == pytest.approx(
        package.buffett_authority.payload["overall_score"]
    )
    assert rec == pytest.approx(
        package.investment_recommendation.payload["overall_investment_score"]
    )
    assert dumped["buffett_analysis"]["buffett_overall_score_100"] == pytest.approx(
        buffett
    )
    assert dumped["recommendation"]["recommendation_score_100"] == pytest.approx(rec)


def test_public_serialization_contains_only_approved_fields() -> None:
    _request, _result, _package, report = _compose()
    dumped = report.to_public_dict()
    assert set(dumped) == PUBLIC_TOP_LEVEL_KEYS
    assert dumped["schema_version"] == PUBLIC_RESEARCH_REPORT_SCHEMA_VERSION
    assert dumped["valuation"]["authority"] == CANONICAL_VALUATION_AUTHORITY
    assert dumped["valuation"]["intrinsic_value_per_share"]["source"] == "dsp"
    assert dumped["executive_summary"]["source"] == "ai"
    assert dumped["business_quality"]["narrative"]["source"] == "ai"


def test_private_fields_cannot_leak() -> None:
    _request, _result, _package, report = _compose()
    dumped = report.to_public_dict()
    for name in PRIVATE_REPORT_FIELD_NAMES:
        assert name not in dumped
    assert_public_report_privacy(dumped)
    with pytest.raises(ValueError, match="private fields leaked"):
        assert_public_report_privacy({"provider": "openai", "recommendation": "BUY"})
    text = str(dumped).lower()
    for name in ("openai", "anthropic", "gemini", "deepseek", "gpt-", "claude"):
        assert name not in text
    assert "DSP_PRIVATE_METHODOLOGY_PROMPT" not in str(dumped)
    assert "canary" not in dumped


def test_research_package_is_not_the_public_dto() -> None:
    _request, _result, package, report = _compose()
    dumped = report.to_public_dict()
    package_dump = package.to_dict()
    assert dumped != package_dump
    assert dumped["schema_version"] != RESEARCH_PACKAGE_SCHEMA_VERSION
    assert "pipeline_ok" not in dumped
    assert "errors" not in dumped
    assert "buffett_authority" not in dumped
    assert "investment_committee" not in dumped
    assert "research_package" not in dumped
    assert not hasattr(PublicResearchReport, "from_dict")
    assert not hasattr(PublicResearchReport, "from_json")


def test_rejects_non_research_package() -> None:
    with pytest.raises(PublicResearchReportError, match="ResearchPackage"):
        build_public_research_report({"ticker": TICKER})
    with pytest.raises(PublicResearchReportError):
        build_public_research_report(object())


def test_dsp_facts_are_not_replaced_by_ai_narrative() -> None:
    _request, _result, package, report = _compose()
    iv_pkg = package.valuation.payload["intrinsic_value"]["intrinsic_value_per_share"]
    mos_pkg = package.valuation.payload["margin_of_safety"]
    assert report.valuation.intrinsic_value_per_share.value == pytest.approx(iv_pkg)
    assert report.valuation.margin_of_safety.value == pytest.approx(mos_pkg)
    assert report.valuation.narrative.text is None
    assert report.valuation.narrative.source == "ai"
    assert report.executive_summary.text is None
    assert report.financials.metrics
    for metric in report.financials.metrics:
        assert metric.source == "dsp"
        if metric.value is None:
            assert metric.status == "unavailable"


def test_report_is_frozen() -> None:
    _request, _result, _package, report = _compose()
    with pytest.raises(FrozenInstanceError):
        report.research_status = "complete"  # type: ignore[misc]


def test_future_validation_checks_are_documented() -> None:
    required = {
        "dsp_intrinsic_value_equality",
        "dsp_margin_of_safety_equality",
        "dsp_quality_score_equality",
        "dsp_recommendation_equality",
        "evidence_reference_validity",
        "score_10_remains_not_implemented",
        "entry_exit_remains_not_implemented",
        "scenarios_remain_unavailable",
        "expected_returns_remain_unavailable",
        "private_field_scan",
        "methodology_canary_scan",
    }
    assert required.issubset(set(FUTURE_VALIDATION_CHECKS))


def test_analyze_decision_pack_call_count_is_zero(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = {"n": 0}

    def _spy(self, *args, **kwargs):  # noqa: ANN001
        calls["n"] += 1
        raise AssertionError("analyze_decision_pack must not be used")

    monkeypatch.setattr(
        "dsp_platform.platform.DSPPlatform.analyze_decision_pack",
        _spy,
    )
    _request, _result, _package, report = _compose()
    assert calls["n"] == 0
    assert report.source_pipeline == "compose_intelligence"
    dumped = report.to_public_dict()
    assert dumped["schema_version"] == PUBLIC_RESEARCH_REPORT_SCHEMA_VERSION


def test_none_is_not_converted_to_zero() -> None:
    request = CompositionRequest(
        financial_statements=_statements(),
        current_market_price=None,
        ticker=TICKER,
        company="Reliance Industries",
    )
    result = PlatformOrchestrator(platform_version="0.7.0").execute(request)
    report = build_public_research_report(
        build_research_package(result, request=request)
    )
    assert report.valuation.intrinsic_value_per_share.value is None
    assert report.valuation.intrinsic_value_per_share.value != 0
    assert report.valuation.margin_of_safety.value is None
    assert report.valuation.margin_of_safety.value != 0
    assert report.expected_returns.value is None
    assert report.risk.score_100 is None
    assert report.risk.score_10 is None
