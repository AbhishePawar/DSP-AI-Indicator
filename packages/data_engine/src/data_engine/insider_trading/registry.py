"""Insider trading provider registry — priority-aware, thread-safe."""

from __future__ import annotations

from data_engine.connector_framework.registry import PriorityProviderRegistry
from data_engine.insider_trading.service import InsiderTradingProviderPort

__all__ = ["InsiderTradingProviderRegistry"]


class InsiderTradingProviderRegistry(PriorityProviderRegistry[InsiderTradingProviderPort]):
    """Registry of authenticated insider trading providers, ordered by priority."""
