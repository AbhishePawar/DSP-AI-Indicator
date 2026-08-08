"""Authenticated shareholding/ownership (Data Connector Framework)."""

from __future__ import annotations

from data_engine.ownership.adapters import (
    BseOwnershipAdapter,
    FinancialModelingPrepOwnershipAdapter,
    InMemoryOwnershipAdapter,
    NseOwnershipAdapter,
    NullOwnershipAdapter,
    ScreenerOwnershipAdapter,
    YahooFinanceOwnershipAdapter,
    build_default_ownership_registry_from_env,
    build_ownership_bundle_from_mapping,
)
from data_engine.ownership.models import (
    OWNERSHIP_HOLDER_TYPES,
    AuthenticatedOwnership,
    OwnershipStake,
)
from data_engine.ownership.registry import OwnershipProviderRegistry
from data_engine.ownership.service import (
    OwnershipProviderPort,
    OwnershipQuery,
    OwnershipService,
    OwnershipServiceMetrics,
)
from data_engine.ownership.validation import validate_authenticated_ownership

__all__ = [
    "OWNERSHIP_HOLDER_TYPES",
    "AuthenticatedOwnership",
    "BseOwnershipAdapter",
    "FinancialModelingPrepOwnershipAdapter",
    "InMemoryOwnershipAdapter",
    "NseOwnershipAdapter",
    "NullOwnershipAdapter",
    "OwnershipProviderPort",
    "OwnershipProviderRegistry",
    "OwnershipQuery",
    "OwnershipService",
    "OwnershipServiceMetrics",
    "OwnershipStake",
    "ScreenerOwnershipAdapter",
    "YahooFinanceOwnershipAdapter",
    "build_default_ownership_registry_from_env",
    "build_ownership_bundle_from_mapping",
    "validate_authenticated_ownership",
]
