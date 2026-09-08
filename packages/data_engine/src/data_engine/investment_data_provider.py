"""Investment data provider selection for authenticated quote + statements.

``DSP_INVESTMENT_DATA_PROVIDER``:
  - ``none`` / ``unavailable`` / ``null`` — no market-data provider (Null adapters)
  - ``fmp`` — FMP only (explicit opt-in; not an Upstox replacement)
  - unset / ``auto`` — ConfiguredHttp → FMP → memory (non-production)

Upstox is retired. There is no silent vendor fallback from a failed
primary onto a secondary.
"""

from __future__ import annotations

import os
from collections.abc import Mapping

from data_engine.connector_framework.production_profile import (
    ConnectorConfigurationError,
)

__all__ = [
    "DSP_INVESTMENT_DATA_PROVIDER_ENV",
    "InvestmentDataProvider",
    "is_no_data_provider",
    "resolve_investment_data_provider",
]

DSP_INVESTMENT_DATA_PROVIDER_ENV = "DSP_INVESTMENT_DATA_PROVIDER"

InvestmentDataProvider = str  # "auto" | "none" | "fmp"

_NO_DATA = frozenset({"none", "unavailable", "null", "off"})


def resolve_investment_data_provider(
    environ: Mapping[str, str] | None = None,
) -> InvestmentDataProvider:
    """Return normalized provider selection for investment connectors."""
    env_map = environ if environ is not None else os.environ
    raw = str(env_map.get(DSP_INVESTMENT_DATA_PROVIDER_ENV) or "").strip().lower()
    if not raw or raw in {"auto", "default"}:
        return "auto"
    if raw in _NO_DATA:
        return "none"
    if raw == "fmp":
        return raw
    if raw == "upstox":
        raise ConnectorConfigurationError(
            f"P1-03: {DSP_INVESTMENT_DATA_PROVIDER_ENV}=upstox is retired. "
            "Set none (no-data), fmp (explicit), or auto."
        )
    raise ConnectorConfigurationError(
        f"P1-03: invalid {DSP_INVESTMENT_DATA_PROVIDER_ENV}={raw!r}; "
        "allowed values: none, fmp, auto (or unset)"
    )


def is_no_data_provider(environ: Mapping[str, str] | None = None) -> bool:
    return resolve_investment_data_provider(environ) == "none"
