"""EPIC-R001 Research Object API tests."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from api_platform import create_app
from auth_test_helpers import bearer_headers, register_user
from data_engine import DataOrchestrator
from dsp_platform import DSPPlatform, PlatformBuilder, PlatformConfiguration
from dsp_platform.data_orchestrator import reset_data_orchestrator_for_tests
from dsp_platform.investment_provenance import (
    RELEASE_IDENTITY,
    InMemoryInvestmentProvenanceStore,
    InvestmentProvenanceRecord,
    reset_investment_provenance_store_for_tests,
)


@pytest.fixture(autouse=True)
def _reset() -> None:
    reset_data_orchestrator_for_tests(None)
    yield
    reset_data_orchestrator_for_tests(None)
    reset_investment_provenance_store_for_tests(None)


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
    return app_client

@pytest.fixture
def auth_headers(client: TestClient) -> dict[str, str]:
    register_user(client, user_id="research-obj-user", username="researchobj")
    return bearer_headers(client, username="researchobj")


def _mock_orch() -> DataOrchestrator:
    return DataOrchestrator(
        fetch_market_quote=lambda: {
            "authenticated": True,
            "fields": {"current_price": 190.5},
            "provenance": {
                "provider_id": "mq",
                "provider_name": "MQ",
                "source_type": "licensed_vendor",
                "retrieved_at": "2026-07-28T00:00:00+00:00",
            },
        },
        fetch_financial_statements=lambda: None,
        fetch_corporate_actions=lambda: None,
        fetch_historical_series=lambda: None,
        health_market_quote=lambda: {
            "provider_id": "mq",
            "healthy": True,
            "authenticated": True,
        },
        health_financial_statements=lambda: {
            "provider_id": "fs",
            "healthy": True,
            "authenticated": False,
        },
        health_corporate_actions=lambda: {
            "provider_id": "ca",
            "healthy": True,
            "authenticated": False,
        },
        health_historical_series=lambda: {
            "provider_id": "hs",
            "healthy": True,
            "authenticated": False,
        },
    )


def test_research_object_schema(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.get("/api/v1/research/object/schema")
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["schema"]["schema_version"] == "1.0.0"
    assert body["schema"]["immutable"] is True


def test_research_object_build_with_fetch(client: TestClient, auth_headers: dict[str, str]) -> None:
    reset_data_orchestrator_for_tests(_mock_orch())
    aid = str(uuid4())
    now = datetime.now(tz=UTC).isoformat()
    from dsp_platform.investment_provenance import get_investment_provenance_store

    get_investment_provenance_store().append(
        InvestmentProvenanceRecord(
            analysis_id=aid,
            created_at=now,
            ticker="AAPL",
            owner_user_id="research-obj-user",
            valuation={
                "status": "succeeded",
                "available": True,
                "score": 0.5,
                "label": "ok",
                "market_price": 190.5,
                "margin_of_safety": 0.2,
                "reason": None,
            },
            buffett={"overall_status": "unavailable", "recommendation": "Research Mode"},
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
    response = client.post(
        "/api/v1/research/object",
        headers=auth_headers,
        json={
            "symbol": "AAPL",
            "analysis_id": aid,
            "fetch_data_bundle": True,
            "analysis_payload": {
                "ok": True,
                "recommendation_summary": {"margin_of_safety": 0.2},
                "stage_summaries": [
                    {"stage": "valuation", "has_result": True, "summary": "v"}
                ],
            },
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["analysis_id"] == aid
    ro = body["research_object"]
    assert ro["identity"]["available"] is True
    assert ro["market_data"]["available"] is True
    assert ro["market_data"]["payload"]["fields"]["current_price"] == 190.5
    assert ro["financial_statements"]["message"] == "Data unavailable."
    assert ro["margin_of_safety"]["payload"]["margin_of_safety"] == 0.2
    assert ro["audit"]["payload"]["analysis_id"] == aid
    assert ro["version"]["schema_version"] == "1.0.0"


def test_research_object_without_fetch(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.post(
        "/api/v1/research/object",
        headers=auth_headers,
        json={
            "symbol": "MSFT",
            "fetch_data_bundle": False,
            "data_bundle": None,
            "analysis_payload": None,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["research_object"]["market_data"]["available"] is False
    assert body["research_object"]["market_data"]["message"] == "Data unavailable."
