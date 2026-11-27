"""Historical financial research HTTP boundary tests."""

import pytest

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from api_platform.api.routers import analysis

from api_platform.api.dependencies import (
    require_authenticated_actor,
)

from dsp_platform.public_financial_research import (
    PublicFinancialResearchError,
)


PATH = "/analyze/company/historical-financials"

REQUEST = {
    "ticker": "INFY",
    "exchange": "NSE",
    "fiscal_year": 2025,
}


@pytest.fixture
def app():

    app = FastAPI()

    app.include_router(analysis.router)

    app.dependency_overrides[
        require_authenticated_actor
    ] = lambda: {"user_id": "test-research-user"}

    return app


def test_authenticated_historical_research(
    app,
    monkeypatch,
):

    def fake_analyze(self, ticker, *, exchange, fiscal_year):

        assert ticker == "INFY"
        assert exchange == "NSE"
        assert fiscal_year == 2025

        return {
            "ticker": ticker,
            "authenticated_provider": False,
            "authorized_for_valuation": False,
            "limitations": [
                "Historical research only."
            ],
        }

    monkeypatch.setattr(
        analysis.PublicFinancialResearchService,
        "analyze",
        fake_analyze,
    )

    response = TestClient(app).post(
        PATH,
        json=REQUEST,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["ok"] is True

    assert (
        data["payload"]["authorized_for_valuation"]
        is False
    )

    assert (
        data["payload"]["authenticated_provider"]
        is False
    )


def test_unauthenticated_request_rejected(
    app,
    monkeypatch,
):

    def denied():

        raise HTTPException(
            status_code=401,
            detail="Authentication required",
        )

    app.dependency_overrides[
        require_authenticated_actor
    ] = denied

    def unexpected(*args, **kwargs):

        pytest.fail("Unauthenticated request reached research service")

    monkeypatch.setattr(
        analysis.PublicFinancialResearchService,
        "analyze",
        unexpected,
    )

    response = TestClient(app).post(
        PATH,
        json=REQUEST,
    )

    assert response.status_code == 401


def test_unsupported_financial_research(
    app,
    monkeypatch,
):

    def unsupported(*args, **kwargs):

        raise PublicFinancialResearchError(
            "Unsupported instrument"
        )

    monkeypatch.setattr(
        analysis.PublicFinancialResearchService,
        "analyze",
        unsupported,
    )

    response = TestClient(app).post(
        PATH,
        json=REQUEST,
    )

    assert response.status_code == 422


def test_provider_failure_degrades_safely(
    app,
    monkeypatch,
):

    def unavailable(*args, **kwargs):

        raise TimeoutError("Private network error")

    monkeypatch.setattr(
        analysis.PublicFinancialResearchService,
        "analyze",
        unavailable,
    )

    response = TestClient(app).post(
        PATH,
        json=REQUEST,
    )

    assert response.status_code == 503

    assert "Private network error" not in response.text


def test_invalid_year_rejected(app):

    response = TestClient(app).post(
        PATH,
        json={
            **REQUEST,
            "fiscal_year": 1800,
        },
    )

    assert response.status_code == 422


def test_empty_ticker_rejected(app):

    response = TestClient(app).post(
        PATH,
        json={
            **REQUEST,
            "ticker": "",
        },
    )

    assert response.status_code == 422


def test_capacity_limit(
    app,
    monkeypatch,
):

    class ExhaustedCapacity:

        def acquire(self, blocking=False):

            return False

    monkeypatch.setattr(
        analysis,
        "_HISTORICAL_RESEARCH_CAPACITY",
        ExhaustedCapacity(),
    )

    response = TestClient(app).post(
        PATH,
        json=REQUEST,
    )

    assert response.status_code == 429
