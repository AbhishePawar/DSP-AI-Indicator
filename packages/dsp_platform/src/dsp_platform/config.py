"""Immutable configuration models for the platform façade."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from dsp_platform.exceptions import PlatformError

__all__ = [
    "CacheSettings",
    "Environment",
    "FeatureFlags",
    "PlatformConfig",
    "PlatformSecrets",
    "ProviderSettings",
    "TimeoutSettings",
]


class Environment(StrEnum):
    """Deployment environment selector."""

    DEVELOPMENT = "development"
    TEST = "test"
    PRODUCTION = "production"


@dataclass(frozen=True, slots=True)
class ProviderSettings:
    """Which data providers the composition root should register.

    Attributes:
        market_provider_id: Default market-data provider registry id.
        fundamentals_provider_id: Default fundamentals provider id.
        economic_provider_id: Default economic provider id.
        enable_market: Register the market adapter when building.
        enable_fundamentals: Register the fundamentals adapter.
        enable_economic: Register the economic adapter.
    """

    market_provider_id: str = "yahoo_finance"
    fundamentals_provider_id: str = "yahoo_finance_fundamentals"
    economic_provider_id: str = "fred"
    enable_market: bool = True
    enable_fundamentals: bool = True
    enable_economic: bool = True

    def __post_init__(self) -> None:
        """Reject empty provider ids."""
        for name, value in (
            ("market_provider_id", self.market_provider_id),
            ("fundamentals_provider_id", self.fundamentals_provider_id),
            ("economic_provider_id", self.economic_provider_id),
        ):
            if not value.strip():
                msg = f"{name} must not be empty"
                raise PlatformError(msg)


@dataclass(frozen=True, slots=True)
class CacheSettings:
    """Cache behaviour for Data Engine services."""

    ttl_seconds: float | None = 300.0

    def __post_init__(self) -> None:
        if self.ttl_seconds is not None and self.ttl_seconds < 0:
            msg = f"ttl_seconds must be non-negative, got {self.ttl_seconds}"
            raise PlatformError(msg)


@dataclass(frozen=True, slots=True)
class TimeoutSettings:
    """Network / request timeouts applied when constructing adapters."""

    request_seconds: float = 10.0

    def __post_init__(self) -> None:
        if self.request_seconds <= 0:
            msg = f"request_seconds must be positive, got {self.request_seconds}"
            raise PlatformError(msg)


@dataclass(frozen=True, slots=True)
class FeatureFlags:
    """Feature toggles applied as defaults on analysis requests.

    Per-request flags on ``AnalysisRequest`` still win when set
    explicitly by the caller; these are defaults for
    :meth:`DSPPlatform.analyze` when using convenience helpers, and for
    documentation of platform-wide policy.
    """

    include_fundamentals: bool = True
    include_economic: bool = True
    include_valuation: bool = True
    allow_partial: bool = True


@dataclass(frozen=True, slots=True)
class PlatformSecrets:
    """Secret material injected at composition time — never logged.

    Attributes:
        fred_api_key: API key for the FRED economic adapter. ``None``
            is acceptable in tests that inject fake HTTP clients via a
            pre-built ``InvestmentAnalysisService``.
    """

    fred_api_key: str | None = None

    def __repr__(self) -> str:
        """Redact secret values from representations."""
        key = "set" if self.fred_api_key else "unset"
        return f"PlatformSecrets(fred_api_key=<{key}>)"


@dataclass(frozen=True, slots=True)
class PlatformConfig:
    """Immutable root configuration for ``DSPPlatform.from_config``.

    Attributes:
        environment: Deployment environment.
        providers: Provider registration and default ids.
        cache: Cache TTL settings.
        timeouts: Adapter timeout settings.
        features: Default analysis feature flags.
        secrets: Injected credentials (never from source control).
    """

    environment: Environment = Environment.DEVELOPMENT
    providers: ProviderSettings = field(default_factory=ProviderSettings)
    cache: CacheSettings = field(default_factory=CacheSettings)
    timeouts: TimeoutSettings = field(default_factory=TimeoutSettings)
    features: FeatureFlags = field(default_factory=FeatureFlags)
    secrets: PlatformSecrets = field(default_factory=PlatformSecrets)
