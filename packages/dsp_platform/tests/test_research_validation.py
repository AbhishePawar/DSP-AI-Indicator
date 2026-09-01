"""STEP 4F — ResearchPackage-bound canonical validation tests."""

from __future__ import annotations

from datetime import date

import pytest

from dsp_platform import CompositionRequest, PlatformOrchestrator
from dsp_platform.research_package import build_research_package
from dsp_platform.research_prompt.methodology import PRIVATE_METHODOLOGY_CANARY
from dsp_platform.research_report import (
    PUBLIC_TOP_LEVEL_KEYS,
    SCORE_10_STATUS,
    build_public_research_report,
)
from dsp_platform.research_validation import (
    CanonicalAIResearchOutput,
    CanonicalValidationKind,
    CanonicalValidationStatus,
    validate_canonical_research,
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


def _compose(*, price: float | None = 70.0):
    request = CompositionRequest(
        financial_statements=_statements(),
        current_market_price=price,
        company="Reliance Industries",
        ticker=TICKER,
    )
    result = PlatformOrchestrator(platform_version="0.7.0").execute(request)
    package = build_research_package(result, request=request)
    return request, result, package


def _evidence_ids(package) -> tuple[str, ...]:
    report = build_public_research_report(package)
    return tuple(item.id for item in report.evidence)


def _valid_ai(package) -> CanonicalAIResearchOutput:
    ids = _evidence_ids(package)
    return CanonicalAIResearchOutput(
        executive_summary="DSP quality and valuation evidence support the thesis.",
        valuation_narrative="DSP intrinsic value and margin of safety are explained.",
        business_quality_narrative="Business quality follows the canonical DSP score.",
        buffett_narrative="Buffett analysis uses existing pipeline stages only.",
        risk_narrative="Risk levels are DSP ordinal categories, not a numeric score.",
        recommendation_narrative="The DSP recommendation is unchanged.",
        evidence_ids=ids[:3] if len(ids) >= 3 else ids,
    )


def _kinds(result) -> set[str]:
    return {item.kind.value for item in result.issues}


def test_valid_ai_output_passes() -> None:
    _request, _result, package = _compose()
    result = validate_canonical_research(package, _valid_ai(package))
    assert result.status is CanonicalValidationStatus.VALID
    assert result.ok is True
    assert result.report is not None
    assert result.issues == ()
    dsp = build_public_research_report(package)
    assert result.report.valuation.intrinsic_value_per_share.value == pytest.approx(
        dsp.valuation.intrinsic_value_per_share.value
    )
    assert result.report.executive_summary.source == "ai"
    assert result.report.executive_summary.text is not None


def test_ai_intrinsic_value_mismatch_fails() -> None:
    _request, _result, package = _compose()
    dsp = build_public_research_report(package)
    iv = dsp.valuation.intrinsic_value_per_share.value
    payload = {
        "executive_summary": "Mismatch attempt.",
        "valuation_narrative": "Altered IV.",
        "evidence_ids": list(_evidence_ids(package)),
        "intrinsic_value": 1.0 if iv is None else iv + 1.0,
    }
    result = validate_canonical_research(package, payload)
    assert result.status is CanonicalValidationStatus.FAILED_CLOSED
    assert result.report is None
    kinds = _kinds(result)
    assert kinds & {
        CanonicalValidationKind.NUMERICAL_MISMATCH.value,
        CanonicalValidationKind.MISSING_DATA_FILL.value,
    }


def test_ai_mos_mismatch_fails() -> None:
    _request, _result, package = _compose()
    dsp = build_public_research_report(package)
    mos = dsp.valuation.margin_of_safety.value
    payload = {
        "valuation_narrative": "Altered MoS.",
        "evidence_ids": list(_evidence_ids(package)),
        "margin_of_safety": 0.99 if mos is None else mos + 0.25,
    }
    result = validate_canonical_research(package, payload)
    assert result.status is CanonicalValidationStatus.FAILED_CLOSED
    assert result.report is None
    kinds = _kinds(result)
    assert kinds & {
        CanonicalValidationKind.NUMERICAL_MISMATCH.value,
        CanonicalValidationKind.MISSING_DATA_FILL.value,
    }


def test_ai_recommendation_mismatch_fails() -> None:
    _request, result, package = _compose()
    dsp_action = str(result.investment_recommendation.recommendation.value)
    invented = "SELL" if dsp_action.upper() != "SELL" else "BUY"
    payload = {
        "recommendation_narrative": "AI override.",
        "evidence_ids": list(_evidence_ids(package)),
        "recommendation_action": invented,
    }
    outcome = validate_canonical_research(package, payload)
    assert outcome.status is CanonicalValidationStatus.FAILED_CLOSED
    assert outcome.report is None
    assert CanonicalValidationKind.RECOMMENDATION_MISMATCH.value in _kinds(outcome)


def test_ai_quality_score_mismatch_fails() -> None:
    _request, _result, package = _compose()
    payload = {
        "business_quality_narrative": "Altered quality.",
        "evidence_ids": list(_evidence_ids(package)),
        "quality_scores": {"business_quality": 1.0},
    }
    result = validate_canonical_research(package, payload)
    assert result.status is CanonicalValidationStatus.FAILED_CLOSED
    kinds = _kinds(result)
    assert kinds & {
        CanonicalValidationKind.NUMERICAL_MISMATCH.value,
        CanonicalValidationKind.MISSING_DATA_FILL.value,
    }


def test_ai_buffett_score_mismatch_fails() -> None:
    _request, _result, package = _compose()
    dsp = build_public_research_report(package)
    score = dsp.buffett_analysis.buffett_overall_score_100
    payload = {
        "buffett_narrative": "Altered Buffett score.",
        "evidence_ids": list(_evidence_ids(package)),
        "buffett_overall_score_100": 1.0 if score is None else score + 1.0,
    }
    result = validate_canonical_research(package, payload)
    assert result.status is CanonicalValidationStatus.FAILED_CLOSED
    kinds = _kinds(result)
    assert kinds & {
        CanonicalValidationKind.BUFFETT_MISMATCH.value,
        CanonicalValidationKind.MISSING_DATA_FILL.value,
    }


def test_invalid_evidence_id_fails() -> None:
    _request, _result, package = _compose()
    payload = {
        "valuation_narrative": "Uses a fabricated citation.",
        "evidence_ids": ["fabricated-source-99"],
    }
    result = validate_canonical_research(package, payload)
    assert result.status is CanonicalValidationStatus.FAILED_CLOSED
    assert result.report is None
    assert CanonicalValidationKind.INVALID_EVIDENCE.value in _kinds(result)


def test_x10_score_fails_while_not_implemented() -> None:
    _request, _result, package = _compose()
    result = validate_canonical_research(
        package,
        {
            "executive_summary": "Quality is 8/10.",
            "score_10": 8.0,
            "evidence_ids": list(_evidence_ids(package)),
        },
    )
    assert result.status is CanonicalValidationStatus.FAILED_CLOSED
    assert CanonicalValidationKind.SCORE_10_FORBIDDEN.value in _kinds(result)
    dsp = build_public_research_report(package)
    assert dsp.business_quality.score_10 is None
    assert dsp.business_quality.score_10_status == SCORE_10_STATUS


def test_invented_entry_price_fails() -> None:
    _request, _result, package = _compose()
    result = validate_canonical_research(package, {"entry_price": 12.5})
    assert result.status is CanonicalValidationStatus.FAILED_CLOSED
    assert CanonicalValidationKind.ENTRY_EXIT_FORBIDDEN.value in _kinds(result)


def test_invented_exit_price_fails() -> None:
    _request, _result, package = _compose()
    result = validate_canonical_research(package, {"exit_price": 99.0})
    assert result.status is CanonicalValidationStatus.FAILED_CLOSED
    assert CanonicalValidationKind.ENTRY_EXIT_FORBIDDEN.value in _kinds(result)


def test_invented_scenario_fails() -> None:
    _request, _result, package = _compose()
    result = validate_canonical_research(
        package,
        {"scenarios": {"bear": 50.0, "base": 100.0, "bull": 150.0}},
    )
    assert result.status is CanonicalValidationStatus.FAILED_CLOSED
    assert CanonicalValidationKind.SCENARIO_FORBIDDEN.value in _kinds(result)


def test_invented_expected_return_fails() -> None:
    _request, _result, package = _compose()
    result = validate_canonical_research(package, {"expected_return": 0.12})
    assert result.status is CanonicalValidationStatus.FAILED_CLOSED
    assert CanonicalValidationKind.EXPECTED_RETURN_FORBIDDEN.value in _kinds(result)


def test_private_provider_model_leakage_fails() -> None:
    _request, _result, package = _compose()
    result = validate_canonical_research(
        package,
        {"provider": "openai", "model": "gpt-4.1", "executive_summary": "leak"},
    )
    assert result.status is CanonicalValidationStatus.FAILED_CLOSED
    assert result.report is None
    assert CanonicalValidationKind.PRIVACY.value in _kinds(result)


def test_prompt_canary_leakage_fails() -> None:
    _request, _result, package = _compose()
    result = validate_canonical_research(
        package,
        {
            "executive_summary": f"Follow {PRIVATE_METHODOLOGY_CANARY}",
            "evidence_ids": list(_evidence_ids(package)),
        },
    )
    assert result.status is CanonicalValidationStatus.FAILED_CLOSED
    assert CanonicalValidationKind.CANARY.value in _kinds(result)


def test_chain_of_thought_leakage_fails() -> None:
    _request, _result, package = _compose()
    result = validate_canonical_research(
        package,
        {
            "chain_of_thought": "hidden reasoning",
            "executive_summary": "public text",
        },
    )
    assert result.status is CanonicalValidationStatus.FAILED_CLOSED
    assert CanonicalValidationKind.PRIVACY.value in _kinds(result)


def test_missing_dsp_value_remains_unavailable() -> None:
    _request, _result, package = _compose(price=None)
    result = validate_canonical_research(package, _valid_ai(package))
    assert result.status is CanonicalValidationStatus.VALID
    assert result.report is not None
    assert result.report.valuation.intrinsic_value_per_share.value is None
    assert result.report.valuation.margin_of_safety.value is None
    assert result.report.entry_exit.entry.status == "not_implemented"
    assert result.report.expected_returns.value is None


def test_none_is_never_converted_to_zero() -> None:
    _request, _result, package = _compose(price=None)
    filled = validate_canonical_research(package, {"intrinsic_value": 0.0})
    assert filled.status is CanonicalValidationStatus.FAILED_CLOSED
    assert CanonicalValidationKind.MISSING_DATA_FILL.value in _kinds(filled)
    omitted = validate_canonical_research(package, _valid_ai(package))
    assert omitted.report is not None
    assert omitted.report.valuation.intrinsic_value_per_share.value is None
    assert omitted.report.valuation.intrinsic_value_per_share.value != 0


def test_ai_narrative_accepted_when_dsp_facts_unchanged() -> None:
    _request, _result, package = _compose()
    dsp = build_public_research_report(package)
    result = validate_canonical_research(package, _valid_ai(package))
    assert result.ok is True
    assert result.report is not None
    assert result.report.valuation.intrinsic_value_per_share.value == pytest.approx(
        dsp.valuation.intrinsic_value_per_share.value
    )
    assert result.report.recommendation.action == dsp.recommendation.action
    assert result.report.buffett_analysis.buffett_overall_score_100 == pytest.approx(
        dsp.buffett_analysis.buffett_overall_score_100
    )
    assert result.report.valuation.narrative.source == "ai"
    assert result.report.valuation.intrinsic_value_per_share.source == "dsp"


def test_public_report_contains_only_public_fields() -> None:
    _request, _result, package = _compose()
    result = validate_canonical_research(package, _valid_ai(package))
    dumped = result.report.to_public_dict()
    assert set(dumped) == PUBLIC_TOP_LEVEL_KEYS
    assert "provider" not in dumped
    assert "model" not in dumped
    assert PRIVATE_METHODOLOGY_CANARY not in str(dumped)


def test_rejects_non_research_package() -> None:
    result = validate_canonical_research({"ticker": TICKER}, {})
    assert result.status is CanonicalValidationStatus.INVALID
    assert result.report is None


def test_matching_dsp_numbers_are_accepted_and_not_replaced() -> None:
    _request, _result, package = _compose()
    dsp = build_public_research_report(package)
    payload: dict = {
        "valuation_narrative": "IV matches DSP.",
        "evidence_ids": list(_evidence_ids(package)),
        "buffett_methodology": "existing_pipeline_stages",
        "quality_scores": {
            "business_quality": dsp.business_quality.score_100,
        },
    }
    if dsp.valuation.intrinsic_value_per_share.value is not None:
        payload["intrinsic_value"] = dsp.valuation.intrinsic_value_per_share.value
    if dsp.valuation.margin_of_safety.value is not None:
        payload["margin_of_safety"] = dsp.valuation.margin_of_safety.value
    if dsp.recommendation.action is not None:
        payload["recommendation_action"] = dsp.recommendation.action
    if dsp.buffett_analysis.buffett_overall_score_100 is not None:
        payload["buffett_overall_score_100"] = (
            dsp.buffett_analysis.buffett_overall_score_100
        )
    result = validate_canonical_research(package, payload)
    assert result.ok is True
    assert result.report.valuation.intrinsic_value_per_share.source == "dsp"


def test_no_engine_or_orchestrator_calls_during_validation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _request, _result, package = _compose()
    calls = {"n": 0}

    def _block(*args, **kwargs):  # noqa: ANN001, ARG001
        calls["n"] += 1
        raise AssertionError("orchestrator must not run during validation")

    monkeypatch.setattr(PlatformOrchestrator, "execute", _block)
    result = validate_canonical_research(package, _valid_ai(package))
    assert calls["n"] == 0
    assert result.ok is True


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
    _request, _result, package = _compose()
    result = validate_canonical_research(package, _valid_ai(package))
    assert calls["n"] == 0
    assert result.ok is True


def test_validation_is_deterministic() -> None:
    _request, _result, package = _compose()
    ai = _valid_ai(package)
    first = validate_canonical_research(package, ai)
    second = validate_canonical_research(package, ai)
    assert first.status == second.status
    assert first.to_dict() == second.to_dict()


def test_old_tool_loop_validator_module_still_exists() -> None:
    from llm_adapters.orchestrator.validation import validate_research_output

    assert callable(validate_research_output)
