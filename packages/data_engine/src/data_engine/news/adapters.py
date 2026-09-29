"""Authenticated news adapters.

``NewsProviderPort``, ``NewsService``, and every router/façade above
them only ever see :class:`~data_engine.news.models.AuthenticatedNewsFeed`.

Adapters implemented here:

- :class:`NullNewsAdapter` — honest absence when no official feed is configured.
- :class:`InMemoryNewsAdapter` — explicitly seeded feeds, for tests/dev.

Commercial news vendors are not registered. :func:`build_default_news_registry_from_env`
is the composition helper used by ``dsp_platform.news``. Outside production it
attaches :class:`NullNewsAdapter` so the registry is never empty. Production
refuses a Null-only registry rather than substituting a commercial feed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock

from data_engine.connector_framework.models import (
    ConnectorCompanyIdentity,
    ConnectorProvenance,
    ProviderHealth,
)
from data_engine.connector_framework.registry import PriorityProviderRegistry
from data_engine.exceptions import ProviderRequestError
from data_engine.news.models import AuthenticatedNewsFeed, NewsArticle
from data_engine.news.service import NewsProviderPort, NewsQuery
from data_engine.news.validation import validate_authenticated_news_feed

__all__ = [
    "InMemoryNewsAdapter",
    "NullNewsAdapter",
    "build_default_news_registry_from_env",
    "build_news_feed_from_mapping",
]


def build_news_feed_from_mapping(
    *,
    symbol: str,
    articles: list[NewsArticle],
    provenance: ConnectorProvenance,
) -> AuthenticatedNewsFeed:
    """Build + validate a feed from already-normalized articles."""
    feed = AuthenticatedNewsFeed(
        identity=ConnectorCompanyIdentity(symbol=symbol.strip().upper()),
        articles=tuple(articles),
        provenance=provenance,
    )
    validate_authenticated_news_feed(feed)
    return feed


@dataclass
class NullNewsAdapter(NewsProviderPort):
    """Always unavailable — safe default when no feed is configured."""

    _provider_id: str = "null_news"

    @property
    def provider_id(self) -> str:
        return self._provider_id

    def get_news(self, query: NewsQuery) -> AuthenticatedNewsFeed | None:
        return None

    def health(self) -> ProviderHealth:
        return ProviderHealth(
            provider_id=self.provider_id,
            healthy=True,
            authenticated=False,
            detail="null provider — no news feed configured",
        )


@dataclass
class InMemoryNewsAdapter(NewsProviderPort):
    """Explicitly seeded authenticated feeds only — never invents articles."""

    api_key: str | None = None
    _provider_id: str = "memory_news"
    _feeds: dict[str, AuthenticatedNewsFeed] = field(default_factory=dict)
    _lock: Lock = field(default_factory=Lock, repr=False)

    @property
    def provider_id(self) -> str:
        return self._provider_id

    def put(self, feed: AuthenticatedNewsFeed) -> None:
        validate_authenticated_news_feed(feed)
        with self._lock:
            self._feeds[feed.identity.symbol.upper()] = feed

    def get_news(self, query: NewsQuery) -> AuthenticatedNewsFeed | None:
        if not self.api_key:
            raise ProviderRequestError("memory news adapter requires api_key (authentication)")
        with self._lock:
            feed = self._feeds.get(query.instrument.symbol.strip().upper())
        if feed is None:
            return None
        articles = list(feed.articles)
        if query.since is not None:
            articles = [a for a in articles if a.published_at >= query.since]
        articles.sort(key=lambda a: a.published_at, reverse=True)
        articles = articles[: max(1, query.limit)]
        if not articles:
            return None
        return AuthenticatedNewsFeed(
            identity=feed.identity, articles=tuple(articles), provenance=feed.provenance
        )

    def health(self) -> ProviderHealth:
        return ProviderHealth(
            provider_id=self.provider_id,
            healthy=True,
            authenticated=bool(self.api_key),
            detail="seeded in-memory authenticated news" if self.api_key else "missing api_key",
        )


def build_default_news_registry_from_env() -> PriorityProviderRegistry[NewsProviderPort]:
    """Compose a news provider registry.

    No commercial news vendor is registered. P1-03: Null is attached only
    outside production; production refuses a Null-only / memory-only registry.
    """
    from data_engine.connector_framework.production_profile import (
        finalize_provider_registry,
        memory_adapter_allowed,
    )

    registry: PriorityProviderRegistry[NewsProviderPort] = PriorityProviderRegistry()

    if memory_adapter_allowed("DSP_NEWS_MEMORY", connector="news"):
        registry.register(
            InMemoryNewsAdapter(api_key="dev-memory-key"), provider_id="memory_news", priority=90
        )

    return finalize_provider_registry(
        registry,
        connector="news",
        null_factory=NullNewsAdapter,
        null_provider_id="null_news",
    )
