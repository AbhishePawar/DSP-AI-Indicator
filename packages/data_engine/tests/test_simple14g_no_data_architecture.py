"""SIMPLE-14G — provider-neutral no-data architecture.

Proves:
* DSP_INVESTMENT_DATA_PROVIDER=none selects Null adapters
* retired upstox selector is rejected (not a silent fallback)
* previous close cannot become current price
* Security Master identity (NSE / BSE / dual-listed / unknown / unsupported)
* AI output cannot become VERIFIED_DATA
* DSP packages do not import vendor SDKs
* share-count remains quote-field independent of vendor selection
"""

from __future__ import annotations

import ast
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from data_engine.capabilities import (
    CapabilityName,
    CapabilityReport,
    CapabilityStatus,
    PriceKind,
    price_kind_from_fields,
)
from data_engine.connector_framework.production_profile import (
    ConnectorConfigurationError,
    assert_production_investment_connectors_configured,
)
from data_engine.corporate_action_types import (
    SHARE_COUNT_CHANGING_TYPES,
    CorporateActionType,
)
from data_engine.data_states import DataState, QualityDecision, apply_quality_gate
from data_engine.financial_statement.adapters import (
    NullAuthenticatedStatementAdapter,
    build_default_statement_adapter_from_env,
)
from data_engine.investment_data_provider import resolve_investment_data_provider
from data_engine.market_quote.adapters import (
    NullAuthenticatedQuoteAdapter,
    build_default_quote_adapter_from_env,
    build_quote_from_mapping,
)
from data_engine.market_quote.models import MarketQuoteProvenance
from data_engine.security_identity import (
    CatalogSecurityMaster,
    IdentityStatus,
    SecurityListing,
    set_security_master_for_tests,
)
from data_engine.source_policy import SourceDecision, SourceTier, classify_source
from dsp_platform import (
    DATA_UNAVAILABLE,
    AuthenticatedValuationError,
    load_authenticated_valuation_bundle,
)
from dsp_platform.financial_statements import (
    reset_financial_statement_service_for_tests,
)
from dsp_platform.market_quotes import reset_market_quote_service_for_tests

_REPO = Path(__file__).resolve().parents[3]
_FIXED = datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)


@pytest.fixture(autouse=True)
def _reset_identity() -> None:
    set_security_master_for_tests(None)
    yield
    set_security_master_for_tests(None)
    reset_market_quote_service_for_tests(None)
    reset_financial_statement_service_for_tests(None)


def _strip_investment(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in (
        "DSP_INVESTMENT_DATA_PROVIDER",
        "DSP_FMP_API_KEY",
        "DSP_INVESTMENT_FMP_API_KEY",
        "DSP_MARKET_QUOTE_API_KEY",
        "DSP_MARKET_QUOTE_BASE_URL",
        "DSP_MARKET_QUOTE_MEMORY",
        "DSP_FINANCIAL_STATEMENT_API_KEY",
        "DSP_FINANCIAL_STATEMENT_BASE_URL",
        "DSP_FINANCIAL_STATEMENT_MEMORY",
    ):
        monkeypatch.delenv(key, raising=False)


def test_none_provider_selects_null_adapters(monkeypatch: pytest.MonkeyPatch) -> None:
    _strip_investment(monkeypatch)
    monkeypatch.setenv("DSP_ENVIRONMENT", "production")
    monkeypatch.setenv("DSP_INVESTMENT_DATA_PROVIDER", "none")
    assert resolve_investment_data_provider() == "none"
    quote = build_default_quote_adapter_from_env()
    stmt = build_default_statement_adapter_from_env()
    assert isinstance(quote, NullAuthenticatedQuoteAdapter)
    assert isinstance(stmt, NullAuthenticatedStatementAdapter)
    selected = assert_production_investment_connectors_configured()
    assert selected["market_quote"] == "NullAuthenticatedQuoteAdapter"
    assert selected["financial_statement"] == "NullAuthenticatedStatementAdapter"


def test_retired_vendor_selector_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    _strip_investment(monkeypatch)
    monkeypatch.setenv("DSP_INVESTMENT_DATA_PROVIDER", "upstox")
    with pytest.raises(ConnectorConfigurationError, match="retired"):
        resolve_investment_data_provider()


def test_no_silent_fmp_fallback_when_none_selected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _strip_investment(monkeypatch)
    monkeypatch.setenv("DSP_ENVIRONMENT", "production")
    monkeypatch.setenv("DSP_INVESTMENT_DATA_PROVIDER", "none")
    monkeypatch.setenv("DSP_FMP_API_KEY", "must-not-win")
    quote = build_default_quote_adapter_from_env()
    assert isinstance(quote, NullAuthenticatedQuoteAdapter)


def test_capabilities_are_independent() -> None:
    quote = CapabilityReport(CapabilityName.QUOTE, CapabilityStatus.AVAILABLE, "live")
    financials = CapabilityReport(
        CapabilityName.FINANCIALS, CapabilityStatus.UNAVAILABLE, "no provider"
    )
    assert quote.status is CapabilityStatus.AVAILABLE
    assert financials.status is CapabilityStatus.UNAVAILABLE
    assert quote.status is not financials.status


def test_previous_close_is_not_current() -> None:
    kind = price_kind_from_fields(
        current_available=False, previous_close_available=True
    )
    assert kind is PriceKind.PREVIOUS_CLOSE
    assert kind is not PriceKind.CURRENT


def test_previous_close_cannot_become_current_price() -> None:
    from data_engine import (
        FinancialStatementProvenance,
        build_statements_from_mapping,
    )

    quote = build_quote_from_mapping(
        symbol="ALPHA",
        payload={
            "exchange": "NSE",
            "currency": "INR",
            "previous_close": 100.0,
            "shares_outstanding": 250.0,
        },
        provenance=MarketQuoteProvenance(
            provider_id="memory_authenticated_quote",
            provider_name="Memory",
            source_type="licensed_vendor",
            retrieved_at=_FIXED,
            auth_mode="api_key",
        ),
    )
    assert quote.current_price.available is False
    assert quote.previous_close.available is True

    statements = build_statements_from_mapping(
        symbol="ALPHA",
        payload={
            "identity": {"symbol": "ALPHA", "exchange": "NSE", "currency": "INR"},
            "reporting_currency": "INR",
            "statement_basis": "consolidated",
            "unit_scale": "actual",
            "periods": [
                {
                    "period_type": "annual",
                    "fiscal_year": 2024,
                    "period_end": "2024-03-31",
                    "reporting_currency": "INR",
                    "restated": False,
                    "income_statement": {"revenue": 10.0, "net_income": 1.0},
                    "balance_sheet": {"total_equity": 5.0, "total_assets": 8.0},
                    "cash_flow": {"operating_cash_flow": 2.0},
                }
            ],
        },
        provenance=FinancialStatementProvenance(
            provider_id="memory_authenticated_statements",
            provider_name="Memory",
            source_type="licensed_vendor",
            retrieved_at=_FIXED,
            auth_mode="api_key",
        ),
    )
    with pytest.raises(AuthenticatedValuationError, match="previous close"):
        load_authenticated_valuation_bundle(
            "ALPHA",
            exchange="NSE",
            currency="INR",
            get_quote=lambda _s: quote,
            get_statements=lambda _s: statements,
        )


def test_security_master_nse_bse_dual_unknown_unsupported() -> None:
    master = CatalogSecurityMaster(
        listings=(
            SecurityListing(
                ticker="NSEA",
                exchange="NSE",
                isin="INE000A01018",
                mic="XNSE",
                company="NSE Alpha",
            ),
            SecurityListing(
                ticker="BSEA",
                exchange="BSE",
                isin="INE000B01016",
                mic="XBOM",
                company="BSE Alpha",
            ),
            SecurityListing(
                ticker="DUAL",
                exchange="NSE",
                isin="INE000D01012",
                mic="XNSE",
                company="Dual Co",
            ),
            SecurityListing(
                ticker="DUAL",
                exchange="BSE",
                isin="INE000D01012",
                mic="XBOM",
                company="Dual Co",
            ),
            SecurityListing(
                ticker="WARR",
                exchange="NSE",
                isin="INE000W01019",
                mic="XNSE",
                security_type="WARRANT",
            ),
        )
    )
    nse = master.resolve(ticker="NSEA")
    assert nse.status is IdentityStatus.RESOLVED
    assert nse.exchange == "NSE"
    assert nse.isin == "INE000A01018"
    bse = master.resolve(ticker="BSEA")
    assert bse.status is IdentityStatus.RESOLVED
    assert bse.exchange == "BSE"
    dual = master.resolve(ticker="DUAL")
    assert dual.status is IdentityStatus.AMBIGUOUS
    dual_nse = master.resolve(ticker="DUAL", exchange="NSE")
    assert dual_nse.status is IdentityStatus.RESOLVED
    assert dual_nse.mic == "XNSE"
    unknown = master.resolve(ticker="ZZZZZUNKNOWN")
    assert unknown.status is IdentityStatus.UNKNOWN
    warrant = master.resolve(ticker="WARR")
    assert warrant.status is IdentityStatus.UNSUPPORTED
    rejected = master.resolve(
        ticker="NSEA", vendor_hints={"instrument_key": "NSE_EQ|INE000A01018"}
    )
    assert rejected.status is IdentityStatus.REJECTED


def test_quality_gate_rejects_ai_as_verified() -> None:
    result = apply_quality_gate(
        source="nse",
        has_evidence=True,
        identity_ok=True,
        agent="gemini",
    )
    assert result.decision is QualityDecision.REJECT
    assert result.state is DataState.RAW_PROVIDER_DATA


def test_source_whitelist_rejects_vendor_as_truth() -> None:
    tier, decision = classify_source("upstox")
    assert tier is SourceTier.FORBIDDEN
    assert decision is SourceDecision.REJECT
    tier, decision = classify_source("nse")
    assert tier is SourceTier.PRIMARY
    assert decision is SourceDecision.ACCEPT
    tier, decision = classify_source("yahoo_finance")
    assert tier is SourceTier.SECONDARY
    assert decision is SourceDecision.UNKNOWN


def test_acquisition_is_not_automatically_share_count_changing() -> None:
    assert CorporateActionType.ACQUISITION not in SHARE_COUNT_CHANGING_TYPES
    assert CorporateActionType.SPLIT in SHARE_COUNT_CHANGING_TYPES


def test_dsp_packages_do_not_import_vendors() -> None:
    forbidden = (
        "upstox",
        "gemini",
        "chatgpt",
        "openai",
        "anthropic",
        "claude",
        "yfinance",
        "yahoo",
        "alphavantage",
    )
    roots = [
        _REPO / "packages" / "dsp" / "src",
        _REPO / "packages" / "valuation" / "src",
    ]
    offenders: list[str] = []
    for root in roots:
        for path in root.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                names: list[str] = []
                if isinstance(node, ast.Import):
                    names = [a.name.lower() for a in node.names]
                elif isinstance(node, ast.ImportFrom) and node.module:
                    names = [node.module.lower()]
                for name in names:
                    if any(tok in name for tok in forbidden):
                        offenders.append(f"{path}: {name}")
    assert offenders == []


def test_share_count_uses_quote_field_not_vendor_identity() -> None:
    quote = build_quote_from_mapping(
        symbol="ARBITRARY",
        payload={
            "exchange": "NSE",
            "currency": "INR",
            "current_price": 10.0,
            "shares_outstanding": 42.0,
        },
        provenance=MarketQuoteProvenance(
            provider_id="memory_authenticated_quote",
            provider_name="Memory",
            source_type="licensed_vendor",
            retrieved_at=_FIXED,
            auth_mode="api_key",
        ),
    )
    assert float(quote.shares_outstanding.value) == pytest.approx(42.0)
    assert "upstox" not in quote.provenance.provider_id.lower()
    assert quote.provenance.metadata.get("instrument_key") is None


def test_api_health_pass_in_no_data_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    from api_platform import create_app
    from dsp_platform import PlatformBuilder, PlatformConfiguration

    _strip_investment(monkeypatch)
    monkeypatch.setenv("DSP_ENVIRONMENT", "production")
    monkeypatch.setenv("DSP_INVESTMENT_DATA_PROVIDER", "none")
    monkeypatch.setenv("DSP_JWT_SECRET", "unit-test-production-secret-not-default")
    monkeypatch.setenv("DSP_AUTH_JWT_SECRET", "unit-test-production-secret-not-default")
    monkeypatch.setenv("DSP_INFRA_OFFLINE", "1")
    monkeypatch.setattr(
        "api_platform.api.durable_product_stores.require_durable_product_database",
        lambda database: None,
    )
    platform = (
        PlatformBuilder()
        .with_configuration(PlatformConfiguration(require_analysis_service=False))
        .auto_ready(True)
        .build()
    )
    client = TestClient(create_app(platform=platform, enable_security=False))
    ready = client.get("/api/v1/health/ready")
    assert ready.status_code == 200
    body = ready.json()
    assert body.get("ready") is True
    checks = {c["name"]: c for c in body.get("checks", [])}
    investment = checks["investment_data_provider"]
    assert investment["status"] == "pass"
    assert "UNAVAILABLE" in investment["message"]


def test_analyse_fail_closed_without_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    from api_platform import create_app
    from dsp_platform import PlatformBuilder, PlatformConfiguration

    _strip_investment(monkeypatch)
    monkeypatch.setenv("DSP_ENVIRONMENT", "production")
    monkeypatch.setenv("DSP_INVESTMENT_DATA_PROVIDER", "none")
    monkeypatch.setenv("DSP_JWT_SECRET", "unit-test-production-secret-not-default")
    monkeypatch.setenv("DSP_AUTH_JWT_SECRET", "unit-test-production-secret-not-default")
    monkeypatch.setenv("DSP_INFRA_OFFLINE", "1")
    monkeypatch.setattr(
        "api_platform.api.durable_product_stores.require_durable_product_database",
        lambda database: None,
    )
    platform = (
        PlatformBuilder()
        .with_configuration(PlatformConfiguration(require_analysis_service=False))
        .auto_ready(True)
        .build()
    )
    client = TestClient(create_app(platform=platform, enable_security=False))
    response = client.post(
        "/api/v1/analyse",
        json={"ticker": "ARBITRARY", "company": "Arbitrary Co", "exchange": "NSE"},
    )
    assert response.status_code in {200, 422, 503, 400}
    text = response.text
    assert "Data unavailable" in text or "unavailable" in text.lower()
    assert DATA_UNAVAILABLE.split(".")[0] in text or "unavailable" in text.lower()
