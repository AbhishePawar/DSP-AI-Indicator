"""EPIC-001 platform composition pipeline tests."""

from __future__ import annotations

from datetime import date

import pytest

from dsp_platform import (
    COMPOSITION_PIPELINE_VERSION,
    EXECUTION_ORDER,
    CompositionRequest,
    DSPPlatform,
    DependencyResolver,
    PipelineConfiguration,
    PipelineStage,
    PlatformOrchestrator,
)
from financial import (
    BalanceSheet,
    CashFlowStatement,
    CurrencyCode,
    CurrencyRef,
    FinancialEngine,
    FinancialPeriod,
    FinancialStatements,
    IncomeStatement,
    PeriodType,
    UnitScale,
)
from financial.metadata import StatementMetadata
from investment_recommendation import ValuationSignals


@pytest.fixture
def statements() -> FinancialStatements:
    period = FinancialPeriod(
        period_type=PeriodType.ANNUAL,
        period_end=date(2024, 12, 31),
        fiscal_year=2024,
        currency=CurrencyRef(CurrencyCode.USD),
    )
    return FinancialStatements(
        period=period,
        income_statement=IncomeStatement(
            revenue=1000.0, cogs=400.0, gross_profit=600.0, ebit=300.0,
            ebitda=350.0, interest_expense=20.0, pretax_income=280.0,
            tax=70.0, net_income=210.0, weighted_shares=100.0, eps=2.1,
        ),
        balance_sheet=BalanceSheet(
            cash=150.0, short_term_investments=50.0, accounts_receivable=120.0,
            inventory=80.0, current_assets=450.0, ppe=400.0, goodwill=50.0,
            intangibles=50.0, total_assets=1000.0, accounts_payable=60.0,
            short_term_debt=50.0, current_liabilities=200.0,
            long_term_debt=200.0, total_liabilities=400.0,
            retained_earnings=300.0, equity=600.0, total_equity=600.0,
        ),
        cash_flow=CashFlowStatement(
            operating_cash_flow=250.0, capex=-80.0, free_cash_flow=170.0,
            dividends_paid=-50.0, share_buybacks=-30.0, debt_issued=10.0,
            debt_repaid=-40.0,
        ),
        statement_metadata=StatementMetadata(unit_scale=UnitScale.MILLIONS),
    )


def test_execution_order_is_canonical() -> None:
    assert [s.value for s in EXECUTION_ORDER] == [
        "financial",
        "valuation",
        "economic_moat",
        "management_quality",
        "financial_strength",
        "earnings_quality",
        "growth_quality",
        "risk",
        "business_quality_aggregator",
        "investment_recommendation",
        "investment_committee",
    ]
    assert DependencyResolver().validate_order(EXECUTION_ORDER) is True
    assert (
        DependencyResolver().validate_order(
            (PipelineStage.VALUATION, PipelineStage.FINANCIAL)
        )
        is False
    )


def test_pipeline_runs_end_to_end(statements: FinancialStatements) -> None:
    request = CompositionRequest(
        financial_statements=statements,
        current_market_price=70.0,
        company="Acme",
        ticker="ACM",
    )
    result = PlatformOrchestrator(platform_version="0.7.0").execute(request)
    assert result.ok is True
    assert result.financial_analysis is not None
    assert result.business_quality is not None
    assert result.investment_recommendation is not None
    assert result.investment_committee is not None
    assert result.metadata.pipeline_version == COMPOSITION_PIPELINE_VERSION
    assert list(result.metadata.execution_order) == [s.value for s in EXECUTION_ORDER]
    assert len(result.trace) == len(EXECUTION_ORDER)
    assert [t.stage for t in result.trace] == [s.value for s in EXECUTION_ORDER]
    payload = result.to_dict()
    assert payload["ok"] is True
    assert payload["has_investment_committee"] is True


def test_pipeline_is_deterministic(statements: FinancialStatements) -> None:
    request = CompositionRequest(
        financial_statements=statements,
        current_market_price=70.0,
    )
    orch = PlatformOrchestrator(platform_version="0.7.0")
    a = orch.execute(request).to_dict()
    b = orch.execute(request).to_dict()
    a["metadata"].pop("total_elapsed_ms", None)
    b["metadata"].pop("total_elapsed_ms", None)
    for entry in a["trace"]:
        entry.pop("elapsed_ms", None)
    for entry in b["trace"]:
        entry.pop("elapsed_ms", None)
    assert a == b


def test_failure_preserves_completed_stages(statements: FinancialStatements) -> None:
    request = CompositionRequest(
        financial_statements=statements,
        current_market_price=None,
        valuation_signals=None,
        overall_valuation=None,
        financial_snapshot=None,
        stop_on_stage_failure=False,
    )
    result = PlatformOrchestrator(platform_version="0.7.0").execute(request)
    assert result.ok is False
    assert result.metadata.failed_stage == "valuation"
    assert result.financial_analysis is not None


def test_platform_compose_intelligence(statements: FinancialStatements) -> None:
    platform = DSPPlatform()
    request = CompositionRequest(
        financial_analysis=FinancialEngine().analyze_financials(statements),
        current_market_price=75.0,
    )
    envelope = platform.compose_intelligence(request)
    assert envelope.capability == "compose_intelligence"
    assert envelope.ok is True
    assert envelope.payload.investment_committee is not None


def test_p0_02_client_valuation_signals_cannot_set_intrinsic_value(
    statements: FinancialStatements,
) -> None:
    """P0-02 — forged client IV must not become authoritative signals."""
    forged_iv = 999.0
    request = CompositionRequest(
        financial_statements=statements,
        valuation_signals=ValuationSignals(
            intrinsic_value_per_share=forged_iv,
            current_market_price=70.0,
            confidence=0.99,
        ),
        company="Acme",
        ticker="ACM",
    )
    result = PlatformOrchestrator(platform_version="0.7.0").execute(request)
    assert result.ok is True
    valuation_outcome = next(s for s in result.stages if s.stage == "valuation")
    assert any("P0-02" in w for w in valuation_outcome.warnings)
    signals = result.valuation
    # Pipeline returns ValuationSignals on the degraded price-only path.
    assert signals is not None
    iv = getattr(signals, "intrinsic_value_per_share", None)
    assert iv != forged_iv
    assert iv is None  # no ValuationEngine snapshot → honest price-only


def test_build_composition_request_from_dict(statements: FinancialStatements) -> None:
    from dsp_platform import build_composition_request, pipeline_result_public_dict

    req = build_composition_request(
        ticker="acm",
        company="Acme",
        financial_statements=statements.to_dict(),
        current_market_price=70.0,
    )
    assert req.ticker == "ACM"
    assert req.financial_statements is not None
    result = PlatformOrchestrator(platform_version="0.7.1").execute(req)
    public = pipeline_result_public_dict(result)
    assert public["ok"] is True
    assert public["committee_summary"] is not None
    assert len(public["stage_summaries"]) == 11
    assert public["risk"] is not None
    assert public["risk"]["financial_risk"]["available"] is True


def test_pipeline_configuration_defaults() -> None:
    cfg = PipelineConfiguration()
    assert cfg.stages == EXECUTION_ORDER
    assert cfg.stop_on_stage_failure is False
