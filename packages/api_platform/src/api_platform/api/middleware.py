"""API middleware — request metadata only (K1.1)."""

from __future__ import annotations

import time
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

__all__ = [
    "API_VERSION_HEADER",
    "REQUEST_ID_HEADER",
    "RequestContextMiddleware",
]

API_VERSION_HEADER = "X-API-Version"
REQUEST_ID_HEADER = "X-Request-Id"


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Attach request id + API version headers; no business logic."""

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
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        response.headers[REQUEST_ID_HEADER] = request_id
        response.headers[API_VERSION_HEADER] = self._api_version
        response.headers["X-Response-Time-Ms"] = f"{elapsed_ms:.2f}"
        return response
