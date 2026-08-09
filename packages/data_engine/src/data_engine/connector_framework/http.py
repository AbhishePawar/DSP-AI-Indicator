"""Minimal, generic JSON-over-HTTP client shared by connector adapters.

Mirrors ``data_engine.adapters.yahoo_finance.http_client`` exactly (that
module's own docstring already anticipated this: "a future adapter
could reuse ``JsonHttpClient``/``UrllibJsonHttpClient`` as-is if
useful"). Promoted to a shared location now that many vendor adapters
across six new domains need it, instead of copy-pasting it six times.

Knows nothing about any vendor — only how to GET a URL (optionally with
custom headers) and parse a JSON response. Every vendor-specific detail
(URL shape, query parameters, headers, response schema) stays in the
adapter that uses this client.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any, Protocol
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from data_engine.exceptions import ProviderRequestError

__all__ = ["JsonHttpClient", "UrllibJsonHttpClient"]


class JsonHttpClient(Protocol):
    """Dependency-inversion boundary for adapters that speak HTTP+JSON.

    Any adapter can depend on this instead of a concrete HTTP library,
    letting tests inject a fake implementation with no network access.
    """

    def get_json(
        self,
        url: str,
        *,
        params: Mapping[str, str] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> Any:
        """Issue a GET request and return the parsed JSON response body.

        Args:
            url: The base URL to request, without a query string.
            params: Optional query parameters to append.
            headers: Optional extra request headers (e.g. API keys,
                required ``User-Agent`` values, ``Accept`` overrides).

        Returns:
            The response body, parsed as JSON (object or array).

        Raises:
            ProviderRequestError: If the request fails, times out,
                returns a non-2xx status, or returns a body that is
                not valid JSON.
        """
        ...


class UrllibJsonHttpClient:
    """Default :class:`JsonHttpClient` built entirely on the standard library.

    Deliberately minimal: no retries, no connection pooling, no async
    I/O — those concerns are handled one layer up by each domain's
    ``Service`` (:class:`~data_engine.market_quote.service.RetryPolicy`,
    :class:`~data_engine.market_quote.service.CircuitBreaker`, etc.).
    """

    def __init__(
        self,
        *,
        timeout_seconds: float = 10.0,
        default_headers: Mapping[str, str] | None = None,
    ) -> None:
        self._timeout_seconds = timeout_seconds
        self._default_headers = dict(default_headers or {})

    def get_json(
        self,
        url: str,
        *,
        params: Mapping[str, str] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> Any:
        full_url = url if not params else f"{url}?{urlencode(params)}"
        merged_headers = {**self._default_headers, **(headers or {})}
        request = Request(full_url, headers=merged_headers, method="GET")
        try:
            with urlopen(request, timeout=self._timeout_seconds) as response:
                raw_body = response.read()
        except HTTPError as exc:
            # Never include Authorization headers or response bodies (may echo secrets).
            status = int(getattr(exc, "code", 0) or 0)
            if status == 429:
                raise ProviderRequestError(
                    f"HTTP 429 rate limited for '{url}'"
                ) from None
            if status in {401, 403}:
                raise ProviderRequestError(
                    f"HTTP {status} authentication failed for '{url}'"
                ) from None
            raise ProviderRequestError(
                f"HTTP {status} for '{url}'"
            ) from None
        except OSError as exc:
            msg = f"HTTP request to '{url}' failed: {type(exc).__name__}"
            raise ProviderRequestError(msg) from None

        try:
            return json.loads(raw_body)
        except json.JSONDecodeError as exc:
            msg = f"HTTP response from '{url}' was not valid JSON: {type(exc).__name__}"
            raise ProviderRequestError(msg) from None
