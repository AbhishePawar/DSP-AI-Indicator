"""Regression tests for explicit Upstox standby mode."""

import pytest

from data_engine.upstox.availability import upstox_enabled
from data_engine.market_quote.upstox_adapter import (
    UpstoxQuoteAdapter,
    build_upstox_quote_adapter_from_env,
)
from data_engine.historical_series.upstox_adapter import (
    UpstoxHistoricalAdapter,
)
from data_engine.market_quote.adapters import (
    build_default_quote_adapter_from_env,
    ConfiguredHttpQuoteAdapter,
)
from data_engine.historical_series.adapters import (
    build_default_historical_adapter_from_env,
    NullAuthenticatedHistoricalAdapter,
)


@pytest.fixture
def standby(monkeypatch):
    monkeypatch.setenv("DSP_UPSTOX_ENABLED", "false")

    for key in (
        "DSP_UPSTOX_ANALYTICS_TOKEN",
        "DSP_UPSTOX_ACCESS_TOKEN",
        "UPSTOX_ACCESS_TOKEN",
    ):
        monkeypatch.setenv(key, "inactive-test-token")

    monkeypatch.setenv(
        "DSP_INVESTMENT_DATA_PROVIDER", "upstox"
    )
    monkeypatch.setenv(
        "DSP_HISTORICAL_SERIES_PROVIDER", "upstox"
    )


@pytest.mark.parametrize(
    "value",
    ["false", "0", "no", "off", ""],
)
def test_disabled_switch(monkeypatch, value):
    monkeypatch.setenv("DSP_UPSTOX_ENABLED", value)
    assert not upstox_enabled()


@pytest.mark.parametrize(
    "value",
    ["true", "1", "yes", "on"],
)
def test_enabled_switch(monkeypatch, value):
    monkeypatch.setenv("DSP_UPSTOX_ENABLED", value)
    assert upstox_enabled()


def test_legacy_default(monkeypatch):
    monkeypatch.delenv(
        "DSP_UPSTOX_ENABLED", raising=False
    )
    assert upstox_enabled()


@pytest.mark.parametrize(
    "adapter_class",
    [UpstoxQuoteAdapter, UpstoxHistoricalAdapter],
)
def test_stored_token_cannot_activate_provider(
    standby, adapter_class
):
    adapter = adapter_class(
        access_token="inactive-test-token"
    )

    assert not adapter.is_configured()

    health = adapter.health()

    assert health.detail == "DISABLED"
    assert not health.authenticated


def test_optional_factory_disabled(standby):
    assert build_upstox_quote_adapter_from_env() is None


def test_quote_factory_uses_http_fallback(
    standby, monkeypatch
):
    monkeypatch.setenv(
        "DSP_MARKET_QUOTE_API_KEY", "test-key"
    )
    monkeypatch.setenv(
        "DSP_MARKET_QUOTE_BASE_URL",
        "https://quotes.example.invalid",
    )
    monkeypatch.delenv(
        "DSP_MARKET_QUOTE_MEMORY", raising=False
    )

    adapter = build_default_quote_adapter_from_env()

    assert isinstance(
        adapter, ConfiguredHttpQuoteAdapter
    )
    assert not isinstance(
        adapter, UpstoxQuoteAdapter
    )


def test_historical_factory_stays_disabled(
    standby, monkeypatch
):
    for key in (
        "DSP_HISTORICAL_SERIES_API_KEY",
        "DSP_HISTORICAL_SERIES_BASE_URL",
        "DSP_HISTORICAL_SERIES_MEMORY",
    ):
        monkeypatch.delenv(key, raising=False)

    adapter = build_default_historical_adapter_from_env()

    assert isinstance(
        adapter, NullAuthenticatedHistoricalAdapter
    )


def test_no_historical_network_request(
    standby, monkeypatch
):
    def forbidden(*args, **kwargs):
        pytest.fail(
            "Network request attempted in standby mode"
        )

    import socket
    import urllib.request

    monkeypatch.setattr(
        socket, "create_connection", forbidden
    )
    monkeypatch.setattr(
        urllib.request, "urlopen", forbidden
    )

    adapter = UpstoxHistoricalAdapter(
        access_token="inactive-test-token"
    )

    result = adapter.get_candles(
        "NSE_EQ|INE009A01021",
        unit="days",
        interval=1,
        from_date="2026-11-01",
        to_date="2026-11-26",
    )

    assert result == []


def test_manual_reactivation(monkeypatch):
    monkeypatch.setenv(
        "DSP_UPSTOX_ENABLED", "true"
    )

    adapter = UpstoxQuoteAdapter(
        access_token="test-token"
    )

    assert adapter.is_configured()



def test_no_quote_network_request(standby, monkeypatch):
    import socket
    import urllib.request

    def forbidden(*args, **kwargs):
        pytest.fail("Network request attempted in standby mode")

    monkeypatch.setattr(
        socket, "create_connection", forbidden
    )

    monkeypatch.setattr(
        urllib.request, "urlopen", forbidden
    )

    adapter = UpstoxQuoteAdapter(
        access_token="inactive-test-token"
    )

    # Disabled adapter must return before instrument resolution.
    assert adapter.get_quote(None) is None
