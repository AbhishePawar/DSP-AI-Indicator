"""Investment data provider selection.

Production supports configured HTTP market data or FMP.
Investment provider selection is configuration-driven.
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
    "resolve_investment_data_provider",
]

DSP_INVESTMENT_DATA_PROVIDER_ENV = "DSP_INVESTMENT_DATA_PROVIDER"

InvestmentDataProvider = str  # "auto" | "fmp"


def resolve_investment_data_provider(
    environ: Mapping[str, str] | None = None,
) -> InvestmentDataProvider:
    """Return normalized investment provider selection."""
    env_map = environ if environ is not None else os.environ
    raw = str(
        env_map.get(DSP_INVESTMENT_DATA_PROVIDER_ENV) or ""
    ).strip().lower()

    if not raw or raw in {"auto", "default"}:
        return "auto"

    if raw == "fmp":
        return "fmp"

    raise ConnectorConfigurationError(
        f"P1-03: invalid {DSP_INVESTMENT_DATA_PROVIDER_ENV}={raw!r}; "
        "allowed values: fmp, auto (or unset)"
    )
