"""Commercial provider wiring is rejected. No FMP/Upstox fallback."""

from __future__ import annotations

import pytest

from data_engine.connector_framework.production_profile import (
    ConnectorConfigurationError,
    assert_production_investment_connectors_configured,
)
from data_engine.financial_statement.adapters import (
    NullAuthenticatedStatementAdapter,
    build_default_statement_adapter_from_env,
)
from data_engine.investment_data_provider import (
    INVESTMENT_DATA_UNAVAILABLE,
    resolve_investment_data_provider,
)
from data_engine.market_quote.adapters import (
    NullAuthenticatedQuoteAdapter,
    build_default_quote_adapter_from_env,
)


@pytest.fixture(autouse=True)
def _clear_commercial_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "DSP_INVESTMENT_DATA_PROVIDER",
        "DSP_FMP_API_KEY",
        "DSP_INVESTMENT_FMP_API_KEY",
        "DSP_MARKET_QUOTE_MEMORY",
        "DSP_FINANCIAL_STATEMENT_MEMORY",
    ):
        monkeypatch.delenv(name, raising=False)


def test_no_commercial_provider_is_selected() -> None:
    assert resolve_investment_data_provider() == "unavailable"
    assert isinstance(build_default_quote_adapter_from_env(), NullAuthenticatedQuoteAdapter)
    assert isinstance(
        build_default_statement_adapter_from_env(), NullAuthenticatedStatementAdapter
    )


@pytest.mark.parametrize("name", ["fmp", "upstox", "yahoo", "eodhd", "alphavantage"])
def test_commercial_provider_env_is_rejected(
    monkeypatch: pytest.MonkeyPatch, name: str
) -> None:
    monkeypatch.setenv("DSP_INVESTMENT_DATA_PROVIDER", name)
    with pytest.raises(ConnectorConfigurationError, match="not permitted"):
        resolve_investment_data_provider()


def test_explicit_unavailable_is_honest(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DSP_INVESTMENT_DATA_PROVIDER", "unavailable")
    assert resolve_investment_data_provider() == "unavailable"


def test_production_does_not_require_fmp_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DSP_ENVIRONMENT", "production")
    selected = assert_production_investment_connectors_configured()
    assert selected["market_quote"] == INVESTMENT_DATA_UNAVAILABLE
    assert selected["financial_statement"] == INVESTMENT_DATA_UNAVAILABLE
    assert selected["selection"] == "unavailable"


def test_stale_upstox_provider_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DSP_INVESTMENT_DATA_PROVIDER", "upstox")
    with pytest.raises(ConnectorConfigurationError, match="upstox"):
        resolve_investment_data_provider()
