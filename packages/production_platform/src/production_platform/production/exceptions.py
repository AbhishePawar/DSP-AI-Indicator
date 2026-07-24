"""Production Services exceptions — no business semantics."""

from __future__ import annotations

from core.exceptions import DSPAIError

__all__ = [
    "ConfigurationError",
    "ProductionError",
    "ProviderError",
]


class ProductionError(DSPAIError):
    """Base production-platform error."""


class ConfigurationError(ProductionError):
    """Configuration missing or inconsistent."""


class ProviderError(ProductionError):
    """Port / adapter invocation failure."""
