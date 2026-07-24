"""Registration wiring for the FRED economic adapter."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from data_engine.adapters import BaseAdapter
from data_engine.adapters.fred.adapter import FredEconomicAdapter
from data_engine.providers import (
    AuthenticationType,
    ProviderCapabilities,
    ProviderFactory,
    ProviderMetadata,
    ProviderRegistry,
    RateLimitPolicy,
)

__all__ = [
    "FRED_METADATA",
    "build_fred_adapter",
    "register_fred",
]

FRED_METADATA = ProviderMetadata(
    provider_id="fred",
    name="FRED",
    version="1.0.0",
    description=(
        "US macroeconomic series via the Federal Reserve Economic Data "
        "(FRED) observations API."
    ),
    homepage="https://fred.stlouisfed.org",
    capabilities=ProviderCapabilities.from_flags(economic_data=True),
    rate_limit=RateLimitPolicy(requests_per_day=120_000),
    auth_type=AuthenticationType.API_KEY,
    priority=1,
)


def build_fred_adapter(config: Mapping[str, Any]) -> BaseAdapter:
    """Build a :class:`FredEconomicAdapter` from configuration.

    Recognized keys: ``api_key``, ``timeout_seconds``.
    """
    return FredEconomicAdapter(
        api_key=config.get("api_key"),
        timeout_seconds=config.get("timeout_seconds", 10.0),
    )


def register_fred(
    factory: ProviderFactory,
    registry: ProviderRegistry,
    config: Mapping[str, Any] | None = None,
) -> BaseAdapter:
    """Build and register the FRED adapter using existing infrastructure."""
    provider_id = FRED_METADATA.provider_id
    if not factory.is_registered(provider_id):
        factory.register_builder(provider_id, build_fred_adapter)
    adapter = factory.create(provider_id, config)
    registry.register(adapter, FRED_METADATA)
    return adapter
