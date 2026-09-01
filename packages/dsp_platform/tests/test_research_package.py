"""STEP 4B — private ResearchPackage aggregator tests."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, date, datetime

import pytest

from data_engine import (
    FinancialStatementProvenance,
    FinancialStatementService,
    InMemoryAuthenticatedQuoteAdapter,
    InMemoryAuthenticatedStatementAdapter,
    MarketQuoteProvenance,
    MarketQuoteService,
    build_quote_from_mapping,
    build_statements_from_mapping,
)
from dsp_platform import (
    COMPOSITION_PIPELINE_VERSION,
    CompositionRequest,
    DSPPlatform,
    PlatformOrchestrator,
    pipeline_result_public_dict,
)
from dsp_platform.composition.versions import (
    COMPOSITION_PIPELINE_VERSION as PIPELINE_VERSION,
)
from dsp_platform.financial_statements import (
    reset_financial_statement_service_for_tests,
)
from dsp_platform.market_quotes import reset_market_quote_service_for_tests
from dsp_platform.research_package import (
    ENTRY_EXIT_NOT_IMPLEMENTED_MESSAGE,
    RESEARCH_PACKAGE_SCHEMA_VERSION,
    SOURCE_PIPELINE_COMPOSE_INTELLIGENCE,
    ResearchPackage,
    ResearchPackageSourceError,
    build_research_package,
    contains_private_fields,
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
FIXED_RETRIEVED = datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)


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


def _compose(statements: FinancialStatements | None = None) -> tuple:
    request = CompositionRequest(
        financial_statements=statements or _statements(),
        current_market_price=70.0,
        company="Reliance Industries",
        ticker=TICKER,
    )
    result = PlatformOrchestrator(platform_version="0.7.0").execute(request)
    public = pipeline_result_public_dict(result)
    package = build_research_package(result, request=request)
    return request, result, public, package


def test_package_source_and_methodology() -> None:
    _request, _result, _public, package = _compose()
    assert package.schema_version == RESEARCH_PACKAGE_SCHEMA_VERSION
    assert package.methodology_version == COMPOSITION_PIPELINE_VERSION
    assert package.methodology_version == PIPELINE_VERSION
    assert package.methodology_version == "1.0.0-epic-001"
    assert package.source_pipeline == SOURCE_PIPELINE_COMPOSE_INTELLIGENCE
    assert package.source_pipeline == "compose_intelligence"


def test_identity_from_request() -> None:
    _request, _result, _public, package = _compose()
    assert package.identity.available is True
    assert package.identity.payload is not None
    assert package.identity.payload["ticker"] == TICKER
    assert package.identity.payload["company"] == "Reliance Industries"


def test_valuation_matches_composition_without_substitute() -> None:
    _request, result, public, package = _compose()
    signals = result.valuation_signals
    payload = package.valuation.payload
    assert payload is not None
    server = public["server_valuation"]
    assert payload["server_valuation"] == server
    assert payload["intrinsic_value"]["intrinsic_value_per_share"] == server[
        "intrinsic_value_per_share"
    ]
    assert (
        payload["intrinsic_value"]["current_market_price"]
        == signals.current_market_price
    )
    assert payload["margin_of_safety"] == signals.margin_of_safety
    # Non-auth fixture: per-share IV/MoS stay unavailable (P1-04). No substitute.
    assert payload["intrinsic_value"]["intrinsic_value_per_share"] is None
    assert payload["margin_of_safety"] is None
    assert payload["range"] is None
    assert payload["methods"] is None


def test_recommendation_matches_investment_recommendation_engine() -> None:
    _request, result, public, package = _compose()
    rec = result.investment_recommendation
    assert rec is not None
    payload = package.investment_recommendation.payload
    assert payload is not None
    summary = public["recommendation_summary"]
    assert payload["recommendation_summary"] == summary
    engine_decision = getattr(rec, "recommendation", None)
    engine_value = getattr(engine_decision, "value", engine_decision)
    assert payload.get("recommendation") == engine_value
    assert summary.get("decision") in {engine_value, payload.get("recommendation")}


def test_buffett_authority_is_existing_pipeline_projection() -> None:
    _request, _result, public, package = _compose()
    authority = package.buffett_authority.payload
    assert authority == public["buffett_authority"]
    assert authority["methodology"] == "existing_pipeline_stages"
    assert package.buffett_authority.payload["authority"] == "server"
    assert package.buffett_authority.payload["client_overrides_accepted"] is False


def test_financials_match_financial_stage() -> None:
    _request, result, public, package = _compose()
    assert result.financial_analysis is not None
    assert package.financials.available is True
    assert package.financials.payload is not None
    expected = result.financial_analysis.to_dict()
    assert (
        package.financials.to_dict()["payload"]["overall_summary"]
        == expected["overall_summary"]
    )
    financial_summary = next(
        row for row in public["stage_summaries"] if row["stage"] == "financial"
    )
    assert package.financials.status == financial_summary["status"]


def test_quality_sections_match_stage_summaries() -> None:
    _request, _result, public, package = _compose()
    mapping = {
        "economic_moat": package.economic_moat,
        "management_quality": package.management_quality,
        "financial_strength": package.financial_strength,
        "earnings_quality": package.earnings_quality,
        "growth_quality": package.growth_quality,
        "business_quality_aggregator": package.business_quality,
        "risk": package.risk,
        "investment_committee": package.investment_committee,
    }
    by_stage = {row["stage"]: row for row in public["stage_summaries"]}
    for stage, section in mapping.items():
        summary = by_stage[stage]
        assert section.status == summary["status"]
        if summary["has_result"] and summary["status"] in {"succeeded", "degraded"}:
            assert section.available is True
            assert section.payload is not None


def test_evidence_uses_canonical_source_evidence() -> None:
    _request, result, public, package = _compose()
    assert package.evidence.payload is not None
    assert package.evidence.payload["source_evidence"] == public["source_evidence"]
    assert package.evidence.payload["evidence_counts"] == dict(
        result.metadata.evidence_counts
    )


def test_entry_exit_is_not_implemented() -> None:
    _request, _result, _public, package = _compose()
    assert package.entry_exit.available is False
    assert package.entry_exit.status == "not_implemented"
    assert package.entry_exit.payload is None
    assert package.entry_exit.message == ENTRY_EXIT_NOT_IMPLEMENTED_MESSAGE
    dumped = package.to_dict()
    assert "entry_price" not in dumped
    assert dumped["entry_exit"]["payload"] is None


def test_builder_is_deterministic_for_same_pipeline_result() -> None:
    request, result, _public, _first = _compose()
    a = build_research_package(result, request=request).to_dict()
    b = build_research_package(result, request=request).to_dict()
    assert a == b


def test_missing_valuation_stays_unavailable() -> None:
    request = CompositionRequest(
        financial_statements=_statements(),
        current_market_price=None,
        ticker=TICKER,
        company="Reliance Industries",
    )
    result = PlatformOrchestrator(platform_version="0.7.0").execute(request)
    public = pipeline_result_public_dict(result)
    package = build_research_package(result, request=request)
    assert result.ok is False
    assert package.pipeline_ok is False
    assert public["server_valuation"]["intrinsic_value_per_share"] is None
    iv = package.valuation.payload["intrinsic_value"]["intrinsic_value_per_share"]
    assert iv is None
    assert package.valuation.payload["margin_of_safety"] is None
    assert package.valuation.status == "failed"
    assert package.valuation.available is False


def test_rejects_analyze_decision_pack_objects() -> None:
    class DecisionPack:  # noqa: N801 — legacy type name under test
        pass

    with pytest.raises(ResearchPackageSourceError, match="analyze_decision_pack"):
        build_research_package(DecisionPack())
    with pytest.raises(ResearchPackageSourceError):
        build_research_package({"ticker": TICKER, "recommendation": "BUY"})


def test_no_from_dict_client_constructor() -> None:
    assert not hasattr(ResearchPackage, "from_dict")
    assert not hasattr(ResearchPackage, "from_json")
    assert not hasattr(ResearchPackage, "parse_obj")


def test_no_private_ai_fields() -> None:
    _request, _result, _public, package = _compose()
    dumped = package.to_dict()
    leaked = contains_private_fields(dumped)
    assert leaked == []
    text = str(dumped).lower()
    for name in ("openai", "anthropic", "gemini", "deepseek", "gpt-", "claude"):
        assert name not in text


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

    def _legacy_analyze(*args, **kwargs):  # noqa: ANN001, ARG001
        calls["n"] += 1
        raise AssertionError("legacy InvestmentAnalysisService must not be used")

    monkeypatch.setattr(
        "orchestration.service.InvestmentAnalysisService.analyze",
        _legacy_analyze,
    )

    request, result, _public, package = _compose()
    envelope = DSPPlatform().compose_intelligence(request)
    packed = build_research_package(envelope.payload, request=request)
    assert calls["n"] == 0
    assert package.source_pipeline == "compose_intelligence"
    assert packed.source_pipeline == "compose_intelligence"
    assert envelope.capability == "compose_intelligence"


def _stmt_provenance() -> FinancialStatementProvenance:
    return FinancialStatementProvenance(
        provider_id="memory_authenticated_statements",
        provider_name="Memory Statements",
        source_type="licensed_vendor",
        retrieved_at=FIXED_RETRIEVED,
        auth_mode="api_key",
    )


def _seed_statements(symbol: str = TICKER):
    return build_statements_from_mapping(
        symbol=symbol,
        payload={
            "identity": {
                "symbol": symbol,
                "exchange": "NSE",
                "company_name": "Reliance Industries",
                "currency": "USD",
            },
            "reporting_currency": "USD",
            "statement_basis": "consolidated",
            "unit_scale": "actual",
            "periods": [
                {
                    "period_type": "annual",
                    "fiscal_year": 2024,
                    "period_end": "2024-12-31",
                    "filing_date": "2025-02-01",
                    "reporting_currency": "USD",
                    "restated": False,
                    "income_statement": {
                        "revenue": 500.0,
                        "net_income": 100.0,
                        "eps_basic": 1.0,
                        "operating_income": 120.0,
                    },
                    "balance_sheet": {
                        "cash": 50.0,
                        "total_assets": 1500.0,
                        "total_liabilities": 500.0,
                        "equity": 1000.0,
                        "total_debt": 200.0,
                    },
                    "cash_flow": {
                        "operating_cash_flow": 150.0,
                        "capex": -30.0,
                        "free_cash_flow": 120.0,
                    },
                    "ratios": {},
                },
                {
                    "period_type": "annual",
                    "fiscal_year": 2023,
                    "period_end": "2023-12-31",
                    "reporting_currency": "USD",
                    "income_statement": {
                        "revenue": 450.0,
                        "net_income": 90.0,
                        "eps_basic": 0.9,
                    },
                    "balance_sheet": {
                        "equity": 900.0,
                        "total_assets": 1400.0,
                        "total_liabilities": 500.0,
                    },
                    "cash_flow": {
                        "operating_cash_flow": 130.0,
                        "capex": -25.0,
                        "free_cash_flow": 105.0,
                    },
                    "ratios": {},
                },
            ],
        },
        provenance=_stmt_provenance(),
    )


def _seed_quote(symbol: str = TICKER, *, price: float = 8.0, shares: float = 100.0):
    return build_quote_from_mapping(
        symbol=symbol,
        payload={
            "exchange": "NSE",
            "currency": "USD",
            "current_price": price,
            "previous_close": price,
            "market_cap": price * shares,
            "shares_outstanding": shares,
        },
        provenance=MarketQuoteProvenance(
            provider_id="memory_authenticated_quote",
            provider_name="Memory Quote",
            source_type="licensed_vendor",
            retrieved_at=FIXED_RETRIEVED,
            auth_mode="api_key",
        ),
    )


@pytest.fixture
def seeded_reliance_services():
    stmt_adapter = InMemoryAuthenticatedStatementAdapter(api_key="test-key")
    stmt_adapter.put(_seed_statements())
    quote_adapter = InMemoryAuthenticatedQuoteAdapter(api_key="test-key")
    quote_adapter.put(_seed_quote())
    reset_financial_statement_service_for_tests(FinancialStatementService(stmt_adapter))
    reset_market_quote_service_for_tests(MarketQuoteService(quote_adapter))
    yield
    reset_financial_statement_service_for_tests(None)
    reset_market_quote_service_for_tests(None)


def test_authenticated_iv_mos_recommendation_match_composition(
    seeded_reliance_services,
) -> None:
    request = CompositionRequest(
        financial_statements=_statements(),
        current_market_price=999.0,
        ticker=TICKER,
        company="Reliance Industries",
    )
    result = PlatformOrchestrator(platform_version="0.7.0").execute(request)
    public = pipeline_result_public_dict(result)
    package = build_research_package(result, request=request)
    signals = result.valuation_signals
    assert result.ok is True
    assert signals is not None
    iv = getattr(signals, "intrinsic_value_per_share", None)
    mos = getattr(signals, "margin_of_safety", None)
    assert iv is not None and iv > 0
    assert mos is not None
    payload = package.valuation.payload
    assert payload["intrinsic_value"]["intrinsic_value_per_share"] == pytest.approx(iv)
    assert payload["margin_of_safety"] == pytest.approx(mos)
    assert payload["intrinsic_value"]["current_market_price"] == pytest.approx(8.0)
    assert payload["server_valuation"] == public["server_valuation"]
    assert payload["range"] is not None
    assert payload["methods"] is not None
    method_names = {row["method"] for row in payload["methods"]}
    assert "dcf" in method_names
    rec = result.investment_recommendation
    assert rec is not None
    assert package.investment_recommendation.payload["recommendation"] == getattr(
        rec.recommendation, "value", rec.recommendation
    )
    assert package.buffett_authority.payload == public["buffett_authority"]
    assert package.source_pipeline == "compose_intelligence"


def test_package_is_frozen() -> None:
    _request, _result, _public, package = _compose()
    with pytest.raises(FrozenInstanceError):
        package.source_pipeline = "analyze_decision_pack"  # type: ignore[misc]
