"""Tests for the authenticated news connector domain."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from contracts.domain.instrument import Instrument
from contracts.enums import AssetClass

from data_engine import (
    CircuitOpenError,
    ConnectorProvenance,
    FailoverGroup,
    InMemoryNewsAdapter,
    InvalidProviderDataError,
    NewsArticle,
    NewsProviderRegistry,
    NewsQuery,
    NewsService,
    NullNewsAdapter,
    ProviderRequestError,
    build_default_news_registry_from_env,
    build_news_feed_from_mapping,
    validate_authenticated_news_feed,
)


def _instrument(symbol: str = "AAPL") -> Instrument:
    return Instrument(symbol=symbol, asset_class=AssetClass.EQUITY, currency="USD")


class TestNullAndInMemoryAdapters:
    def test_null_adapter_always_unavailable(self) -> None:
        adapter = NullNewsAdapter()
        assert adapter.get_news(NewsQuery(instrument=_instrument())) is None
        health = adapter.health()
        assert health.healthy is True
        assert health.authenticated is False

    def test_in_memory_requires_api_key(self) -> None:
        adapter = InMemoryNewsAdapter()
        with pytest.raises(ProviderRequestError):
            adapter.get_news(NewsQuery(instrument=_instrument()))

    def test_in_memory_put_and_get(self) -> None:
        adapter = InMemoryNewsAdapter(api_key="k")
        feed = build_news_feed_from_mapping(
            symbol="AAPL",
            articles=[
                NewsArticle(
                    article_id="1",
                    headline="Apple beats earnings",
                    url="https://example.com/1",
                    source="Reuters",
                    published_at=datetime.now(tz=UTC),
                )
            ],
            provenance=ConnectorProvenance(
                provider_id="memory_news",
                provider_name="Memory",
                source_type="licensed_vendor",
                retrieved_at=datetime.now(tz=UTC),
            ),
        )
        adapter.put(feed)
        result = adapter.get_news(NewsQuery(instrument=_instrument(), limit=10))
        assert result is not None
        assert result.articles[0].headline == "Apple beats earnings"

    def test_in_memory_unknown_symbol_returns_none(self) -> None:
        adapter = InMemoryNewsAdapter(api_key="k")
        assert adapter.get_news(NewsQuery(instrument=_instrument("ZZZZ"))) is None


class TestValidation:
    def test_rejects_empty_articles(self) -> None:
        with pytest.raises(InvalidProviderDataError):
            build_news_feed_from_mapping(
                symbol="AAPL",
                articles=[],
                provenance=ConnectorProvenance(
                    provider_id="x",
                    provider_name="X",
                    source_type="licensed_vendor",
                    retrieved_at=datetime.now(tz=UTC),
                ),
            )

    def test_rejects_bad_sentiment_label(self) -> None:
        with pytest.raises(InvalidProviderDataError):
            build_news_feed_from_mapping(
                symbol="AAPL",
                articles=[
                    NewsArticle(
                        article_id="1",
                        headline="h",
                        url="https://x",
                        source="s",
                        published_at=datetime.now(tz=UTC),
                        sentiment="ecstatic",
                    )
                ],
                provenance=ConnectorProvenance(
                    provider_id="x",
                    provider_name="X",
                    source_type="licensed_vendor",
                    retrieved_at=datetime.now(tz=UTC),
                ),
            )


class TestCommercialNewsAdaptersAbsent:
    def test_commercial_news_adapters_are_not_exported(self) -> None:
        import data_engine

        for name in (
            "FinancialModelingPrepNewsAdapter",
            "YahooFinanceNewsAdapter",
            "AlphaVantageNewsAdapter",
            "PolygonNewsAdapter",
        ):
            assert not hasattr(data_engine, name)


class TestNewsProviderRegistryAndFailover:
    def test_registry_orders_by_priority(self) -> None:
        registry = NewsProviderRegistry()
        registry.register(NullNewsAdapter(_provider_id="a"), provider_id="a", priority=50)
        registry.register(NullNewsAdapter(_provider_id="b"), provider_id="b", priority=10)
        assert registry.ordered_ids() == ("b", "a")

    def test_failover_across_providers(self) -> None:
        seeded = InMemoryNewsAdapter(api_key="k")
        seeded.put(
            build_news_feed_from_mapping(
                symbol="AAPL",
                articles=[
                    NewsArticle(
                        article_id="1",
                        headline="h",
                        url="https://x",
                        source="s",
                        published_at=datetime.now(tz=UTC),
                    )
                ],
                provenance=ConnectorProvenance(
                    provider_id="memory_news",
                    provider_name="Memory",
                    source_type="licensed_vendor",
                    retrieved_at=datetime.now(tz=UTC),
                ),
            )
        )
        registry = NewsProviderRegistry()
        registry.register(NullNewsAdapter(), provider_id="null_news", priority=10)
        registry.register(seeded, provider_id="memory_news", priority=20)

        services = [NewsService(p) for p in registry.ordered()]
        group: FailoverGroup = FailoverGroup(
            services,
            call=lambda svc, q: svc.get_news(q),
            domain="news",
            operation="get_news",
        )
        outcome = group.call(NewsQuery(instrument=_instrument()), symbol="AAPL")
        assert outcome is not None
        assert outcome.provider_id == "memory_news"
        assert outcome.attempted_provider_ids == ("null_news", "memory_news")


class TestBuildDefaultRegistryFromEnv:
    def test_defaults_to_null_only(self, monkeypatch: pytest.MonkeyPatch) -> None:
        for key in (
            "DSP_NEWS_FMP_API_KEY",
            "DSP_NEWS_POLYGON_API_KEY",
            "DSP_NEWS_ALPHAVANTAGE_API_KEY",
            "DSP_NEWS_YAHOO_ENABLED",
            "DSP_NEWS_MEMORY",
        ):
            monkeypatch.delenv(key, raising=False)
        registry = build_default_news_registry_from_env()
        assert registry.ordered_ids() == ("null_news",)

    def test_commercial_news_keys_do_not_register_vendors(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("DSP_NEWS_FMP_API_KEY", "key123")
        monkeypatch.setenv("DSP_NEWS_POLYGON_API_KEY", "poly")
        monkeypatch.setenv("DSP_NEWS_ALPHAVANTAGE_API_KEY", "av")
        monkeypatch.setenv("DSP_NEWS_YAHOO_ENABLED", "1")
        registry = build_default_news_registry_from_env()
        ids = registry.ordered_ids()
        assert ids == ("null_news",)


class TestNewsServiceResilience:
    def test_caches_successful_result(self) -> None:
        adapter = InMemoryNewsAdapter(api_key="k")
        adapter.put(
            build_news_feed_from_mapping(
                symbol="AAPL",
                articles=[
                    NewsArticle(
                        article_id="1",
                        headline="h",
                        url="https://x",
                        source="s",
                        published_at=datetime.now(tz=UTC),
                    )
                ],
                provenance=ConnectorProvenance(
                    provider_id="memory_news",
                    provider_name="Memory",
                    source_type="licensed_vendor",
                    retrieved_at=datetime.now(tz=UTC),
                ),
            )
        )
        service = NewsService(adapter)
        query = NewsQuery(instrument=_instrument())
        first = service.get_news(query)
        second = service.get_news(query)
        assert first is not None and second is not None
        assert service.metrics.cache_hits == 1
        assert second.provenance.cache_hit is True

    def test_propagates_circuit_open_after_failures(self) -> None:
        class _Flaky:
            provider_id = "flaky"

            def get_news(self, query):
                raise RuntimeError("boom")

            def health(self):
                from data_engine import ProviderHealth

                return ProviderHealth(provider_id="flaky", healthy=False, authenticated=False, detail="x")

        from data_engine import CircuitBreaker, RetryPolicy

        service = NewsService(
            _Flaky(),
            circuit_breaker=CircuitBreaker(failure_threshold=1),
            retry=RetryPolicy(max_attempts=1),
        )
        query = NewsQuery(instrument=_instrument())
        with pytest.raises(RuntimeError):
            service.get_news(query)
        with pytest.raises(CircuitOpenError):
            service.get_news(query)
