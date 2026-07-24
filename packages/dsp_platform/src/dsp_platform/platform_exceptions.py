"""Platform integration exceptions (K1.0).

Stable error surface for external consumers. Domain / provider / engine
exception types are never leaked through the platform façade.
"""

from __future__ import annotations

from core.exceptions import DSPAIError

__all__ = [
    "PlatformConfigurationError",
    "PlatformError",
    "PlatformLifecycleError",
    "ServiceRegistryError",
]


class PlatformError(DSPAIError):
    """Stable error surface for external platform consumers.

    Wraps orchestration / recommendation / wiring / integration failures so
    callers never observe provider, engine, bridge, or committee exception types.
    """


class PlatformConfigurationError(PlatformError):
    """Raised when platform configuration is missing or inconsistent."""


class ServiceRegistryError(PlatformError):
    """Raised when service registration or lookup fails."""


class PlatformLifecycleError(PlatformError):
    """Raised when lifecycle transitions or readiness checks fail."""
