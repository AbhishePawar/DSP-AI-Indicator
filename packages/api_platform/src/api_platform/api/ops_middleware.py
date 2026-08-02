"""Security and rate-limit middleware hooks (EPIC-013 RC1 + EPIC-011A)."""

from __future__ import annotations

import os
import time
from collections import defaultdict
from collections.abc import Awaitable, Callable
from threading import Lock
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

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
    """Rate limiting — Redis RateLimitPort when infra attached, else memory.

    Set ``DSP_RATE_LIMIT_ENABLED=true`` to enable. Prefer edge limiting in
    multi-replica production when Redis is unavailable.
    """

    _PUBLIC = frozenset(
        {
            "/health",
            "/health/live",
            "/health/ready",
            "/metrics",
            "/api/v1/health",
            "/api/v1/health/live",
            "/api/v1/health/ready",
            "/api/v1/metrics",
        }
    )

    def __init__(self, app: Any) -> None:
        super().__init__(app)
        self._enabled = os.environ.get("DSP_RATE_LIMIT_ENABLED", "").lower() in {
            "1",
            "true",
            "yes",
        }
        self._limit = int(os.environ.get("DSP_RATE_LIMIT_PER_MINUTE", "600"))
        self._window = 60.0
        self._hits: dict[str, list[float]] = defaultdict(list)
        self._lock = Lock()

    def _client_key(self, request: Request) -> str:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip() or "unknown"
        if request.client and request.client.host:
            return request.client.host
        return "unknown"

    def _allow_memory(self, key: str) -> bool:
        now = time.monotonic()
        with self._lock:
            bucket = self._hits[key]
            cutoff = now - self._window
            while bucket and bucket[0] < cutoff:
                bucket.pop(0)
            if len(bucket) >= self._limit:
                return False
            bucket.append(now)
            return True

    def _allow(self, request: Request, key: str) -> bool:
        infra = getattr(request.app.state, "infrastructure", None)
        rate_port = getattr(infra, "rate_limit", None) if infra is not None else None
        if rate_port is not None and hasattr(rate_port, "allow"):
            try:
                return bool(
                    rate_port.allow(
                        key, limit=self._limit, window_seconds=self._window
                    )
                )
            except Exception:  # noqa: BLE001 — degrade to process-local
                pass
        return self._allow_memory(key)

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        if self._enabled and request.url.path not in self._PUBLIC:
            request.state.rate_limit_budget = self._limit
            if not self._allow(request, self._client_key(request)):
                return JSONResponse(
                    status_code=429,
                    content={
                        "ok": False,
                        "error": "RateLimitError",
                        "detail": "Rate limit exceeded",
                        "api_version": "v1",
                        "status_code": 429,
                    },
                    headers={"Retry-After": "60"},
                )
        return await call_next(request)
