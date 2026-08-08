"""Authenticated company news (Data Connector Framework)."""

from __future__ import annotations

from data_engine.news.adapters import (
    AlphaVantageNewsAdapter,
    FinancialModelingPrepNewsAdapter,
    InMemoryNewsAdapter,
    NullNewsAdapter,
    PolygonNewsAdapter,
    YahooFinanceNewsAdapter,
    build_default_news_registry_from_env,
    build_news_feed_from_mapping,
)
from data_engine.news.models import SENTIMENT_LABELS, AuthenticatedNewsFeed, NewsArticle
from data_engine.news.registry import NewsProviderRegistry
from data_engine.news.service import NewsProviderPort, NewsQuery, NewsService, NewsServiceMetrics
from data_engine.news.validation import validate_authenticated_news_feed

__all__ = [
    "SENTIMENT_LABELS",
    "AlphaVantageNewsAdapter",
    "AuthenticatedNewsFeed",
    "FinancialModelingPrepNewsAdapter",
    "InMemoryNewsAdapter",
    "NewsArticle",
    "NewsProviderPort",
    "NewsProviderRegistry",
    "NewsQuery",
    "NewsService",
    "NewsServiceMetrics",
    "NullNewsAdapter",
    "PolygonNewsAdapter",
    "YahooFinanceNewsAdapter",
    "build_default_news_registry_from_env",
    "build_news_feed_from_mapping",
    "validate_authenticated_news_feed",
]
