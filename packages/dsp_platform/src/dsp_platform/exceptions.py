"""Platform-level exceptions (compat re-export).

Canonical definitions live in ``platform_exceptions`` (K1.0).
"""

from __future__ import annotations

from dsp_platform.platform_exceptions import (
    PlatformConfigurationError,
    PlatformError,
    PlatformLifecycleError,
    ServiceRegistryError,
)

__all__ = [
    "PlatformConfigurationError",
    "PlatformError",
    "PlatformLifecycleError",
    "ServiceRegistryError",
]
