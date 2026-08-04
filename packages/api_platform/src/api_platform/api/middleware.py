"""API middleware — request metadata + structured access logs (K1.1 + P1.3)."""

from __future__ import annotations

import time
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from api_platform.api.monitoring import classify_error, ops_logger
from api_platform.api.ops import metrics_registry

__all__ = [
    "API_VERSION_HEADER",
    "REQUEST_ID_HEADER",
    "RequestContextMiddleware",
]

API_VERSION_HEADER = "X-API-Version"
REQUEST_ID_HEADER = "X-Request-Id"

_SKIP_ACCESS_LOG = frozenset(
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


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Attach request id + API version headers; emit redacted access logs."""

    def __init__(self, app: Any, *, api_version: str = "v1") -> None:
        super().__init__(app)
        self._api_version = api_version

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid.uuid4())
        started = time.perf_counter()
        request.state.request_id = request_id
        request.state.api_version = self._api_version
        try:
            response = await call_next(request)
        except Exception as exc:
            elapsed_ms = (time.perf_counter() - started) * 1000.0
            severity = classify_error(exc)
            ops_logger.log(
                "ERROR",
                "unhandled_exception",
                correlation_id=request_id,
                severity=severity,
                fields={
                    "path": request.url.path,
                    "method": request.method,
                    "error_type": type(exc).__name__,
                    "elapsed_ms": round(elapsed_ms, 2),
                },
            )
            raise
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        response.headers[REQUEST_ID_HEADER] = request_id
        response.headers[API_VERSION_HEADER] = self._api_version
        response.headers["X-Response-Time-Ms"] = f"{elapsed_ms:.2f}"
        metrics_registry.note_path(
            request.url.path,
            status_code=response.status_code,
            elapsed_ms=elapsed_ms,
        )
        if request.url.path not in _SKIP_ACCESS_LOG:
            level = "INFO"
            severity = None
            if response.status_code >= 500:
                level = "ERROR"
                severity = classify_error(status_code=response.status_code)
            elif response.status_code in {401, 403}:
                level = "WARNING"
                severity = classify_error(status_code=response.status_code)
                msg = (
                    "authentication_failure"
                    if response.status_code == 401
                    else "authorization_denial"
                )
                ops_logger.log(
                    level,
                    msg,
                    correlation_id=request_id,
                    severity=severity,
                    fields={
                        "path": request.url.path,
                        "method": request.method,
                        "status_code": response.status_code,
                        "elapsed_ms": round(elapsed_ms, 2),
                    },
                )
            else:
                category = "api_request"
                lower = request.url.path.lower()
                if "/analyse" in lower or "/analyze" in lower:
                    category = "analysis_request"
                elif "/research" in lower:
                    category = "research_generation"
                elif "/export" in lower:
                    category = "export"
                elif "/auth" in lower:
                    category = "authentication"
                ops_logger.log(
                    level,
                    category,
                    correlation_id=request_id,
                    fields={
                        "path": request.url.path,
                        "method": request.method,
                        "status_code": response.status_code,
                        "elapsed_ms": round(elapsed_ms, 2),
                    },
                )
        return response
