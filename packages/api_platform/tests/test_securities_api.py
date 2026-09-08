"""Security Master HTTP routes — official NSE/BSE identity only."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api_platform import create_app
from dsp_platform import DSPPlatform, PlatformBuilder, PlatformConfiguration


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


def test_search_infy_returns_official_listings(client: TestClient) -> None:
    response = client.get("/api/v1/securities/search", params={"q": "INFY"})
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["status"] == "MATCHES"
    tickers = {row["ticker"] for row in body["results"]}
    assert tickers == {"INFY"}
    isins = {row["isin"] for row in body["results"]}
    assert isins == {"INE009A01021"}
    mics = {row["mic"] for row in body["results"]}
    assert "XNSE" in mics
    assert "XBOM" in mics
    assert all("NSE_EQ|" not in str(row) for row in body["results"])


def test_resolve_infy_nse(client: TestClient) -> None:
    response = client.get(
        "/api/v1/securities/resolve",
        params={"q": "INFY", "exchange": "NSE"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "RESOLVED"
    identity = body["identity"]
    assert identity["ticker"] == "INFY"
    assert identity["company_name"] == "Infosys Limited"
    assert identity["isin"] == "INE009A01021"
    assert identity["mic"] == "XNSE"
    assert identity["eligibility"] is True


def test_resolve_hdfcbank_and_wipro(client: TestClient) -> None:
    hdfc = client.get(
        "/api/v1/securities/resolve",
        params={"q": "HDFCBANK", "exchange": "NSE"},
    ).json()
    assert hdfc["status"] == "RESOLVED"
    assert hdfc["identity"]["isin"] == "INE040A01034"
    assert hdfc["identity"]["mic"] == "XNSE"
    wipro = client.get(
        "/api/v1/securities/search", params={"q": "Wipro", "exchange": "NSE"}
    ).json()
    assert wipro["status"] == "MATCHES"
    assert wipro["results"][0]["ticker"] == "WIPRO"
    assert wipro["results"][0]["isin"] == "INE075A01022"


def test_resolve_dual_listed_without_exchange_is_ambiguous(client: TestClient) -> None:
    body = client.get("/api/v1/securities/resolve", params={"q": "INFY"}).json()
    assert body["status"] == "AMBIGUOUS"
    assert body["identity"] is None
    assert {row["mic"] for row in body["candidates"]} == {"XNSE", "XBOM"}


def test_unknown_ticker(client: TestClient) -> None:
    body = client.get(
        "/api/v1/securities/search", params={"q": "ZZZZZUNKNOWN"}
    ).json()
    assert body["status"] == "UNKNOWN"
    assert body["results"] == []


def test_vendor_shaped_identity_rejected(client: TestClient) -> None:
    body = client.get(
        "/api/v1/securities/search",
        params={"q": "NSE_EQ|INE009A01021"},
    ).json()
    assert body["status"] == "REJECTED"
    assert body["results"] == []
    resolved = client.get(
        "/api/v1/securities/resolve",
        params={"q": "NSE_EQ|INE009A01021"},
    ).json()
    assert resolved["status"] == "REJECTED"
    assert resolved["identity"] is None


def test_name_search_infosys_and_hdfc_bank(client: TestClient) -> None:
    infosys = client.get("/api/v1/securities/search", params={"q": "Infosys"}).json()
    assert infosys["status"] == "MATCHES"
    assert any(
        row["ticker"] == "INFY" and row["isin"] == "INE009A01021"
        for row in infosys["results"]
    )
    hdfc = client.get("/api/v1/securities/search", params={"q": "HDFC Bank"}).json()
    assert hdfc["status"] == "MATCHES"
    assert any(row["ticker"] == "HDFCBANK" for row in hdfc["results"])
