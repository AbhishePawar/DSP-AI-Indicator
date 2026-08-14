"""Auth package exceptions (EPIC-A009)."""

from __future__ import annotations

__all__ = [
    "AuthError",
    "AuthenticationError",
    "AuthorizationError",
    "DuplicateUserError",
    "InvalidTokenError",
    "RefreshTokenReuseError",
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


class RefreshTokenReuseError(SessionError):
    """A refresh token that was already rotated away (or forged) was presented.

    Per OAuth 2.0 Security Best Current Practice, this is treated as a
    credential-theft signal: the entire refresh-token family (i.e. the
    session it belongs to, since one A009 session has exactly one active
    refresh-token lineage) is revoked immediately, not just the offending
    token. Subclasses :class:`SessionError` so existing callers that only
    catch the broader ``SessionError``/``InvalidTokenError`` hierarchy keep
    working unchanged.
    """


class ValidationError(AuthError):
    """Input validation failure."""
