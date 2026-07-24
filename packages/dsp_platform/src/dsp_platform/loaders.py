"""Optional configuration loaders for the platform façade.

Dependency injection remains the primary configuration approach.
These helpers map environment variables (or an explicit mapping) onto
immutable ``PlatformConfig`` models. Secrets are never hardcoded.
"""

from __future__ import annotations

import os
from collections.abc import Mapping

from dsp_platform.config import (
    CacheSettings,
    Environment,
    FeatureFlags,
    PlatformConfig,
    PlatformSecrets,
    ProviderSettings,
    TimeoutSettings,
)
from dsp_platform.exceptions import PlatformError

__all__ = ["load_platform_config", "load_secrets_from_environ"]

_ENV_KEY = "DSP_AI_ENVIRONMENT"
_FRED_KEY = "DSP_AI_FRED_API_KEY"
_MARKET_PROVIDER = "DSP_AI_MARKET_PROVIDER_ID"
_FUND_PROVIDER = "DSP_AI_FUNDAMENTALS_PROVIDER_ID"
_ECON_PROVIDER = "DSP_AI_ECONOMIC_PROVIDER_ID"
_ENABLE_MARKET = "DSP_AI_ENABLE_MARKET"
_ENABLE_FUND = "DSP_AI_ENABLE_FUNDAMENTALS"
_ENABLE_ECON = "DSP_AI_ENABLE_ECONOMIC"
_CACHE_TTL = "DSP_AI_CACHE_TTL_SECONDS"
_TIMEOUT = "DSP_AI_REQUEST_TIMEOUT_SECONDS"
_INCLUDE_FUND = "DSP_AI_INCLUDE_FUNDAMENTALS"
_INCLUDE_ECON = "DSP_AI_INCLUDE_ECONOMIC"
_INCLUDE_VAL = "DSP_AI_INCLUDE_VALUATION"
_ALLOW_PARTIAL = "DSP_AI_ALLOW_PARTIAL"


def load_secrets_from_environ(
    environ: Mapping[str, str] | None = None,
) -> PlatformSecrets:
    """Load secrets from the environment without logging values.

    Args:
        environ: Mapping to read (defaults to ``os.environ``).

    Returns:
        Immutable ``PlatformSecrets``. Missing keys yield ``None``.
    """
    env = environ if environ is not None else os.environ
    fred = env.get(_FRED_KEY)
    if fred is not None:
        fred = fred.strip() or None
    return PlatformSecrets(fred_api_key=fred)


def load_platform_config(
    environ: Mapping[str, str] | None = None,
    *,
    secrets: PlatformSecrets | None = None,
) -> PlatformConfig:
    """Build ``PlatformConfig`` from environment variables.

    Unset variables keep ``PlatformConfig`` defaults. Explicit
    ``secrets`` override environment-derived secrets.

    Supported variables:

    - ``DSP_AI_ENVIRONMENT`` — development | test | production
    - ``DSP_AI_FRED_API_KEY`` — FRED API key (optional)
    - ``DSP_AI_MARKET_PROVIDER_ID`` / ``DSP_AI_FUNDAMENTALS_PROVIDER_ID`` /
      ``DSP_AI_ECONOMIC_PROVIDER_ID``
    - ``DSP_AI_ENABLE_MARKET`` / ``DSP_AI_ENABLE_FUNDAMENTALS`` /
      ``DSP_AI_ENABLE_ECONOMIC`` — true/false
    - ``DSP_AI_CACHE_TTL_SECONDS`` — float or empty for no TTL
    - ``DSP_AI_REQUEST_TIMEOUT_SECONDS`` — float
    - ``DSP_AI_INCLUDE_FUNDAMENTALS`` / ``DSP_AI_INCLUDE_ECONOMIC`` /
      ``DSP_AI_INCLUDE_VALUATION`` / ``DSP_AI_ALLOW_PARTIAL`` — true/false
    """
    env = environ if environ is not None else os.environ
    try:
        environment = _parse_environment(env.get(_ENV_KEY))
        providers = ProviderSettings(
            market_provider_id=_str_or_default(
                env.get(_MARKET_PROVIDER), "yahoo_finance"
            ),
            fundamentals_provider_id=_str_or_default(
                env.get(_FUND_PROVIDER), "yahoo_finance_fundamentals"
            ),
            economic_provider_id=_str_or_default(
                env.get(_ECON_PROVIDER), "fred"
            ),
            enable_market=_parse_bool(env.get(_ENABLE_MARKET), default=True),
            enable_fundamentals=_parse_bool(env.get(_ENABLE_FUND), default=True),
            enable_economic=_parse_bool(env.get(_ENABLE_ECON), default=True),
        )
        cache = CacheSettings(ttl_seconds=_parse_optional_float(env.get(_CACHE_TTL), 300.0))
        timeouts = TimeoutSettings(
            request_seconds=_parse_float(env.get(_TIMEOUT), default=10.0)
        )
        features = FeatureFlags(
            include_fundamentals=_parse_bool(
                env.get(_INCLUDE_FUND), default=True
            ),
            include_economic=_parse_bool(env.get(_INCLUDE_ECON), default=True),
            include_valuation=_parse_bool(env.get(_INCLUDE_VAL), default=True),
            allow_partial=_parse_bool(env.get(_ALLOW_PARTIAL), default=True),
        )
        resolved_secrets = (
            secrets if secrets is not None else load_secrets_from_environ(env)
        )
        return PlatformConfig(
            environment=environment,
            providers=providers,
            cache=cache,
            timeouts=timeouts,
            features=features,
            secrets=resolved_secrets,
        )
    except PlatformError:
        raise
    except Exception as exc:
        msg = f"failed to load platform config: {exc}"
        raise PlatformError(msg) from exc


def _parse_environment(raw: str | None) -> Environment:
    if raw is None or not raw.strip():
        return Environment.DEVELOPMENT
    value = raw.strip().lower()
    try:
        return Environment(value)
    except ValueError as exc:
        msg = (
            f"invalid {_ENV_KEY}={raw!r}; "
            f"expected one of {[e.value for e in Environment]}"
        )
        raise PlatformError(msg) from exc


def _str_or_default(raw: str | None, default: str) -> str:
    if raw is None or not raw.strip():
        return default
    return raw.strip()


def _parse_bool(raw: str | None, *, default: bool) -> bool:
    if raw is None or not raw.strip():
        return default
    value = raw.strip().lower()
    if value in {"1", "true", "yes", "on"}:
        return True
    if value in {"0", "false", "no", "off"}:
        return False
    msg = f"invalid boolean value: {raw!r}"
    raise PlatformError(msg)


def _parse_float(raw: str | None, *, default: float) -> float:
    if raw is None or not raw.strip():
        return default
    try:
        return float(raw.strip())
    except ValueError as exc:
        msg = f"invalid float value: {raw!r}"
        raise PlatformError(msg) from exc


def _parse_optional_float(raw: str | None, default: float | None) -> float | None:
    if raw is None:
        return default
    if not raw.strip() or raw.strip().lower() in {"none", "null"}:
        return None
    return _parse_float(raw, default=default if default is not None else 0.0)
