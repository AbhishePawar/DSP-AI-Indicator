"""Investment data provider selection for authenticated quote + statements.

Mirrors the FMP env-factory path used by ``/analyse`` via
``build_default_quote_adapter_from_env`` /
``build_default_statement_adapter_from_env``.

``DSP_INVESTMENT_DATA_PROVIDER``:
  - ``upstox`` — Upstox U2 quote + U4 statements only (no FMP/Yahoo/memory fallback)
  - ``fmp`` — FMP only (explicit)
  - unset / ``auto`` — existing ConfiguredHttp → FMP → memory → null route

Does not clear G2. Does not redesign valuation / Buffett / MoS.
"""

from __future__ import annotations

import os
from typing import Mapping

from data_engine.connector_framework.production_profile import (
    ConnectorConfigurationError,
    is_production_environment,
)

__all__ = [
    "DSP_INVESTMENT_DATA_PROVIDER_ENV",
    "InvestmentDataProvider",
    "resolve_investment_data_provider",
    "require_upstox_analytics_token",
]

DSP_INVESTMENT_DATA_PROVIDER_ENV = "DSP_INVESTMENT_DATA_PROVIDER"

# Normalized selection values
InvestmentDataProvider = str  # "auto" | "upstox" | "fmp"


def resolve_investment_data_provider(
    environ: Mapping[str, str] | None = None,
) -> InvestmentDataProvider:
    """Return normalized provider selection for investment connectors."""
    env_map = environ if environ is not None else os.environ
    raw = str(env_map.get(DSP_INVESTMENT_DATA_PROVIDER_ENV) or "").strip().lower()
    if not raw or raw in {"auto", "default"}:
        return "auto"
    if raw in {"upstox", "fmp"}:
        return raw
    raise ConnectorConfigurationError(
        f"P1-03: invalid {DSP_INVESTMENT_DATA_PROVIDER_ENV}={raw!r}; "
        "allowed values: upstox, fmp, auto (or unset)"
    )


def require_upstox_analytics_token(
    *,
    connector: str,
    environ: Mapping[str, str] | None = None,
) -> str:
    """Return Upstox Analytics Token or fail closed in production.

    Outside production, returns empty string when absent (caller may select Null).
    Never logs or returns the token to callers beyond the credential string itself.
    """
    from data_engine.upstox_investment import resolve_upstox_analytics_token

    token = resolve_upstox_analytics_token(environ)
    if token:
        return token
    if is_production_environment(environ):  # type: ignore[arg-type]
        raise ConnectorConfigurationError(
            f"P1-03: production requires authenticated {connector} provider; "
            f"{DSP_INVESTMENT_DATA_PROVIDER_ENV}=upstox but "
            "DSP_UPSTOX_ANALYTICS_TOKEN is absent. "
            "Null/demo/seed/FMP fallback is not permitted when Upstox is selected."
        )
    return ""
