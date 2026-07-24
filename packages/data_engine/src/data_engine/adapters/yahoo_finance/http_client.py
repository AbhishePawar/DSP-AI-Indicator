"""Minimal, generic JSON-over-HTTP client.

This module knows nothing about Yahoo Finance — it only knows how to GET
a URL and parse a JSON response, translating any transport-level failure
into :class:`~data_engine.exceptions.ProviderRequestError`. It is kept
alongside the Yahoo Finance adapter (the only adapter that currently uses
it) rather than in a shared top-level module, since no second adapter
exists yet to justify a shared location; a future adapter could reuse
:class:`JsonHttpClient`/:class:`UrllibJsonHttpClient` as-is if useful.

``YahooFinanceAdapter`` is still "the only class aware of Yahoo Finance":
this module has no knowledge of Yahoo's URL structure, query parameters,
or response shape — only the adapter does.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any, Protocol
from urllib.parse import urlencode
from urllib.request import urlopen

from data_engine.exceptions import ProviderRequestError

__all__ = ["JsonHttpClient", "UrllibJsonHttpClient"]


class JsonHttpClient(Protocol):
    """Dependency-inversion boundary for adapters that speak HTTP+JSON.

    Any adapter can depend on this instead of a concrete HTTP library,
    letting tests inject a fake implementation with no network access.
    """

    def get_json(
        self, url: str, *, params: Mapping[str, str] | None = None
    ) -> Mapping[str, Any]:
        """Issue a GET request and return the parsed JSON response body.

        Args:
            url: The base URL to request, without a query string.
            params: Optional query parameters to append.

        Returns:
            The response body, parsed as JSON.

        Raises:
            ProviderRequestError: If the request fails, times out,
                returns a non-2xx status, or returns a body that is
                not valid JSON.
        """


class UrllibJsonHttpClient:
    """Default :class:`JsonHttpClient` built entirely on the standard library.

    Deliberately minimal: no retries, no connection pooling, no async
    I/O. Those are explicitly out of scope for this sprint and can be
    layered on top (e.g. by wrapping this class) without changing the
    ``JsonHttpClient`` contract adapters depend on.
    """

    def __init__(self, *, timeout_seconds: float = 10.0) -> None:
        """Initialize the client.

        Args:
            timeout_seconds: Maximum time to wait for a response.
        """
        self._timeout_seconds = timeout_seconds

    def get_json(
        self, url: str, *, params: Mapping[str, str] | None = None
    ) -> Mapping[str, Any]:
        """Issue a GET request and return the parsed JSON response body.

        Args:
            url: The base URL to request, without a query string.
            params: Optional query parameters to append.

        Returns:
            The response body, parsed as JSON.

        Raises:
            ProviderRequestError: If the request fails, times out,
                returns a non-2xx status (surfaced by ``urllib`` as an
                ``HTTPError``), or returns a body that is not valid
                JSON. ``URLError``, ``HTTPError``, and ``TimeoutError``
                are all ``OSError`` subclasses, so catching ``OSError``
                covers every transport-level failure ``urlopen`` can
                raise.
        """
        full_url = url if not params else f"{url}?{urlencode(params)}"
        try:
            with urlopen(full_url, timeout=self._timeout_seconds) as response:
                raw_body = response.read()
        except OSError as exc:
            msg = f"HTTP request to '{url}' failed: {exc}"
            raise ProviderRequestError(msg) from exc

        try:
            return json.loads(raw_body)
        except json.JSONDecodeError as exc:
            msg = f"HTTP response from '{url}' was not valid JSON: {exc}"
            raise ProviderRequestError(msg) from exc
