"""STEP 4G — in-process canonical research assembler (no AI execution)."""

from __future__ import annotations

from datetime import date

import pytest

from dsp_platform import CompositionRequest, PlatformOrchestrator
from dsp_platform.research_assembly import (
    AI_EXECUTION_BLOCKED,
    AI_OUTPUT_FIXTURE,
    PUBLIC_ASSEMBLY_KEYS,
    assemble_canonical_research,
)
from dsp_platform.research_assembly.testing import (
    FIXTURE_ORIGIN,
    TEST_ONLY,
    build_test_only_ai_output_fixture,
)
from dsp_platform.research_package import build_research_package
from dsp_platform.research_prompt.methodology import PRIVATE_METHODOLOGY_CANARY
from dsp_platform.research_report import (
    BUFFETT_METHODOLOGY,
    PUBLIC_TOP_LEVEL_KEYS,
    SCORE_10_STATUS,
    build_public_research_report,
)
from dsp_platform.research_validation import CanonicalValidationKind
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
    return package


def _kinds(assembly) -> set[str]:
    if assembly.validation is None:
        return set()
    return {item.kind.value for item in assembly.validation.issues}


def _assert_fail_closed(assembly) -> None:
    assert assembly.outcome in {"invalid", "failed_closed"}
    assert assembly.report is None
    dumped = assembly.to_public_dict()
    assert dumped["report"] is None


def test_ai_execution_blocked_without_fixture() -> None:
    package = _compose()
    assembly = assemble_canonical_research(package)
    assert assembly.ai_execution_state == AI_EXECUTION_BLOCKED
    assert assembly.outcome == AI_EXECUTION_BLOCKED
    assert assembly.report is None
    assert assembly.validation is None
    assert assembly.private_prompt is not None
    dumped = assembly.to_public_dict()
    assert set(dumped) == PUBLIC_ASSEMBLY_KEYS
    assert "private_prompt" not in dumped
    assert "canary" not in dumped
    assert assembly.private_prompt.canary == PRIVATE_METHODOLOGY_CANARY
    assert PRIVATE_METHODOLOGY_CANARY not in str(dumped)
    assert assembly.private_prompt.text not in str(dumped)


def test_positive_fixture_produces_public_report() -> None:
    package = _compose()
    dsp = build_public_research_report(package)
    assert TEST_ONLY is True
    assert FIXTURE_ORIGIN == AI_OUTPUT_FIXTURE
    fixture = build_test_only_ai_output_fixture(package)
    assembly = assemble_canonical_research(package, fixture)
    assert assembly.ai_execution_state == AI_OUTPUT_FIXTURE
    assert assembly.outcome == "valid"
    assert assembly.report is not None
    report = assembly.report
    assert report.valuation.intrinsic_value_per_share.value == (
        dsp.valuation.intrinsic_value_per_share.value
    )
    assert (
        report.valuation.margin_of_safety.value
        == dsp.valuation.margin_of_safety.value
    )
    assert report.valuation.current_price.value == dsp.valuation.current_price.value
    assert report.recommendation.action == dsp.recommendation.action
    assert report.recommendation.recommendation_score_100 == (
        dsp.recommendation.recommendation_score_100
    )
    assert report.buffett_analysis.methodology == BUFFETT_METHODOLOGY
    assert report.buffett_analysis.buffett_overall_score_100 == (
        dsp.buffett_analysis.buffett_overall_score_100
    )
    assert report.business_quality.score_100 == dsp.business_quality.score_100
    assert report.business_quality.score_10 is None
    assert report.business_quality.score_10_status == SCORE_10_STATUS
    assert report.entry_exit.entry.status == "not_implemented"
    assert report.scenarios.bear.status == "unavailable"
    assert report.expected_returns.status == "not_implemented"
    assert report.executive_summary.source == "ai"
    assert report.executive_summary.text is not None
    assert report.valuation.intrinsic_value_per_share.source == "dsp"
    dumped = assembly.to_public_dict()
    assert dumped["report"] is not None
    assert set(dumped["report"]) == PUBLIC_TOP_LEVEL_KEYS
    assert "provider" not in dumped
    assert "model" not in dumped
    assert "private_prompt" not in dumped
    assert PRIVATE_METHODOLOGY_CANARY not in str(dumped)
    assert "openai" not in str(dumped).lower()


def test_changed_intrinsic_value_fails() -> None:
    package = _compose()
    dsp = build_public_research_report(package)
    iv = dsp.valuation.intrinsic_value_per_share.value
    payload = {
        "valuation_narrative": "Altered IV.",
        "evidence_ids": [item.id for item in dsp.evidence],
        "intrinsic_value": 1.0 if iv is None else iv + 1.0,
    }
    assembly = assemble_canonical_research(package, payload)
    _assert_fail_closed(assembly)
    assert _kinds(assembly) & {
        CanonicalValidationKind.NUMERICAL_MISMATCH.value,
        CanonicalValidationKind.MISSING_DATA_FILL.value,
    }


def test_changed_mos_fails() -> None:
    package = _compose()
    dsp = build_public_research_report(package)
    mos = dsp.valuation.margin_of_safety.value
    assembly = assemble_canonical_research(
        package,
        {
            "valuation_narrative": "Altered MoS.",
            "evidence_ids": [item.id for item in dsp.evidence],
            "margin_of_safety": 0.99 if mos is None else mos + 0.25,
        },
    )
    _assert_fail_closed(assembly)


def test_changed_recommendation_fails() -> None:
    package = _compose()
    dsp = build_public_research_report(package)
    action = (dsp.recommendation.action or "HOLD").upper()
    invented = "SELL" if action != "SELL" else "BUY"
    assembly = assemble_canonical_research(
        package,
        {
            "recommendation_narrative": "Override.",
            "evidence_ids": [item.id for item in dsp.evidence],
            "recommendation_action": invented,
        },
    )
    _assert_fail_closed(assembly)
    assert CanonicalValidationKind.RECOMMENDATION_MISMATCH.value in _kinds(assembly)


def test_changed_quality_score_fails() -> None:
    package = _compose()
    dsp = build_public_research_report(package)
    score = dsp.business_quality.score_100
    assembly = assemble_canonical_research(
        package,
        {
            "business_quality_narrative": "Override quality.",
            "evidence_ids": [item.id for item in dsp.evidence],
            "quality_scores": {
                "business_quality": 1.0 if score is None else score + 1.0
            },
        },
    )
    _assert_fail_closed(assembly)


def test_changed_buffett_score_fails() -> None:
    package = _compose()
    dsp = build_public_research_report(package)
    score = dsp.buffett_analysis.buffett_overall_score_100
    assembly = assemble_canonical_research(
        package,
        {
            "buffett_narrative": "Override Buffett.",
            "evidence_ids": [item.id for item in dsp.evidence],
            "buffett_overall_score_100": 1.0 if score is None else score + 1.0,
        },
    )
    _assert_fail_closed(assembly)


def test_fabricated_evidence_id_fails() -> None:
    package = _compose()
    assembly = assemble_canonical_research(
        package,
        {
            "valuation_narrative": "Uses a fake citation.",
            "evidence_ids": ["fabricated-source-99"],
        },
    )
    _assert_fail_closed(assembly)
    assert CanonicalValidationKind.INVALID_EVIDENCE.value in _kinds(assembly)


def test_x10_number_fails() -> None:
    package = _compose()
    assembly = assemble_canonical_research(
        package,
        {"executive_summary": "Quality is 8/10.", "score_10": 8.0},
    )
    _assert_fail_closed(assembly)
    assert CanonicalValidationKind.SCORE_10_FORBIDDEN.value in _kinds(assembly)


def test_entry_price_fails() -> None:
    package = _compose()
    assembly = assemble_canonical_research(package, {"entry_price": 12.5})
    _assert_fail_closed(assembly)
    assert CanonicalValidationKind.ENTRY_EXIT_FORBIDDEN.value in _kinds(assembly)


def test_exit_price_fails() -> None:
    package = _compose()
    assembly = assemble_canonical_research(package, {"exit_price": 99.0})
    _assert_fail_closed(assembly)
    assert CanonicalValidationKind.ENTRY_EXIT_FORBIDDEN.value in _kinds(assembly)


def test_scenario_value_fails() -> None:
    package = _compose()
    assembly = assemble_canonical_research(
        package,
        {"scenarios": {"bear": 50.0, "base": 100.0, "bull": 150.0}},
    )
    _assert_fail_closed(assembly)
    assert CanonicalValidationKind.SCENARIO_FORBIDDEN.value in _kinds(assembly)


def test_expected_return_fails() -> None:
    package = _compose()
    assembly = assemble_canonical_research(package, {"expected_return": 0.12})
    _assert_fail_closed(assembly)
    assert CanonicalValidationKind.EXPECTED_RETURN_FORBIDDEN.value in _kinds(assembly)


def test_provider_leakage_fails() -> None:
    package = _compose()
    assembly = assemble_canonical_research(
        package, {"provider": "openai", "executive_summary": "leak"}
    )
    _assert_fail_closed(assembly)
    assert CanonicalValidationKind.PRIVACY.value in _kinds(assembly)


def test_model_leakage_fails() -> None:
    package = _compose()
    assembly = assemble_canonical_research(
        package, {"model": "gpt-4.1", "executive_summary": "leak"}
    )
    _assert_fail_closed(assembly)
    assert CanonicalValidationKind.PRIVACY.value in _kinds(assembly)


def test_private_prompt_leakage_fails() -> None:
    package = _compose()
    assembly = assemble_canonical_research(
        package,
        {"private_prompt": "secret instructions", "executive_summary": "leak"},
    )
    _assert_fail_closed(assembly)
    assert CanonicalValidationKind.PRIVACY.value in _kinds(assembly)


def test_canary_leakage_fails() -> None:
    package = _compose()
    dsp = build_public_research_report(package)
    assembly = assemble_canonical_research(
        package,
        {
            "executive_summary": f"Follow {PRIVATE_METHODOLOGY_CANARY}",
            "evidence_ids": [item.id for item in dsp.evidence],
        },
    )
    _assert_fail_closed(assembly)
    assert CanonicalValidationKind.CANARY.value in _kinds(assembly)


def test_chain_of_thought_fails() -> None:
    package = _compose()
    assembly = assemble_canonical_research(
        package,
        {"chain_of_thought": "hidden reasoning", "executive_summary": "public"},
    )
    _assert_fail_closed(assembly)
    assert CanonicalValidationKind.PRIVACY.value in _kinds(assembly)


def test_unavailable_dsp_value_replaced_by_ai_fails() -> None:
    package = _compose(price=None)
    assembly = assemble_canonical_research(package, {"intrinsic_value": 0.0})
    _assert_fail_closed(assembly)
    assert CanonicalValidationKind.MISSING_DATA_FILL.value in _kinds(assembly)
    blocked = assemble_canonical_research(package)
    assert blocked.report is None
    fixture = build_test_only_ai_output_fixture(package)
    valid = assemble_canonical_research(package, fixture)
    assert valid.outcome == "valid"
    assert valid.report is not None
    assert valid.report.valuation.intrinsic_value_per_share.value is None
    assert valid.report.valuation.intrinsic_value_per_share.value != 0


def test_rejects_non_research_package() -> None:
    assembly = assemble_canonical_research({"ticker": TICKER})
    _assert_fail_closed(assembly)
    assert assembly.outcome == "invalid"


def test_assembly_is_deterministic() -> None:
    package = _compose()
    fixture = build_test_only_ai_output_fixture(package)
    first = assemble_canonical_research(package, fixture)
    second = assemble_canonical_research(package, fixture)
    assert first.to_public_dict() == second.to_public_dict()
    assert first.private_prompt is not None
    assert second.private_prompt is not None
    assert first.private_prompt.text == second.private_prompt.text


def test_no_orchestrator_calls_during_assembly(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    package = _compose()
    calls = {"n": 0}

    def _block(*args, **kwargs):  # noqa: ANN001, ARG001
        calls["n"] += 1
        raise AssertionError("orchestrator must not run during assembly")

    monkeypatch.setattr(PlatformOrchestrator, "execute", _block)
    fixture = build_test_only_ai_output_fixture(package)
    assembly = assemble_canonical_research(package, fixture)
    assert calls["n"] == 0
    assert assembly.outcome == "valid"


def test_analyze_decision_pack_unused(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {"n": 0}

    def _spy(self, *args, **kwargs):  # noqa: ANN001
        calls["n"] += 1
        raise AssertionError("analyze_decision_pack must not be used")

    monkeypatch.setattr(
        "dsp_platform.platform.DSPPlatform.analyze_decision_pack",
        _spy,
    )
    package = _compose()
    assembly = assemble_canonical_research(
        package, build_test_only_ai_output_fixture(package)
    )
    assert calls["n"] == 0
    assert assembly.outcome == "valid"
