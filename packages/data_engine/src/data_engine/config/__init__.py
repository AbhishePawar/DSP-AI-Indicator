"""Configuration shape for the Data Engine.

This module defines *what* the Data Engine needs to be configured with,
not *how* that configuration is loaded. Reading values from environment
variables, files, or a secrets manager is a platform-wide concern that
belongs to a future, dedicated configuration sprint — this package only
declares a stable settings shape so ports and services can be written
against it today.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["DataEngineConfig"]


@dataclass(frozen=True, slots=True)
class DataEngineConfig:
    """Runtime configuration for the Data Engine.

    Attributes:
        default_provider: Name of the provider to use when a caller does
            not specify one explicitly. ``None`` means callers must
            always specify a provider.
        cache_ttl_seconds: Default cache time-to-live applied by services
            when a request does not specify its own TTL.
        request_timeout_seconds: Default timeout services should apply
            to provider calls once real, network-calling adapters exist.
    """

    default_provider: str | None = None
    cache_ttl_seconds: float = 300.0
    request_timeout_seconds: float = 30.0
