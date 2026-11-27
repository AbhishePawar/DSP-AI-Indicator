"""Upstox V3 Market Data Subsystem.

Provides server-side authenticated market quote and historical candle integration
using official Upstox V3 REST endpoints:
- GET /v3/market-quote/quotes
- GET /v3/historical-candle/{instrument_key}/{unit}/{interval}/{to_date}/{from_date}

Credentials are read server-side from UPSTOX_ACCESS_TOKEN and never exposed.
"""

from __future__ import annotations

from data_engine.upstox.instrument_resolver import (
    UpstoxInstrumentRecord,
    UpstoxInstrumentResolver,
    UpstoxResolutionResult,
    get_upstox_resolver,
)

__all__ = [
    "UpstoxInstrumentRecord",
    "UpstoxInstrumentResolver",
    "UpstoxResolutionResult",
    "get_upstox_resolver",
]
