"""EPIC-D002 authenticated financial statement API tests."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from api_platform import create_app
from data_engine import (
    FinancialStatementProvenance,
    FinancialStatementService,
    InMemoryAuthenticatedStatementAdapter,
    InMemoryCache,
    RateLimiter,
    RetryPolicy,
    build_statements_from_mapping,
)
from dsp_platform import DSPPlatform, PlatformBuilder, PlatformConfiguration
from dsp_platform.financial_statements import (
    reset_financial_statement_service_for_tests,
)


@pytest.fixture(autouse=True)
def _reset_statement_service() -> None:
    reset_financial_statement_service_for_tests(None)
    yield
    reset_financial_statement_service_for_tests(None)


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


def _seed_service() -> FinancialStatementService:
    adapter = InMemoryAuthenticatedStatementAdapter(api_key="test-key")
    adapter.put(
        build_statements_from_mapping(
            symbol="AAPL",
            payload={
                "identity": {
                    "symbol": "AAPL",
                    "exchange": "NASDAQ",
                    "currency": "USD",
                    "provider_company_id": "AAPL-USD",
                },
                "reporting_currency": "USD",
                "periods": [
                    {
                        "period_type": "annual",
                        "fiscal_year": 2024,
                        "period_end": "2024-09-28",
                        "reporting_currency": "USD",
                        "income_statement": {"revenue": 391_000_000_000},
                        "balance_sheet": {"cash": 60_000_000_000},
                        "cash_flow": {"operating_cash_flow": 110_000_000_000},
                        "ratios": {"roe": 0.15},
                    }
                ],
            },
            provenance=FinancialStatementProvenance(
                provider_id="memory_authenticated_statements",
                provider_name="Memory",
                source_type="licensed_vendor",
                retrieved_at=datetime.now(tz=UTC),
                auth_mode="api_key",
            ),
        )
    )
    return FinancialStatementService(
        adapter,
        cache=InMemoryCache(),
        cache_ttl_seconds=60,
        rate_limiter=RateLimiter(requests_per_minute=120),
        retry=RetryPolicy(max_attempts=2, backoff_seconds=0.0),
    )


def test_statements_unavailable_by_default(client: TestClient) -> None:
    response = client.get(
        "/api/v1/fundamentals/statements", params={"symbol": "AAPL"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["available"] is False
    assert body["message"] == "Data unavailable."
    assert body["periods"] is None


def test_statements_authenticated_payload(client: TestClient) -> None:
    reset_financial_statement_service_for_tests(_seed_service())
    response = client.get(
        "/api/v1/fundamentals/statements", params={"symbol": "AAPL"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["available"] is True
    assert body["authenticated"] is True
    assert body["periods"][0]["income_statement"]["revenue"] == pytest.approx(
        391_000_000_000
    )
    assert body["provenance"]["provider_id"] == "memory_authenticated_statements"


def test_resolve_and_health(client: TestClient) -> None:
    reset_financial_statement_service_for_tests(_seed_service())
    resolve = client.get("/api/v1/fundamentals/resolve", params={"symbol": "AAPL"})
    assert resolve.status_code == 200
    assert resolve.json()["available"] is True
    assert resolve.json()["identity"]["provider_company_id"] == "AAPL-USD"

    health = client.get("/api/v1/fundamentals/health")
    assert health.status_code == 200
    assert health.json()["ok"] is True
    assert "provider" in health.json()
