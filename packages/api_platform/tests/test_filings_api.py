"""Data Connector Framework authenticated filings API tests."""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest
from fastapi.testclient import TestClient

from api_platform import create_app
from data_engine import (
    ConnectorProvenance,
    Filing,
    FilingsService,
    InMemoryCache,
    InMemoryFilingsAdapter,
    RateLimiter,
    RetryPolicy,
    build_filings_bundle_from_mapping,
)
from dsp_platform import DSPPlatform, PlatformBuilder, PlatformConfiguration
from dsp_platform.filings import reset_filings_service_for_tests


@pytest.fixture(autouse=True)
def _reset_service() -> None:
    reset_filings_service_for_tests(None)
    yield
    reset_filings_service_for_tests(None)


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


def _seed_service() -> FilingsService:
    adapter = InMemoryFilingsAdapter(api_key="test-key")
    adapter.put(
        build_filings_bundle_from_mapping(
            symbol="AAPL",
            filings=[
                Filing(
                    filing_id="f-1",
                    filing_type="10-K",
                    title="Apple Inc. Annual Report",
                    url="https://example.com/f-1",
                    filed_at=date(2023, 11, 3),
                )
            ],
            provenance=ConnectorProvenance(
                provider_id="memory_filings",
                provider_name="Memory",
                source_type="licensed_vendor",
                retrieved_at=datetime.now(tz=UTC),
                auth_mode="api_key",
            ),
        )
    )
    return FilingsService(
        adapter,
        cache=InMemoryCache(),
        cache_ttl_seconds=60,
        rate_limiter=RateLimiter(requests_per_minute=120),
        retry=RetryPolicy(max_attempts=2, backoff_seconds=0.0),
    )


def test_filings_unavailable_by_default(client: TestClient) -> None:
    response = client.get("/api/v1/filings", params={"symbol": "AAPL"})
    assert response.status_code == 200
    body = response.json()
    assert body["available"] is False
    assert body["message"] == "Data unavailable."
    assert body["filings"] is None


def test_filings_authenticated_payload(client: TestClient) -> None:
    reset_filings_service_for_tests((_seed_service(),))
    response = client.get("/api/v1/filings", params={"symbol": "AAPL"})
    assert response.status_code == 200
    body = response.json()
    assert body["available"] is True
    assert body["authenticated"] is True
    assert body["filings"][0]["filing_type"] == "10-K"
    assert body["provenance"]["provider_id"] == "memory_filings"


def test_filings_health(client: TestClient) -> None:
    response = client.get("/api/v1/filings/health")
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert "providers" in body
