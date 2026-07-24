"""Security exceptions — no business semantics."""

from __future__ import annotations

from core.exceptions import DSPAIError

__all__ = [
    "AuthenticationError",
    "AuthorizationError",
    "RateLimitError",
    "SecurityError",
    "TokenError",
]


class SecurityError(DSPAIError):
    """Base security-platform error."""


class AuthenticationError(SecurityError):
    """Caller could not be authenticated."""


class AuthorizationError(SecurityError):
    """Caller is authenticated but lacks permission."""


class TokenError(SecurityError):
    """JWT / token parsing or validation failed."""


class RateLimitError(SecurityError):
    """Caller exceeded configured rate limits."""
