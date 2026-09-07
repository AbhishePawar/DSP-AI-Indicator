"""SIMPLE-13 Security Master HTTP contract. Does not change POST /analyse."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api_platform import create_app
from auth_test_helpers import bearer_headers, register_user
from dsp_platform import DSPPlatform, PlatformBuilder, PlatformConfiguration
from dsp_platform.security_master.ingest import ingest_documents
from dsp_platform.security_master.models import SourceDocument
from dsp_platform.security_master.store import (
    MemorySecurityMasterStore,
    reset_security_master_store_for_tests,
)


def _doc(source_id: str, exchange: str, kind: str, body: bytes, uri: str) -> SourceDocument:
    return SourceDocument(
        source_id=source_id,
        exchange=exchange,
        document_kind=kind,
        uri=uri,
        body=body,
        retrieved_at="2026-09-07T12:00:00+00:00",
        last_modified="Sun, 06 Sep 2026 21:35:03 GMT",
        content_type="text/csv",
        status=200,
    )


def _seed_universe() -> None:
    reset_security_master_store_for_tests(MemorySecurityMasterStore())
    equity = (
        b"SYMBOL,NAME OF COMPANY,SERIES,ISIN NUMBER\n"
        b"WIPRO,Wipro Limited,EQ,INE075A01022\n"
        b"AAKASH,Aakash Exploration Services Limited,EQ,INE087Z01024\n"
    )
    bse = json.dumps(
        [
            {
                "scrip_id": "WIPRO",
                "Issuer_Name": "Wipro Limited",
                "ISIN_NUMBER": "INE075A01022",
                "SCRIP_CD": "507685",
                "GROUP": "A",
                "Status": "Active",
            },
            {
                "scrip_id": "ANDHRAPET",
                "Issuer_Name": "Andhra Petrochemicals Ltd",
                "ISIN_NUMBER": "INE714B01016",
                "SCRIP_CD": "500012",
                "GROUP": "X",
                "Status": "Active",
            },
        ]
    ).encode("utf-8")
    ingest_documents(
        (
            _doc(
                "nse_equity",
                "NSE",
                "equity",
                equity,
                "https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv",
            ),
            _doc(
                "bse_active",
                "BSE",
                "equity_active",
                bse,
                "https://api.bseindia.com/BseIndiaAPI/api/ListofScripData/w?status=Active",
            ),
        )
    )


@pytest.fixture
def platform() -> DSPPlatform:
    return (
        PlatformBuilder()
        .with_configuration(PlatformConfiguration(require_analysis_service=False))
        .auto_ready(True)
        .build()
    )


@pytest.fixture
def client(platform: DSPPlatform, tmp_path: Path) -> TestClient:
    _ = tmp_path
    app = create_app(platform=platform)
    _seed_universe()
    try:
        yield TestClient(app)
    finally:
        reset_security_master_store_for_tests(MemorySecurityMasterStore())


@pytest.fixture
def headers(client: TestClient) -> dict[str, str]:
    register_user(
        client,
        user_id="u-sec-1",
        username="secuser",
        roles=["research_analyst"],
    )
    return bearer_headers(client, username="secuser")


def test_search_requires_auth(client: TestClient) -> None:
    response = client.get("/api/v1/securities/search", params={"q": "WIPRO"})
    assert response.status_code == 401


def test_search_wipro_is_dual_listing(client: TestClient, headers: dict[str, str]) -> None:
    response = client.get(
        "/api/v1/securities/search",
        params={"q": "WIPRO"},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["available"] is True
    assert payload["resolution"] == "DUAL_LISTING_CANDIDATES"
    assert {row["exchange"] for row in payload["candidates"]} == {"NSE", "BSE"}
    assert all(row["isin"] == "INE075A01022" for row in payload["candidates"])


def test_search_company_name_isin_and_bse_code(client: TestClient, headers: dict[str, str]) -> None:
    name = client.get("/api/v1/securities/search", params={"q": "Wipro"}, headers=headers)
    assert name.status_code == 200
    assert name.json()["resolution"] == "DUAL_LISTING_CANDIDATES"
    isin = client.get(
        "/api/v1/securities/search",
        params={"q": "INE075A01022"},
        headers=headers,
    )
    assert isin.json()["resolution"] == "DUAL_LISTING_CANDIDATES"
    code = client.get("/api/v1/securities/search", params={"q": "507685"}, headers=headers)
    assert code.status_code == 200
    payload = code.json()
    assert payload["resolution"] == "EXACT"
    assert payload["candidates"][0]["exchange"] == "BSE"
    assert payload["candidates"][0]["exchange_security_code"] == "507685"


def test_search_unknown_fails_closed(client: TestClient, headers: dict[str, str]) -> None:
    response = client.get(
        "/api/v1/securities/search",
        params={"q": "THIS_SECURITY_DOES_NOT_EXIST"},
        headers=headers,
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["resolution"] == "UNKNOWN"
    assert payload["candidates"] == []


def test_universe_metadata(client: TestClient, headers: dict[str, str]) -> None:
    response = client.get("/api/v1/securities/universe", headers=headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload["available"] is True
    assert payload["snapshot"]["source_date"] == "2026-09-06"
    assert payload["snapshot"]["counts"]["dual_listed"] == 1


def test_ingest_requires_admin(client: TestClient, headers: dict[str, str]) -> None:
    response = client.post("/api/v1/securities/universe/ingest", headers=headers)
    assert response.status_code == 403


def test_analyse_route_still_exists(client: TestClient, headers: dict[str, str]) -> None:
    response = client.post("/api/v1/analyse", headers=headers, json={"ticker": "WIPRO"})
    assert response.status_code != 404


def test_search_empty_query_does_not_dump(client: TestClient, headers: dict[str, str]) -> None:
    response = client.get("/api/v1/securities/search", params={"q": ""}, headers=headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload["candidates"] == []
    assert payload["available"] is True
    assert payload["resolution"] == "UNKNOWN"


def test_search_without_snapshot_is_data_unavailable(platform: DSPPlatform) -> None:
    reset_security_master_store_for_tests(MemorySecurityMasterStore())
    app = create_app(platform=platform)
    client = TestClient(app)
    register_user(client, user_id="u-sec-empty", username="secempty", roles=["research_analyst"])
    headers = bearer_headers(client, username="secempty")
    try:
        response = client.get(
            "/api/v1/securities/search",
            params={"q": "WIPRO"},
            headers=headers,
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["available"] is False
        assert payload["resolution"] == "UNAVAILABLE"
        assert payload["message"] == "Data unavailable."
        assert payload["candidates"] == []
    finally:
        reset_security_master_store_for_tests(MemorySecurityMasterStore())


def test_search_database_unavailable_fails_closed(client: TestClient, headers: dict[str, str], monkeypatch: pytest.MonkeyPatch) -> None:
    class BoomStore:
        def current_snapshot(self):
            raise RuntimeError("database unavailable")

    monkeypatch.setattr(
        "api_platform.api.routers.securities.get_security_master_store",
        lambda: BoomStore(),
    )
    response = client.get(
        "/api/v1/securities/search",
        params={"q": "WIPRO"},
        headers=headers,
    )
    assert response.status_code == 503
    assert "Data unavailable." in response.text


def test_analyse_rejects_unknown_fields(client: TestClient, headers: dict[str, str]) -> None:
    response = client.post(
        "/api/v1/analyse",
        headers=headers,
        json={"ticker": "WIPRO", "listing_id": "should-not-pass"},
    )
    assert response.status_code == 422
