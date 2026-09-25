"""Investment data provider selection for authenticated quote + statements.

Mirrors the FMP env-factory path used by ``/analyse`` via
``build_default_quote_adapter_from_env`` /
``build_default_statement_adapter_from_env``.

``DSP_INVESTMENT_DATA_PROVIDER``:
  - ``unavailable`` / ``none`` / ``off`` — no investment feed; fail closed honestly
  - ``fmp`` — FMP only (explicit)
  - unset / ``auto`` — existing ConfiguredHttp → FMP → memory → null route

Does not clear G2. Does not redesign valuation / Buffett / MoS.
"""

from __future__ import annotations

import os
from collections.abc import Mapping

from data_engine.connector_framework.production_profile import (
    ConnectorConfigurationError,
)

__all__ = [
    "DSP_INVESTMENT_DATA_PROVIDER_ENV",
    "INVESTMENT_DATA_UNAVAILABLE",
    "InvestmentDataProvider",
    "investment_data_is_unavailable",
    "resolve_investment_data_provider",
]

DSP_INVESTMENT_DATA_PROVIDER_ENV = "DSP_INVESTMENT_DATA_PROVIDER"
INVESTMENT_DATA_UNAVAILABLE = "INVESTMENT_DATA_UNAVAILABLE"

# Normalized selection values
InvestmentDataProvider = str  # "auto" | "fmp" | "unavailable"


def resolve_investment_data_provider(
    environ: Mapping[str, str] | None = None,
) -> InvestmentDataProvider:
    """Return normalized provider selection for investment connectors."""
    env_map = environ if environ is not None else os.environ
    raw = str(env_map.get(DSP_INVESTMENT_DATA_PROVIDER_ENV) or "").strip().lower()
    if not raw or raw in {"auto", "default"}:
        return "auto"
    if raw in {"unavailable", "none", "off"}:
        return "unavailable"
    if raw == "fmp":
        return raw
    raise ConnectorConfigurationError(
        f"P1-03: invalid {DSP_INVESTMENT_DATA_PROVIDER_ENV}={raw!r}; "
        "allowed values: unavailable, fmp, auto (or unset)"
    )


def investment_data_is_unavailable(
    environ: Mapping[str, str] | None = None,
) -> bool:
    """True when production has no approved investment feed (honest absence)."""
    return resolve_investment_data_provider(environ) == "unavailable"
