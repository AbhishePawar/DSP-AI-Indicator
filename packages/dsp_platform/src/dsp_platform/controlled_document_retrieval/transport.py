"""Pinned-IP HTTPS GET. Redirects are validated by the adapter.

Tests inject FakeDocumentTransport. Stdlib transport is unused unless a
composition root supplies it. This module does not construct share counts.
"""

from __future__ import annotations

import http.client
import socket
import ssl
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol
from urllib.parse import urlparse

from dsp_platform.controlled_document_retrieval.ssrf import (
    ALLOWED_HTTPS_PORT,
    resolve_public_addresses,
)
from dsp_platform.external_evidence import ExternalEvidenceValidationError

__all__ = [
    "DocumentTransport",
    "StdlibHttpsTransport",
    "TransportResponse",
]


@dataclass(frozen=True, slots=True)
class TransportResponse:
    status_code: int
    headers: Mapping[str, str]
    body: bytes
    location: str = ""


class DocumentTransport(Protocol):
    def fetch(
        self, url: str, *, timeout_seconds: float, max_bytes: int
    ) -> TransportResponse:
        ...


class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    """Connect to a pre-validated public IP while keeping Host/SNI as hostname."""

    def __init__(
        self,
        hostname: str,
        pinned_ip: str,
        *,
        timeout: float,
        context: ssl.SSLContext,
    ) -> None:
        super().__init__(
            hostname,
            ALLOWED_HTTPS_PORT,
            timeout=timeout,
            context=context,
        )
        self._pinned_ip = pinned_ip

    def connect(self) -> None:
        timeout = (
            self.timeout if self.timeout is not None else socket.getdefaulttimeout()
        )
        sock = socket.create_connection(
            (self._pinned_ip, self.port),
            timeout,
            self.source_address,
        )
        context = self._context or ssl.create_default_context()
        self.sock = context.wrap_socket(sock, server_hostname=self.host)


class StdlibHttpsTransport:
    """stdlib HTTPS GET to a resolved public IP. Redirects are not followed."""

    def fetch(
        self, url: str, *, timeout_seconds: float, max_bytes: int
    ) -> TransportResponse:
        parsed = urlparse(url)
        if parsed.scheme != "https":
            raise ExternalEvidenceValidationError(
                "document locator rejected: only https URLs may be fetched"
            )
        hostname = (parsed.hostname or "").strip().lower().rstrip(".")
        if not hostname:
            raise ExternalEvidenceValidationError(
                "document locator rejected: missing host"
            )
        addresses = resolve_public_addresses(hostname)
        path = parsed.path or "/"
        if parsed.query:
            path = f"{path}?{parsed.query}"
        _reject_unsafe_request_target(path)
        pinned_ip = addresses[0]
        headers = {
            "Host": hostname,
            "User-Agent": "DSP-AI-Indicator/document-retrieval",
            "Accept": "text/html, text/plain, application/xhtml+xml",
            "Accept-Encoding": "identity",
            "Connection": "close",
        }
        connection = _PinnedHTTPSConnection(
            hostname,
            pinned_ip,
            timeout=timeout_seconds,
            context=ssl.create_default_context(),
        )
        try:
            connection.request("GET", path, headers=headers)
            response = connection.getresponse()
            raw_headers = {
                str(key).lower(): str(value) for key, value in response.getheaders()
            }
            body = _read_limited(response, max_bytes=max_bytes)
            return TransportResponse(
                status_code=int(response.status),
                headers=raw_headers,
                body=body,
                location=raw_headers.get("location", ""),
            )
        except TimeoutError:
            raise
        except (OSError, ssl.SSLError, http.client.HTTPException) as exc:
            raise OSError("document retrieval rejected: transport failure") from exc
        finally:
            connection.close()


def _reject_unsafe_request_target(path: str) -> None:
    if not path.startswith("/"):
        raise ExternalEvidenceValidationError(
            "document locator rejected: request path must be absolute"
        )
    if any(ch.isspace() or ord(ch) < 32 or ord(ch) == 127 for ch in path):
        raise ExternalEvidenceValidationError(
            "document locator rejected: control characters are not allowed"
        )


def _read_limited(stream: object, *, max_bytes: int) -> bytes:
    read = getattr(stream, "read", None)
    if not callable(read):
        return b""
    chunks: list[bytes] = []
    remaining = max_bytes + 1
    while remaining > 0:
        piece = read(min(65536, remaining))
        if not piece:
            break
        chunks.append(piece)
        remaining -= len(piece)
    data = b"".join(chunks)
    if len(data) > max_bytes:
        raise ValueError("document retrieval rejected: response exceeds size limit")
    return data
