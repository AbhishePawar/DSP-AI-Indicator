"""Integration tests for Research Orchestrator and Upstox market data in /api/v1/analyse."""

from __future__ import annotations

import json
from decimal import Decimal
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from api_platform import create_app
from contracts.domain.instrument import Instrument
from contracts.enums import AssetClass
from data_engine.market_quote.upstox_adapter import UpstoxQuoteAdapter
from data_engine.upstox.instrument_resolver import (
    UpstoxInstrumentRecord,
    UpstoxInstrumentResolver,
)
from dsp_platform import PlatformBuilder, PlatformConfiguration
from llm_adapters import (
    PublicDecisionPack,
    UserResearchRequest,
)
from llm_adapters.orchestrator import PRIVATE_PROMPT_CANARY
from llm_adapters.privacy_boundary import assert_no_private_leakage


class MockOrchestrator:
    """Mock orchestrator for testing API platform routing."""

    def __init__(
        self,
        public_pack: PublicDecisionPack | None = None,
        should_fail: bool = False,
    ) -> None:
        self.public_pack = public_pack or PublicDecisionPack(
            recommendation="BUY",
            valuation="Undervalued relative to intrinsic value per share of ₹1150 vs ₹950",
            analysis="Strong economic moat with robust balance sheet and consistent returns.",
            risks=["Currency volatility", "Commodity input costs"],
            evidence_citations=["dsp.valuation:1150.0", "dsp.economic_moat:Wide"],
            confidence=0.88,
            limitations=["Based on latest annual filings"],
        )
        self.should_fail = should_fail
        self.calls: list[UserResearchRequest] = []

    def run(self, request: UserResearchRequest) -> Any:
        self.calls.append(request)
        if self.should_fail:
            raise RuntimeError("Internal provider failure")
        outcome = MagicMock()
        outcome.to_public.return_value = self.public_pack
        return outcome


def _sample_analyse_body(**overrides: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "ticker": "TATAMOTORS",
        "exchange": "NSE",
        "company": "Tata Motors Limited",
        "current_market_price": 950.0,
        "financial_statements": {
            "period": {
                "period_type": "annual",
                "period_end": "2025-03-31",
                "fiscal_year": 2025,
                "currency": "INR",
            },
            "income_statement": {
                "revenue": 435000.0,
                "cogs": 260000.0,
                "gross_profit": 175000.0,
                "ebit": 42000.0,
                "ebitda": 58000.0,
                "interest_expense": 9000.0,
                "pretax_income": 33000.0,
                "tax": 8000.0,
                "net_income": 25000.0,
                "weighted_shares": 3800.0,
                "eps": 6.58,
            },
            "balance_sheet": {
                "cash": 40000.0,
                "short_term_investments": 10000.0,
                "accounts_receivable": 22000.0,
                "inventory": 45000.0,
                "current_assets": 125000.0,
                "ppe": 140000.0,
                "goodwill": 8000.0,
                "intangibles": 12000.0,
                "total_assets": 340000.0,
                "accounts_payable": 75000.0,
                "short_term_debt": 25000.0,
                "current_liabilities": 120000.0,
                "long_term_debt": 60000.0,
                "total_liabilities": 200000.0,
                "retained_earnings": 80000.0,
                "equity": 140000.0,
                "total_equity": 140000.0,
            },
            "cash_flow": {
                "operating_cash_flow": 48000.0,
                "capex": -22000.0,
                "free_cash_flow": 26000.0,
                "dividends_paid": -4000.0,
                "share_buybacks": 0.0,
                "debt_issued": 5000.0,
                "debt_repaid": -12000.0,
            },
            "statement_metadata": {"unit_scale": "crores"},
        },
    }
    body.update(overrides)
    return body


def test_analyse_deterministic_fallback_when_orchestrator_absent():
    """When research_orchestrator is None, /analyse falls back cleanly to deterministic output."""
    platform = (
        PlatformBuilder()
        .with_configuration(PlatformConfiguration(require_analysis_service=False))
        .auto_ready(True)
        .build()
    )
    app = create_app(platform=platform)
    app.state.api.research_orchestrator = None
    client = TestClient(app)

    body = _sample_analyse_body()
    resp = client.post("/api/v1/analyse", json=body)
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    payload = data["payload"]

    # Deterministic output must be present
    assert payload.get("has_valuation") is True
    assert payload.get("has_economic_moat") is True
    assert "buffett_authority" in payload
    assert "server_valuation" in payload

    # research_report must be None when orchestrator is not configured
    assert payload["research_report"] is None


def test_analyse_graceful_degradation_when_orchestrator_raises():
    """When orchestrator raises an exception, /analyse must degrade gracefully without 500."""
    platform = (
        PlatformBuilder()
        .with_configuration(PlatformConfiguration(require_analysis_service=False))
        .auto_ready(True)
        .build()
    )
    app = create_app(platform=platform)
    app.state.api.research_orchestrator = MockOrchestrator(should_fail=True)
    client = TestClient(app)

    body = _sample_analyse_body()
    resp = client.post("/api/v1/analyse", json=body)
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    payload = data["payload"]

    # Deterministic output remains intact
    assert payload.get("has_valuation") is True
    assert payload["research_report"] is None
    # Limitations should explain unavailable status without leaking internal exception trace
    assert any("Research orchestrator unavailable" in lim for lim in payload.get("limitations", []))


def test_analyse_configured_orchestration_populates_research_report():
    """When orchestrator is configured, /analyse populates public research_report."""
    platform = (
        PlatformBuilder()
        .with_configuration(PlatformConfiguration(require_analysis_service=False))
        .auto_ready(True)
        .build()
    )
    app = create_app(platform=platform)
    mock_orch = MockOrchestrator()
    app.state.api.research_orchestrator = mock_orch
    client = TestClient(app)

    body = _sample_analyse_body()
    resp = client.post("/api/v1/analyse", json=body)
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    payload = data["payload"]

    assert len(mock_orch.calls) == 1
    assert mock_orch.calls[0].symbol == "TATAMOTORS"
    assert mock_orch.calls[0].exchange == "NSE"

    report = payload["research_report"]
    assert report is not None
    assert report["recommendation"] == "BUY"
    assert "intrinsic value" in report["valuation"]
    assert "Strong economic moat" in report["analysis"]
    assert report["risks"] == ["Currency volatility", "Commodity input costs"]
    assert report["evidence_citations"] == ["dsp.valuation:1150.0", "dsp.economic_moat:Wide"]
    assert report["confidence"] == 0.88


def test_analyse_research_report_preserves_privacy_boundary():
    """Ensure no private prompt, canary, provider details, or secrets leak into response."""
    platform = (
        PlatformBuilder()
        .with_configuration(PlatformConfiguration(require_analysis_service=False))
        .auto_ready(True)
        .build()
    )
    app = create_app(platform=platform)
    mock_orch = MockOrchestrator()
    app.state.api.research_orchestrator = mock_orch
    client = TestClient(app)

    body = _sample_analyse_body()
    resp = client.post("/api/v1/analyse", json=body)
    assert resp.status_code == 200
    data = resp.json()
    payload = data["payload"]

    report = payload["research_report"]
    assert report is not None
    assert_no_private_leakage(report)

    # Response JSON must not contain internal canaries or prompt tokens
    raw_text = resp.text
    assert PRIVATE_PROMPT_CANARY not in raw_text
    assert "system_prompt" not in raw_text
    assert "gemini_api_key" not in raw_text
    assert "openai_api_key" not in raw_text
    assert "upstox_access_token" not in raw_text


def test_end_to_end_upstox_to_research_report_flow():
    """End-to-end mocked test following an asset query through:

    1. Upstox dynamic instrument resolution
    2. Upstox V3 Market Quote retrieval
    3. Provenance validation
    4. Deterministic DSP analysis pipeline
    5. Research Orchestrator AI synthesis
    6. Final verified research report
    """
    # 1. Asset Query & Upstox Instrument Resolution
    query_ticker = "TATAMOTORS"
    query_exchange = "NSE"
    instrument = Instrument(
        symbol=query_ticker,
        exchange=query_exchange,
        asset_class=AssetClass.EQUITY,
        currency="INR",
    )

    record = UpstoxInstrumentRecord(
        instrument_key="NSE_EQ|INE155A01022",
        symbol="TATAMOTORS",
        name="Tata Motors Limited",
        exchange="NSE",
        instrument_type="EQUITY",
        isin="INE155A01022",
        segment="NSE_EQ",
    )
    resolver = UpstoxInstrumentResolver(records=[record])
    resolution = resolver.resolve(instrument)

    assert resolution.is_resolved is True
    assert resolution.instrument_key == "NSE_EQ|INE155A01022"
    assert resolution.isin == "INE155A01022"

    # 2. Upstox V3 Market Quote Retrieval (mocked official V3 payload)
    adapter = UpstoxQuoteAdapter(access_token="mock_upstox_token", resolver=resolver)

    mock_v3_response = {
        "status": "success",
        "data": {
            "NSE_EQ:TATAMOTORS": {
                "last_price": 950.0,
                "volume": 12500000,
                "average_price": 948.5,
                "net_change": 12.5,
                "prev_close_price": 937.5,
                "year_high": 1065.6,
                "year_low": 650.0,
                "timestamp": "2026-04-18T15:30:00+05:30",
                "ohlc": {
                    "open": 940.0,
                    "high": 955.0,
                    "low": 935.0,
                    "close": 950.0,
                    "volume": 12500000,
                    "ts": "2026-04-18T15:30:00+05:30",
                },
            }
        },
    }

    def mock_urlopen(req: Any, timeout: float = 10.0) -> Any:
        # Verify V3 endpoint, query params, and Authorization header
        assert req.full_url.startswith("https://api.upstox.com/v3/market-quote/quotes")
        assert "instrument_key=NSE_EQ%7CINE155A01022" in req.full_url
        assert req.get_header("Authorization") == "Bearer mock_upstox_token"
        assert req.get_header("Accept") == "application/json"

        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(mock_v3_response).encode("utf-8")
        mock_resp.status = 200
        mock_resp.__enter__.return_value = mock_resp
        mock_resp.__exit__.return_value = False
        return mock_resp

    with patch("urllib.request.urlopen", side_effect=mock_urlopen):
        quote = adapter.get_quote(instrument)

    # 3. Provenance Validation
    assert quote.symbol == "TATAMOTORS"
    assert quote.exchange == "NSE"
    assert quote.currency == "INR"
    assert quote.current_price.value == Decimal("950.0")
    assert quote.open.value == Decimal("940.0")
    assert quote.high.value == Decimal("955.0")
    assert quote.low.value == Decimal("935.0")
    assert quote.volume.value == Decimal("12500000")

    provenance = quote.provenance
    assert provenance.provider_id == "upstox"
    assert provenance.source_type == "licensed_vendor"
    assert provenance.auth_mode == "oauth_bearer"
    assert provenance.metadata["instrument_key"] == "NSE_EQ|INE155A01022"
    assert provenance.as_of is not None

    # 4. Deterministic Analysis Pipeline via POST /api/v1/analyse
    platform = (
        PlatformBuilder()
        .with_configuration(PlatformConfiguration(require_analysis_service=False))
        .auto_ready(True)
        .build()
    )
    app = create_app(platform=platform)

    # 5. Connect Research Orchestrator with evidence-grounded synthesis
    custom_public_pack = PublicDecisionPack(
        recommendation="BUY",
        valuation=f"Market price ₹{quote.current_price.value} offers attractive entry against DCF intrinsic value.",
        analysis="Resilient operational cash flows, solid margins, and expanding market leadership.",
        risks=["Input cost volatility", "Competitive EV price discounting"],
        evidence_citations=[
            f"upstox.market_quote:last_price={quote.current_price.value}",
            f"upstox.provenance:as_of={provenance.as_of.isoformat()}",
            "dsp.valuation:dcf_model",
        ],
        confidence=0.85,
        limitations=["Quarterly cyclicality in commercial vehicle division"],
    )
    mock_orch = MockOrchestrator(public_pack=custom_public_pack)
    app.state.api.research_orchestrator = mock_orch
    client = TestClient(app)

    # Feed validated quote price directly into the deterministic composition request
    body = _sample_analyse_body(
        ticker=quote.symbol,
        exchange=quote.exchange,
        current_market_price=float(quote.current_price.value),
    )

    resp = client.post("/api/v1/analyse", json=body)
    assert resp.status_code == 200
    res_data = resp.json()
    assert res_data["ok"] is True
    payload = res_data["payload"]

    # 6. Verify Final Research Report and Provenance Integrity
    assert payload["research_team"] is not None
    assert payload["research_team"]["identity"]["ticker"] == "TATAMOTORS"
    assert payload["research_team"]["identity"]["exchange"] == "NSE"

    report = payload["research_report"]
    assert report is not None
    assert report["recommendation"] == "BUY"
    assert "950.0" in report["valuation"]
    assert any("upstox.market_quote:last_price=950.0" in c for c in report["evidence_citations"])
    assert any("upstox.provenance" in c for c in report["evidence_citations"])
    assert report["confidence"] == 0.85
    assert_no_private_leakage(report)
