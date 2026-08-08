"""HttpOnly session cookie helpers + CSRF (EPIC-016 / OWASP-aligned)."""

from __future__ import annotations

import hmac
import os
import secrets
from hashlib import sha256
from typing import Any

from starlette.requests import Request
from starlette.responses import Response

__all__ = [
    "ACCESS_COOKIE",
    "CSRF_COOKIE",
    "CSRF_HEADER",
    "REFRESH_COOKIE",
    "SESSION_COOKIE",
    "clear_auth_cookies",
    "cookie_auth_enabled",
    "csrf_token_from_request",
    "issue_csrf_token",
    "read_access_token",
    "read_refresh_token",
    "set_auth_cookies",
    "validate_csrf",
]

ACCESS_COOKIE = "dsp_access"
REFRESH_COOKIE = "dsp_refresh"
CSRF_COOKIE = "dsp_csrf"
SESSION_COOKIE = "dsp_session"
CSRF_HEADER = "X-CSRF-Token"


def cookie_auth_enabled() -> bool:
    """Production default: HttpOnly cookies. Opt out with DSP_COOKIE_AUTH=false."""
    raw = os.environ.get("DSP_COOKIE_AUTH", "true").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _secure_flag() -> bool:
    env = os.environ.get("DSP_ENVIRONMENT", "").strip().lower()
    if env == "production":
        return True
    explicit = os.environ.get("DSP_COOKIE_SECURE", "").strip().lower()
    if explicit in {"1", "true", "yes"}:
        return True
    if explicit in {"0", "false", "no"}:
        return False
    return env == "production"


def _samesite() -> str:
    value = os.environ.get("DSP_COOKIE_SAMESITE", "lax").strip().lower()
    if value in {"lax", "strict", "none"}:
        return value
    return "lax"


def _access_max_age(remember_me: bool) -> int:
    if remember_me:
        return int(os.environ.get("DSP_COOKIE_ACCESS_MAX_AGE_REMEMBER", str(30 * 24 * 3600)))
    return int(os.environ.get("DSP_COOKIE_ACCESS_MAX_AGE", "3600"))


def _refresh_max_age(remember_me: bool) -> int:
    if remember_me:
        return int(os.environ.get("DSP_COOKIE_REFRESH_MAX_AGE_REMEMBER", str(30 * 24 * 3600)))
    return int(os.environ.get("DSP_COOKIE_REFRESH_MAX_AGE", str(7 * 24 * 3600)))


def issue_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def set_auth_cookies(
    response: Response,
    *,
    access_token: str,
    refresh_token: str | None = None,
    session_id: str | None = None,
    remember_me: bool = False,
    csrf_token: str | None = None,
) -> str:
    """Attach HttpOnly auth cookies + readable CSRF cookie. Returns CSRF token."""
    secure = _secure_flag()
    samesite = _samesite()
    # SameSite=None requires Secure
    if samesite == "none":
        secure = True
    csrf = csrf_token or issue_csrf_token()
    common: dict[str, Any] = {
        "httponly": True,
        "secure": secure,
        "samesite": samesite,
        "path": "/",
    }
    response.set_cookie(
        ACCESS_COOKIE,
        access_token,
        max_age=_access_max_age(remember_me),
        **common,
    )
    if refresh_token:
        response.set_cookie(
            REFRESH_COOKIE,
            refresh_token,
            max_age=_refresh_max_age(remember_me),
            **common,
        )
    if session_id:
        response.set_cookie(
            SESSION_COOKIE,
            session_id,
            max_age=_refresh_max_age(remember_me),
            **common,
        )
    # CSRF cookie is readable by JS (double-submit cookie pattern)
    response.set_cookie(
        CSRF_COOKIE,
        csrf,
        max_age=_refresh_max_age(remember_me),
        httponly=False,
        secure=secure,
        samesite=samesite,
        path="/",
    )
    return csrf


def clear_auth_cookies(response: Response) -> None:
    for name in (ACCESS_COOKIE, REFRESH_COOKIE, CSRF_COOKIE, SESSION_COOKIE):
        response.delete_cookie(name, path="/")


def read_access_token(request: Request) -> str | None:
    token = request.cookies.get(ACCESS_COOKIE)
    if token:
        return token
    auth = request.headers.get("authorization") or request.headers.get("Authorization")
    if auth and auth.lower().startswith("bearer "):
        return auth[7:].strip() or None
    return None


def read_refresh_token(request: Request) -> str | None:
    return request.cookies.get(REFRESH_COOKIE)


def csrf_token_from_request(request: Request) -> str | None:
    header = request.headers.get(CSRF_HEADER) or request.headers.get(CSRF_HEADER.lower())
    if header:
        return header.strip()
    return request.cookies.get(CSRF_COOKIE)


def validate_csrf(request: Request) -> bool:
    """Double-submit CSRF: header must match cookie (constant-time)."""
    cookie = request.cookies.get(CSRF_COOKIE)
    header = request.headers.get(CSRF_HEADER) or request.headers.get("x-csrf-token")
    if not cookie or not header:
        return False
    return hmac.compare_digest(cookie, header)


def csrf_hmac(secret: str, session_id: str) -> str:
    return hmac.new(secret.encode("utf-8"), session_id.encode("utf-8"), sha256).hexdigest()
