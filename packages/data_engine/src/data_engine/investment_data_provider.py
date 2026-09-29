"""Investment-data policy: official evidence only.

Commercial vendors (FMP, Upstox, yfinance, EODHD, Alpha Vantage) are never
selected. ``DSP_INVESTMENT_DATA_PROVIDER`` is not a vendor switch — setting it
to a commercial name fails closed. Official/evidence-backed DSP data
(Security Master + NSE/BSE + EvidenceJudge + dsp_gate) remains authoritative.
"""

from __future__ import annotations

import os
from collections.abc import Mapping

from data_engine.connector_framework.production_profile import (
    ConnectorConfigurationError,
)

__all__ = [
    "COMMERCIAL_INVESTMENT_PROVIDERS",
    "DSP_INVESTMENT_DATA_PROVIDER_ENV",
    "INVESTMENT_DATA_UNAVAILABLE",
    "InvestmentDataProvider",
    "investment_data_is_unavailable",
    "resolve_investment_data_provider",
]

DSP_INVESTMENT_DATA_PROVIDER_ENV = "DSP_INVESTMENT_DATA_PROVIDER"
INVESTMENT_DATA_UNAVAILABLE = "INVESTMENT_DATA_UNAVAILABLE"

COMMERCIAL_INVESTMENT_PROVIDERS = frozenset(
    {
        "fmp",
        "financialmodelingprep",
        "upstox",
        "yahoo",
        "yfinance",
        "eodhd",
        "alphavantage",
        "alpha_vantage",
        "polygon",
    }
)

# Normalized selection values: only the honest "no commercial feed" state.
InvestmentDataProvider = str  # "unavailable"


def resolve_investment_data_provider(
    environ: Mapping[str, str] | None = None,
) -> InvestmentDataProvider:
    """Return the investment-feed policy. Commercial names are rejected."""
    env_map = environ if environ is not None else os.environ
    raw = str(env_map.get(DSP_INVESTMENT_DATA_PROVIDER_ENV) or "").strip().lower()
    if raw in COMMERCIAL_INVESTMENT_PROVIDERS:
        raise ConnectorConfigurationError(
            f"P1-03: commercial provider {raw!r} is not permitted; "
            "official/evidence-backed DSP data is authoritative. "
            "FMP, Upstox, yfinance, EODHD and Alpha Vantage are rejected."
        )
    if raw and raw not in {"unavailable", "none", "off", "auto", "default", "official"}:
        raise ConnectorConfigurationError(
            f"P1-03: invalid {DSP_INVESTMENT_DATA_PROVIDER_ENV}={raw!r}; "
            "commercial providers are rejected; leave unset or use unavailable"
        )
    return "unavailable"


def investment_data_is_unavailable(
    environ: Mapping[str, str] | None = None,
) -> bool:
    """True: no commercial investment feed is selected."""
    return resolve_investment_data_provider(environ) == "unavailable"
