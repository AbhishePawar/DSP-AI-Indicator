"""Registration wiring for the Yahoo Finance fundamentals adapter.

Bridges :class:`YahooFinanceFundamentalsAdapter` to the existing
:class:`~data_engine.providers.factory.ProviderFactory` and
:class:`~data_engine.providers.registry.ProviderRegistry` without
adding a new registration mechanism. Registration is never automatic
at import time — composing applications decide when to call
:func:`register_yahoo_finance_fundamentals`.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from data_engine.adapters import BaseAdapter
from data_engine.adapters.yahoo_finance.fundamentals_adapter import (
    YahooFinanceFundamentalsAdapter,
)
from data_engine.providers import (
    ProviderCapabilities,
    ProviderFactory,
    ProviderMetadata,
    ProviderRegistry,
    RateLimitPolicy,
)

__all__ = [
    "YAHOO_FINANCE_FUNDAMENTALS_METADATA",
    "build_yahoo_finance_fundamentals_adapter",
    "register_yahoo_finance_fundamentals",
]

YAHOO_FINANCE_FUNDAMENTALS_METADATA = ProviderMetadata(
    provider_id="yahoo_finance_fundamentals",
    name="Yahoo Finance Fundamentals",
    version="1.0.0",
    description=(
        "As-reported annual/quarterly financial statements and key "
        "statistics via Yahoo Finance's quoteSummary API."
    ),
    homepage="https://finance.yahoo.com",
    capabilities=ProviderCapabilities.from_flags(fundamentals=True),
    rate_limit=RateLimitPolicy(),
    priority=1,
)


def build_yahoo_finance_fundamentals_adapter(config: Mapping[str, Any]) -> BaseAdapter:
    """Build a :class:`YahooFinanceFundamentalsAdapter` from configuration.

    Conforms to the ``ProviderBuilder`` signature expected by
    :meth:`ProviderFactory.register_builder`.

    Args:
        config: Configuration mapping. Recognizes an optional
            ``timeout_seconds`` key; all other keys are ignored.

    Returns:
        A newly constructed ``YahooFinanceFundamentalsAdapter``.
    """
    timeout_seconds = config.get("timeout_seconds", 10.0)
    return YahooFinanceFundamentalsAdapter(timeout_seconds=timeout_seconds)


def register_yahoo_finance_fundamentals(
    factory: ProviderFactory,
    registry: ProviderRegistry,
    config: Mapping[str, Any] | None = None,
) -> BaseAdapter:
    """Build and register the Yahoo Finance fundamentals adapter.

    Args:
        factory: The provider factory to register the builder with.
        registry: The provider registry to register the built adapter
            with.
        config: Optional configuration forwarded to
            :func:`build_yahoo_finance_fundamentals_adapter`.

    Returns:
        The constructed and registered adapter.
    """
    provider_id = YAHOO_FINANCE_FUNDAMENTALS_METADATA.provider_id
    if not factory.is_registered(provider_id):
        factory.register_builder(provider_id, build_yahoo_finance_fundamentals_adapter)
    adapter = factory.create(provider_id, config)
    registry.register(adapter, YAHOO_FINANCE_FUNDAMENTALS_METADATA)
    return adapter
