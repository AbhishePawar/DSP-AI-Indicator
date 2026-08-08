"""News provider registry — priority-aware, thread-safe."""

from __future__ import annotations

from data_engine.connector_framework.registry import PriorityProviderRegistry
from data_engine.news.service import NewsProviderPort

__all__ = ["NewsProviderRegistry"]


class NewsProviderRegistry(PriorityProviderRegistry[NewsProviderPort]):
    """Registry of authenticated news providers, ordered by priority."""
