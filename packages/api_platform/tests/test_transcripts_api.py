"""Data Connector Framework authenticated transcripts API tests."""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest
from fastapi.testclient import TestClient

from api_platform import create_app
from data_engine import (
    ConnectorProvenance,
    EarningsCallTranscript,
    InMemoryCache,
    InMemoryTranscriptAdapter,
    RateLimiter,
    RetryPolicy,
    TranscriptService,
    build_transcripts_bundle_from_mapping,
)
from dsp_platform import DSPPlatform, PlatformBuilder, PlatformConfiguration
from dsp_platform.transcripts import reset_transcripts_service_for_tests


@pytest.fixture(autouse=True)
def _reset_service() -> None:
    reset_transcripts_service_for_tests(None)
    yield
    reset_transcripts_service_for_tests(None)


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


def _seed_service() -> TranscriptService:
    adapter = InMemoryTranscriptAdapter(api_key="test-key")
    adapter.put(
        build_transcripts_bundle_from_mapping(
            symbol="AAPL",
            transcripts=[
                EarningsCallTranscript(
                    transcript_id="t-2023-q3",
                    quarter=3,
                    year=2023,
                    call_date=date(2023, 8, 3),
                    title="AAPL Q3 2023 Earnings Call Transcript",
                    content="Operator: Welcome to the call...",
                )
            ],
            provenance=ConnectorProvenance(
                provider_id="memory_transcripts",
                provider_name="Memory",
                source_type="licensed_vendor",
                retrieved_at=datetime.now(tz=UTC),
                auth_mode="api_key",
            ),
        )
    )
    return TranscriptService(
        adapter,
        cache=InMemoryCache(),
        cache_ttl_seconds=60,
        rate_limiter=RateLimiter(requests_per_minute=120),
        retry=RetryPolicy(max_attempts=2, backoff_seconds=0.0),
    )


def test_transcripts_unavailable_by_default(client: TestClient) -> None:
    response = client.get("/api/v1/transcripts", params={"symbol": "AAPL"})
    assert response.status_code == 200
    body = response.json()
    assert body["available"] is False
    assert body["message"] == "Data unavailable."
    assert body["transcripts"] is None


def test_transcripts_authenticated_payload(client: TestClient) -> None:
    reset_transcripts_service_for_tests((_seed_service(),))
    response = client.get("/api/v1/transcripts", params={"symbol": "AAPL"})
    assert response.status_code == 200
    body = response.json()
    assert body["available"] is True
    assert body["authenticated"] is True
    assert body["transcripts"][0]["quarter"] == 3
    assert body["provenance"]["provider_id"] == "memory_transcripts"


def test_transcripts_health(client: TestClient) -> None:
    response = client.get("/api/v1/transcripts/health")
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert "providers" in body
