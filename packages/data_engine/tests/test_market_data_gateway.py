"""Tests for the private vendor-neutral market-data gateway."""

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from data_engine.market_quote import gateway_app


class FakeQuote:
    def __init__(self, symbol: str, price: float = 123.0) -> None:
        self.symbol = symbol
        self.price = price

    def has_any_price(self) -> bool:
        return self.price > 0

    def to_public_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "exchange": "NSE",
            "currency": "INR",
            "fields": {"current_price": self.price},
            "provenance": {"provider_id": "fake-test-provider"},
        }


def test_gateway_prefers_upstox_when_usable(monkeypatch):
    monkeypatch.setenv("DSP_MARKET_GATEWAY_API_KEY", "test-gateway-key")
    monkeypatch.setattr(gateway_app, "is_approved_source", lambda source, purpose: True)
    monkeypatch.setattr(
        gateway_app, "_upstox",
        lambda: SimpleNamespace(
            get_quote=lambda instrument: FakeQuote(instrument.symbol)
        ),
    )
    fallback_called = False

    def fallback():
        nonlocal fallback_called
        fallback_called = True
        return None

    monkeypatch.setattr(gateway_app, "_fallback", fallback)
    result = gateway_app.get_quote(
        symbol="RELIANCE", exchange="NSE", currency="INR",
        authorization="Bearer test-gateway-key",
    )
    assert result["gateway"]["selected_source"] == "upstox"
    assert result["gateway"]["fallback_used"] is False
    assert fallback_called is False


def test_gateway_falls_back_when_upstox_fails(monkeypatch):
    monkeypatch.setenv("DSP_MARKET_GATEWAY_API_KEY", "test-gateway-key")
    monkeypatch.setattr(gateway_app, "is_approved_source", lambda source, purpose: True)

    def raise_provider_error(instrument):
        raise RuntimeError("provider unavailable")

    monkeypatch.setattr(
        gateway_app, "_upstox",
        lambda: SimpleNamespace(get_quote=raise_provider_error),
    )
    monkeypatch.setattr(
        gateway_app, "_fallback",
        lambda: SimpleNamespace(
            get_quote=lambda instrument: FakeQuote(instrument.symbol, 99.0)
        ),
    )
    result = gateway_app.get_quote(
        symbol="TCS", exchange="NSE", currency="INR",
        authorization="Bearer test-gateway-key",
    )
    assert result["gateway"]["selected_source"] == "approved_http_fallback"
    assert result["gateway"]["fallback_used"] is True
    assert result["gateway"]["fallback_reason"] == "RuntimeError"


def test_gateway_returns_unavailable_when_all_sources_fail(monkeypatch):
    monkeypatch.setenv("DSP_MARKET_GATEWAY_API_KEY", "test-gateway-key")
    monkeypatch.setattr(gateway_app, "is_approved_source", lambda source, purpose: True)
    monkeypatch.setattr(
        gateway_app, "_upstox",
        lambda: SimpleNamespace(get_quote=lambda instrument: None),
    )
    monkeypatch.setattr(gateway_app, "_fallback", lambda: None)
    with pytest.raises(HTTPException) as exc:
        gateway_app.get_quote(
            symbol="INFY", exchange="NSE", currency="INR",
            authorization="Bearer test-gateway-key",
        )
    assert exc.value.status_code == 503
    assert exc.value.detail["code"] == "market_quote_unavailable"


def test_gateway_rejects_missing_or_invalid_internal_key(monkeypatch):
    monkeypatch.setenv("DSP_MARKET_GATEWAY_API_KEY", "test-gateway-key")
    with pytest.raises(HTTPException) as exc:
        gateway_app.get_quote(
            symbol="INFY", exchange="NSE", currency="INR",
            authorization="Bearer wrong-key",
        )
    assert exc.value.status_code == 401


def test_gateway_does_not_use_unapproved_upstox_source(monkeypatch):
    monkeypatch.setenv("DSP_MARKET_GATEWAY_API_KEY", "test-gateway-key")
    monkeypatch.setattr(
        gateway_app, "is_approved_source", lambda source, purpose: False
    )
    upstox_called = False

    def upstox_quote(instrument):
        nonlocal upstox_called
        upstox_called = True
        return FakeQuote(instrument.symbol)

    monkeypatch.setattr(
        gateway_app, "_upstox",
        lambda: SimpleNamespace(get_quote=upstox_quote),
    )
    monkeypatch.setattr(
        gateway_app, "_fallback",
        lambda: SimpleNamespace(
            get_quote=lambda instrument: FakeQuote(instrument.symbol, 99.0)
        ),
    )
    result = gateway_app.get_quote(
        symbol="INFY", exchange="NSE", currency="INR",
        authorization="Bearer test-gateway-key",
    )
    assert result["gateway"]["selected_source"] == "approved_http_fallback"
    assert result["gateway"]["fallback_reason"] == "upstox_not_approved_by_source_governance"
    assert upstox_called is False



def test_upstox_is_approved_for_market_data_only():
    from data_engine.source_governance import DataProvenance, is_approved_source

    assert is_approved_source("UPSTOX", purpose="market_quote") is True
    assert is_approved_source("UPSTOX", purpose="historical_series") is True
    assert is_approved_source("UPSTOX", purpose="financial_statements") is False
    with pytest.raises(ValueError, match="unapproved financial source"):
        DataProvenance(
            source="UPSTOX", source_type="primary", purpose="financial_statements"
        )
