"""Investment data provider selection for authenticated quote + statements.

``DSP_INVESTMENT_DATA_PROVIDER`` accepts unset/``auto`` or ``http`` for the
vendor-neutral authenticated HTTP route. Commercial vendor selection is not
supported. Missing verified data remains unavailable, never a vendor fallback.
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

# Normalized selection values
InvestmentDataProvider = str  # "auto" | "http"


def resolve_investment_data_provider(
    environ: Mapping[str, str] | None = None,
) -> InvestmentDataProvider:
    """Return normalized provider selection for investment connectors."""
    env_map = environ if environ is not None else os.environ
    raw = str(env_map.get(DSP_INVESTMENT_DATA_PROVIDER_ENV) or "").strip().lower()
    if not raw or raw in {"auto", "default"}:
        return "auto"
    if raw == "http":
        return raw
    raise ConnectorConfigurationError(
        f"P1-03: invalid {DSP_INVESTMENT_DATA_PROVIDER_ENV}={raw!r}; "
        "allowed values: http, auto (or unset); commercial vendors are disabled"
    )
