"""FMP adapters are gone. Official evidence is authoritative."""

from __future__ import annotations

import importlib
import sys

import pytest

from data_engine.connector_framework.production_profile import ConnectorConfigurationError
from data_engine.financial_statement.adapters import (
    NullAuthenticatedStatementAdapter,
    build_default_statement_adapter_from_env,
)
from data_engine.investment_data_provider import resolve_investment_data_provider
from data_engine.market_quote.adapters import (
    NullAuthenticatedQuoteAdapter,
    build_default_quote_adapter_from_env,
)


def test_fmp_investment_module_is_absent() -> None:
    sys.modules.pop("data_engine.fmp_investment", None)
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("data_engine.fmp_investment")


def test_fmp_adapter_types_are_not_exported() -> None:
    import data_engine

    assert not hasattr(data_engine, "FinancialModelingPrepQuoteAdapter")
    assert not hasattr(data_engine, "FinancialModelingPrepStatementAdapter")


def test_fmp_and_upstox_provider_names_are_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DSP_INVESTMENT_DATA_PROVIDER", "fmp")
    with pytest.raises(ConnectorConfigurationError, match="not permitted"):
        resolve_investment_data_provider()
    monkeypatch.setenv("DSP_INVESTMENT_DATA_PROVIDER", "upstox")
    with pytest.raises(ConnectorConfigurationError, match="not permitted"):
        resolve_investment_data_provider()


def test_fmp_key_does_not_select_a_commercial_adapter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("DSP_INVESTMENT_DATA_PROVIDER", raising=False)
    monkeypatch.setenv("DSP_FMP_API_KEY", "must-not-activate")
    monkeypatch.delenv("DSP_MARKET_QUOTE_MEMORY", raising=False)
    monkeypatch.delenv("DSP_FINANCIAL_STATEMENT_MEMORY", raising=False)
    assert isinstance(build_default_quote_adapter_from_env(), NullAuthenticatedQuoteAdapter)
    assert isinstance(
        build_default_statement_adapter_from_env(), NullAuthenticatedStatementAdapter
    )


def test_default_policy_is_unavailable_without_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("DSP_INVESTMENT_DATA_PROVIDER", raising=False)
    monkeypatch.delenv("DSP_FMP_API_KEY", raising=False)
    assert resolve_investment_data_provider() == "unavailable"
