"""TEST-ONLY document transport. No network. Not a production adapter."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from dsp_platform.controlled_document_retrieval.transport import TransportResponse

__all__ = ["FakeDocumentTransport", "FakeHop", "public_resolver"]

TEST_ONLY = True


@dataclass(frozen=True, slots=True)
class FakeHop:
    status_code: int = 200
    body: bytes = b""
    headers: Mapping[str, str] | None = None
    location: str = ""
    timeout: bool = False
    oversized: bool = False


class FakeDocumentTransport:
    """Deterministic URL → response map. Makes no network calls."""

    def __init__(self, hops: Mapping[str, FakeHop]) -> None:
        self._hops = dict(hops)
        self.fetched: list[str] = []

    def fetch(
        self, url: str, *, timeout_seconds: float, max_bytes: int
    ) -> TransportResponse:
        del timeout_seconds
        self.fetched.append(url)
        hop = self._hops.get(url)
        if hop is None:
            return TransportResponse(status_code=404, headers={}, body=b"")
        if hop.timeout:
            raise TimeoutError("document retrieval timed out")
        body = hop.body
        if hop.oversized or len(body) > max_bytes:
            raise ValueError("document retrieval rejected: response exceeds size limit")
        headers = dict(hop.headers or {})
        if hop.location and "location" not in {k.lower() for k in headers}:
            headers["location"] = hop.location
        return TransportResponse(
            status_code=hop.status_code,
            headers=headers,
            body=body,
            location=hop.location or headers.get("location", ""),
        )


def public_resolver(_host: str, _port: int, *args: object, **kwargs: object):
    """Return a globally routed IPv4 address so SSRF resolution succeeds."""
    del args, kwargs
    return [(2, 1, 6, "", ("8.8.8.8", 443))]
