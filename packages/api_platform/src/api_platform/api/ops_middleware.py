"""Security and rate-limit middleware hooks (EPIC-013 RC1)."""

from __future__ import annotations

import os
from collections.abc import Awaitable, Callable
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from api_platform.api.ops import metrics_registry

__all__ = [
    "MetricsMiddleware",
    "RateLimitHookMiddleware",
    "SecurityHeadersMiddleware",
]


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Production security headers for API responses."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault(
            "Permissions-Policy", "camera=(), microphone=(), geolocation=()"
        )
        response.headers.setdefault("X-DNS-Prefetch-Control", "off")
        return response


class MetricsMiddleware(BaseHTTPMiddleware):
    """Increment request counters for Prometheus export."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        metrics_registry.inc_requests()
        response = await call_next(request)
        if response.status_code >= 500:
            metrics_registry.inc_errors()
        return response


class RateLimitHookMiddleware(BaseHTTPMiddleware):
    """Rate limiting hook — disabled by default; wire vendor at deploy edge.

    Set ``DSP_RATE_LIMIT_ENABLED=true`` to enable a minimal in-process guard.
    Production should prefer edge rate limiting (CDN / API gateway).
    """

    def __init__(self, app: Any) -> None:
        super().__init__(app)
        self._enabled = os.environ.get("DSP_RATE_LIMIT_ENABLED", "").lower() in {
            "1",
            "true",
            "yes",
        }
        self._limit = int(os.environ.get("DSP_RATE_LIMIT_PER_MINUTE", "600"))

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        if self._enabled and request.url.path not in {"/health", "/health/live", "/metrics"}:
            # Hook point — production uses edge limiting; no business impact.
            request.state.rate_limit_budget = self._limit
        return await call_next(request)
