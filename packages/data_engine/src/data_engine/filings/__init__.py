"""Authenticated regulatory/corporate filings (Data Connector Framework)."""

from __future__ import annotations

from data_engine.filings.adapters import (
    BseFilingsAdapter,
    FinancialModelingPrepFilingsAdapter,
    InMemoryFilingsAdapter,
    NseFilingsAdapter,
    NullFilingsAdapter,
    ScreenerFilingsAdapter,
    SecEdgarFilingsAdapter,
    build_default_filings_registry_from_env,
    build_filings_bundle_from_mapping,
)
from data_engine.filings.models import FILING_TYPES, AuthenticatedFilings, Filing
from data_engine.filings.registry import FilingsProviderRegistry
from data_engine.filings.service import (
    FilingsProviderPort,
    FilingsQuery,
    FilingsService,
    FilingsServiceMetrics,
)
from data_engine.filings.validation import validate_authenticated_filings

__all__ = [
    "FILING_TYPES",
    "AuthenticatedFilings",
    "BseFilingsAdapter",
    "Filing",
    "FilingsProviderPort",
    "FilingsProviderRegistry",
    "FilingsQuery",
    "FilingsService",
    "FilingsServiceMetrics",
    "FinancialModelingPrepFilingsAdapter",
    "InMemoryFilingsAdapter",
    "NseFilingsAdapter",
    "NullFilingsAdapter",
    "ScreenerFilingsAdapter",
    "SecEdgarFilingsAdapter",
    "build_default_filings_registry_from_env",
    "build_filings_bundle_from_mapping",
    "validate_authenticated_filings",
]
