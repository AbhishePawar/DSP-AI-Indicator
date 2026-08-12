"""Production Services exceptions — no business semantics.

Typed startup / dependency failures must never leak DSNs, passwords, or
stack traces to HTTP clients. Message text is safe for ops logs; use
``safe_public_message`` for API responses.
"""

from __future__ import annotations

from core.exceptions import DSPAIError

__all__ = [
    "ConfigurationError",
    "DatabaseUnavailableError",
    "DependencyError",
    "ProductionError",
    "ProviderError",
    "RedisUnavailableError",
    "StartupError",
    "safe_public_message",
]


class ProductionError(DSPAIError):
    """Base production-platform error."""

    public_code: str = "PRODUCTION_ERROR"
    public_message: str = "a production platform error occurred"


class ConfigurationError(ProductionError):
    """Configuration missing or inconsistent."""

    public_code = "CONFIGURATION_ERROR"
    public_message = "configuration is invalid or incomplete"


class ProviderError(ProductionError):
    """Port / adapter invocation failure."""

    public_code = "PROVIDER_ERROR"
    public_message = "a dependency provider failed"


class StartupError(ProductionError):
    """Process cannot start safely with the current runtime configuration."""

    public_code = "STARTUP_ERROR"
    public_message = "service failed to start"


class DependencyError(ProductionError):
    """Required runtime dependency unavailable."""

    public_code = "DEPENDENCY_ERROR"
    public_message = "a required dependency is unavailable"


class DatabaseUnavailableError(DependencyError):
    """PostgreSQL / database adapter unavailable when required."""

    public_code = "DATABASE_UNAVAILABLE"
    public_message = "database dependency is unavailable"


class RedisUnavailableError(DependencyError):
    """Redis adapter unavailable when required (graceful_fallback=false)."""

    public_code = "REDIS_UNAVAILABLE"
    public_message = "cache dependency is unavailable"


def safe_public_message(exc: BaseException) -> tuple[str, str]:
    """Return ``(error_code, public_message)`` that never leaks internals."""
    if isinstance(exc, ProductionError):
        return exc.public_code, exc.public_message
    return "INTERNAL_ERROR", "an unexpected error occurred"
