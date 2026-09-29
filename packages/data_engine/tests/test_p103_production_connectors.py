"""P1-03 — production connector fail-closed (no silent Null/demo/seed)."""

from __future__ import annotations

import pytest

from data_engine.connector_framework.production_profile import (
    ConnectorConfigurationError,
    adapter_is_production_unsafe,
    assert_production_investment_connectors_configured,
    classify_provider_id,
    is_production_environment,
)
from data_engine.financial_statement.adapters import (
    ConfiguredHttpStatementAdapter,
    InMemoryAuthenticatedStatementAdapter,
    NullAuthenticatedStatementAdapter,
    build_default_statement_adapter_from_env,
)
from data_engine.market_quote.adapters import (
    ConfiguredHttpQuoteAdapter,
    InMemoryAuthenticatedQuoteAdapter,
    NullAuthenticatedQuoteAdapter,
    build_default_quote_adapter_from_env,
)
from data_engine.news.adapters import (
    NullNewsAdapter,
    build_default_news_registry_from_env,
)


@pytest.fixture(autouse=True)
def _clear_connector_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in list(
        {
            "DSP_ENVIRONMENT",
            "DSP_INVESTMENT_DATA_PROVIDER",
            "DSP_FMP_API_KEY",
            "DSP_INVESTMENT_FMP_API_KEY",
            "DSP_MARKET_QUOTE_API_KEY",
            "DSP_MARKET_QUOTE_BASE_URL",
            "DSP_MARKET_QUOTE_MEMORY",
            "DSP_FINANCIAL_STATEMENT_API_KEY",
            "DSP_FINANCIAL_STATEMENT_BASE_URL",
            "DSP_FINANCIAL_STATEMENT_MEMORY",
            "DSP_NEWS_FMP_API_KEY",
            "DSP_NEWS_POLYGON_API_KEY",
            "DSP_NEWS_ALPHAVANTAGE_API_KEY",
            "DSP_NEWS_YAHOO_ENABLED",
            "DSP_NEWS_MEMORY",
        }
    ):
        monkeypatch.delenv(key, raising=False)


def test_dev_default_still_allows_null() -> None:
    assert is_production_environment() is False
    quote = build_default_quote_adapter_from_env()
    statements = build_default_statement_adapter_from_env()
    assert isinstance(quote, NullAuthenticatedQuoteAdapter)
    assert isinstance(statements, NullAuthenticatedStatementAdapter)
    assert adapter_is_production_unsafe(quote) is True


def test_production_quote_is_honestly_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DSP_ENVIRONMENT", "production")
    quote = build_default_quote_adapter_from_env()
    assert isinstance(quote, NullAuthenticatedQuoteAdapter)
    assert type(quote).__name__ != "FinancialModelingPrepQuoteAdapter"


def test_production_statements_are_honestly_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DSP_ENVIRONMENT", "production")
    statements = build_default_statement_adapter_from_env()
    assert isinstance(statements, NullAuthenticatedStatementAdapter)
    assert type(statements).__name__ != "FinancialModelingPrepStatementAdapter"


def test_production_rejects_memory_quote(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DSP_ENVIRONMENT", "production")
    monkeypatch.setenv("DSP_MARKET_QUOTE_MEMORY", "1")
    with pytest.raises(ConnectorConfigurationError, match="in-memory"):
        build_default_quote_adapter_from_env()


def test_production_rejects_memory_statements(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DSP_ENVIRONMENT", "production")
    monkeypatch.setenv("DSP_FINANCIAL_STATEMENT_MEMORY", "true")
    with pytest.raises(ConnectorConfigurationError, match="in-memory"):
        build_default_statement_adapter_from_env()


def test_dev_memory_still_allowed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DSP_MARKET_QUOTE_MEMORY", "1")
    monkeypatch.setenv("DSP_FINANCIAL_STATEMENT_MEMORY", "1")
    quote = build_default_quote_adapter_from_env()
    statements = build_default_statement_adapter_from_env()
    assert isinstance(quote, InMemoryAuthenticatedQuoteAdapter)
    assert isinstance(statements, InMemoryAuthenticatedStatementAdapter)


def test_production_does_not_select_configured_http_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DSP_ENVIRONMENT", "production")
    monkeypatch.setenv("DSP_MARKET_QUOTE_API_KEY", "test-key")
    monkeypatch.setenv("DSP_MARKET_QUOTE_BASE_URL", "https://vendor.example/quotes")
    monkeypatch.setenv("DSP_FINANCIAL_STATEMENT_API_KEY", "test-key")
    monkeypatch.setenv(
        "DSP_FINANCIAL_STATEMENT_BASE_URL", "https://vendor.example/statements"
    )
    quote = build_default_quote_adapter_from_env()
    statements = build_default_statement_adapter_from_env()
    assert isinstance(quote, NullAuthenticatedQuoteAdapter)
    assert isinstance(statements, NullAuthenticatedStatementAdapter)
    assert not isinstance(quote, ConfiguredHttpQuoteAdapter)
    selected = assert_production_investment_connectors_configured()
    assert selected["market_quote"] == "INVESTMENT_DATA_UNAVAILABLE"
    assert selected["financial_statement"] == "INVESTMENT_DATA_UNAVAILABLE"


def test_production_news_rejects_null_only_registry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DSP_ENVIRONMENT", "production")
    with pytest.raises(ConnectorConfigurationError, match="news"):
        build_default_news_registry_from_env()


def test_dev_news_keeps_null_fallback() -> None:
    registry = build_default_news_registry_from_env()
    assert "null_news" in registry.all_ids()
    assert isinstance(registry.get("null_news"), NullNewsAdapter)


def test_production_news_fmp_key_does_not_register_fmp(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DSP_ENVIRONMENT", "production")
    monkeypatch.setenv("DSP_NEWS_FMP_API_KEY", "fmp-test-key")
    with pytest.raises(ConnectorConfigurationError, match="news"):
        build_default_news_registry_from_env()


def test_classify_provider_ids() -> None:
    assert classify_provider_id("null_news") == "NULL_UNAVAILABLE"
    assert classify_provider_id("memory_news") == "TEST_MEMORY"
    # Historical commercial id is not treated as an official feed.
    assert classify_provider_id("fmp_news") == "PRODUCTION_CANDIDATE"


def test_fmp_provider_name_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DSP_ENVIRONMENT", "production")
    monkeypatch.setenv("DSP_INVESTMENT_DATA_PROVIDER", "fmp")
    with pytest.raises(ConnectorConfigurationError, match="not permitted"):
        build_default_quote_adapter_from_env()
