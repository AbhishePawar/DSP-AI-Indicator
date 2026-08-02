"""Auth package exceptions (EPIC-A009)."""

from __future__ import annotations

__all__ = [
    "AuthError",
    "AuthenticationError",
    "AuthorizationError",
    "DuplicateUserError",
    "InvalidTokenError",
    "SessionError",
    "ValidationError",
]


class AuthError(ValueError):
    """Base auth error."""


class AuthenticationError(AuthError):
    """Invalid credentials or failed login."""


class AuthorizationError(AuthError):
    """Missing permission."""


class DuplicateUserError(AuthError):
    """Duplicate username or email."""


class InvalidTokenError(AuthError):
    """Invalid or expired token."""


class SessionError(AuthError):
    """Session revocation / expiration."""


class ValidationError(AuthError):
    """Input validation failure."""
