"""Data Connector Framework authenticated news API tests."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from api_platform import create_app
from data_engine import (
    ConnectorProvenance,
    InMemoryCache,
    InMemoryNewsAdapter,
    NewsArticle,
    NewsService,
    RateLimiter,
    RetryPolicy,
    build_news_feed_from_mapping,
)
from dsp_platform import DSPPlatform, PlatformBuilder, PlatformConfiguration
from dsp_platform.news import reset_news_service_for_tests


@pytest.fixture(autouse=True)
def _reset_service() -> None:
    reset_news_service_for_tests(None)
    yield
    reset_news_service_for_tests(None)


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


def _seed_service() -> NewsService:
    adapter = InMemoryNewsAdapter(api_key="test-key")
    adapter.put(
        build_news_feed_from_mapping(
            symbol="AAPL",
            articles=[
                NewsArticle(
                    article_id="a-1",
                    headline="Apple posts record quarter",
                    url="https://example.com/a-1",
                    source="Example Wire",
                    published_at=datetime.now(tz=UTC),
                )
            ],
            provenance=ConnectorProvenance(
                provider_id="memory_news",
                provider_name="Memory",
                source_type="licensed_vendor",
                retrieved_at=datetime.now(tz=UTC),
                auth_mode="api_key",
            ),
        )
    )
    return NewsService(
        adapter,
        cache=InMemoryCache(),
        cache_ttl_seconds=60,
        rate_limiter=RateLimiter(requests_per_minute=120),
        retry=RetryPolicy(max_attempts=2, backoff_seconds=0.0),
    )


def test_news_unavailable_by_default(client: TestClient) -> None:
    response = client.get("/api/v1/news", params={"symbol": "AAPL"})
    assert response.status_code == 200
    body = response.json()
    assert body["available"] is False
    assert body["message"] == "Data unavailable."
    assert body["articles"] is None


def test_news_authenticated_payload(client: TestClient) -> None:
    reset_news_service_for_tests((_seed_service(),))
    response = client.get("/api/v1/news", params={"symbol": "AAPL"})
    assert response.status_code == 200
    body = response.json()
    assert body["available"] is True
    assert body["authenticated"] is True
    assert body["articles"][0]["headline"] == "Apple posts record quarter"
    assert body["provenance"]["provider_id"] == "memory_news"
    assert body["attempted_provider_ids"] == ["memory_news"]


def test_news_health(client: TestClient) -> None:
    response = client.get("/api/v1/news/health")
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert "providers" in body
