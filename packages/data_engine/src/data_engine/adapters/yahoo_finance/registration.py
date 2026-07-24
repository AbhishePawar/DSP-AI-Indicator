"""Registration wiring for the Yahoo Finance adapter.

This module bridges :class:`YahooFinanceAdapter` to the existing,
unmodified :class:`~data_engine.providers.factory.ProviderFactory` and
:class:`~data_engine.providers.registry.ProviderRegistry` — it adds no
new registration mechanism of its own.

Nothing here runs automatically at import time. Consistent with the
pattern established in Sprint 2.2/2.3, actually registering a provider
is an application-composition decision, not something this package
performs as a side effect of being imported.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from data_engine.adapters import BaseAdapter
from data_engine.adapters.yahoo_finance.adapter import YahooFinanceAdapter
from data_engine.providers import (
    ProviderCapabilities,
    ProviderFactory,
    ProviderMetadata,
    ProviderRegistry,
    RateLimitPolicy,
)

__all__ = [
    "YAHOO_FINANCE_METADATA",
    "build_yahoo_finance_adapter",
    "register_yahoo_finance",
]

YAHOO_FINANCE_METADATA = ProviderMetadata(
    provider_id="yahoo_finance",
    name="Yahoo Finance",
    version="1.0.0",
    description="Historical daily OHLCV market data via Yahoo Finance's chart API.",
    homepage="https://finance.yahoo.com",
    capabilities=ProviderCapabilities.from_flags(market_data=True, daily=True),
    rate_limit=RateLimitPolicy(),
    priority=1,
)


def build_yahoo_finance_adapter(config: Mapping[str, Any]) -> BaseAdapter:
    """Build a :class:`YahooFinanceAdapter` from a configuration mapping.

    Conforms to the ``ProviderBuilder`` signature expected by
    :meth:`ProviderFactory.register_builder`.

    Args:
        config: Configuration mapping. Recognizes an optional
            ``timeout_seconds`` key; all other keys are ignored.

    Returns:
        A newly constructed ``YahooFinanceAdapter``.
    """
    timeout_seconds = config.get("timeout_seconds", 10.0)
    return YahooFinanceAdapter(timeout_seconds=timeout_seconds)


def register_yahoo_finance(
    factory: ProviderFactory,
    registry: ProviderRegistry,
    config: Mapping[str, Any] | None = None,
) -> BaseAdapter:
    """Build and register the Yahoo Finance adapter using existing infrastructure.

    This is a convenience wrapper around the standard
    build-then-register sequence — it does not add any new capability
    to ``ProviderFactory`` or ``ProviderRegistry``, and it is never
    called automatically; whoever composes the running application
    decides if and when to call it.

    Args:
        factory: The provider factory to register the builder with.
        registry: The provider registry to register the built adapter
            with.
        config: Optional configuration forwarded to
            :func:`build_yahoo_finance_adapter`.

    Returns:
        The constructed and registered ``YahooFinanceAdapter``.
    """
    if not factory.is_registered(YAHOO_FINANCE_METADATA.provider_id):
        factory.register_builder(
            YAHOO_FINANCE_METADATA.provider_id, build_yahoo_finance_adapter
        )
    adapter = factory.create(YAHOO_FINANCE_METADATA.provider_id, config)
    registry.register(adapter, YAHOO_FINANCE_METADATA)
    return adapter
