"""Integration tests for Research Orchestrator and Upstox market data in /api/v1/analyse."""

from __future__ import annotations

import time

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

    def run(
        self,
        request: UserResearchRequest,
        *,
        timeout_seconds: float | None = None,
        cancellation_event: Any | None = None,
        **kwargs: Any,
    ) -> Any:
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


def test_orchestration_timeout_bounds_execution_and_falls_back(monkeypatch):
    """When research orchestration exceeds timeout, deterministic fallback is preserved."""
    from api_platform.api.ops import metrics_registry

    initial_timeouts = metrics_registry._counters.get("dsp_research_orchestration_timed_out_total", 0)

    class SlowOrchestrator:
        def __init__(self):
            self.cancelled = False

        def run(self, request, timeout_seconds=None, cancellation_event=None):
            # Sleep longer than the configured timeout
            for _ in range(20):
                if cancellation_event and cancellation_event.is_set():
                    self.cancelled = True
                    break
                time.sleep(0.05)
            outcome = MagicMock()
            outcome.to_public.return_value = PublicDecisionPack(
                recommendation="BUY",
                valuation="Delayed",
                analysis="Delayed",
                risks=[],
                evidence_citations=[],
                confidence=0.9,
                limitations=[],
            )
            return outcome

    monkeypatch.setenv("DSP_RESEARCH_ORCHESTRATION_TIMEOUT_SECONDS", "0.1")
    platform = (
        PlatformBuilder()
        .with_configuration(PlatformConfiguration(require_analysis_service=False))
        .auto_ready(True)
        .build()
    )
    app = create_app(platform=platform)
    slow_orch = SlowOrchestrator()
    app.state.api.research_orchestrator = slow_orch
    client = TestClient(app)

    body = _sample_analyse_body()
    resp = client.post("/api/v1/analyse", json=body)
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    payload = data["payload"]

    assert payload["research_report"] is None
    assert any("Research orchestrator timed out." in lim for lim in payload.get("limitations", []))
    assert metrics_registry._counters["dsp_research_orchestration_timed_out_total"] > initial_timeouts


def test_orchestration_report_schema_validation_failures():
    """Malformed schema or invalid confidence drops report safely."""
    from api_platform.api.ops import metrics_registry

    initial_fails = metrics_registry._counters.get("dsp_research_report_validation_failed_total", 0)

    class MalformedOrchestrator:
        def __init__(self, pack_dict):
            self.pack_dict = pack_dict

        def run(self, request, **kwargs):
            outcome = MagicMock()
            pack_mock = MagicMock()
            pack_mock.to_dict.return_value = self.pack_dict
            outcome.to_public.return_value = pack_mock
            return outcome

    platform = (
        PlatformBuilder()
        .with_configuration(PlatformConfiguration(require_analysis_service=False))
        .auto_ready(True)
        .build()
    )
    app = create_app(platform=platform)

    # 1. Missing required field 'analysis'
    malformed_orch = MalformedOrchestrator({
        "recommendation": "BUY",
        "valuation": "Value",
        "risks": [],
        "evidence_citations": ["c1"],
        "confidence": 0.8,
        "limitations": [],
        "schema_version": "public_decision_pack_v1",
    })
    app.state.api.research_orchestrator = malformed_orch
    client = TestClient(app)
    resp = client.post("/api/v1/analyse", json=_sample_analyse_body())
    assert resp.status_code == 200
    assert resp.json()["payload"]["research_report"] is None
    assert any("schema validation" in l for l in resp.json()["payload"].get("limitations", []))

    # 2. Out-of-bounds confidence (e.g. 1.5)
    invalid_conf_orch = MalformedOrchestrator({
        "recommendation": "BUY",
        "valuation": "Value",
        "analysis": "Valid analysis text",
        "risks": [],
        "evidence_citations": ["c1"],
        "confidence": 1.5,
        "limitations": [],
        "schema_version": "public_decision_pack_v1",
    })
    app.state.api.research_orchestrator = invalid_conf_orch
    resp = client.post("/api/v1/analyse", json=_sample_analyse_body())
    assert resp.status_code == 200
    assert resp.json()["payload"]["research_report"] is None

    # 3. Privacy violation: forbidden key 'chain_of_thought'
    leak_orch = MalformedOrchestrator({
        "recommendation": "BUY",
        "valuation": "Value",
        "analysis": "Valid analysis text",
        "risks": [],
        "evidence_citations": ["c1"],
        "confidence": 0.8,
        "limitations": [],
        "schema_version": "public_decision_pack_v1",
        "chain_of_thought": "Private reasoning steps",
    })
    app.state.api.research_orchestrator = leak_orch
    resp = client.post("/api/v1/analyse", json=_sample_analyse_body())
    assert resp.status_code == 200
    assert resp.json()["payload"]["research_report"] is None

    # 4. Privacy violation: secret canary in text
    canary_orch = MalformedOrchestrator({
        "recommendation": "BUY",
        "valuation": "Value",
        "analysis": "Here is canary_secret_99887766 that leaked",
        "risks": [],
        "evidence_citations": ["c1"],
        "confidence": 0.8,
        "limitations": [],
        "schema_version": "public_decision_pack_v1",
    })
    app.state.api.research_orchestrator = canary_orch
    resp = client.post("/api/v1/analyse", json=_sample_analyse_body())
    assert resp.status_code == 200
    assert resp.json()["payload"]["research_report"] is None

    assert metrics_registry._counters["dsp_research_report_validation_failed_total"] >= initial_fails + 4


def test_metrics_registry_prometheus_rendering_has_bounded_labels():
    """Prometheus output includes research orchestration counters without sensitive labels."""
    from api_platform.api.ops import metrics_registry

    rendered = metrics_registry.render_prometheus()
    assert "dsp_research_orchestration_attempted_total" in rendered
    assert "dsp_research_orchestration_succeeded_total" in rendered
    assert "dsp_research_orchestration_timed_out_total" in rendered
    assert "dsp_research_orchestration_provider_failed_total" in rendered
    assert "dsp_research_report_validation_failed_total" in rendered
    assert "dsp_research_deterministic_fallback_used_total" in rendered
    # Confirm bounded names and no raw tickers/canaries in metric declarations
    assert "TATAMOTORS" not in rendered
    assert "canary" not in rendered


def test_route_fetches_verified_upstox_quote_in_ticker_only_mode():
    """Verify Upstox quote endpoint output and its handoff to deterministic composition."""
    from dsp_platform.market_quotes import reset_market_quote_service_for_tests
    from dsp_platform.financial_statements import (
        reset_financial_statement_service_for_tests,
        FinancialStatementService,
    )
    from data_engine import InMemoryAuthenticatedStatementAdapter, build_statements_from_mapping, FinancialStatementProvenance
    from datetime import datetime, timezone
    from data_engine.market_quote.service import MarketQuoteService
    from data_engine.cache import InMemoryCache

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
    adapter = UpstoxQuoteAdapter(access_token="mock_token", resolver=resolver)

    v3_payload = {
        "status": "success",
        "data": {
            "NSE_EQ:TATAMOTORS": {
                "symbol": "NSE_EQ:TATAMOTORS",
                "instrument_token": "NSE_EQ|INE155A01022",
                "last_price": 985.50,
                "ohlc": {"open": 980.0, "high": 990.0, "low": 975.0, "close": 985.50, "volume": 500000},
                "timestamp": int(datetime.now(timezone.utc).timestamp() * 1000),
            }
        }
    }

    def mock_urlopen(req, timeout=None):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(v3_payload).encode("utf-8")
        mock_resp.status = 200
        mock_resp.__enter__.return_value = mock_resp
        mock_resp.__exit__.return_value = False
        return mock_resp

    # Seed authenticated statements for TATAMOTORS
    stmt_adapter = InMemoryAuthenticatedStatementAdapter(api_key="test-key")
    stmt_adapter.put(build_statements_from_mapping(
        symbol="TATAMOTORS",
        payload={
            "identity": {"symbol": "TATAMOTORS", "exchange": "NSE", "currency": "INR"},
            "reporting_currency": "INR",
            "statement_basis": "consolidated",
            "unit_scale": "actual",
            "periods": [
                {
                    "period_type": "annual",
                    "fiscal_year": 2024,
                    "period_end": "2024-12-31",
                    "reporting_currency": "INR",
                    "income_statement": {"revenue": 500000.0, "net_income": 100000.0, "eps_basic": 26.0, "operating_income": 120000.0},
                    "balance_sheet": {"cash": 50000.0, "total_assets": 1500000.0, "total_liabilities": 500000.0, "equity": 1000000.0, "total_debt": 200000.0},
                    "cash_flow": {"operating_cash_flow": 150000.0, "free_cash_flow": 100000.0, "capex": -50000.0},
                    "ratios": {},
                },
                {
                    "period_type": "annual",
                    "fiscal_year": 2023,
                    "period_end": "2023-12-31",
                    "reporting_currency": "INR",
                    "income_statement": {"revenue": 450000.0, "net_income": 80000.0, "eps_basic": 21.0, "operating_income": 100000.0},
                    "balance_sheet": {"cash": 40000.0, "total_assets": 1400000.0, "total_liabilities": 500000.0, "equity": 900000.0, "total_debt": 200000.0},
                    "cash_flow": {"operating_cash_flow": 130000.0, "free_cash_flow": 90000.0, "capex": -40000.0},
                    "ratios": {},
                },
            ],
        },
        provenance=FinancialStatementProvenance(
            provider_id="memory_authenticated_statements",
            provider_name="Memory Statements",
            source_type="licensed_vendor",
            retrieved_at=datetime.now(timezone.utc),
            auth_mode="api_key",
        ),
    ))
    stmt_service = FinancialStatementService(stmt_adapter)
    reset_financial_statement_service_for_tests(stmt_service)

    quote_service = MarketQuoteService(adapter, cache=InMemoryCache())
    reset_market_quote_service_for_tests(quote_service)

    try:
        platform = (
            PlatformBuilder()
            .with_configuration(PlatformConfiguration(require_analysis_service=False))
            .auto_ready(True)
            .build()
        )
        app = create_app(platform=platform)
        custom_pack = PublicDecisionPack(
            recommendation="BUY",
            valuation="Intrinsic value ₹1100 vs market price ₹985.50",
            analysis="Robust operational execution.",
            risks=["Raw material inflation"],
            evidence_citations=["upstox.market_quote:last_price=985.50"],
            confidence=0.88,
            limitations=[],
        )
        app.state.api.research_orchestrator = MockOrchestrator(public_pack=custom_pack)
        client = TestClient(app)

        with patch("urllib.request.urlopen", side_effect=mock_urlopen):
            # 1. Fetch verified quote via /api/v1/market/quote
            quote_resp = client.get("/api/v1/market/quote?symbol=TATAMOTORS&exchange=NSE")
            assert quote_resp.status_code == 200
            q_data = quote_resp.json()
            assert q_data["ok"] is True
            assert q_data["available"] is True
            assert q_data["authenticated"] is True
            assert q_data["symbol"] == "TATAMOTORS"
            assert q_data["exchange"] == "NSE"
            assert q_data["fields"]["current_price"] == 985.50
            assert q_data["provenance"]["provider_id"] == "upstox"
            assert q_data["provenance"]["metadata"]["instrument_key"] == "NSE_EQ|INE155A01022"

            # 2. Feed verified quote into deterministic composition and research report
            resp = client.post("/api/v1/analyse", json=_sample_analyse_body(
                ticker="TATAMOTORS",
                exchange="NSE",
                current_market_price=q_data["fields"]["current_price"],
            ))
            assert resp.status_code == 200
            data = resp.json()
            assert data["ok"] is True
            payload = data["payload"]
            assert payload["research_report"] is not None
            assert payload["research_report"]["recommendation"] == "BUY"
            assert payload["server_valuation"]["current_market_price"] == 985.50

            # 3. True route-level verification of ticker-only execution without client price:
            # Demonstrates that /analyse autonomously invokes the registered Upstox quote adapter.
            # Because Upstox V3 quote API provides OHLC/last_price but omits shares_outstanding,
            # the platform pipeline fails closed honestly without fabricating share counts.
            ticker_only_resp = client.post("/api/v1/analyse", json={
                "ticker": "TATAMOTORS",
                "exchange": "NSE",
            })
            assert ticker_only_resp.status_code == 200
            t_data = ticker_only_resp.json()
            # Graceful degradation with honest disclosure of missing share count
            assert t_data["ok"] is False
            assert any("shares outstanding unavailable" in err.lower() for err in t_data.get("errors", []))
            assert t_data["payload"]["research_report"] is not None
            payload = data["payload"]
            assert payload["research_report"] is not None
            assert payload["research_report"]["recommendation"] == "BUY"
            assert payload["server_valuation"]["current_market_price"] == 985.50
    finally:
        reset_market_quote_service_for_tests(None)
        reset_financial_statement_service_for_tests(None)


def test_quote_failure_paths_fail_closed_without_fabrication():
    """Provider failure or invalid data fails closed without fabricating market quotes."""
    from dsp_platform.market_quotes import reset_market_quote_service_for_tests
    from data_engine.market_quote.service import MarketQuoteService, RetryPolicy
    from data_engine.cache import InMemoryCache
    import urllib.error

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
    adapter = UpstoxQuoteAdapter(access_token="mock_token", resolver=resolver)

    def mock_401(req, timeout=None):
        raise urllib.error.HTTPError(req.full_url, 401, "Unauthorized", {}, None)

    quote_service = MarketQuoteService(adapter, cache=InMemoryCache(), retry=RetryPolicy(max_attempts=1))
    reset_market_quote_service_for_tests(quote_service)

    try:
        platform = (
            PlatformBuilder()
            .with_configuration(PlatformConfiguration(require_analysis_service=False))
            .auto_ready(True)
            .build()
        )
        app = create_app(platform=platform)
        client = TestClient(app)

        with patch("urllib.request.urlopen", side_effect=mock_401):
            resp = client.post("/api/v1/analyse", json={
                "ticker": "TATAMOTORS",
                "exchange": "NSE",
            })
            assert resp.status_code == 200
            data = resp.json()
            # Fails closed without fabricating a market price
            assert data["ok"] is False
            payload = data.get("payload")
            if isinstance(payload, dict):
                assert payload.get("ok") is False
                val = payload.get("server_valuation") or {}
                assert val.get("current_market_price") is None
    finally:
        reset_market_quote_service_for_tests(None)


def test_orchestration_capacity_exhaustion_fallback():
    """When all worker slots are occupied, additional requests degrade gracefully with deterministic fallback."""
    from api_platform.api.routers import composition
    from api_platform.api.ops import metrics_registry

    initial_exhausted = metrics_registry._counters["dsp_research_orchestration_capacity_exhausted_total"]

    # Acquire all permits from the semaphore to simulate saturated worker capacity
    acquired = []
    for _ in range(composition._MAX_ORCHESTRATION_WORKERS):
        acquired.append(composition._ORCHESTRATION_SEMAPHORE.acquire(blocking=False))
    assert all(acquired), "Should acquire all worker permits"

    try:
        platform = (
            PlatformBuilder()
            .with_configuration(PlatformConfiguration(require_analysis_service=False))
            .auto_ready(True)
            .build()
        )
        app = create_app(platform=platform)
        app.state.api.research_orchestrator = MockOrchestrator()
        client = TestClient(app)

        # 5th request should immediately fall back without queuing
        resp = client.post("/api/v1/analyse", json=_sample_analyse_body())
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["payload"]["research_report"] is None
        assert any("capacity exhausted" in lim.lower() for lim in data["limitations"])
        assert metrics_registry._counters["dsp_research_orchestration_capacity_exhausted_total"] == initial_exhausted + 1
    finally:
        # Release the permits
        for _ in acquired:
            composition._ORCHESTRATION_SEMAPHORE.release()


def test_invalid_timeout_env_values_handled_safely():
    """Non-finite, negative, or malformed timeout env vars fallback to safe default."""
    from api_platform.api.routers.composition import parse_orchestration_timeout
    import os

    with patch.dict(os.environ, {"DSP_RESEARCH_ORCHESTRATION_TIMEOUT_SECONDS": "0"}):
        assert parse_orchestration_timeout() == 15.0

    with patch.dict(os.environ, {"DSP_RESEARCH_ORCHESTRATION_TIMEOUT_SECONDS": "-10"}):
        assert parse_orchestration_timeout() == 15.0

    with patch.dict(os.environ, {"DSP_RESEARCH_ORCHESTRATION_TIMEOUT_SECONDS": "nan"}):
        assert parse_orchestration_timeout() == 15.0

    with patch.dict(os.environ, {"DSP_RESEARCH_ORCHESTRATION_TIMEOUT_SECONDS": "inf"}):
        assert parse_orchestration_timeout() == 15.0

    with patch.dict(os.environ, {"DSP_RESEARCH_ORCHESTRATION_TIMEOUT_SECONDS": "malformed_string"}):
        assert parse_orchestration_timeout() == 15.0

    # Unreasonably large timeout clamped to 120.0
    with patch.dict(os.environ, {"DSP_RESEARCH_ORCHESTRATION_TIMEOUT_SECONDS": "500.0"}):
        assert parse_orchestration_timeout() == 120.0

    # Valid positive timeout accepted
    with patch.dict(os.environ, {"DSP_RESEARCH_ORCHESTRATION_TIMEOUT_SECONDS": "25.5"}):
        assert parse_orchestration_timeout() == 25.5


def test_concurrency_safe_metrics_updates():
    """Concurrent threads updating metrics cannot corrupt counters or raise exceptions."""
    from api_platform.api.ops import metrics_registry
    import threading

    initial = metrics_registry._counters["dsp_research_orchestration_attempted_total"]
    threads = []
    n_threads = 10
    increments_per_thread = 50

    def worker():
        for _ in range(increments_per_thread):
            metrics_registry.record_research_orchestration_event("attempted")
            _ = metrics_registry.snapshot()
            _ = metrics_registry.render_prometheus()

    for _ in range(n_threads):
        t = threading.Thread(target=worker)
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    expected = initial + (n_threads * increments_per_thread)
    assert metrics_registry._counters["dsp_research_orchestration_attempted_total"] == expected


def test_research_orchestration_service_boundary_isolation():
    """Verify that ResearchOrchestrationService cleanly encapsulates worker pool, admission control, and execution."""
    from api_platform.api.research_orchestration_service import ResearchOrchestrationService
    import threading

    custom_sem = threading.BoundedSemaphore(value=2)
    service = ResearchOrchestrationService(semaphore=custom_sem)

    # 1. Successful execution through service boundary
    mock_orch = MockOrchestrator()
    report, limitations = service.execute(
        mock_orch,
        ticker="INFY",
        company="Infosys Limited",
        exchange="NSE",
        correlation_id="test-boundary-1",
        timeout_seconds=5.0,
    )
    assert report is not None
    assert report["recommendation"] == "BUY"
    assert limitations == []

    # 2. Capacity exhaustion through service boundary
    custom_sem.acquire(blocking=False)
    custom_sem.acquire(blocking=False)
    try:
        report, limitations = service.execute(
            mock_orch,
            ticker="INFY",
            company="Infosys Limited",
            exchange="NSE",
            correlation_id="test-boundary-2",
            timeout_seconds=5.0,
        )
        assert report is None
        assert any("capacity exhausted" in lim.lower() for lim in limitations)
    finally:
        custom_sem.release()
        custom_sem.release()
