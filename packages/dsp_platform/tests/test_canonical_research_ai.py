"""B2 — deterministic CanonicalResearchAiPort end-to-end seam tests."""

from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from dsp_platform import CompositionRequest, PlatformOrchestrator
from dsp_platform.canonical_research_ai import (
    CanonicalAIDraft,
    CanonicalResearchAiBlockedError,
    ProductionBlockedCanonicalResearchAiPort,
)
from dsp_platform.canonical_research_ai.testing import (
    FIXTURE_ORIGIN,
    TEST_ONLY,
    DeterministicCanonicalResearchAiPort,
)
from dsp_platform.external_evidence import (
    EvidenceKind,
    EvidenceQuality,
    EvidenceValidationStatus,
    ExternalEvidenceIdentity,
    ExternalEvidenceRecord,
    QualitativeEvidenceTopic,
    SourceTier,
    SourceType,
    build_validated_external_evidence_package,
)
from dsp_platform.research_assembly import (
    AI_EXECUTION_BLOCKED,
    AI_OUTPUT_FIXTURE,
    assemble_canonical_research,
)
from dsp_platform.research_package import (
    attach_validated_external_evidence,
    build_research_package,
)
from dsp_platform.research_prompt import (
    PRIVATE_METHODOLOGY_CANARY,
    build_private_research_prompt,
)
from dsp_platform.research_report import (
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
from llm_adapters.activation_evidence import (
    ActivationEvidence,
    BenchmarkEvidence,
    ConfigurationEvidence,
    FailClosedEvidence,
    PrivacyEvidence,
    ToolEvidence,
)
from llm_adapters.activation_guard import ActivationState, evaluate_activation

TICKER = "RELIANCE"
FIXED_RETRIEVED = datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)
SUBJECT = ExternalEvidenceIdentity(
    symbol="RELIANCE",
    exchange="NSE",
    isin="INE002A01018",
    company_name="Reliance Industries",
)


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


def _compose_package():
    request = CompositionRequest(
        financial_statements=_statements(),
        current_market_price=70.0,
        company="Reliance Industries",
        ticker=TICKER,
    )
    result = PlatformOrchestrator(platform_version="0.7.0").execute(request)
    return build_research_package(result, request=request)


def _validated_evidence():
    qualitative = ExternalEvidenceRecord(
        fact_id="mgmt_guidance_fy25_capex",
        identity=SUBJECT,
        evidence_kind=EvidenceKind.QUALITATIVE,
        text_value="Management guided internally funded capacity expansion.",
        topic=QualitativeEvidenceTopic.MANAGEMENT_GUIDANCE,
        publication_date=date(2024, 4, 15),
        source_url="https://www.nseindia.com/corporates/reliance-transcript",
        source_type=SourceType.TRANSCRIPT,
        source_tier=SourceTier.TIER_1_PRIMARY,
        evidence_reference="Q&A: capex remains internally funded.",
        retrieved_at=FIXED_RETRIEVED,
        evidence_quality=EvidenceQuality.HIGH,
        validation_status=EvidenceValidationStatus.VALIDATED,
    )
    numerical = ExternalEvidenceRecord(
        fact_id="claimed_current_outstanding",
        identity=SUBJECT,
        evidence_kind=EvidenceKind.NUMERICAL,
        numeric_value=6_762_000_000.0,
        unit="shares",
        as_of=date(2024, 3, 31),
        publication_date=date(2024, 4, 15),
        source_url="https://www.bseindia.com/corporates/reliance-shares",
        source_type=SourceType.EXCHANGE_NOTICE,
        source_tier=SourceTier.TIER_1_PRIMARY,
        evidence_reference="Webpage stated a share count; not a DSP port.",
        retrieved_at=FIXED_RETRIEVED,
        evidence_quality=EvidenceQuality.MEDIUM,
        validation_status=EvidenceValidationStatus.VALIDATED,
    )
    return build_validated_external_evidence_package(
        (qualitative, numerical),
        subject=SUBJECT,
    )


def _package_with_evidence():
    return attach_validated_external_evidence(
        _compose_package(),
        _validated_evidence(),
    )


def _kinds(result) -> set[str]:
    return {item.kind.value for item in result.issues}


def _assert_rejected(result) -> None:
    assert result.ok is False
    assert result.report is None
    assert result.status in {
        CanonicalValidationStatus.INVALID,
        CanonicalValidationStatus.FAILED_CLOSED,
    }


def test_prompt_to_port_connectivity() -> None:
    package = _package_with_evidence()
    prompt = build_private_research_prompt(package)
    assert "mgmt_guidance_fy25_capex" in prompt.data_block
    assert "validated_external_evidence" in prompt.data_block
    assert '"may_influence_calculation":false' in prompt.data_block
    port = DeterministicCanonicalResearchAiPort()
    assert TEST_ONLY is True
    draft = port.interpret(prompt)
    assert isinstance(draft, CanonicalAIDraft)
    assert draft.test_only is True
    assert draft.origin == FIXTURE_ORIGIN == AI_OUTPUT_FIXTURE
    assert isinstance(draft.output, CanonicalAIResearchOutput)
    assert "mgmt_guidance_fy25_capex" in draft.output.management_quality_narrative
    assert PRIVATE_METHODOLOGY_CANARY not in (
        draft.output.executive_summary or ""
    )


def test_ai_interprets_validated_external_evidence() -> None:
    package = _package_with_evidence()
    prompt = build_private_research_prompt(package)
    draft = DeterministicCanonicalResearchAiPort().interpret(prompt)
    text = " ".join(
        part
        for part in (
            draft.output.executive_summary,
            draft.output.management_quality_narrative,
        )
        if part
    )
    assert "management_guidance" in text
    assert "internally funded" in text
    assert "not a DSP calculation input" in text
    assert draft.output.intrinsic_value is None
    assert draft.output.margin_of_safety is None
    assert draft.output.recommendation_action is None
    assert draft.output.financial_metrics is None


def test_dsp_authority_preserved_after_test_assembly() -> None:
    package = _package_with_evidence()
    dsp = build_public_research_report(package)
    prompt = build_private_research_prompt(package)
    draft = DeterministicCanonicalResearchAiPort().interpret(prompt)
    assembly = assemble_canonical_research(package, draft)
    assert assembly.outcome == "valid"
    assert assembly.ai_execution_state == AI_OUTPUT_FIXTURE
    report = assembly.report
    assert report is not None
    assert report.valuation.intrinsic_value_per_share.value == (
        dsp.valuation.intrinsic_value_per_share.value
    )
    assert report.valuation.margin_of_safety.value == (
        dsp.valuation.margin_of_safety.value
    )
    assert report.recommendation.action == dsp.recommendation.action
    assert report.business_quality.score_100 == dsp.business_quality.score_100
    assert report.economic_moat.score_100 == dsp.economic_moat.score_100
    assert report.buffett_analysis.buffett_overall_score_100 == (
        dsp.buffett_analysis.buffett_overall_score_100
    )
    assert report.valuation.intrinsic_value_per_share.source == "dsp"
    assert report.business_quality.score_10 is None
    assert report.business_quality.score_10_status == SCORE_10_STATUS
    dsp_metrics = {row.name: row.value for row in dsp.financials.metrics}
    ai_metrics = {row.name: row.value for row in report.financials.metrics}
    assert ai_metrics == dsp_metrics
    assert all(row.source == "dsp" for row in report.financials.metrics)
    assert not hasattr(report, "current_outstanding")
    assert not hasattr(report, "shares")
    public = assembly.to_public_dict()
    assert "private_prompt" not in public
    assert assembly.private_prompt is not None
    assert assembly.private_prompt.text not in str(public)


def test_evidence_does_not_become_dsp_data() -> None:
    package = _package_with_evidence()
    evidence = package.external_evidence
    assert evidence is not None
    assert evidence.records[0].may_influence_calculation is False
    assert dict(evidence.canonical_calculation_inputs()) == {}
    dsp_before = build_public_research_report(_compose_package())
    prompt = build_private_research_prompt(package)
    draft = DeterministicCanonicalResearchAiPort().interpret(prompt)
    assembly = assemble_canonical_research(package, draft)
    report = assembly.report
    assert report is not None
    assert report.valuation.intrinsic_value_per_share.value == (
        dsp_before.valuation.intrinsic_value_per_share.value
    )
    assert report.recommendation.action == dsp_before.recommendation.action
    dsp_metrics = {row.name: row.value for row in report.financials.metrics}
    assert 6_762_000_000.0 not in dsp_metrics.values()
    assert "current_outstanding" not in dsp_metrics
    assert "shares_outstanding" not in dsp_metrics
    assert not hasattr(report, "current_outstanding")
    assert not hasattr(report, "shares")
    assert report.recommendation.action == dsp_before.recommendation.action


def test_production_port_is_blocked() -> None:
    package = _package_with_evidence()
    prompt = build_private_research_prompt(package)
    port = ProductionBlockedCanonicalResearchAiPort()
    with pytest.raises(CanonicalResearchAiBlockedError, match=AI_EXECUTION_BLOCKED):
        port.interpret(prompt)
    blocked = assemble_canonical_research(package)
    assert blocked.ai_execution_state == AI_EXECUTION_BLOCKED
    assert blocked.report is None
    assert blocked.outcome == AI_EXECUTION_BLOCKED


def test_production_activation_guard_remains_blocked() -> None:
    verdict = evaluate_activation(
        ActivationEvidence(
            benchmark=BenchmarkEvidence.empty(),
            successful_evaluations=(),
            configuration=ConfigurationEvidence(
                default_provider="",
                cost_efficient_model="",
                premium_model="",
                available_providers=(),
                pricing_known_for_all_tiers=False,
                routing_tier_count=0,
                all_provider_keys_configured=False,
            ),
            tools=ToolEvidence(
                available_tools=(),
                minimum_tool_count=1,
                all_tools_healthy=False,
            ),
            privacy=PrivacyEvidence(
                private_fields_enumerated=False,
                public_pack_present=False,
                leakage_guard_active=False,
                benchmark_report_audited=False,
            ),
            fail_closed=FailClosedEvidence(
                quality_gate_present=False,
                no_fabrication_guarantee=False,
                deterministic_fallback_present=False,
                escalation_present=False,
            ),
            required_quality_threshold=60.0,
        )
    )
    assert verdict.state is ActivationState.AI_PRODUCTION_BLOCKED
    assert verdict.is_ready() is False


def test_privacy_draft_and_public_report() -> None:
    package = _package_with_evidence()
    prompt = build_private_research_prompt(package)
    draft = DeterministicCanonicalResearchAiPort().interpret(prompt)
    assembly = assemble_canonical_research(package, draft)
    public = str(assembly.to_public_dict()).lower()
    report = str(assembly.report.to_public_dict()).lower()
    for token in (
        "api_key",
        "bearer",
        "client_secret",
        "authorization",
        "chain_of_thought",
        "system_prompt",
        "private_prompt",
        "routing_tier",
        "token_count",
        "openai",
        "anthropic",
        PRIVATE_METHODOLOGY_CANARY.lower(),
    ):
        assert token not in public
        assert token not in report
    assert prompt.text not in str(assembly.to_public_dict())
    assert prompt.instructions not in str(assembly.to_public_dict())


def test_override_intrinsic_value_rejected() -> None:
    package = _package_with_evidence()
    dsp = build_public_research_report(package)
    iv = dsp.valuation.intrinsic_value_per_share.value
    result = validate_canonical_research(
        package,
        {
            "valuation_narrative": "Altered IV.",
            "evidence_ids": [item.id for item in dsp.evidence],
            "intrinsic_value": 1.0 if iv is None else iv + 1.0,
        },
    )
    _assert_rejected(result)
    assert _kinds(result) & {
        CanonicalValidationKind.NUMERICAL_MISMATCH.value,
        CanonicalValidationKind.MISSING_DATA_FILL.value,
    }


def test_override_margin_of_safety_rejected() -> None:
    package = _package_with_evidence()
    dsp = build_public_research_report(package)
    mos = dsp.valuation.margin_of_safety.value
    result = validate_canonical_research(
        package,
        {
            "valuation_narrative": "Altered MoS.",
            "evidence_ids": [item.id for item in dsp.evidence],
            "margin_of_safety": 0.99 if mos is None else mos + 0.25,
        },
    )
    _assert_rejected(result)


def test_override_recommendation_rejected() -> None:
    package = _package_with_evidence()
    dsp = build_public_research_report(package)
    action = (dsp.recommendation.action or "HOLD").upper()
    invented = "SELL" if action != "SELL" else "BUY"
    result = validate_canonical_research(
        package,
        {
            "recommendation_narrative": "Override.",
            "evidence_ids": [item.id for item in dsp.evidence],
            "recommendation_action": invented,
        },
    )
    _assert_rejected(result)
    assert CanonicalValidationKind.RECOMMENDATION_MISMATCH.value in _kinds(result)


def test_override_business_quality_score_rejected() -> None:
    package = _package_with_evidence()
    dsp = build_public_research_report(package)
    score = dsp.business_quality.score_100
    result = validate_canonical_research(
        package,
        {
            "business_quality_narrative": "Override quality.",
            "evidence_ids": [item.id for item in dsp.evidence],
            "quality_scores": {
                "business_quality": 1.0 if score is None else score + 1.0
            },
        },
    )
    _assert_rejected(result)


def test_override_moat_score_rejected() -> None:
    package = _package_with_evidence()
    dsp = build_public_research_report(package)
    score = dsp.economic_moat.score_100
    result = validate_canonical_research(
        package,
        {
            "economic_moat_narrative": "Override moat.",
            "evidence_ids": [item.id for item in dsp.evidence],
            "quality_scores": {
                "economic_moat": 1.0 if score is None else score + 1.0
            },
        },
    )
    _assert_rejected(result)


def test_override_current_outstanding_rejected() -> None:
    package = _package_with_evidence()
    dsp = build_public_research_report(package)
    result = validate_canonical_research(
        package,
        {
            "financials_narrative": "Invented shares.",
            "evidence_ids": [item.id for item in dsp.evidence],
            "financial_metrics": {"current_outstanding": 6_762_000_000.0},
        },
    )
    _assert_rejected(result)
    assert CanonicalValidationKind.NUMERICAL_MISMATCH.value in _kinds(result)


def test_override_eps_rejected() -> None:
    package = _package_with_evidence()
    dsp = build_public_research_report(package)
    metrics = {row.name: row.value for row in dsp.financials.metrics}
    eps = metrics.get("eps")
    result = validate_canonical_research(
        package,
        {
            "financials_narrative": "Invented EPS.",
            "evidence_ids": [item.id for item in dsp.evidence],
            "financial_metrics": {"eps": 1.0 if eps is None else eps + 1.0},
        },
    )
    _assert_rejected(result)


def test_override_revenue_rejected() -> None:
    package = _package_with_evidence()
    dsp = build_public_research_report(package)
    metrics = {row.name: row.value for row in dsp.financials.metrics}
    revenue = metrics.get("revenue")
    result = validate_canonical_research(
        package,
        {
            "financials_narrative": "Invented revenue.",
            "evidence_ids": [item.id for item in dsp.evidence],
            "financial_metrics": {
                "revenue": 1.0 if revenue is None else revenue + 1.0
            },
        },
    )
    _assert_rejected(result)


def test_override_financial_ratio_rejected() -> None:
    package = _package_with_evidence()
    dsp = build_public_research_report(package)
    metrics = {row.name: row.value for row in dsp.financials.metrics}
    margin = metrics.get("gross_margin")
    result = validate_canonical_research(
        package,
        {
            "financials_narrative": "Invented ratio.",
            "evidence_ids": [item.id for item in dsp.evidence],
            "financial_metrics": {
                "gross_margin": 0.99 if margin is None else margin + 0.5
            },
        },
    )
    _assert_rejected(result)


def test_override_x10_moat_rating_rejected() -> None:
    package = _package_with_evidence()
    dsp = build_public_research_report(package)
    result = validate_canonical_research(
        package,
        {
            "economic_moat_narrative": "Moat is 8/10.",
            "evidence_ids": [item.id for item in dsp.evidence],
            "score_10": {"economic_moat": 8.0},
        },
    )
    _assert_rejected(result)
    assert CanonicalValidationKind.SCORE_10_FORBIDDEN.value in _kinds(result)
    text_result = validate_canonical_research(
        package,
        {
            "economic_moat_narrative": "Moat is 8/10.",
            "evidence_ids": [item.id for item in dsp.evidence],
        },
    )
    _assert_rejected(text_result)
    assert CanonicalValidationKind.SCORE_10_FORBIDDEN.value in _kinds(text_result)


def test_research_http_does_not_use_test_ai() -> None:
    from api_platform.api.routers import research_company as router_mod

    text = Path(router_mod.__file__).read_text(encoding="utf-8")
    assert "DeterministicCanonicalResearchAiPort" not in text
    assert "assemble_canonical_research" not in text
    assert "canonical_research_ai" not in text
