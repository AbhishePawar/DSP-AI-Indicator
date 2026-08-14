"""EPIC-D003 authenticated corporate actions API tests."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from api_platform import create_app
from data_engine import (
    CorporateActionProvenance,
    CorporateActionService,
    InMemoryAuthenticatedCorporateActionAdapter,
    InMemoryCache,
    RateLimiter,
    RetryPolicy,
    build_actions_from_mapping,
)
from dsp_platform import DSPPlatform, PlatformBuilder, PlatformConfiguration
from dsp_platform.corporate_actions import reset_corporate_actions_service_for_tests


@pytest.fixture(autouse=True)
def _reset_service() -> None:
    reset_corporate_actions_service_for_tests(None)
    yield
    reset_corporate_actions_service_for_tests(None)


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


def _seed_service() -> CorporateActionService:
    adapter = InMemoryAuthenticatedCorporateActionAdapter(api_key="test-key")
    adapter.put(
        build_actions_from_mapping(
            symbol="AAPL",
            payload={
                "identity": {
                    "symbol": "AAPL",
                    "exchange": "NASDAQ",
                    "provider_company_id": "AAPL-USD",
                },
                "events": [
                    {
                        "action_id": "div-1",
                        "action_type": "dividend",
                        "ex_date": "2024-05-10",
                        "amount": 0.25,
                        "currency": "USD",
                    }
                ],
            },
            provenance=CorporateActionProvenance(
                provider_id="memory_authenticated_corporate_actions",
                provider_name="Memory",
                source_type="licensed_vendor",
                retrieved_at=datetime.now(tz=UTC),
                auth_mode="api_key",
            ),
        )
    )
    return CorporateActionService(
        adapter,
        cache=InMemoryCache(),
        cache_ttl_seconds=60,
        rate_limiter=RateLimiter(requests_per_minute=120),
        retry=RetryPolicy(max_attempts=2, backoff_seconds=0.0),
    )


def test_corporate_actions_unavailable_by_default(client: TestClient) -> None:
    response = client.get("/api/v1/corporate-actions", params={"symbol": "AAPL"})
    assert response.status_code == 200
    body = response.json()
    assert body["available"] is False
    assert body["message"] == "Data unavailable."
    assert body["events"] is None


def test_corporate_actions_authenticated_payload(client: TestClient) -> None:
    reset_corporate_actions_service_for_tests(_seed_service())
    response = client.get("/api/v1/corporate-actions", params={"symbol": "AAPL"})
    assert response.status_code == 200
    body = response.json()
    assert body["available"] is True
    assert body["authenticated"] is True
    assert body["events"][0]["action_type"] == "dividend"
    assert body["events"][0]["amount"] == pytest.approx(0.25)
    assert body["provenance"]["provider_id"] == "memory_authenticated_corporate_actions"


def test_corporate_actions_health(client: TestClient) -> None:
    response = client.get("/api/v1/corporate-actions/health")
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert "provider" in body
