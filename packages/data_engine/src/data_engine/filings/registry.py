"""Filings provider registry — priority-aware, thread-safe."""

from __future__ import annotations

from data_engine.connector_framework.registry import PriorityProviderRegistry
from data_engine.filings.service import FilingsProviderPort

__all__ = ["FilingsProviderRegistry"]


class FilingsProviderRegistry(PriorityProviderRegistry[FilingsProviderPort]):
    """Registry of authenticated filings providers, ordered by priority."""
