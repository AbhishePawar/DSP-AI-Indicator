"""Opt-in select_listing on existing /fundamentals/resolve. Default path unchanged."""

from __future__ import annotations

from fastapi.testclient import TestClient

from api_platform import create_app
from dsp_platform import DSPPlatform, PlatformBuilder, PlatformConfiguration


def _platform() -> DSPPlatform:
    return (
        PlatformBuilder()
        .with_configuration(PlatformConfiguration(require_analysis_service=False))
        .build()
    )


def test_default_resolve_does_not_apply_indian_listing_policy(monkeypatch) -> None:
    platform = _platform()
    calls: list[tuple[str, str | None]] = []

    def _boom(symbol: str, *, explicit_exchange: str | None = None, candidates=None):
        calls.append((symbol, explicit_exchange))
        raise AssertionError("listing policy must not run without select_listing")

    monkeypatch.setattr(platform, "select_indian_listing", _boom)
    monkeypatch.setattr(
        platform,
        "resolve_company_identity",
        lambda symbol, exchange=None, currency="USD": {
            "symbol": symbol,
            "exchange": exchange,
            "provider_company_id": "AAPL-USD",
        },
    )
    client = TestClient(create_app(platform=platform))
    resp = client.get("/api/v1/fundamentals/resolve", params={"symbol": "AAPL"})
    assert resp.status_code == 200
    assert resp.json()["available"] is True
    assert "status" not in resp.json()
    assert calls == []


def test_select_listing_tcs_bse_first(monkeypatch) -> None:
    platform = _platform()

    def _select(symbol: str, *, explicit_exchange: str | None = None, candidates=None):
        assert explicit_exchange is None
        return {
            "status": "SELECTED",
            "symbol": "TCS",
            "exchange": "BSE",
            "isin": "INE467B01029",
            "detail": "BSE-first",
        }

    resolved: list[str | None] = []

    def _identity(symbol: str, exchange=None, currency="USD"):
        resolved.append(exchange)
        return {"symbol": symbol, "exchange": exchange}

    monkeypatch.setattr(platform, "select_indian_listing", _select)
    monkeypatch.setattr(platform, "resolve_company_identity", _identity)
    client = TestClient(create_app(platform=platform))
    resp = client.get(
        "/api/v1/fundamentals/resolve",
        params={"symbol": "TCS", "select_listing": True},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "SELECTED"
    assert body["exchange"] == "BSE"
    assert resolved == ["BSE"]


def test_select_listing_explicit_nse_not_overridden(monkeypatch) -> None:
    platform = _platform()

    def _select(symbol: str, *, explicit_exchange: str | None = None, candidates=None):
        assert explicit_exchange == "NSE"
        return {
            "status": "SELECTED",
            "symbol": "TCS",
            "exchange": "NSE",
            "isin": "INE467B01029",
            "detail": "explicit",
        }

    monkeypatch.setattr(platform, "select_indian_listing", _select)
    monkeypatch.setattr(
        platform,
        "resolve_company_identity",
        lambda symbol, exchange=None, currency="USD": {
            "symbol": symbol,
            "exchange": exchange,
        },
    )
    client = TestClient(create_app(platform=platform))
    resp = client.get(
        "/api/v1/fundamentals/resolve",
        params={"symbol": "TCS", "exchange": "NSE", "select_listing": True},
    )
    assert resp.json()["exchange"] == "NSE"


def test_select_listing_ambiguous_does_not_resolve_identity(monkeypatch) -> None:
    platform = _platform()
    monkeypatch.setattr(
        platform,
        "select_indian_listing",
        lambda symbol, *, explicit_exchange=None, candidates=None: {
            "status": "AMBIGUOUS",
            "symbol": "FOO",
            "exchange": None,
            "isin": None,
            "detail": "multiple ISINs",
        },
    )
    monkeypatch.setattr(
        platform,
        "resolve_company_identity",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("must not resolve")),
    )
    client = TestClient(create_app(platform=platform))
    resp = client.get(
        "/api/v1/fundamentals/resolve",
        params={"symbol": "FOO", "select_listing": True},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "AMBIGUOUS"
    assert resp.json()["available"] is False
