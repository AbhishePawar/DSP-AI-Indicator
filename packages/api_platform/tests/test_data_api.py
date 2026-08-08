"""EPIC-D005 unified data gateway API tests."""

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


def test_data_bundle_partial(client: TestClient) -> None:
    reset_data_orchestrator_for_tests(_mock_orch())
    response = client.get("/api/v1/data/bundle", params={"symbol": "AAPL"})
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    bundle = body["bundle"]
    assert bundle["market_quote"]["status"]["status"] == "ok"
    assert bundle["financial_statements"]["status"]["message"] == "Data unavailable."
    assert bundle["retrieval"]["partial"] is True
    assert bundle["retrieval"]["any_available"] is True


def test_data_bundle_default_all_unavailable(client: TestClient) -> None:
    response = client.get("/api/v1/data/bundle", params={"symbol": "AAPL"})
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["bundle"]["retrieval"]["any_available"] is False
    assert body["bundle"]["market_quote"]["status"]["message"] == "Data unavailable."


def test_data_health(client: TestClient) -> None:
    reset_data_orchestrator_for_tests(_mock_orch())
    response = client.get("/api/v1/data/health")
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert "providers" in body["health"]
    assert body["health"]["overall_authenticated"] is True
