"""P1-09 — critical investment journey API hard-gate (evidence_class=test_fixture).

Exercises:
  login → authenticated principal → analyse → valuation → Buffett →
  provenance → forgery refusal → IDOR → honest unavailable

Never claims real_live_authenticated_provider.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api_platform import create_app
from auth_test_helpers import bearer_headers, register_user
from data_engine import (
    FinancialStatementService,
    InMemoryAuthenticatedQuoteAdapter,
    InMemoryAuthenticatedStatementAdapter,
    MarketQuoteService,
)
from dsp_platform import PlatformBuilder, PlatformConfiguration
from dsp_platform.financial_statements import reset_financial_statement_service_for_tests
from dsp_platform.investment_provenance import (
    RELEASE_IDENTITY,
    DatabaseInvestmentProvenanceStore,
    reset_investment_provenance_store_for_tests,
)
from dsp_platform.market_quotes import reset_market_quote_service_for_tests
from dsp_platform.p109_e2e_fixture import (
    P109_EVIDENCE_CLASS,
    P109_FIXTURE_TICKER,
    build_p109_quote,
    build_p109_statements,
)
from production_platform import InMemoryDatabasePort

ROOT = Path(__file__).resolve().parents[3]
EVIDENCE_PATH = ROOT / "artifacts" / "p109_critical_investment_evidence.json"


@pytest.fixture()
def db() -> InMemoryDatabasePort:
    return InMemoryDatabasePort()


@pytest.fixture()
def seeded_client(db: InMemoryDatabasePort, monkeypatch: pytest.MonkeyPatch):
    """API client with memory quote/statements seeded as P1-09 test_fixture."""
    monkeypatch.setenv("DSP_ENVIRONMENT", "development")
    monkeypatch.delenv("DSP_P109_E2E_FIXTURE", raising=False)

    quote_adapter = InMemoryAuthenticatedQuoteAdapter(api_key="p109-fixture-key")
    stmt_adapter = InMemoryAuthenticatedStatementAdapter(api_key="p109-fixture-key")
    quote_adapter.put(build_p109_quote())
    stmt_adapter.put(build_p109_statements())
    reset_market_quote_service_for_tests(MarketQuoteService(quote_adapter))
    reset_financial_statement_service_for_tests(
        FinancialStatementService(stmt_adapter)
    )

    platform = (
        PlatformBuilder()
        .with_configuration(PlatformConfiguration(require_analysis_service=False))
        .auto_ready(True)
        .build()
    )
    client = TestClient(create_app(platform=platform))
    reset_investment_provenance_store_for_tests(
        DatabaseInvestmentProvenanceStore(db)
    )
    yield client
    reset_market_quote_service_for_tests(None)
    reset_financial_statement_service_for_tests(None)
    reset_investment_provenance_store_for_tests(None)


def _write_evidence(payload: dict) -> None:
    EVIDENCE_PATH.parent.mkdir(parents=True, exist_ok=True)
    EVIDENCE_PATH.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )


def _analyse_from_authenticated(client: TestClient, headers: dict[str, str]) -> dict:
    ticker = P109_FIXTURE_TICKER
    quote = client.get(f"/api/v1/market/quote?symbol={ticker}", headers=headers)
    assert quote.status_code == 200, quote.text
    q = quote.json()
    assert q["available"] is True
    assert q["authenticated"] is True
    price = q["fields"]["current_price"]
    assert isinstance(price, (int, float)) and price > 0

    stmts = client.get(
        f"/api/v1/fundamentals/statements?symbol={ticker}&limit=2",
        headers=headers,
    )
    assert stmts.status_code == 200, stmts.text
    s = stmts.json()
    assert s["available"] is True
    assert s["authenticated"] is True
    assert s["periods"]
    latest = s["periods"][0]
    assert latest["reporting_currency"] == "USD"
    assert latest.get("statement_basis") in {None, "consolidated"}
    assert latest.get("unit_scale") in {None, "actual"}

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
    resp = client.post("/api/v1/analyse", headers=headers, json=body)
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_p109_critical_investment_journey_hard_gate(seeded_client: TestClient) -> None:
    client = seeded_client

    # --- Health (Track 2 dual mount) ---
    live = client.get("/health/live")
    ready = client.get("/health/ready")
    live_v1 = client.get("/api/v1/health/live")
    ready_v1 = client.get("/api/v1/health/ready")
    assert live.status_code == 200
    assert ready.status_code == 200
    assert live_v1.status_code == 200
    assert ready_v1.status_code == 200

    # --- Auth: User A ---
    register_user(
        client,
        user_id="p109-user-a",
        username="p109usera",
        roles=["administrator"],
    )
    headers_a = bearer_headers(client, username="p109usera")
    assert "Authorization" in headers_a
    assert headers_a["Authorization"].startswith("Bearer ")

    # --- X-User-Id spoofing is not authoritative ---
    spoof = {
        **headers_a,
        "X-User-Id": "p109-attacker",
    }
    # Analyse still attributes ownership from JWT, not header (checked via IDOR).

    analyse = _analyse_from_authenticated(client, spoof)
    assert analyse["ok"] is True
    analysis_id = analyse["analysis_id"]
    assert analysis_id
    assert analyse["audit_reference"] == analysis_id
    assert analyse["provenance_persisted"] is True

    payload = analyse["payload"]
    assert payload.get("buffett_authority")
    buffett = payload["buffett_authority"]
    assert "overall_score" in buffett or "overall_status" in buffett
    assert payload.get("source_evidence") is not None

    stages = payload.get("stage_summaries") or []
    valuation_stage = next((s for s in stages if s.get("stage") == "valuation"), None)
    assert valuation_stage is not None
    assert valuation_stage.get("status") in {"succeeded", "degraded", "unavailable"}

    # --- Provenance lineage ---
    prov_resp = client.get(
        f"/api/v1/analyse/provenance/{analysis_id}",
        headers=headers_a,
    )
    assert prov_resp.status_code == 200, prov_resp.text
    prov = prov_resp.json()["provenance"]
    assert prov["analysis_id"] == analysis_id
    assert prov["ticker"] == P109_FIXTURE_TICKER
    assert prov["release"]["epic"] == "EPS-003"
    assert prov["release"]["product_version"] == "2.0.0-rc.1"
    assert prov["release"]["channel"] == "rc"
    assert prov["release"]["decision"] == "RELEASE_CANDIDATE"
    assert prov["release"]["label"] == RELEASE_IDENTITY["label"]
    assert prov["input_fingerprint"]
    assert prov["result_fingerprint"]
    assert "source_evidence" in prov
    assert "financial_validation" in prov
    assert "valuation" in prov
    assert "buffett" in prov
    assert "conclusion" in prov

    # --- Forgery protection (P0-02 / P1-05) ---
    forged = {
        "ticker": P109_FIXTURE_TICKER,
        "company": "DSP Fixture Corp",
        "current_market_price": 25.0,
        "valuation_signals": {
            "intrinsic_value_per_share": 9999.0,
            "margin_of_safety": 0.99,
            "current_market_price": 25.0,
            "confidence": 0.99,
        },
        "financial_statements": {
            "period": {
                "period_type": "annual",
                "period_end": "2024-12-31",
                "fiscal_year": 2024,
                "currency": "USD",
            },
            "income_statement": {
                "revenue": 1.0,
                "net_income": 1.0,
                "buffett_score": 100,
                "buffett_rating": "excellent",
            },
            "balance_sheet": {"total_equity": 1.0, "total_assets": 2.0},
            "cash_flow": {"operating_cash_flow": 1.0},
            "statement_metadata": {"recommendation": "BUY"},
        },
    }
    forged_resp = client.post("/api/v1/analyse", headers=headers_a, json=forged)
    assert forged_resp.status_code == 422, forged_resp.text
    forged_body = forged_resp.json()
    assert forged_body["ok"] is False
    errors = " ".join(forged_body.get("validation_errors") or [])
    assert "intrinsic_value_per_share" in errors or "P0-02" in errors
    assert "buffett_score" in errors or "P1-05" in errors

    # Top-level recommendation / buffett_score forbidden by schema extra=forbid
    schema_forged = {
        "ticker": P109_FIXTURE_TICKER,
        "company": "X",
        "current_market_price": 25.0,
        "recommendation": "BUY",
        "buffett_score": 100,
        "financial_statements": forged["financial_statements"],
    }
    # Remove forbidden keys from statement maps for pure top-level test
    schema_forged["financial_statements"] = {
        "period": forged["financial_statements"]["period"],
        "income_statement": {"revenue": 1.0, "net_income": 1.0},
        "balance_sheet": {"total_equity": 1.0},
        "cash_flow": {"operating_cash_flow": 1.0},
        "statement_metadata": {},
    }
    schema_resp = client.post(
        "/api/v1/analyse", headers=headers_a, json=schema_forged
    )
    assert schema_resp.status_code == 422

    # --- IDOR: User B cannot read User A's provenance ---
    register_user(
        client,
        user_id="p109-user-b",
        username="p109userb",
        roles=["administrator"],
    )
    headers_b = bearer_headers(client, username="p109userb")
    deny = client.get(
        f"/api/v1/analyse/provenance/{analysis_id}",
        headers=headers_b,
    )
    assert deny.status_code in {403, 404}, deny.text

    # Owner can still read
    assert (
        client.get(
            f"/api/v1/analyse/provenance/{analysis_id}",
            headers=headers_a,
        ).status_code
        == 200
    )

    # --- Honest failure: unknown ticker ---
    missing = client.get(
        "/api/v1/fundamentals/statements?symbol=ZZZZNOPE",
        headers=headers_a,
    )
    assert missing.status_code == 200
    missing_body = missing.json()
    assert missing_body["available"] is False
    assert missing_body.get("message") == "Data unavailable."

    missing_quote = client.get(
        "/api/v1/market/quote?symbol=ZZZZNOPE",
        headers=headers_a,
    )
    assert missing_quote.status_code == 200
    assert missing_quote.json()["available"] is False

    evidence = {
        "ok": True,
        "gate": "P1-09",
        "evidence_class": P109_EVIDENCE_CLASS,
        "g2_claim": False,
        "ticker": P109_FIXTURE_TICKER,
        "analysis_id": analysis_id,
        "input_fingerprint": prov["input_fingerprint"],
        "result_fingerprint": prov["result_fingerprint"],
        "release_identity": prov["release"],
        "valuation_status": valuation_stage.get("status"),
        "buffett_status": buffett.get("overall_status"),
        "forgery_rejected": True,
        "idor_status": deny.status_code,
        "health": {
            "live": live.status_code,
            "ready": ready.status_code,
        },
        "note": (
            "Deterministic memory fixture only — NOT real_live_authenticated_provider"
        ),
    }
    _write_evidence(evidence)
    assert evidence["evidence_class"] == "test_fixture"
    assert evidence["evidence_class"] != "real_live_authenticated_provider"


def test_p109_fixture_refused_in_production_env(monkeypatch: pytest.MonkeyPatch) -> None:
    from dsp_platform.p109_e2e_fixture import p109_fixture_enabled

    monkeypatch.setenv("DSP_ENVIRONMENT", "production")
    monkeypatch.setenv("DSP_P109_E2E_FIXTURE", "1")
    assert p109_fixture_enabled() is False
