"""Investment data provider selection for authenticated quote + statements.

``DSP_INVESTMENT_DATA_PROVIDER`` supports the remaining vendor-neutral routes:
``fmp`` for an explicit FMP-only selection, or unset/``auto`` for the normal
configured HTTP → FMP → development-memory → null precedence.
"""

from __future__ import annotations

import os
from collections.abc import Mapping

from data_engine.connector_framework.production_profile import (
    ConnectorConfigurationError,
    is_production_environment,
)

__all__ = [
    "DSP_INVESTMENT_DATA_PROVIDER_ENV",
    "InvestmentDataProvider",
    "resolve_investment_data_provider",
]

DSP_INVESTMENT_DATA_PROVIDER_ENV = "DSP_INVESTMENT_DATA_PROVIDER"

# Normalized selection values
InvestmentDataProvider = str  # "auto" | "fmp"


def resolve_investment_data_provider(
    environ: Mapping[str, str] | None = None,
) -> InvestmentDataProvider:
    """Return normalized provider selection for investment connectors."""
    env_map = environ if environ is not None else os.environ
    raw = str(env_map.get(DSP_INVESTMENT_DATA_PROVIDER_ENV) or "").strip().lower()
    if not raw or raw in {"auto", "default"}:
        return "auto"
    if raw in {"fmp"}:
        return raw
    raise ConnectorConfigurationError(
        f"P1-03: invalid {DSP_INVESTMENT_DATA_PROVIDER_ENV}={raw!r}; "
        "allowed values: fmp, auto (or unset)"
    )
