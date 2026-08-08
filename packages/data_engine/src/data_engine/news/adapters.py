"""Authenticated news adapters.

Every vendor-specific field name lives in this file and nowhere else —
``NewsProviderPort``, ``NewsService``, and every router/façade above
them only ever see :class:`~data_engine.news.models.AuthenticatedNewsFeed`.

Adapters implemented here:

- :class:`NullNewsAdapter` — safe default, always unavailable.
- :class:`InMemoryNewsAdapter` — explicitly seeded feeds, for tests/dev.
- :class:`YahooFinanceNewsAdapter` — Yahoo Finance's unauthenticated
  search endpoint (``/v1/finance/search``), which returns a ``news``
  array alongside quote/ticker matches.
- :class:`AlphaVantageNewsAdapter` — Alpha Vantage ``NEWS_SENTIMENT``.
- :class:`FinancialModelingPrepNewsAdapter` — FMP ``/stable/news/stock``
  (legacy alias ``/api/v3/stock_news``).
- :class:`PolygonNewsAdapter` — Polygon.io ``/v2/reference/news``.

:func:`build_default_news_registry_from_env` is the composition helper
used by ``dsp_platform.news`` — it registers whichever vendors have
credentials configured via environment variables, always with
:class:`NullNewsAdapter` as the lowest-priority fallback so the
registry is never empty.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import UTC, datetime
from threading import Lock
from typing import Any, Mapping

from contracts.domain.instrument import Instrument
from data_engine.connector_framework.http import JsonHttpClient, UrllibJsonHttpClient
from data_engine.connector_framework.models import ProviderHealth, utc_now
from data_engine.connector_framework.registry import PriorityProviderRegistry
from data_engine.exceptions import ProviderRequestError
from data_engine.news.models import AuthenticatedNewsFeed, NewsArticle
from data_engine.news.service import NewsProviderPort, NewsQuery
from data_engine.news.validation import validate_authenticated_news_feed
from data_engine.connector_framework.models import ConnectorCompanyIdentity, ConnectorProvenance

__all__ = [
    "AlphaVantageNewsAdapter",
    "FinancialModelingPrepNewsAdapter",
    "InMemoryNewsAdapter",
    "NullNewsAdapter",
    "PolygonNewsAdapter",
    "YahooFinanceNewsAdapter",
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


@dataclass
class YahooFinanceNewsAdapter(NewsProviderPort):
    """Yahoo Finance unauthenticated news search adapter.

    Uses the public (unauthenticated, unofficial) ``/v1/finance/search``
    endpoint, which returns a ``news`` array alongside quote matches.
    Kept as opt-in (``enabled`` flag) since it is an unofficial surface
    that Yahoo may change or rate-limit without notice.
    """

    enabled: bool = False
    base_url: str = "https://query1.finance.yahoo.com/v1/finance/search"
    timeout_seconds: float = 10.0
    http_client: JsonHttpClient | None = None
    _provider_id: str = "yahoo_finance_news"

    @property
    def provider_id(self) -> str:
        return self._provider_id

    def _client(self) -> JsonHttpClient:
        return self.http_client or UrllibJsonHttpClient(timeout_seconds=self.timeout_seconds)

    def get_news(self, query: NewsQuery) -> AuthenticatedNewsFeed | None:
        if not self.enabled:
            raise ProviderRequestError("yahoo finance news adapter is not enabled")
        symbol = query.instrument.symbol.strip().upper()
        payload = self._client().get_json(
            self.base_url,
            params={"q": symbol, "newsCount": str(max(1, min(query.limit, 50)))},
        )
        if not isinstance(payload, Mapping):
            return None
        raw_news = payload.get("news")
        if not isinstance(raw_news, list) or not raw_news:
            return None

        articles: list[NewsArticle] = []
        for item in raw_news:
            if not isinstance(item, Mapping):
                continue
            uuid_ = str(item.get("uuid") or "").strip()
            title = str(item.get("title") or "").strip()
            link = str(item.get("link") or "").strip()
            if not uuid_ or not title or not link:
                continue
            publish_ts = item.get("providerPublishTime")
            try:
                published_at = (
                    datetime.fromtimestamp(float(publish_ts), tz=UTC)
                    if publish_ts is not None
                    else utc_now()
                )
            except (TypeError, ValueError):
                published_at = utc_now()
            related = item.get("relatedTickers")
            related_symbols = (
                tuple(str(t).upper() for t in related) if isinstance(related, list) else ()
            )
            thumbnail = item.get("thumbnail")
            image_url = None
            if isinstance(thumbnail, Mapping):
                resolutions = thumbnail.get("resolutions")
                if isinstance(resolutions, list) and resolutions:
                    first = resolutions[0]
                    if isinstance(first, Mapping):
                        image_url = first.get("url")
            articles.append(
                NewsArticle(
                    article_id=uuid_,
                    headline=title,
                    url=link,
                    source=str(item.get("publisher") or "Yahoo Finance"),
                    published_at=published_at,
                    related_symbols=related_symbols,
                    image_url=str(image_url) if image_url else None,
                )
            )
        if not articles:
            return None
        articles = articles[: max(1, query.limit)]
        provenance = ConnectorProvenance(
            provider_id=self.provider_id,
            provider_name="Yahoo Finance",
            source_type="public_endpoint",
            retrieved_at=utc_now(),
            auth_mode="none",
            metadata={"base_url": self.base_url},
        )
        return build_news_feed_from_mapping(symbol=symbol, articles=articles, provenance=provenance)

    def health(self) -> ProviderHealth:
        return ProviderHealth(
            provider_id=self.provider_id,
            healthy=self.enabled,
            authenticated=False,
            detail="enabled" if self.enabled else "disabled (set DSP_NEWS_YAHOO_ENABLED=1)",
        )


_ALPHA_VANTAGE_SENTIMENT_MAP = {
    "bullish": "positive",
    "somewhat-bullish": "positive",
    "neutral": "neutral",
    "somewhat-bearish": "negative",
    "bearish": "negative",
}


@dataclass
class AlphaVantageNewsAdapter(NewsProviderPort):
    """Alpha Vantage ``NEWS_SENTIMENT`` function adapter."""

    api_key: str
    base_url: str = "https://www.alphavantage.co/query"
    timeout_seconds: float = 15.0
    http_client: JsonHttpClient | None = None
    _provider_id: str = "alpha_vantage_news"

    @property
    def provider_id(self) -> str:
        return self._provider_id

    def _client(self) -> JsonHttpClient:
        return self.http_client or UrllibJsonHttpClient(timeout_seconds=self.timeout_seconds)

    def get_news(self, query: NewsQuery) -> AuthenticatedNewsFeed | None:
        if not self.api_key.strip():
            raise ProviderRequestError("alpha vantage news adapter requires api_key")
        symbol = query.instrument.symbol.strip().upper()
        payload = self._client().get_json(
            self.base_url,
            params={
                "function": "NEWS_SENTIMENT",
                "tickers": symbol,
                "limit": str(max(1, min(query.limit, 200))),
                "apikey": self.api_key,
            },
        )
        if not isinstance(payload, Mapping):
            return None
        feed_raw = payload.get("feed")
        if not isinstance(feed_raw, list) or not feed_raw:
            return None

        articles: list[NewsArticle] = []
        for item in feed_raw:
            if not isinstance(item, Mapping):
                continue
            title = str(item.get("title") or "").strip()
            url = str(item.get("url") or "").strip()
            if not title or not url:
                continue
            time_published = str(item.get("time_published") or "").strip()
            try:
                published_at = (
                    datetime.strptime(time_published, "%Y%m%dT%H%M%S").replace(tzinfo=UTC)
                    if time_published
                    else utc_now()
                )
            except ValueError:
                published_at = utc_now()
            sentiment_raw = str(item.get("overall_sentiment_label") or "").strip().lower()
            sentiment = _ALPHA_VANTAGE_SENTIMENT_MAP.get(sentiment_raw)
            ticker_sentiment = item.get("ticker_sentiment")
            related_symbols: tuple[str, ...] = ()
            if isinstance(ticker_sentiment, list):
                related_symbols = tuple(
                    str(t.get("ticker")).upper()
                    for t in ticker_sentiment
                    if isinstance(t, Mapping) and t.get("ticker")
                )
            articles.append(
                NewsArticle(
                    article_id=url,
                    headline=title,
                    url=url,
                    source=str(item.get("source") or "Alpha Vantage"),
                    published_at=published_at,
                    summary=str(item.get("summary")) if item.get("summary") else None,
                    sentiment=sentiment,
                    related_symbols=related_symbols or (symbol,),
                    image_url=str(item.get("banner_image")) if item.get("banner_image") else None,
                )
            )
        if not articles:
            return None
        provenance = ConnectorProvenance(
            provider_id=self.provider_id,
            provider_name="Alpha Vantage",
            source_type="licensed_vendor",
            retrieved_at=utc_now(),
            auth_mode="api_key",
            metadata={"base_url": self.base_url},
        )
        return build_news_feed_from_mapping(symbol=symbol, articles=articles, provenance=provenance)

    def health(self) -> ProviderHealth:
        ok = bool(self.api_key.strip())
        return ProviderHealth(
            provider_id=self.provider_id, healthy=ok, authenticated=ok,
            detail="configured" if ok else "missing api_key",
        )


@dataclass
class FinancialModelingPrepNewsAdapter(NewsProviderPort):
    """Financial Modeling Prep ``stock_news`` adapter."""

    api_key: str
    base_url: str = "https://financialmodelingprep.com/api/v3/stock_news"
    timeout_seconds: float = 15.0
    http_client: JsonHttpClient | None = None
    _provider_id: str = "fmp_news"

    @property
    def provider_id(self) -> str:
        return self._provider_id

    def _client(self) -> JsonHttpClient:
        return self.http_client or UrllibJsonHttpClient(timeout_seconds=self.timeout_seconds)

    def get_news(self, query: NewsQuery) -> AuthenticatedNewsFeed | None:
        if not self.api_key.strip():
            raise ProviderRequestError("financial modeling prep news adapter requires api_key")
        symbol = query.instrument.symbol.strip().upper()
        payload = self._client().get_json(
            self.base_url,
            params={
                "tickers": symbol,
                "limit": str(max(1, min(query.limit, 250))),
                "apikey": self.api_key,
            },
        )
        if not isinstance(payload, list) or not payload:
            return None

        articles: list[NewsArticle] = []
        for item in payload:
            if not isinstance(item, Mapping):
                continue
            title = str(item.get("title") or "").strip()
            url = str(item.get("url") or "").strip()
            if not title or not url:
                continue
            published_raw = str(item.get("publishedDate") or "").strip()
            try:
                published_at = (
                    datetime.fromisoformat(published_raw.replace(" ", "T")).replace(tzinfo=UTC)
                    if published_raw
                    else utc_now()
                )
            except ValueError:
                published_at = utc_now()
            articles.append(
                NewsArticle(
                    article_id=url,
                    headline=title,
                    url=url,
                    source=str(item.get("site") or "Financial Modeling Prep"),
                    published_at=published_at,
                    summary=str(item.get("text")) if item.get("text") else None,
                    related_symbols=(str(item.get("symbol")).upper(),) if item.get("symbol") else (symbol,),
                    image_url=str(item.get("image")) if item.get("image") else None,
                )
            )
        if not articles:
            return None
        provenance = ConnectorProvenance(
            provider_id=self.provider_id,
            provider_name="Financial Modeling Prep",
            source_type="licensed_vendor",
            retrieved_at=utc_now(),
            auth_mode="api_key",
            metadata={"base_url": self.base_url},
        )
        return build_news_feed_from_mapping(symbol=symbol, articles=articles, provenance=provenance)

    def health(self) -> ProviderHealth:
        ok = bool(self.api_key.strip())
        return ProviderHealth(
            provider_id=self.provider_id, healthy=ok, authenticated=ok,
            detail="configured" if ok else "missing api_key",
        )


@dataclass
class PolygonNewsAdapter(NewsProviderPort):
    """Polygon.io ``/v2/reference/news`` adapter."""

    api_key: str
    base_url: str = "https://api.polygon.io/v2/reference/news"
    timeout_seconds: float = 15.0
    http_client: JsonHttpClient | None = None
    _provider_id: str = "polygon_news"

    @property
    def provider_id(self) -> str:
        return self._provider_id

    def _client(self) -> JsonHttpClient:
        return self.http_client or UrllibJsonHttpClient(timeout_seconds=self.timeout_seconds)

    def get_news(self, query: NewsQuery) -> AuthenticatedNewsFeed | None:
        if not self.api_key.strip():
            raise ProviderRequestError("polygon news adapter requires api_key")
        symbol = query.instrument.symbol.strip().upper()
        payload = self._client().get_json(
            self.base_url,
            params={
                "ticker": symbol,
                "limit": str(max(1, min(query.limit, 1000))),
                "apiKey": self.api_key,
            },
        )
        if not isinstance(payload, Mapping):
            return None
        results = payload.get("results")
        if not isinstance(results, list) or not results:
            return None

        articles: list[NewsArticle] = []
        for item in results:
            if not isinstance(item, Mapping):
                continue
            title = str(item.get("title") or "").strip()
            url = str(item.get("article_url") or "").strip()
            article_id = str(item.get("id") or url).strip()
            if not title or not url or not article_id:
                continue
            published_raw = str(item.get("published_utc") or "").strip()
            try:
                published_at = (
                    datetime.fromisoformat(published_raw.replace("Z", "+00:00"))
                    if published_raw
                    else utc_now()
                )
            except ValueError:
                published_at = utc_now()
            publisher = item.get("publisher")
            source = "Polygon"
            if isinstance(publisher, Mapping) and publisher.get("name"):
                source = str(publisher["name"])
            tickers = item.get("tickers")
            related_symbols = (
                tuple(str(t).upper() for t in tickers) if isinstance(tickers, list) else (symbol,)
            )
            articles.append(
                NewsArticle(
                    article_id=article_id,
                    headline=title,
                    url=url,
                    source=source,
                    published_at=published_at,
                    summary=str(item.get("description")) if item.get("description") else None,
                    related_symbols=related_symbols,
                    image_url=str(item.get("image_url")) if item.get("image_url") else None,
                )
            )
        if not articles:
            return None
        provenance = ConnectorProvenance(
            provider_id=self.provider_id,
            provider_name="Polygon.io",
            source_type="licensed_vendor",
            retrieved_at=utc_now(),
            auth_mode="api_key",
            metadata={"base_url": self.base_url},
        )
        return build_news_feed_from_mapping(symbol=symbol, articles=articles, provenance=provenance)

    def health(self) -> ProviderHealth:
        ok = bool(self.api_key.strip())
        return ProviderHealth(
            provider_id=self.provider_id, healthy=ok, authenticated=ok,
            detail="configured" if ok else "missing api_key",
        )


def build_default_news_registry_from_env() -> PriorityProviderRegistry[NewsProviderPort]:
    """Compose a news provider registry from environment configuration.

    Registers every vendor with credentials/flags present, in a fixed
    priority order (licensed structured feeds before unofficial public
    endpoints). P1-03: Null is registered only outside production; production
    refuses a Null-only / memory-only registry.
    """
    from data_engine.connector_framework.production_profile import (
        finalize_provider_registry,
        memory_adapter_allowed,
    )

    registry: PriorityProviderRegistry[NewsProviderPort] = PriorityProviderRegistry()

    fmp_key = os.environ.get("DSP_NEWS_FMP_API_KEY", "").strip()
    if fmp_key:
        registry.register(
            FinancialModelingPrepNewsAdapter(api_key=fmp_key),
            provider_id="fmp_news",
            priority=10,
        )

    polygon_key = os.environ.get("DSP_NEWS_POLYGON_API_KEY", "").strip()
    if polygon_key:
        registry.register(
            PolygonNewsAdapter(api_key=polygon_key), provider_id="polygon_news", priority=20
        )

    av_key = os.environ.get("DSP_NEWS_ALPHAVANTAGE_API_KEY", "").strip()
    if av_key:
        registry.register(
            AlphaVantageNewsAdapter(api_key=av_key), provider_id="alpha_vantage_news", priority=30
        )

    if os.environ.get("DSP_NEWS_YAHOO_ENABLED", "").lower() in {"1", "true", "yes"}:
        registry.register(
            YahooFinanceNewsAdapter(enabled=True), provider_id="yahoo_finance_news", priority=40
        )

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
