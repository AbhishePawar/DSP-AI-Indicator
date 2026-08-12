"""EPIC-D004 authenticated historical series API tests."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from api_platform import create_app
from data_engine import (
    HistoricalProvenance,
    HistoricalSeriesService,
    InMemoryAuthenticatedHistoricalAdapter,
    InMemoryCache,
    RateLimiter,
    RetryPolicy,
    build_historical_bundle_from_mapping,
)
from dsp_platform import DSPPlatform, PlatformBuilder, PlatformConfiguration
from dsp_platform.historical_series import reset_historical_series_service_for_tests


@pytest.fixture(autouse=True)
def _reset_service() -> None:
    reset_historical_series_service_for_tests(None)
    yield
    reset_historical_series_service_for_tests(None)


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


def _seed_service() -> HistoricalSeriesService:
    adapter = InMemoryAuthenticatedHistoricalAdapter(api_key="test-key")
    adapter.put(
        build_historical_bundle_from_mapping(
            symbol="AAPL",
            payload={
                "identity": {"symbol": "AAPL", "currency": "USD"},
                "series_kind": "ohlcv",
                "frequency": "daily",
                "bars": [
                    {
                        "date": "2024-01-02",
                        "open": 100,
                        "high": 105,
                        "low": 99,
                        "close": 104,
                        "volume": 1_000_000,
                    }
                ],
            },
            provenance=HistoricalProvenance(
                provider_id="memory_authenticated_historical",
                provider_name="Memory",
                source_type="licensed_vendor",
                retrieved_at=datetime.now(tz=UTC),
                auth_mode="api_key",
            ),
        )
    )
    return HistoricalSeriesService(
        adapter,
        cache=InMemoryCache(),
        cache_ttl_seconds=60,
        rate_limiter=RateLimiter(requests_per_minute=120),
        retry=RetryPolicy(max_attempts=2, backoff_seconds=0.0),
    )


def test_historical_unavailable_by_default(client: TestClient) -> None:
    response = client.get(
        "/api/v1/historical/series",
        params={"symbol": "AAPL", "series_kind": "ohlcv"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["available"] is False
    assert body["message"] == "Data unavailable."
    assert body["bars"] is None


def test_historical_authenticated_payload(client: TestClient) -> None:
    reset_historical_series_service_for_tests(_seed_service())
    response = client.get(
        "/api/v1/historical/series",
        params={"symbol": "AAPL", "series_kind": "ohlcv"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["available"] is True
    assert body["authenticated"] is True
    assert body["bars"][0]["close"] == pytest.approx(104)
    assert body["provenance"]["provider_id"] == "memory_authenticated_historical"


def test_historical_health(client: TestClient) -> None:
    response = client.get("/api/v1/historical/health")
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert "provider" in body
