"""Data Connector Framework authenticated ESG API tests."""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest
from fastapi.testclient import TestClient

from api_platform import create_app
from data_engine import (
    ConnectorField,
    ConnectorProvenance,
    EsgService,
    InMemoryCache,
    InMemoryEsgAdapter,
    RateLimiter,
    RetryPolicy,
    build_esg_score_from_mapping,
)
from dsp_platform import DSPPlatform, PlatformBuilder, PlatformConfiguration
from dsp_platform.esg import reset_esg_service_for_tests


@pytest.fixture(autouse=True)
def _reset_service() -> None:
    reset_esg_service_for_tests(None)
    yield
    reset_esg_service_for_tests(None)


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


def _seed_service() -> EsgService:
    adapter = InMemoryEsgAdapter(api_key="test-key")
    adapter.put(
        build_esg_score_from_mapping(
            symbol="AAPL",
            as_of=date(2023, 12, 31),
            environmental_score=ConnectorField.of(20.0),
            social_score=ConnectorField.of(15.0),
            governance_score=ConnectorField.of(10.0),
            total_score=ConnectorField.of(45.0),
            controversy_level="low",
            provenance=ConnectorProvenance(
                provider_id="memory_esg",
                provider_name="Memory",
                source_type="licensed_vendor",
                retrieved_at=datetime.now(tz=UTC),
                auth_mode="api_key",
            ),
        )
    )
    return EsgService(
        adapter,
        cache=InMemoryCache(),
        cache_ttl_seconds=60,
        rate_limiter=RateLimiter(requests_per_minute=120),
        retry=RetryPolicy(max_attempts=2, backoff_seconds=0.0),
    )


def test_esg_unavailable_by_default(client: TestClient) -> None:
    response = client.get("/api/v1/esg", params={"symbol": "AAPL"})
    assert response.status_code == 200
    body = response.json()
    assert body["available"] is False
    assert body["message"] == "Data unavailable."


def test_esg_authenticated_payload(client: TestClient) -> None:
    reset_esg_service_for_tests((_seed_service(),))
    response = client.get("/api/v1/esg", params={"symbol": "AAPL"})
    assert response.status_code == 200
    body = response.json()
    assert body["available"] is True
    assert body["authenticated"] is True
    assert body["total_score"] == pytest.approx(45.0)
    assert body["controversy_level"] == "low"
    assert body["provenance"]["provider_id"] == "memory_esg"


def test_esg_health(client: TestClient) -> None:
    response = client.get("/api/v1/esg/health")
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert "providers" in body
