"""Ownership provider registry — priority-aware, thread-safe."""

from __future__ import annotations

from data_engine.connector_framework.registry import PriorityProviderRegistry
from data_engine.ownership.service import OwnershipProviderPort

__all__ = ["OwnershipProviderRegistry"]


class OwnershipProviderRegistry(PriorityProviderRegistry[OwnershipProviderPort]):
    """Registry of authenticated ownership providers, ordered by priority."""
