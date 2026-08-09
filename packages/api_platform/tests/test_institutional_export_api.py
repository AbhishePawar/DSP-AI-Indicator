"""EPIC-R003 Institutional Export API tests (P1-12 trust-bound)."""

from __future__ import annotations

import base64
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from api_platform import create_app
from auth_test_helpers import bearer_headers, register_user
from dsp_platform import DSPPlatform, PlatformBuilder, PlatformConfiguration
from dsp_platform.investment_provenance import (
    RELEASE_IDENTITY,
    InMemoryInvestmentProvenanceStore,
    InvestmentProvenanceRecord,
    get_investment_provenance_store,
    reset_investment_provenance_store_for_tests,
)


@pytest.fixture
def platform() -> DSPPlatform:
    return (
        PlatformBuilder()
        .with_configuration(PlatformConfiguration(require_analysis_service=False))
        .build()
    )


@pytest.fixture
def client(platform: DSPPlatform) -> TestClient:
    app_client = TestClient(create_app(platform=platform))
    reset_investment_provenance_store_for_tests(InMemoryInvestmentProvenanceStore())
    yield app_client
    reset_investment_provenance_store_for_tests(None)


@pytest.fixture
def auth_headers(client: TestClient) -> dict[str, str]:
    register_user(client, user_id="export-tester", username="exporttester")
    return bearer_headers(client, username="exporttester")


def _seed() -> InvestmentProvenanceRecord:
    aid = str(uuid4())
    now = datetime.now(tz=UTC).isoformat()
    record = InvestmentProvenanceRecord(
        analysis_id=aid,
        created_at=now,
        ticker="AAPL",
        company="Apple",
        exchange="NASDAQ",
        owner_user_id="export-tester",
        calculated_at=now,
        source_evidence={"status": "unavailable", "authenticated": False},
        financial_validation={"status": "unavailable", "available": False},
        valuation={
            "status": "unavailable",
            "available": False,
            "score": None,
            "label": None,
            "market_price": None,
            "margin_of_safety": None,
            "reason": "valuation stage unavailable",
        },
        buffett={
            "overall_score": None,
            "overall_label": None,
            "overall_status": "unavailable",
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


def _bound_report(
    client: TestClient,
    auth_headers: dict[str, str],
) -> tuple[dict, str]:
    record = _seed()
    obj = client.post(
        "/api/v1/research/object",
        headers=auth_headers,
        json={
            "symbol": "AAPL",
            "analysis_id": record.analysis_id,
            "fetch_data_bundle": False,
            "analysis_payload": {
                "ok": True,
                "recommendation_summary": {"label": "client-stale"},
            },
        },
    )
    assert obj.status_code == 200, obj.text
    report = client.post(
        "/api/v1/research/report",
        headers=auth_headers,
        json={
            "research_object": obj.json()["research_object"],
            "analysis_id": record.analysis_id,
            "report_id": "rpt-api-exp",
            "generated_at": "2026-07-28T00:00:00+00:00",
        },
    )
    assert report.status_code == 200, report.text
    return report.json()["report"], record.analysis_id


def test_export_schema(client: TestClient) -> None:
    response = client.get("/api/v1/research/export/schema")
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["schema"]["source"] == "institutional_report"
    assert "pdf" in body["schema"]["formats"]


def test_export_requires_authentication(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    report, analysis_id = _bound_report(client, auth_headers)
    response = client.post(
        "/api/v1/research/export",
        json={"report": report, "analysis_id": analysis_id, "format": "json"},
    )
    assert response.status_code == 401


def test_export_json(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    report, analysis_id = _bound_report(client, auth_headers)
    response = client.post(
        "/api/v1/research/export",
        headers=auth_headers,
        json={
            "report": report,
            "analysis_id": analysis_id,
            "format": "json",
            "export_id": "exp-api-1",
            "exported_at": "2026-07-28T12:00:00+00:00",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["analysis_id"] == analysis_id
    assert body["export"]["metadata"]["format"] == "json"
    assert body["export"]["structured_json"]["executive_summary"]["rs_id"] == "RS-001"


def test_export_pdf(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    report, analysis_id = _bound_report(client, auth_headers)
    response = client.post(
        "/api/v1/research/export",
        headers=auth_headers,
        json={"report": report, "analysis_id": analysis_id, "format": "pdf"},
    )
    assert response.status_code == 200
    raw = base64.b64decode(response.json()["export"]["content_base64"])
    assert raw.startswith(b"%PDF")


def test_export_docx(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    report, analysis_id = _bound_report(client, auth_headers)
    response = client.post(
        "/api/v1/research/export",
        headers=auth_headers,
        json={"report": report, "analysis_id": analysis_id, "format": "docx"},
    )
    assert response.status_code == 200
    raw = base64.b64decode(response.json()["export"]["content_base64"])
    assert raw[:2] == b"PK"


def test_export_pptx(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    report, analysis_id = _bound_report(client, auth_headers)
    response = client.post(
        "/api/v1/research/export",
        headers=auth_headers,
        json={"report": report, "analysis_id": analysis_id, "format": "pptx"},
    )
    assert response.status_code == 200
    raw = base64.b64decode(response.json()["export"]["content_base64"])
    assert raw[:2] == b"PK"
