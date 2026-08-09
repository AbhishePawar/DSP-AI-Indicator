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
            "DSP_UPSTOX_ANALYTICS_TOKEN",
            "DSP_UPSTOX_ACCESS_TOKEN",
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


def test_production_rejects_null_quote(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DSP_ENVIRONMENT", "production")
    with pytest.raises(ConnectorConfigurationError, match="P1-03"):
        build_default_quote_adapter_from_env()


def test_production_rejects_null_statements(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DSP_ENVIRONMENT", "production")
    with pytest.raises(ConnectorConfigurationError, match="financial_statement"):
        build_default_statement_adapter_from_env()


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


def test_production_selects_configured_http(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DSP_ENVIRONMENT", "production")
    monkeypatch.setenv("DSP_MARKET_QUOTE_API_KEY", "test-key")
    monkeypatch.setenv("DSP_MARKET_QUOTE_BASE_URL", "https://vendor.example/quotes")
    monkeypatch.setenv("DSP_FINANCIAL_STATEMENT_API_KEY", "test-key")
    monkeypatch.setenv(
        "DSP_FINANCIAL_STATEMENT_BASE_URL", "https://vendor.example/statements"
    )
    quote = build_default_quote_adapter_from_env()
    statements = build_default_statement_adapter_from_env()
    assert isinstance(quote, ConfiguredHttpQuoteAdapter)
    assert isinstance(statements, ConfiguredHttpStatementAdapter)
    assert adapter_is_production_unsafe(quote) is False
    selected = assert_production_investment_connectors_configured()
    assert selected["market_quote"] == "ConfiguredHttpQuoteAdapter"
    assert selected["financial_statement"] == "ConfiguredHttpStatementAdapter"


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


def test_production_news_with_vendor_omits_null(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DSP_ENVIRONMENT", "production")
    monkeypatch.setenv("DSP_NEWS_FMP_API_KEY", "fmp-test-key")
    registry = build_default_news_registry_from_env()
    assert "fmp_news" in registry.all_ids()
    assert "null_news" not in registry.all_ids()


def test_classify_provider_ids() -> None:
    assert classify_provider_id("null_news") == "NULL_UNAVAILABLE"
    assert classify_provider_id("memory_news") == "TEST_MEMORY"
    assert classify_provider_id("fmp_news") == "PRODUCTION_CANDIDATE"


def test_missing_credentials_fail_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DSP_ENVIRONMENT", "production")
    monkeypatch.setenv("DSP_MARKET_QUOTE_API_KEY", "only-key")
    # base URL missing → fail closed (not Null)
    with pytest.raises(ConnectorConfigurationError, match="DSP_MARKET_QUOTE_BASE_URL"):
        build_default_quote_adapter_from_env()
