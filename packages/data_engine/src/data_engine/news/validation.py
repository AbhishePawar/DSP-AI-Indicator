"""Validate authenticated news feeds — reject invalid / fabricated envelopes."""

from __future__ import annotations

from data_engine.exceptions import InvalidProviderDataError
from data_engine.news.models import SENTIMENT_LABELS, AuthenticatedNewsFeed, NewsArticle

__all__ = ["validate_authenticated_news_feed"]

_DISALLOWED_SOURCE = frozenset(
    {"", "example", "dummy", "placeholder", "fabricated", "estimated"}
)


def _validate_article(article: NewsArticle, index: int) -> None:
    prefix = f"articles[{index}]"
    if not article.article_id or not str(article.article_id).strip():
        raise InvalidProviderDataError(f"{prefix} missing article_id")
    if not article.headline or not str(article.headline).strip():
        raise InvalidProviderDataError(f"{prefix} missing headline")
    if not article.url or not str(article.url).strip():
        raise InvalidProviderDataError(f"{prefix} missing url")
    if not article.source or not str(article.source).strip():
        raise InvalidProviderDataError(f"{prefix} missing source")
    if article.sentiment is not None and article.sentiment not in SENTIMENT_LABELS:
        raise InvalidProviderDataError(
            f"{prefix}.sentiment must be one of {sorted(SENTIMENT_LABELS)} or "
            f"null, got {article.sentiment!r}"
        )


def validate_authenticated_news_feed(bundle: AuthenticatedNewsFeed) -> None:
    """Reject structurally invalid news bundles. Never invent replacements."""
    if not bundle.identity.symbol or not str(bundle.identity.symbol).strip():
        raise InvalidProviderDataError("news feed missing identity.symbol")
    if not bundle.provenance.provider_id.strip():
        raise InvalidProviderDataError("news feed missing provider_id provenance")
    if not bundle.provenance.provider_name.strip():
        raise InvalidProviderDataError("news feed missing provider_name provenance")
    if bundle.provenance.source_type.strip().lower() in _DISALLOWED_SOURCE:
        raise InvalidProviderDataError(
            f"disallowed provenance source_type={bundle.provenance.source_type!r}"
        )
    if not bundle.articles:
        raise InvalidProviderDataError(
            "authenticated news feed must include at least one article "
            "(use None from adapter when unavailable)"
        )
    for i, article in enumerate(bundle.articles):
        _validate_article(article, i)
