"""EPIC-D001 authenticated market quote API tests."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from api_platform import create_app
from data_engine import (
    InMemoryAuthenticatedQuoteAdapter,
    InMemoryCache,
    MarketQuoteProvenance,
    MarketQuoteService,
    RateLimiter,
    RetryPolicy,
    build_quote_from_mapping,
)
from dsp_platform import DSPPlatform, PlatformBuilder, PlatformConfiguration
from dsp_platform.market_quotes import reset_market_quote_service_for_tests


@pytest.fixture(autouse=True)
def _reset_quote_service() -> None:
    reset_market_quote_service_for_tests(None)
    yield
    reset_market_quote_service_for_tests(None)


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


def _seed_service() -> MarketQuoteService:
    adapter = InMemoryAuthenticatedQuoteAdapter(api_key="test-key")
    adapter.put(
        build_quote_from_mapping(
            symbol="AAPL",
            payload={
                "exchange": "NASDAQ",
                "currency": "USD",
                "current_price": 190.5,
                "open": 189.0,
                "high": 191.0,
                "low": 188.5,
                "previous_close": 188.0,
                "week_52_high": 200.0,
                "week_52_low": 140.0,
                "volume": 1_000_000,
                "average_volume": 900_000,
                "market_cap": 3_000_000_000_000,
                "enterprise_value": 3_100_000_000_000,
                "shares_outstanding": 15_000_000_000,
                "dividend_yield": 0.005,
                "beta": 1.2,
            },
            provenance=MarketQuoteProvenance(
                provider_id="memory_authenticated_quote",
                provider_name="Memory",
                source_type="licensed_vendor",
                retrieved_at=datetime.now(tz=UTC),
                auth_mode="api_key",
            ),
        )
    )
    return MarketQuoteService(
        adapter,
        cache=InMemoryCache(),
        cache_ttl_seconds=60,
        rate_limiter=RateLimiter(requests_per_minute=120),
        retry=RetryPolicy(max_attempts=2, backoff_seconds=0.0),
    )


def test_market_quote_unavailable_by_default(client: TestClient) -> None:
    response = client.get("/api/v1/market/quote", params={"symbol": "AAPL"})
    assert response.status_code == 200
    body = response.json()
    assert body["available"] is False
    assert body["message"] == "Data unavailable."
    assert body["fields"] is None


def test_market_quote_authenticated_payload(client: TestClient) -> None:
    reset_market_quote_service_for_tests(_seed_service())
    response = client.get("/api/v1/market/quote", params={"symbol": "AAPL"})
    assert response.status_code == 200
    body = response.json()
    assert body["available"] is True
    assert body["authenticated"] is True
    assert body["fields"]["current_price"] == pytest.approx(190.5)
    assert body["provenance"]["provider_id"] == "memory_authenticated_quote"
    assert Decimal(str(body["fields"]["beta"])) == Decimal("1.2")


def test_market_health(client: TestClient) -> None:
    response = client.get("/api/v1/market/health")
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert "provider" in body
