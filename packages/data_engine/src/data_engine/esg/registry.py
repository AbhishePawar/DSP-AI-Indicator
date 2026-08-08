"""ESG provider registry — priority-aware, thread-safe."""

from __future__ import annotations

from data_engine.connector_framework.registry import PriorityProviderRegistry
from data_engine.esg.service import EsgProviderPort

__all__ = ["EsgProviderRegistry"]


class EsgProviderRegistry(PriorityProviderRegistry[EsgProviderPort]):
    """Registry of authenticated ESG providers, ordered by priority."""
