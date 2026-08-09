"""EPIC-R002 Institutional Research Report API tests (P1-12 trust-bound)."""

from __future__ import annotations

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
    register_user(client, user_id="research-rpt-user", username="researchrpt")
    return bearer_headers(client, username="researchrpt")


def _bound_ro(
    client: TestClient,
    auth_headers: dict[str, str],
) -> tuple[dict, str]:
    aid = str(uuid4())
    now = datetime.now(tz=UTC).isoformat()
    get_investment_provenance_store().append(
        InvestmentProvenanceRecord(
            analysis_id=aid,
            created_at=now,
            ticker="AAPL",
            owner_user_id="research-rpt-user",
            valuation={
                "status": "succeeded",
                "available": True,
                "score": 0.5,
                "label": "ok",
                "market_price": 190.5,
                "margin_of_safety": 0.2,
                "reason": None,
            },
            buffett={
                "overall_status": "unavailable",
                "recommendation": "Research Mode",
            },
            conclusion={
                "recommendation": "Research Mode",
                "recommendation_label": "Research Mode",
                "pipeline_ok": True,
            },
            release=dict(RELEASE_IDENTITY),
            input_fingerprint=f"in-{aid}",
            result_fingerprint=f"out-{aid}",
        )
    )
    obj = client.post(
        "/api/v1/research/object",
        headers=auth_headers,
        json={
            "symbol": "AAPL",
            "company": "Apple Inc",
            "analysis_id": aid,
            "fetch_data_bundle": False,
            "data_bundle": {
                "identity": {
                    "symbol": "AAPL",
                    "ticker": "AAPL",
                    "company_name": "Apple Inc",
                },
                "market_quote": {
                    "status": {
                        "available": True,
                        "status": "ok",
                        "retrieved_at": "2026-07-28T00:00:00+00:00",
                    },
                    "payload": {"fields": {"current_price": 190.5}},
                    "provenance": {
                        "provider_id": "mq",
                        "source_type": "licensed_vendor",
                    },
                },
                "financial_statements": {
                    "status": {
                        "available": False,
                        "status": "unavailable",
                        "message": "Data unavailable.",
                    },
                    "payload": None,
                },
                "corporate_actions": {
                    "status": {
                        "available": False,
                        "status": "unavailable",
                        "message": "Data unavailable.",
                    },
                    "payload": None,
                },
                "historical_series": {
                    "status": {
                        "available": False,
                        "status": "unavailable",
                        "message": "Data unavailable.",
                    },
                    "payload": None,
                },
            },
            "analysis_payload": {
                "ok": True,
                "recommendation_summary": {
                    "label": "Research Mode",
                    "margin_of_safety": 0.2,
                },
                "stage_summaries": [
                    {"stage": "valuation", "has_result": True, "summary": "v"}
                ],
            },
        },
    )
    assert obj.status_code == 200, obj.text
    return obj.json()["research_object"], aid


def test_report_schema(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.get("/api/v1/research/report/schema")
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["schema"]["schema_version"] == "1.0.0"
    assert body["schema"]["source"] == "research_object"
    assert "RS-001" in body["schema"]["rs_coverage"]


def test_generate_report(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    ro, analysis_id = _bound_ro(client, auth_headers)
    response = client.post(
        "/api/v1/research/report",
        headers=auth_headers,
        json={
            "research_object": ro,
            "analysis_id": analysis_id,
            "report_id": "rpt-api-1",
            "generated_at": "2026-07-28T12:00:00+00:00",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["analysis_id"] == analysis_id
    report = body["report"]
    assert report["metadata"]["report_id"] == "rpt-api-1"
    assert report["executive_summary"]["rs_id"] == "RS-001"
    assert report["market_data"]["available"] is True
    assert report["financial_statements"]["message"] == "Data unavailable."
    assert report["audit"]["payload"]["analysis_id"] == analysis_id
    assert report["version"]["research_object_schema_version"] == "1.0.0"


def test_generate_report_requires_object(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.post(
        "/api/v1/research/report", headers=auth_headers, json={}
    )
    assert response.status_code == 422
