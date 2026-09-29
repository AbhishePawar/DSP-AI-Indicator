"""B1: India investment path does not use FMP. Fail closed, official only."""

from __future__ import annotations

import pytest

from data_engine.connector_framework.production_profile import ConnectorConfigurationError
from data_engine.investment_data_provider import resolve_investment_data_provider
from data_engine.market_quote.adapters import (
    NullAuthenticatedQuoteAdapter,
    build_default_quote_adapter_from_env,
)


def test_india_quote_factory_does_not_construct_fmp(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("DSP_INVESTMENT_DATA_PROVIDER", raising=False)
    monkeypatch.setenv("DSP_FMP_API_KEY", "india-fmp-key")
    monkeypatch.delenv("DSP_MARKET_QUOTE_MEMORY", raising=False)
    adapter = build_default_quote_adapter_from_env()
    assert type(adapter).__name__ == "NullAuthenticatedQuoteAdapter"
    assert isinstance(adapter, NullAuthenticatedQuoteAdapter)


def test_fmp_provider_flag_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DSP_INVESTMENT_DATA_PROVIDER", "fmp")
    with pytest.raises(ConnectorConfigurationError, match="DSP_FMP|not permitted|fmp"):
        resolve_investment_data_provider()
