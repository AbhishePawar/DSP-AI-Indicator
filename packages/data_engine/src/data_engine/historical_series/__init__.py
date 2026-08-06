"""Authenticated historical time-series subsystem (EPIC-D004)."""

from __future__ import annotations

from data_engine.historical_series.adapters import (
    ConfiguredHttpHistoricalAdapter,
    InMemoryAuthenticatedHistoricalAdapter,
    NullAuthenticatedHistoricalAdapter,
    build_default_historical_adapter_from_env,
    build_historical_bundle_from_mapping,
)
from data_engine.historical_series.models import (
    BAR_FREQUENCIES,
    SERIES_KINDS,
    AuthenticatedHistoricalBundle,
    AuthenticatedOhlcvBar,
    AuthenticatedPoint,
    AuthenticatedSnapshot,
    HistoricalCompanyIdentity,
    HistoricalField,
    HistoricalProvenance,
    utc_now,
)
from data_engine.historical_series.registry import HistoricalSeriesProviderRegistry
from data_engine.historical_series.service import (
    HistoricalProviderHealth,
    HistoricalSeriesPort,
    HistoricalSeriesQuery,
    HistoricalSeriesService,
    HistoricalSeriesServiceMetrics,
)
from data_engine.historical_series.validation import (
    validate_authenticated_historical_bundle,
)

__all__ = [
    "BAR_FREQUENCIES",
    "SERIES_KINDS",
    "AuthenticatedHistoricalBundle",
    "AuthenticatedOhlcvBar",
    "AuthenticatedPoint",
    "AuthenticatedSnapshot",
    "ConfiguredHttpHistoricalAdapter",
    "HistoricalCompanyIdentity",
    "HistoricalField",
    "HistoricalProviderHealth",
    "HistoricalProvenance",
    "HistoricalSeriesPort",
    "HistoricalSeriesProviderRegistry",
    "HistoricalSeriesQuery",
    "HistoricalSeriesService",
    "HistoricalSeriesServiceMetrics",
    "InMemoryAuthenticatedHistoricalAdapter",
    "NullAuthenticatedHistoricalAdapter",
    "build_default_historical_adapter_from_env",
    "build_historical_bundle_from_mapping",
    "utc_now",
    "validate_authenticated_historical_bundle",
]
