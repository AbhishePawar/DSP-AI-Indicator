"""Authenticated news models.

Retrieval and normalization only — no sentiment scoring is computed
here; a ``sentiment`` label is only ever carried through when a
provider reports one itself (never invented, never derived).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from data_engine.connector_framework.models import (
    ConnectorCompanyIdentity,
    ConnectorProvenance,
)

__all__ = [
    "SENTIMENT_LABELS",
    "AuthenticatedNewsFeed",
    "NewsArticle",
]

SENTIMENT_LABELS = frozenset({"positive", "negative", "neutral", "mixed"})


@dataclass(frozen=True, slots=True)
class NewsArticle:
    """One authenticated news article — as-reported fields only."""

    article_id: str
    headline: str
    url: str
    source: str
    published_at: datetime
    summary: str | None = None
    sentiment: str | None = None
    """Only present when the provider itself reports it; never computed here."""
    related_symbols: tuple[str, ...] = ()
    image_url: str | None = None
    metadata: dict[str, str] = field(default_factory=dict)

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "article_id": self.article_id,
            "headline": self.headline,
            "url": self.url,
            "source": self.source,
            "published_at": self.published_at.isoformat(),
            "summary": self.summary,
            "sentiment": self.sentiment,
            "related_symbols": list(self.related_symbols),
            "image_url": self.image_url,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True, slots=True)
class AuthenticatedNewsFeed:
    """Authenticated news bundle for one company."""

    identity: ConnectorCompanyIdentity
    articles: tuple[NewsArticle, ...]
    provenance: ConnectorProvenance

    def has_any_article(self) -> bool:
        return len(self.articles) > 0

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "authenticated": True,
            "identity": self.identity.to_dict(),
            "articles": [a.to_public_dict() for a in self.articles],
            "provenance": self.provenance.to_dict(),
        }
