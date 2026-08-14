"""Data Connector Framework authenticated insider trading API tests."""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest
from fastapi.testclient import TestClient

from api_platform import create_app
from data_engine import (
    ConnectorField,
    ConnectorProvenance,
    InMemoryCache,
    InMemoryInsiderTradingAdapter,
    InsiderTradingService,
    InsiderTransaction,
    RateLimiter,
    RetryPolicy,
    build_insider_activity_from_mapping,
)
from dsp_platform import DSPPlatform, PlatformBuilder, PlatformConfiguration
from dsp_platform.insider_trading import reset_insider_trading_service_for_tests


@pytest.fixture(autouse=True)
def _reset_service() -> None:
    reset_insider_trading_service_for_tests(None)
    yield
    reset_insider_trading_service_for_tests(None)


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


def _seed_service() -> InsiderTradingService:
    adapter = InMemoryInsiderTradingAdapter(api_key="test-key")
    adapter.put(
        build_insider_activity_from_mapping(
            symbol="AAPL",
            transactions=[
                InsiderTransaction(
                    transaction_id="t-1",
                    insider_name="Jane Doe",
                    role="CEO",
                    transaction_type="buy",
                    shares=ConnectorField.of(1000),
                    price=ConnectorField.of(10.0),
                    value=ConnectorField.of(10000.0),
                    transaction_date=date(2023, 6, 1),
                )
            ],
            provenance=ConnectorProvenance(
                provider_id="memory_insider_trading",
                provider_name="Memory",
                source_type="licensed_vendor",
                retrieved_at=datetime.now(tz=UTC),
                auth_mode="api_key",
            ),
        )
    )
    return InsiderTradingService(
        adapter,
        cache=InMemoryCache(),
        cache_ttl_seconds=60,
        rate_limiter=RateLimiter(requests_per_minute=120),
        retry=RetryPolicy(max_attempts=2, backoff_seconds=0.0),
    )


def test_insider_trading_unavailable_by_default(client: TestClient) -> None:
    response = client.get("/api/v1/insider-trading", params={"symbol": "AAPL"})
    assert response.status_code == 200
    body = response.json()
    assert body["available"] is False
    assert body["message"] == "Data unavailable."
    assert body["transactions"] is None


def test_insider_trading_authenticated_payload(client: TestClient) -> None:
    reset_insider_trading_service_for_tests((_seed_service(),))
    response = client.get("/api/v1/insider-trading", params={"symbol": "AAPL"})
    assert response.status_code == 200
    body = response.json()
    assert body["available"] is True
    assert body["authenticated"] is True
    assert body["transactions"][0]["transaction_type"] == "buy"
    assert body["provenance"]["provider_id"] == "memory_insider_trading"


def test_insider_trading_health(client: TestClient) -> None:
    response = client.get("/api/v1/insider-trading/health")
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert "providers" in body
