"""Tests for API composition endpoints under recovery and missing-data scenarios."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient

from api_platform import create_app
from copilot.enums import LanguageModelStatus
from copilot.models import LanguageModelRequest, LanguageModelResult
from data_engine import (
    FinancialStatementService,
    InMemoryAuthenticatedQuoteAdapter,
    NullAuthenticatedStatementAdapter,
)
from data_engine.market_quote.adapters import build_quote_from_mapping
from data_engine.market_quote.models import MarketQuoteProvenance
from dsp_platform import (
    PlatformBuilder,
    PlatformConfiguration,
)
from dsp_platform.financial_statements import (
    reset_financial_statement_service_for_tests,
)
from dsp_platform.market_quotes import (
    MarketQuoteService,
    reset_market_quote_service_for_tests,
)
from dsp_platform.recovery import (
    StatementRecoveryService,
    reset_statement_recovery_service_for_tests,
)


class MockLLMAdapter:
    def __init__(
        self,
        response_dict: dict[str, Any] | None,
        status: LanguageModelStatus = LanguageModelStatus.COMPLETE,
    ):
        self._dict = response_dict
        self._status = status

    def is_configured(self) -> bool:
        return True

    def invoke(self, request: LanguageModelRequest) -> LanguageModelResult:
        content = json.dumps(self._dict) if self._dict is not None else ""
        return LanguageModelResult(
            result_id=f"mock-{request.request_id}",
            status=self._status,
            provenance=("mock",),
            narrative_text=content,
        )


@pytest.fixture
def client() -> TestClient:
    platform = (
        PlatformBuilder()
        .with_configuration(PlatformConfiguration(require_analysis_service=False))
        .auto_ready(True)
        .build()
    )
    return TestClient(create_app(platform=platform))


def test_api_quote_succeeds_financials_unavailable_and_unrecoverable(
    client: TestClient, monkeypatch
):
    """Scenario 1: Market quote succeeds, statements unavailable and recovery fails.

    Endpoint must return HTTP 200, financial stage unavailable, valuation degraded (CMP price-only,
    null IV, confidence 0.0), no fabricated valuation, and no secret leakage.
    """
    SECRET = "TEST_SECRET_API_KEY_SCENARIO_1"
    quote_adapter = InMemoryAuthenticatedQuoteAdapter(api_key=SECRET)
    quote = build_quote_from_mapping(
        symbol="TCS",
        payload={
            "exchange": "NSE",
            "currency": "INR",
            "current_price": 3800.0,
            "previous_close": 3750.0,
        },
        provenance=MarketQuoteProvenance(
            provider_id="upstox",
            provider_name="Upstox",
            source_type="licensed_vendor",
            retrieved_at=datetime.now(tz=UTC),
            auth_mode="oauth",
        ),
    )
    quote_adapter.put(quote)
    reset_market_quote_service_for_tests(MarketQuoteService(quote_adapter))
    reset_financial_statement_service_for_tests(
        FinancialStatementService(NullAuthenticatedStatementAdapter())
    )
    # Recovery service where providers fail
    recovery_svc = StatementRecoveryService(
        gemini_adapter=MockLLMAdapter(None, status=LanguageModelStatus.FAILED),
        openai_adapter=MockLLMAdapter(None, status=LanguageModelStatus.FAILED),
    )
    reset_statement_recovery_service_for_tests(recovery_svc)

    try:
        resp = client.post(
            "/api/v1/analyse",
            json={
                "ticker": "TCS",
                "exchange": "NSE",
                "current_market_price": 3800.0,
                "stop_on_stage_failure": False,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is False  # pipeline degraded
        payload = data["payload"]

        # Server valuation exists with price-only signals
        sv = payload.get("server_valuation")
        assert sv is not None
        assert sv["current_market_price"] == 3800.0
        assert sv["intrinsic_value_per_share"] is None
        assert sv["confidence"] == 0.0

        # Stage summaries check
        stages = {s["stage"]: s for s in payload.get("stage_summaries", [])}
        assert "financial" in stages
        assert stages["financial"]["status"] in ("unavailable", "failed")
        assert stages["financial"]["status"] in ("unavailable", "failed")

        assert "valuation" in stages
        assert stages["valuation"]["status"] == "degraded"

        # Verify no secret leaked anywhere in response
        raw_text = resp.text
        assert SECRET not in raw_text
    finally:
        reset_market_quote_service_for_tests(None)
        reset_financial_statement_service_for_tests(None)
        reset_statement_recovery_service_for_tests(None)


def test_api_statement_recovery_succeeds_corroborated(client: TestClient, monkeypatch):
    """Scenario 2: Primary provider missing, but recovery corroborates filing data from Gemini & OpenAI."""
    extracted = {
        "issuer_symbol": "INFY",
        "period_type": "annual",
        "period_end": "2024-03-31",
        "filing_date": "2024-05-15",
        "currency": "INR",
        "statement_basis": "consolidated",
        "unit_scale": "crores",
        "shares_outstanding": 415.0,
        "revenue": 150000.0,
        "cost_of_revenue": 100000.0,
        "gross_profit": 50000.0,
        "operating_income": 30000.0,
        "ebit": 30000.0,
        "ebitda": 35000.0,
        "net_income": 25000.0,
        "eps_basic": 60.0,
        "eps_diluted": 60.0,
        "cash_and_equivalents": 20000.0,
        "current_assets": 45000.0,
        "total_assets": 100000.0,
        "current_liabilities": 20000.0,
        "total_liabilities": 25000.0,
        "total_equity": 75000.0,
        "total_debt": 5000.0,
        "operating_cash_flow": 28000.0,
        "investing_cash_flow": -8000.0,
        "financing_cash_flow": -18000.0,
        "capital_expenditures": 5000.0,
        "free_cash_flow": 23000.0,
    }

    quote_adapter = InMemoryAuthenticatedQuoteAdapter()
    quote = build_quote_from_mapping(
        symbol="INFY",
        payload={
            "exchange": "NSE",
            "currency": "INR",
            "current_price": 1450.0,
            "previous_close": 1440.0,
        },
        provenance=MarketQuoteProvenance(
            provider_id="upstox",
            provider_name="Upstox",
            source_type="licensed_vendor",
            retrieved_at=datetime.now(tz=UTC),
            auth_mode="oauth",
        ),
    )
    quote_adapter.put(quote)
    reset_market_quote_service_for_tests(MarketQuoteService(quote_adapter))
    reset_financial_statement_service_for_tests(
        FinancialStatementService(NullAuthenticatedStatementAdapter())
    )

    # Provide mocked filing text
    import dsp_platform.filings

    monkeypatch.setattr(
        dsp_platform.filings,
        "get_authenticated_filings",
        lambda sym, exchange=None, limit=10: {
            "filings": [
                {
                    "filing_id": "FILING-INFY-2024",
                    "title": "Infosys FY24 Annual Report",
                    "url": "https://example.com/infy-fy24.pdf",
                    "filed_at": "2024-05-15",
                    "period_of_report": "2024-03-31",
                    "content": "INFOSYS ANNUAL REPORT 2024 CONSOLIDATED STATEMENTS...",
                }
            ]
        },
    )

    recovery_svc = StatementRecoveryService(
        gemini_adapter=MockLLMAdapter(extracted),
        openai_adapter=MockLLMAdapter(extracted),
    )
    reset_statement_recovery_service_for_tests(recovery_svc)

    try:
        resp = client.post(
            "/api/v1/analyse",
            json={
                "ticker": "INFY",
                "exchange": "NSE",
                "current_market_price": 1450.0,
                "stop_on_stage_failure": False,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        payload = data["payload"]

        # Financial stage succeeded using recovered statements
        stages = {s["stage"]: s for s in payload.get("stage_summaries", [])}
        assert stages["financial"]["status"] == "succeeded"
        assert stages["financial"]["has_result"] is True
    finally:
        reset_market_quote_service_for_tests(None)
        reset_financial_statement_service_for_tests(None)
        reset_statement_recovery_service_for_tests(None)


def test_api_conflicting_extractions_fails_closed_no_secret_leak(
    client: TestClient, monkeypatch
):
    """Scenario 3: Gemini and OpenAI provide irreconcilable conflicting values (>5% conflict).

    Recovery fails closed, valuation does not average or fabricate, returns degraded response.
    """
    SECRET = "TOP_SECRET_ORCHESTRATION_TOKEN_999"
    g_data = {
        "issuer_symbol": "WIPRO",
        "period_end": "2024-03-31",
        "filing_date": "2024-05-20",
        "currency": "INR",
        "unit_scale": "actual",
        "revenue": 1000000.0,
        "net_income": 200000.0,
        "shares_outstanding": 50000.0,
    }
    o_data = {
        "issuer_symbol": "WIPRO",
        "period_end": "2024-03-31",
        "filing_date": "2024-05-20",
        "currency": "INR",
        "unit_scale": "actual",
        "revenue": 1500000.0,  # 50% conflict
        "net_income": 350000.0,  # conflict
        "shares_outstanding": 90000.0,  # conflict
    }

    import dsp_platform.filings

    monkeypatch.setattr(
        dsp_platform.filings,
        "get_authenticated_filings",
        lambda sym, exchange=None, limit=10: {
            "filings": [
                {
                    "filing_id": "FILING-WIPRO",
                    "title": "Wipro FY24",
                    "content": f"Wipro report text with token {SECRET}",
                }
            ]
        },
    )

    quote_adapter = InMemoryAuthenticatedQuoteAdapter(api_key=SECRET)
    quote = build_quote_from_mapping(
        symbol="WIPRO",
        payload={
            "exchange": "NSE",
            "currency": "INR",
            "current_price": 520.0,
        },
        provenance=MarketQuoteProvenance(
            provider_id="upstox",
            provider_name="Upstox",
            source_type="licensed_vendor",
            retrieved_at=datetime.now(tz=UTC),
            auth_mode="oauth",
        ),
    )
    quote_adapter.put(quote)
    reset_market_quote_service_for_tests(MarketQuoteService(quote_adapter))
    reset_financial_statement_service_for_tests(
        FinancialStatementService(NullAuthenticatedStatementAdapter())
    )

    recovery_svc = StatementRecoveryService(
        gemini_adapter=MockLLMAdapter(g_data),
        openai_adapter=MockLLMAdapter(o_data),
    )
    reset_statement_recovery_service_for_tests(recovery_svc)

    try:
        resp = client.post(
            "/api/v1/analyse",
            json={
                "ticker": "WIPRO",
                "exchange": "NSE",
                "current_market_price": 520.0,
                "stop_on_stage_failure": False,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is False

        # Financial stage unavailable due to conflict
        stages = {s["stage"]: s for s in data["payload"].get("stage_summaries", [])}
        assert stages["financial"]["status"] in ("unavailable", "failed")

        # Valuation is degraded (CMP price-only)
        assert stages["valuation"]["status"] == "degraded"
        assert data["payload"]["server_valuation"]["intrinsic_value_per_share"] is None
        assert data["payload"]["server_valuation"]["confidence"] == 0.0

        # Secret token is not leaked
        assert SECRET not in resp.text
    finally:
        reset_market_quote_service_for_tests(None)
        reset_financial_statement_service_for_tests(None)
        reset_statement_recovery_service_for_tests(None)
