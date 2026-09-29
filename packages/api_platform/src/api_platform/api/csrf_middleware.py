"""CSRF protection for cookie-authenticated mutating requests (EPIC-016)."""

from __future__ import annotations

import os
from collections.abc import Awaitable, Callable
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from security_platform import (
    ACCESS_COOKIE,
    cookie_auth_enabled,
    validate_csrf,
)

__all__ = ["CsrfMiddleware"]

_SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "TRACE"})
_PUBLIC_PREFIXES = (
    "/health",
    "/api/v1/health",
    "/metrics",
    "/api/v1/metrics",
    "/docs",
    "/redoc",
    "/openapi.json",
)
# Login/refresh establish cookies — CSRF not required on first auth exchange.
# The enterprise credential-establishing endpoints (password login, OTP
# verify, OAuth callback, magic link, passkey complete) are exempt for the
# same reason: a browser holding a stale/expired `dsp_access` cookie must be
# able to re-authenticate instead of receiving 403 CSRF on the login form.
_AUTH_EXEMPT_PATHS = (
    "/auth/login",
    "/auth/rbac/login",
    "/auth/refresh",
    "/auth/rbac/refresh",
    "/auth/enterprise/login",
    "/auth/enterprise/otp/verify",
    "/auth/enterprise/oauth/callback",
    "/auth/enterprise/magic-link/consume",
    "/auth/mfa/webauthn/authenticate/complete",
    "/auth/passkey/login/complete",
)
_AUTH_EXEMPT = tuple(
    path
    for base in _AUTH_EXEMPT_PATHS
    for path in (base, f"/api/v1{base}")
)
# Razorpay server-to-server webhooks cannot send JWT or CSRF tokens.
_WEBHOOK_EXEMPT = (
    "/saas/webhooks/razorpay",
    "/api/v1/saas/webhooks/razorpay",
)


class CsrfMiddleware(BaseHTTPMiddleware):
    """Double-submit CSRF when HttpOnly cookie auth is active.

    Safe methods and Bearer-only requests (no access cookie) are skipped so
    existing API clients remain compatible.
    """

    def __init__(self, app: Any) -> None:
        super().__init__(app)
        self._enabled = cookie_auth_enabled() and os.environ.get(
            "DSP_CSRF_ENABLED", "true"
        ).strip().lower() in {"1", "true", "yes", "on"}

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        if not self._enabled:
            return await call_next(request)
        if request.method in _SAFE_METHODS:
            return await call_next(request)
        path = request.url.path
        if any(path == p or path.startswith(p + "/") for p in _PUBLIC_PREFIXES):
            return await call_next(request)
        if path in _AUTH_EXEMPT:
            return await call_next(request)
        if path in _WEBHOOK_EXEMPT:
            return await call_next(request)
        # Only enforce when browser cookie session is the auth transport.
        # Explicit Bearer Authorization (API clients / legacy tests) skips CSRF.
        auth = request.headers.get("authorization") or ""
        if auth.lower().startswith("bearer "):
            return await call_next(request)
        if not request.cookies.get(ACCESS_COOKIE):
            return await call_next(request)
        if validate_csrf(request):
            return await call_next(request)
        return JSONResponse(
            status_code=403,
            content={
                "ok": False,
                "error": "CSRFError",
                "detail": "CSRF token missing or invalid",
                "message": "CSRF token missing or invalid",
                "api_version": "v1",
                "status_code": 403,
            },
        )
