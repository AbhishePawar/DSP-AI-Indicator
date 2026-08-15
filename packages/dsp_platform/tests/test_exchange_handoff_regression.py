"""Regression: public ``exchange`` must reach the authenticated statement
provider (Upstox U1 resolver ``preferred_exchange``).

Before the fix, ``AnalyseRequest.exchange`` was dropped at
``build_composition_request`` / ``CompositionRequest`` / the pipeline preloader,
so ``load_authenticated_valuation_bundle`` always queried with
``exchange=None``. For a provider that requires the exchange to disambiguate
(Upstox dual-listed NSE/BSE), that yields no statements and the ``financial``
stage fails closed with ``Data unavailable. (financial statements)``.

These tests use an exchange-gated statement provider to prove:
  * FIX  — with ``exchange`` threaded, the provider receives it and the full
    pipeline (financial → valuation → domains → recommendation → committee)
    succeeds.
  * BUG  — without an exchange, the provider is queried with ``None`` and the
    financial stage fails closed (reproducing the production symptom).
"""

from __future__ import annotations

import pytest

from data_engine import (
    FinancialStatementService,
    InMemoryAuthenticatedQuoteAdapter,
    MarketQuoteService,
    build_quote_from_mapping,
    build_statements_from_mapping,
)
from data_engine.financial_statement.service import (
    FinancialStatementPort,
    StatementProviderHealth,
)
from data_engine.financial_statement.models import (
    FinancialStatementProvenance,
    utc_now,
)
from data_engine.market_quote.models import MarketQuoteProvenance
from dsp_platform import CompositionRequest, PlatformOrchestrator, build_composition_request
from dsp_platform.financial_statements import reset_financial_statement_service_for_tests
from dsp_platform.market_quotes import reset_market_quote_service_for_tests

TICKER = "TCS"
REQUIRED_EXCHANGE = "NSE"


def _seed_bundle():
    return build_statements_from_mapping(
        symbol=TICKER,
        payload={
            "identity": {
                "symbol": TICKER,
                "exchange": REQUIRED_EXCHANGE,
                "company_name": "Test Co",
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
        provenance=FinancialStatementProvenance(
            provider_id="exchange_gated_statements",
            provider_name="Exchange-Gated Statements",
            source_type="licensed_vendor",
            retrieved_at=utc_now(),
            auth_mode="api_key",
        ),
    )


def _seed_quote():
    return build_quote_from_mapping(
        symbol=TICKER,
        payload={
            "exchange": REQUIRED_EXCHANGE,
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
    """Returns statements only when queried with the required exchange."""

    def __init__(self) -> None:
        self._bundle = _seed_bundle()
        self.exchanges_seen: list[str | None] = []

    @property
    def provider_id(self) -> str:
        return "exchange_gated_statements"

    def resolve_company(self, instrument):
        return self._bundle.identity if instrument.exchange == REQUIRED_EXCHANGE else None

    def get_statements(self, query):
        self.exchanges_seen.append(query.instrument.exchange)
        if query.instrument.exchange != REQUIRED_EXCHANGE:
            return None  # provider cannot disambiguate without the exchange
        return self._bundle

    def health(self) -> StatementProviderHealth:
        return StatementProviderHealth(
            provider_id=self.provider_id,
            healthy=True,
            authenticated=True,
            detail="test",
        )


@pytest.fixture
def gated_services(monkeypatch):
    # Production semantics: client financial_statements are ignored; the
    # authenticated provider is authoritative and required.
    monkeypatch.setenv("DSP_ENVIRONMENT", "production")
    stmt_adapter = _ExchangeGatedStatementAdapter()
    quote_adapter = InMemoryAuthenticatedQuoteAdapter(api_key="test-key")
    quote_adapter.put(_seed_quote())
    reset_financial_statement_service_for_tests(FinancialStatementService(stmt_adapter))
    reset_market_quote_service_for_tests(MarketQuoteService(quote_adapter))
    yield stmt_adapter
    reset_financial_statement_service_for_tests(None)
    reset_market_quote_service_for_tests(None)


def test_build_composition_request_threads_exchange():
    """The public adapter now carries ``exchange`` onto CompositionRequest."""
    req = build_composition_request(ticker="tcs", exchange="nse")
    assert isinstance(req, CompositionRequest)
    assert req.exchange == "NSE"


def test_exchange_threaded_makes_financial_stage_succeed(gated_services):
    """FIX: with exchange threaded, the full canonical pipeline succeeds."""
    stmt_adapter = gated_services
    request = CompositionRequest(ticker=TICKER, exchange=REQUIRED_EXCHANGE)
    result = PlatformOrchestrator(platform_version="test").execute(request)

    # Provider was queried WITH the exchange (the dropped-handoff is fixed).
    assert REQUIRED_EXCHANGE in stmt_adapter.exchanges_seen
    assert None not in stmt_adapter.exchanges_seen

    assert result.ok is True
    assert result.metadata.failed_stage is None
    assert result.financial_analysis is not None
    assert (result.valuation_signals or result.valuation) is not None
    assert result.economic_moat is not None
    assert result.financial_strength is not None
    assert result.business_quality is not None
    assert result.investment_recommendation is not None
    assert result.investment_committee is not None


def test_missing_exchange_reproduces_financial_failure(gated_services):
    """BUG repro: no exchange → provider queried with None → fail closed."""
    stmt_adapter = gated_services
    request = CompositionRequest(ticker=TICKER, exchange=None)
    result = PlatformOrchestrator(platform_version="test").execute(request)

    assert None in stmt_adapter.exchanges_seen
    assert result.ok is False
    assert result.metadata.failed_stage == "financial"
    assert any("Data unavailable" in e for e in result.errors)
    assert result.investment_recommendation is None
