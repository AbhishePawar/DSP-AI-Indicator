"""Ticker-only /analyse HTTP contract — server-side authenticated data path.

Proves the production smoke-test body::

    {"ticker": "TCS", "company": "...", "exchange": "NSE"}

is accepted past Pydantic / analyse validation, reaches
``compose_intelligence`` with ``financial_statements=None`` and
``exchange="NSE"``, and that authenticated statements/quote (not client FS)
drive the canonical pipeline. Does not redesign Upstox adapters.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api_platform.api.app import create_app
from api_platform.api.composition_schemas import AnalyseRequest
from api_platform.api.validation import validate_analyse_request
from data_engine import (
    FinancialStatementService,
    InMemoryAuthenticatedQuoteAdapter,
    MarketQuoteService,
    build_quote_from_mapping,
    build_statements_from_mapping,
)
from data_engine.financial_statement.models import (
    FinancialStatementProvenance,
    utc_now,
)
from data_engine.financial_statement.service import (
    FinancialStatementPort,
    StatementProviderHealth,
)
from data_engine.market_quote.models import MarketQuoteProvenance
from dsp_platform import (
    CompositionRequest,
    PlatformBuilder,
    PlatformConfiguration,
    PlatformOrchestrator,
    build_composition_request,
)
from dsp_platform.financial_statements import (
    reset_financial_statement_service_for_tests,
)
from dsp_platform.market_quotes import reset_market_quote_service_for_tests

TICKER = "TCS"
EXCHANGE = "NSE"
_TICKER_ONLY_BODY = {
    "ticker": TICKER,
    "company": "Tata Consultancy Services",
    "exchange": EXCHANGE,
}


def _seed_bundle(*, revenue: float = 500.0):
    return build_statements_from_mapping(
        symbol=TICKER,
        payload={
            "identity": {
                "symbol": TICKER,
                "exchange": EXCHANGE,
                "company_name": "Tata Consultancy Services",
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
                        "revenue": revenue,
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
                        "revenue": revenue * 0.9,
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
        provenance=FinancialStatementProvenance(
            provider_id="ticker_only_auth_statements",
            provider_name="Ticker-Only Auth Statements",
            source_type="licensed_vendor",
            retrieved_at=utc_now(),
            auth_mode="api_key",
        ),
    )


def _seed_quote():
    return build_quote_from_mapping(
        symbol=TICKER,
        payload={
            "exchange": EXCHANGE,
            "currency": "USD",
            "current_price": 8.0,
            "previous_close": 8.0,
            "market_cap": 800.0,
            "shares_outstanding": 100.0,
        },
        provenance=MarketQuoteProvenance(
            provider_id="memory_authenticated_quote",
            provider_name="Memory Quote",
            source_type="licensed_vendor",
            retrieved_at=utc_now(),
            auth_mode="api_key",
        ),
    )


class _ExchangeGatedStatementAdapter(FinancialStatementPort):
    def __init__(self, *, revenue: float = 500.0, fail: bool = False) -> None:
        self._bundle = _seed_bundle(revenue=revenue)
        self._fail = fail
        self.exchanges_seen: list[str | None] = []

    @property
    def provider_id(self) -> str:
        return "ticker_only_auth_statements"

    def resolve_company(self, instrument):
        if self._fail:
            return None
        return self._bundle.identity if instrument.exchange == EXCHANGE else None

    def get_statements(self, query):
        self.exchanges_seen.append(query.instrument.exchange)
        if self._fail or query.instrument.exchange != EXCHANGE:
            return None
        return self._bundle

    def health(self) -> StatementProviderHealth:
        return StatementProviderHealth(
            provider_id=self.provider_id,
            healthy=not self._fail,
            authenticated=True,
            detail="test",
        )


@pytest.fixture
def auth_services(monkeypatch):
    """Inject authenticated statement/quote services (non-production app boot)."""
    # Keep create_app() off the P1-03 production connector gate; pipeline
    # still uses the injected authenticated services below.
    monkeypatch.delenv("DSP_ENVIRONMENT", raising=False)
    stmt = _ExchangeGatedStatementAdapter(revenue=500.0)
    quote = InMemoryAuthenticatedQuoteAdapter(api_key="test-key")
    quote.put(_seed_quote())
    reset_financial_statement_service_for_tests(FinancialStatementService(stmt))
    reset_market_quote_service_for_tests(MarketQuoteService(quote))
    yield stmt
    reset_financial_statement_service_for_tests(None)
    reset_market_quote_service_for_tests(None)


@pytest.fixture
def production_auth_services(monkeypatch):
    """Production fail-closed semantics with a working auth bundle."""
    monkeypatch.setenv("DSP_ENVIRONMENT", "production")
    stmt = _ExchangeGatedStatementAdapter(revenue=500.0)
    quote = InMemoryAuthenticatedQuoteAdapter(api_key="test-key")
    quote.put(_seed_quote())
    reset_financial_statement_service_for_tests(FinancialStatementService(stmt))
    reset_market_quote_service_for_tests(MarketQuoteService(quote))
    yield stmt
    reset_financial_statement_service_for_tests(None)
    reset_market_quote_service_for_tests(None)


@pytest.fixture
def failing_auth_services(monkeypatch):
    monkeypatch.setenv("DSP_ENVIRONMENT", "production")
    stmt = _ExchangeGatedStatementAdapter(fail=True)
    quote = InMemoryAuthenticatedQuoteAdapter(api_key="test-key")
    # No quote seeded — authenticated path cannot build a bundle.
    reset_financial_statement_service_for_tests(FinancialStatementService(stmt))
    reset_market_quote_service_for_tests(MarketQuoteService(quote))
    yield stmt
    reset_financial_statement_service_for_tests(None)
    reset_market_quote_service_for_tests(None)


def _platform_client() -> TestClient:
    platform = (
        PlatformBuilder()
        .with_configuration(PlatformConfiguration(require_analysis_service=False))
        .auto_ready(True)
        .build()
    )
    return TestClient(create_app(platform=platform))


class TestTickerOnlyHttpContract:
    """A — Pydantic must not require body.financial_statements."""

    def test_analyse_request_accepts_ticker_only(self) -> None:
        body = AnalyseRequest.model_validate(_TICKER_ONLY_BODY)
        assert body.ticker == TICKER
        assert body.exchange == EXCHANGE
        assert body.financial_statements is None
        assert validate_analyse_request(body) == []

    def test_post_analyse_not_rejected_for_missing_financial_statements(
        self, auth_services
    ) -> None:
        client = _platform_client()
        response = client.post("/api/v1/analyse", json=_TICKER_ONLY_BODY)
        text = response.text
        assert "body.financial_statements: Field required" not in text
        assert "financial_statements: Field required" not in text
        # Must get past request validation into composition.
        validation_errors = response.json().get("validation_errors", [])
        assert response.status_code != 422 or (
            "Field required" not in text
            and "financial_statements" not in str(validation_errors)
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload.get("ok") is True or (
            payload.get("capability") == "compose_intelligence"
        )


class TestRouterCompositionHandoff:
    """B — router passes financial_statements=None and exchange=NSE."""

    def test_compose_intelligence_receives_none_fs_and_nse(
        self, auth_services, monkeypatch
    ) -> None:
        calls: list[CompositionRequest] = []
        platform = (
            PlatformBuilder()
            .with_configuration(PlatformConfiguration(require_analysis_service=False))
            .auto_ready(True)
            .build()
        )
        original = platform.compose_intelligence

        def _spy(request: CompositionRequest):  # type: ignore[no-untyped-def]
            calls.append(request)
            return original(request)

        monkeypatch.setattr(platform, "compose_intelligence", _spy)
        client = TestClient(create_app(platform=platform))
        response = client.post("/api/v1/analyse", json=_TICKER_ONLY_BODY)
        assert response.status_code == 200
        assert len(calls) == 1
        assert calls[0].financial_statements is None
        assert calls[0].exchange == EXCHANGE
        assert calls[0].ticker == TICKER


class TestAuthenticatedServerSideData:
    """C — ticker-only reaches auth preload; statements/quote populate pipeline."""

    def test_ticker_only_composition_uses_authenticated_bundle(
        self, auth_services
    ) -> None:
        request = build_composition_request(
            ticker=TICKER, company="Tata Consultancy Services", exchange=EXCHANGE
        )
        assert request.financial_statements is None
        assert request.exchange == EXCHANGE
        result = PlatformOrchestrator(platform_version="test").execute(request)
        assert result.ok is True
        assert result.financial_analysis is not None
        assert (result.valuation_signals or result.valuation) is not None
        assert EXCHANGE in auth_services.exchanges_seen


class TestAuthAuthorityOverClientFs:
    """D — authenticated statements remain authoritative when client FS exists."""

    def test_auth_bundle_preferred_over_client_statements(
        self, production_auth_services
    ) -> None:
        # Client FS with a deliberately different revenue fingerprint.
        client_fs = {
            "period": {
                "period_type": "annual",
                "period_end": "2024-12-31",
                "fiscal_year": 2024,
                "currency": "USD",
            },
            "income_statement": {
                "revenue": 1.0,  # not the auth seed (500.0)
                "net_income": 1.0,
                "weighted_shares": 100.0,
                "eps": 0.01,
            },
            "balance_sheet": {
                "total_assets": 10.0,
                "total_liabilities": 5.0,
                "equity": 5.0,
                "total_equity": 5.0,
            },
            "cash_flow": {"operating_cash_flow": 1.0, "free_cash_flow": 1.0},
            "statement_metadata": {},
        }
        request = build_composition_request(
            ticker=TICKER,
            exchange=EXCHANGE,
            financial_statements=client_fs,
            current_market_price=1.0,
        )
        result = PlatformOrchestrator(platform_version="test").execute(request)
        assert result.ok is True
        assert result.financial_analysis is not None
        financial_outcome = next(
            (o for o in result.stages if o.stage == "financial"),
            None,
        )
        assert financial_outcome is not None
        warnings = list(financial_outcome.warnings or ())
        assert any("authenticated server statements" in w for w in warnings)
        assert EXCHANGE in production_auth_services.exchanges_seen


class TestProductionFailClosed:
    """E — auth failure remains unavailable; no silent Yahoo/FRED fallback."""

    def test_production_auth_failure_fails_closed(self, failing_auth_services) -> None:
        request = build_composition_request(ticker=TICKER, exchange=EXCHANGE)
        result = PlatformOrchestrator(platform_version="test").execute(request)
        assert result.ok is False
        assert result.metadata.failed_stage == "financial"
        errors = " ".join(result.errors or []).lower()
        assert "data unavailable" in errors or "unavailable" in errors
        assert "yahoo" not in errors
        assert "fred" not in errors


class TestClientFsPathPreserved:
    """CLIENT-FS PATH — price / income still required when FS is supplied."""

    def test_client_fs_still_requires_market_price(self) -> None:
        body = AnalyseRequest.model_validate(
            {
                "ticker": "ACM",
                "financial_statements": {
                    "period": {
                        "period_type": "annual",
                        "period_end": "2024-12-31",
                    },
                    "income_statement": {"revenue": 100.0, "net_income": 10.0},
                },
            }
        )
        errors = validate_analyse_request(body)
        assert any("current_market_price" in e for e in errors)

    def test_ticker_only_still_rejects_client_intrinsic_value(self) -> None:
        body = AnalyseRequest.model_validate(
            {
                **_TICKER_ONLY_BODY,
                "valuation_signals": {"intrinsic_value_per_share": 99.0},
            }
        )
        errors = validate_analyse_request(body)
        assert any("intrinsic_value_per_share" in e for e in errors)
        assert body.financial_statements is None
