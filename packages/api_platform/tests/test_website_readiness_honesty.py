"""Website readiness — server valuation surface + research auth gates."""

from __future__ import annotations

from auth_test_helpers import bearer_headers, register_user
from fastapi.testclient import TestClient

from api_platform import create_app
from data_engine import (
    FinancialStatementService,
    InMemoryAuthenticatedQuoteAdapter,
    InMemoryAuthenticatedStatementAdapter,
    InMemoryShareCountAdapter,
    MarketQuoteService,
    ShareCountService,
)
from dsp_platform import PlatformBuilder, PlatformConfiguration
from dsp_platform.financial_statements import (
    reset_financial_statement_service_for_tests,
)
from dsp_platform.market_quotes import reset_market_quote_service_for_tests
from dsp_platform.p109_e2e_fixture import (
    P109_EVIDENCE_CLASS,
    P109_FIXTURE_TICKER,
    build_p109_quote,
    build_p109_share_count,
    build_p109_statements,
)
from dsp_platform.share_counts import reset_share_count_service_for_tests


def test_analyse_payload_exposes_server_valuation() -> None:
    quote_adapter = InMemoryAuthenticatedQuoteAdapter(api_key="ux-fixture-key")
    stmt_adapter = InMemoryAuthenticatedStatementAdapter(api_key="ux-fixture-key")
    quote_adapter.put(build_p109_quote())
    stmt_adapter.put(build_p109_statements())
    share_adapter = InMemoryShareCountAdapter(api_key="ux-fixture-key")
    share_adapter.put(build_p109_share_count())
    reset_market_quote_service_for_tests(MarketQuoteService(quote_adapter))
    reset_financial_statement_service_for_tests(
        FinancialStatementService(stmt_adapter)
    )
    reset_share_count_service_for_tests(ShareCountService(share_adapter))
    try:
        platform = (
            PlatformBuilder()
            .with_configuration(PlatformConfiguration(require_analysis_service=False))
            .auto_ready(True)
            .build()
        )
        client = TestClient(create_app(platform=platform))
        register_user(client, user_id="ux-iv", username="uxiv")
        headers = bearer_headers(client, username="uxiv")

        ticker = P109_FIXTURE_TICKER
        quote = client.get(f"/api/v1/market/quote?symbol={ticker}", headers=headers)
        assert quote.status_code == 200, quote.text
        price = quote.json()["fields"]["current_price"]
        stmts = client.get(
            f"/api/v1/fundamentals/statements?symbol={ticker}&limit=1",
            headers=headers,
        )
        assert stmts.status_code == 200, stmts.text
        latest = stmts.json()["periods"][0]
        body = {
            "ticker": ticker,
            "exchange": "NYSE",
            "company": "DSP Fixture Corp",
            "current_market_price": float(price),
            "financial_statements": {
                "period": {
                    "period_type": latest["period_type"],
                    "period_end": latest["period_end"],
                    "fiscal_year": latest.get("fiscal_year"),
                    "currency": latest.get("reporting_currency") or "USD",
                },
                "income_statement": dict(latest.get("income_statement") or {}),
                "balance_sheet": dict(latest.get("balance_sheet") or {}),
                "cash_flow": dict(latest.get("cash_flow") or {}),
                "statement_metadata": {
                    "source": "authenticated_fundamentals",
                    "evidence_class": P109_EVIDENCE_CLASS,
                    "unit_scale": latest.get("unit_scale") or "actual",
                    "statement_basis": latest.get("statement_basis") or "consolidated",
                },
            },
        }
        response = client.post("/api/v1/analyse", json=body, headers=headers)
        assert response.status_code == 200, response.text
        payload = response.json()["payload"]
        assert "server_valuation" in payload
        assert payload["server_valuation"]["authority"] == "server"
        assert "intrinsic_value_per_share" in payload["server_valuation"]
        assert payload["server_valuation"].get("current_market_price") is not None
    finally:
        reset_market_quote_service_for_tests(None)
        reset_financial_statement_service_for_tests(None)
        reset_share_count_service_for_tests(None)


def test_research_archive_get_requires_auth() -> None:
    platform = (
        PlatformBuilder()
        .with_configuration(PlatformConfiguration(require_analysis_service=False))
        .auto_ready(True)
        .build()
    )
    client = TestClient(create_app(platform=platform))
    denied = client.get("/api/v1/research/archive/snapshots/does-not-exist")
    assert denied.status_code == 401
