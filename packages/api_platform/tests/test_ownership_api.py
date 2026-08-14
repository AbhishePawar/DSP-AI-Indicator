"""Data Connector Framework authenticated ownership API tests."""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest
from fastapi.testclient import TestClient

from api_platform import create_app
from data_engine import (
    ConnectorField,
    ConnectorProvenance,
    InMemoryCache,
    InMemoryOwnershipAdapter,
    OwnershipService,
    OwnershipStake,
    RateLimiter,
    RetryPolicy,
    build_ownership_bundle_from_mapping,
)
from dsp_platform import DSPPlatform, PlatformBuilder, PlatformConfiguration
from dsp_platform.ownership import reset_ownership_service_for_tests


@pytest.fixture(autouse=True)
def _reset_service() -> None:
    reset_ownership_service_for_tests(None)
    yield
    reset_ownership_service_for_tests(None)


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


def _seed_service() -> OwnershipService:
    adapter = InMemoryOwnershipAdapter(api_key="test-key")
    adapter.put(
        build_ownership_bundle_from_mapping(
            symbol="RELIANCE",
            as_of=date(2023, 12, 31),
            stakes=[
                OwnershipStake(
                    holder_type="promoter",
                    holder_name="Promoters",
                    percent_held=ConnectorField.of(50.3),
                    shares_held=ConnectorField.missing(),
                )
            ],
            provenance=ConnectorProvenance(
                provider_id="memory_ownership",
                provider_name="Memory",
                source_type="licensed_vendor",
                retrieved_at=datetime.now(tz=UTC),
                auth_mode="api_key",
            ),
            promoter_holding_percent=ConnectorField.of(50.3),
        )
    )
    return OwnershipService(
        adapter,
        cache=InMemoryCache(),
        cache_ttl_seconds=60,
        rate_limiter=RateLimiter(requests_per_minute=120),
        retry=RetryPolicy(max_attempts=2, backoff_seconds=0.0),
    )


def test_ownership_unavailable_by_default(client: TestClient) -> None:
    response = client.get("/api/v1/ownership", params={"symbol": "RELIANCE"})
    assert response.status_code == 200
    body = response.json()
    assert body["available"] is False
    assert body["message"] == "Data unavailable."
    assert body["stakes"] is None


def test_ownership_authenticated_payload(client: TestClient) -> None:
    reset_ownership_service_for_tests((_seed_service(),))
    response = client.get("/api/v1/ownership", params={"symbol": "RELIANCE"})
    assert response.status_code == 200
    body = response.json()
    assert body["available"] is True
    assert body["authenticated"] is True
    assert body["stakes"][0]["holder_type"] == "promoter"
    assert body["promoter_holding_percent"] == pytest.approx(50.3)
    assert body["provenance"]["provider_id"] == "memory_ownership"


def test_ownership_health(client: TestClient) -> None:
    response = client.get("/api/v1/ownership/health")
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert "providers" in body
