"""Provider registration, discovery, and construction for the Data Engine.

This subpackage is the Data Engine's provider framework: a vendor-agnostic
set of building blocks that every future adapter (Yahoo Finance, Alpha
Vantage, Polygon, Financial Modeling Prep, Twelve Data, NSE, RBI, FRED,
Quandl, CoinGecko, or anything added later) plugs into without requiring
any change here.

Modules:
    enums: ``ProviderStatus``, ``AuthenticationType``, ``DataCapability``
        — the closed vocabularies the rest of this subpackage is built on.
    capabilities: ``ProviderCapabilities`` — structured, set-based
        capability description.
    metadata: ``ProviderMetadata``, ``RateLimitPolicy`` — the descriptive
        record stored per registered provider.
    registry: ``ProviderRegistry`` — tracks constructed adapter instances
        and their metadata; supports lookup, capability filtering, and
        preferred-provider selection.
    factory: ``ProviderFactory`` — tracks *how* to construct an adapter
        from configuration, decoupled from the registry that tracks
        already-constructed instances.

No concrete provider is implemented in any of these modules.
"""

from __future__ import annotations

from data_engine.providers.capabilities import ProviderCapabilities
from data_engine.providers.enums import (
    AuthenticationType,
    DataCapability,
    ProviderStatus,
)
from data_engine.providers.factory import ProviderBuilder, ProviderFactory
from data_engine.providers.metadata import ProviderMetadata, RateLimitPolicy
from data_engine.providers.registry import ProviderRegistry

__all__ = [
    "AuthenticationType",
    "DataCapability",
    "ProviderBuilder",
    "ProviderCapabilities",
    "ProviderFactory",
    "ProviderMetadata",
    "ProviderRegistry",
    "ProviderStatus",
    "RateLimitPolicy",
]
