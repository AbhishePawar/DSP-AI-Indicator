"""EPIC-R001 Research Object API tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api_platform import create_app
from data_engine import DataOrchestrator
from dsp_platform import DSPPlatform, PlatformBuilder, PlatformConfiguration
from dsp_platform.data_orchestrator import reset_data_orchestrator_for_tests


@pytest.fixture(autouse=True)
def _reset() -> None:
    reset_data_orchestrator_for_tests(None)
    yield
    reset_data_orchestrator_for_tests(None)


@pytest.fixture
def platform() -> DSPPlatform:
    return (
        PlatformBuilder()
        .with_configuration(PlatformConfiguration(require_analysis_service=False))
        .build()
    )


@pytest.fixture
def client(platform: DSPPlatform) -> TestClient:
    return TestClient(create_app(platform=platform))


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


def test_research_object_schema(client: TestClient) -> None:
    response = client.get("/api/v1/research/object/schema")
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["schema"]["schema_version"] == "1.0.0"
    assert body["schema"]["immutable"] is True


def test_research_object_build_with_fetch(client: TestClient) -> None:
    reset_data_orchestrator_for_tests(_mock_orch())
    response = client.post(
        "/api/v1/research/object",
        json={
            "symbol": "AAPL",
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
    ro = body["research_object"]
    assert ro["identity"]["available"] is True
    assert ro["market_data"]["available"] is True
    assert ro["market_data"]["payload"]["fields"]["current_price"] == 190.5
    assert ro["financial_statements"]["message"] == "Data unavailable."
    assert ro["valuation"]["available"] is True
    assert ro["margin_of_safety"]["payload"]["margin_of_safety"] == 0.2
    assert ro["version"]["schema_version"] == "1.0.0"


def test_research_object_without_fetch(client: TestClient) -> None:
    response = client.post(
        "/api/v1/research/object",
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
