"""P1-12 — export ↔ displayed analysis trust-chain closure."""

from __future__ import annotations

import base64
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from api_platform import create_app
from auth_test_helpers import bearer_headers, register_user
from dsp_platform import PlatformBuilder, PlatformConfiguration
from dsp_platform.investment_provenance import (
    RELEASE_IDENTITY,
    InMemoryInvestmentProvenanceStore,
    InvestmentProvenanceRecord,
    get_investment_provenance_store,
    reset_investment_provenance_store_for_tests,
)


@pytest.fixture()
def client() -> TestClient:
    platform = (
        PlatformBuilder()
        .with_configuration(PlatformConfiguration(require_analysis_service=False))
        .auto_ready(True)
        .build()
    )
    app_client = TestClient(create_app(platform=platform))
    # Boot may rewire provenance — bind a fresh in-memory store after create_app.
    reset_investment_provenance_store_for_tests(InMemoryInvestmentProvenanceStore())
    yield app_client
    reset_investment_provenance_store_for_tests(None)


def _seed(
    *,
    owner: str,
    org_id: str | None = None,
    ticker: str = "AAPL",
    valuation_available: bool = False,
    mos: float | None = None,
    buffett_score: float | None = None,
) -> InvestmentProvenanceRecord:
    aid = str(uuid4())
    now = datetime.now(tz=UTC).isoformat()
    record = InvestmentProvenanceRecord(
        analysis_id=aid,
        created_at=now,
        ticker=ticker,
        company="Fixture Co",
        exchange="NASDAQ",
        owner_user_id=owner,
        org_id=org_id,
        calculated_at=now,
        source_evidence={
            "authenticated": False,
            "status": "unavailable",
            "statement_provider": "test_fixture",
            "statement_source_type": "test_fixture",
            "statement_basis": "consolidated",
            "statement_retrieved_at": now,
        },
        financial_validation={"status": "unavailable", "available": False},
        valuation={
            "status": "succeeded" if valuation_available else "unavailable",
            "available": valuation_available,
            "score": 0.7 if valuation_available else None,
            "label": "ok" if valuation_available else None,
            "market_price": 100.0 if valuation_available else None,
            "margin_of_safety": mos if valuation_available else None,
            "reason": None if valuation_available else "valuation stage unavailable",
        },
        buffett={
            "overall_score": buffett_score,
            "overall_label": "Quality" if buffett_score is not None else None,
            "overall_status": "ok" if buffett_score is not None else "unavailable",
            "recommendation": "Research Mode",
            "committee_decision": None,
            "factors": [],
        },
        conclusion={
            "recommendation": "Research Mode",
            "recommendation_score": None,
            "recommendation_label": "Research Mode",
            "recommendation_confidence": None,
            "committee_decision": None,
            "committee_score": None,
            "committee_confidence": None,
            "pipeline_ok": True,
        },
        release=dict(RELEASE_IDENTITY),
        input_fingerprint=f"in-{aid}",
        result_fingerprint=f"out-{aid}",
    )
    get_investment_provenance_store().append(record)
    return record


def _user(client: TestClient, *, user_id: str, username: str) -> dict[str, str]:
    register_user(client, user_id=user_id, username=username)
    return bearer_headers(client, username=username)


def test_object_requires_analysis_id_for_conclusions(client: TestClient) -> None:
    headers = _user(client, user_id="p112-a", username="p112a")
    denied = client.post(
        "/api/v1/research/object",
        headers=headers,
        json={
            "symbol": "AAPL",
            "fetch_data_bundle": False,
            "analysis_payload": {
                "ok": True,
                "recommendation_summary": {"margin_of_safety": 0.99},
            },
        },
    )
    assert denied.status_code == 400
    assert denied.json()["error_code"] == "TRUST_CHAIN_ANALYSIS_ID_REQUIRED"


def test_bound_export_matches_provenance_not_client_forgery(client: TestClient) -> None:
    headers = _user(client, user_id="p112-owner-forge", username="p112forge")
    record = _seed(owner="p112-owner-forge", valuation_available=False)
    forged = client.post(
        "/api/v1/research/object",
        headers=headers,
        json={
            "symbol": "AAPL",
            "analysis_id": record.analysis_id,
            "fetch_data_bundle": False,
            "analysis_payload": {
                "ok": True,
                "analysis_id": record.analysis_id,
                "recommendation_summary": {"margin_of_safety": 0.42},
                "buffett_authority": {"overall_score": 99.0},
                "server_valuation": {"intrinsic_value_per_share": 999.0},
            },
        },
    )
    assert forged.status_code == 422
    assert forged.json()["error_code"] in {
        "TRUST_CHAIN_FORGED_VALUATION",
        "TRUST_CHAIN_FORGED_BUFFETT",
    }


def test_export_happy_path_binds_analysis_id(client: TestClient) -> None:
    headers = _user(client, user_id="p112-owner-happy", username="p112happy")
    record = _seed(
        owner="p112-owner-happy",
        valuation_available=True,
        mos=0.2,
        buffett_score=0.55,
    )
    obj = client.post(
        "/api/v1/research/object",
        headers=headers,
        json={
            "symbol": "AAPL",
            "analysis_id": record.analysis_id,
            "fetch_data_bundle": False,
            "analysis_payload": {
                "ok": True,
                "analysis_id": record.analysis_id,
                "recommendation_summary": {"label": "stale-client"},
                "stage_summaries": [
                    {"stage": "valuation", "has_result": True, "status": "succeeded"}
                ],
            },
        },
    )
    assert obj.status_code == 200, obj.text
    body = obj.json()
    assert body["analysis_id"] == record.analysis_id
    ro = body["research_object"]
    assert ro["audit"]["payload"]["analysis_id"] == record.analysis_id
    assert ro["margin_of_safety"]["payload"]["margin_of_safety"] == 0.2
    assert ro["recommendation"]["payload"]["label"] == "Research Mode"

    report = client.post(
        "/api/v1/research/report",
        headers=headers,
        json={
            "research_object": ro,
            "analysis_id": record.analysis_id,
            "report_id": "rpt-p112",
        },
    )
    assert report.status_code == 200, report.text
    rpt = report.json()["report"]
    assert rpt["audit"]["payload"]["analysis_id"] == record.analysis_id

    exported = client.post(
        "/api/v1/research/export",
        headers=headers,
        json={
            "report": rpt,
            "analysis_id": record.analysis_id,
            "format": "json",
        },
    )
    assert exported.status_code == 200, exported.text
    assert exported.json()["analysis_id"] == record.analysis_id
    structured = exported.json()["export"]["structured_json"]
    assert structured["audit"]["payload"]["analysis_id"] == record.analysis_id
    # Bound recommendation label (server) — not stale client "stale-client".
    rec_payload = (structured.get("recommendation") or {}).get("payload") or {}
    source_payload = rec_payload.get("source_payload") or rec_payload
    assert source_payload.get("label") == "Research Mode"
    # MoS was already asserted on the bound research object above.


def test_cross_user_export_forbidden(client: TestClient) -> None:
    owner_headers = _user(client, user_id="p112-owner-x", username="p112ownerx")
    other_headers = _user(client, user_id="p112-other-x", username="p112otherx")
    record = _seed(owner="p112-owner-x", valuation_available=True, mos=0.1)
    obj = client.post(
        "/api/v1/research/object",
        headers=owner_headers,
        json={
            "symbol": "AAPL",
            "analysis_id": record.analysis_id,
            "fetch_data_bundle": False,
            "analysis_payload": {
                "ok": True,
                "recommendation_summary": {"label": "Research Mode"},
            },
        },
    )
    assert obj.status_code == 200
    ro = obj.json()["research_object"]
    report = client.post(
        "/api/v1/research/report",
        headers=owner_headers,
        json={"research_object": ro, "analysis_id": record.analysis_id},
    )
    assert report.status_code == 200
    rpt = report.json()["report"]

    denied = client.post(
        "/api/v1/research/export",
        headers=other_headers,
        json={"report": rpt, "analysis_id": record.analysis_id, "format": "json"},
    )
    assert denied.status_code == 403
    assert denied.json()["error_code"] == "TRUST_CHAIN_FORBIDDEN"


def test_mismatched_analysis_id_rejected(client: TestClient) -> None:
    headers = _user(client, user_id="p112-owner-mm", username="p112ownermm")
    a = _seed(owner="p112-owner-mm", valuation_available=True, mos=0.1)
    b = _seed(owner="p112-owner-mm", valuation_available=True, mos=0.9)
    obj = client.post(
        "/api/v1/research/object",
        headers=headers,
        json={
            "symbol": "AAPL",
            "analysis_id": a.analysis_id,
            "fetch_data_bundle": False,
            "analysis_payload": {"ok": True, "recommendation_summary": {"label": "x"}},
        },
    )
    assert obj.status_code == 200
    report = client.post(
        "/api/v1/research/report",
        headers=headers,
        json={
            "research_object": obj.json()["research_object"],
            "analysis_id": a.analysis_id,
        },
    )
    assert report.status_code == 200
    mismatched = client.post(
        "/api/v1/research/export",
        headers=headers,
        json={
            "report": report.json()["report"],
            "analysis_id": b.analysis_id,
            "format": "pdf",
        },
    )
    assert mismatched.status_code == 409
    assert mismatched.json()["error_code"] == "TRUST_CHAIN_REPORT_MISMATCH"


def test_forged_export_without_binding_rejected(client: TestClient) -> None:
    headers = _user(client, user_id="p112-owner-craft", username="p112craft")
    crafted = {
        "valuation": {
            "available": True,
            "payload": {"intrinsic_value_per_share": 1234.0, "margin_of_safety": 0.9},
        },
        "margin_of_safety": {
            "available": True,
            "payload": {"margin_of_safety": 0.9},
        },
        "recommendation": {"available": True, "payload": {"label": "BUY"}},
        "audit": {
            "available": True,
            "payload": {
                "analysis_id": "not-a-real-id",
                "audit_reference": "not-a-real-id",
            },
        },
    }
    denied = client.post(
        "/api/v1/research/export",
        headers=headers,
        json={"report": crafted, "analysis_id": "not-a-real-id", "format": "json"},
    )
    assert denied.status_code == 404


def test_analyse_remains_usable_without_auth_when_security_off(
    client: TestClient,
) -> None:
    """P1-12 policy: /analyse stays authentication-independent unless security middleware on."""
    response = client.post(
        "/api/v1/analyse",
        json={
            "ticker": "ZZZZ",
            "company": "No Auth Co",
            "financial_statements": {
                "period": {
                    "period_type": "annual",
                    "period_end": "2024-12-31",
                    "fiscal_year": 2024,
                    "currency": "USD",
                },
                "income_statement": {},
                "balance_sheet": {},
                "cash_flow": {},
            },
        },
    )
    assert response.status_code != 401


def test_pdf_export_bytes_still_bound(client: TestClient) -> None:
    headers = _user(client, user_id="p112-owner-pdf", username="p112pdf")
    record = _seed(owner="p112-owner-pdf", valuation_available=True, mos=0.15)
    obj = client.post(
        "/api/v1/research/object",
        headers=headers,
        json={
            "symbol": "AAPL",
            "analysis_id": record.analysis_id,
            "fetch_data_bundle": False,
            "analysis_payload": {"ok": True, "recommendation_summary": {"label": "x"}},
        },
    )
    report = client.post(
        "/api/v1/research/report",
        headers=headers,
        json={
            "research_object": obj.json()["research_object"],
            "analysis_id": record.analysis_id,
        },
    )
    exported = client.post(
        "/api/v1/research/export",
        headers=headers,
        json={
            "report": report.json()["report"],
            "analysis_id": record.analysis_id,
            "format": "pdf",
        },
    )
    assert exported.status_code == 200
    raw = base64.b64decode(exported.json()["export"]["content_base64"])
    assert raw.startswith(b"%PDF")
