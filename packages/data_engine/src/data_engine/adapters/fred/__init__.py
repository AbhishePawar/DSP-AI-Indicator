"""FRED macroeconomic adapter package."""

from __future__ import annotations

from data_engine.adapters.fred.adapter import FredEconomicAdapter
from data_engine.adapters.fred.catalog import (
    CANONICAL_INDICATOR_CODES,
    FredSeriesSpec,
    resolve_fred_series,
    supported_indicator_codes,
)
from data_engine.adapters.fred.registration import (
    FRED_METADATA,
    build_fred_adapter,
    register_fred,
)

__all__ = [
    "CANONICAL_INDICATOR_CODES",
    "FRED_METADATA",
    "FredEconomicAdapter",
    "FredSeriesSpec",
    "build_fred_adapter",
    "register_fred",
    "resolve_fred_series",
    "supported_indicator_codes",
]
