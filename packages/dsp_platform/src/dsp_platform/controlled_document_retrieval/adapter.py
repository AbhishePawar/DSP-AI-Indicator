"""Controlled HTTPS retrieval implementing PrimarySourceDocumentRetrievalPort.

AI-discovered URLs are fetched only after SSRF checks. Retrieved text is
not ShareCount authority. Production protocol still uses the blocked port.
"""

from __future__ import annotations

from collections.abc import Mapping
from urllib.parse import urljoin, urlparse

from dsp_platform.controlled_document_retrieval.html_text import html_to_visible_text
from dsp_platform.controlled_document_retrieval.policy import (
    source_tier_for_host,
    source_type_for_host,
)
from dsp_platform.controlled_document_retrieval.ssrf import (
    assert_public_https_locator,
    hosts_equivalent,
    resolve_public_addresses,
)
from dsp_platform.controlled_document_retrieval.transport import (
    DocumentTransport,
    StdlibHttpsTransport,
    TransportResponse,
)
from dsp_platform.external_evidence import ExternalEvidenceValidationError
from dsp_platform.primary_source_retrieval import (
    PrimarySourceDocumentRequest,
    RetrievedPrimarySourceDocument,
    validate_retrieval_request,
)

__all__ = [
    "ALLOWED_MEDIA_TYPES",
    "MAX_DOCUMENT_BYTES",
    "MAX_REDIRECTS",
    "RETRIEVAL_TIMEOUT_SECONDS",
    "ControlledHttpsDocumentRetrieval",
]

MAX_DOCUMENT_BYTES = 1_000_000
MAX_REDIRECTS = 3
RETRIEVAL_TIMEOUT_SECONDS = 10.0
ALLOWED_MEDIA_TYPES = frozenset(
    {
        "text/html",
        "text/plain",
        "application/xhtml+xml",
    }
)


class ControlledHttpsDocumentRetrieval:
    """Fetch HTTPS documents behind PrimarySourceDocumentRetrievalPort."""

    def __init__(
        self,
        *,
        transport: DocumentTransport | None = None,
        resolver: object | None = None,
        tier_1_hosts: frozenset[str] | None = None,
        timeout_seconds: float = RETRIEVAL_TIMEOUT_SECONDS,
        max_bytes: int = MAX_DOCUMENT_BYTES,
        max_redirects: int = MAX_REDIRECTS,
    ) -> None:
        self._transport = transport or StdlibHttpsTransport()
        self._resolver = resolver
        self._tier_1_hosts = tier_1_hosts
        self._timeout_seconds = float(timeout_seconds)
        self._max_bytes = int(max_bytes)
        self._max_redirects = int(max_redirects)

    def retrieve(
        self, request: PrimarySourceDocumentRequest
    ) -> RetrievedPrimarySourceDocument:
        validate_retrieval_request(request)
        requested = request.locator.strip()
        host = assert_public_https_locator(requested)
        resolve_public_addresses(host, resolver=self._resolver)
        response, final_url, final_host = self._follow(requested, origin_host=host)
        _reject_content_encoding(response.headers)
        media_type = _media_type(response.headers)
        text = _decode_body(response.body, media_type=media_type)
        if not text.strip():
            raise ExternalEvidenceValidationError(
                "document retrieval rejected: missing document content"
            )
        tier = source_tier_for_host(final_host, tier_1_hosts=self._tier_1_hosts)
        source_type = source_type_for_host(
            final_host,
            document_type=request.document_type,
            tier=tier,
        )
        return RetrievedPrimarySourceDocument(
            identity=request.identity,
            locator=requested,
            document_type=request.document_type,
            source_type=source_type,
            source_tier=tier,
            retrieved_at=request.retrieved_at,
            text=text,
            media_type=media_type,
            requested_locator=requested,
            final_locator=final_url,
            hostname=final_host,
            source_name=final_host,
            retrieval_status="retrieved",
        )

    def _follow(
        self, locator: str, *, origin_host: str
    ) -> tuple[TransportResponse, str, str]:
        current = locator
        current_host = origin_host
        for _hop in range(self._max_redirects + 1):
            try:
                response = self._transport.fetch(
                    current,
                    timeout_seconds=self._timeout_seconds,
                    max_bytes=self._max_bytes,
                )
            except TimeoutError as exc:
                raise ExternalEvidenceValidationError(
                    "document retrieval rejected: timeout"
                ) from exc
            except ValueError as exc:
                raise ExternalEvidenceValidationError(str(exc)) from exc
            except OSError as exc:
                raise ExternalEvidenceValidationError(
                    "document retrieval rejected: transport failure"
                ) from exc
            status = int(response.status_code)
            if status in {301, 302, 303, 307, 308}:
                current = _next_locator(
                    current,
                    response.location,
                    origin_host=origin_host,
                    resolver=self._resolver,
                )
                current_host = (
                    urlparse(current).hostname or current_host
                ).strip().lower().rstrip(".")
                continue
            if status != 200:
                raise ExternalEvidenceValidationError(
                    f"document retrieval rejected: HTTP {status}"
                )
            return response, current, current_host
        raise ExternalEvidenceValidationError(
            "document retrieval rejected: too many redirects"
        )


def _next_locator(
    current: str,
    location: str,
    *,
    origin_host: str,
    resolver: object | None,
) -> str:
    if not str(location or "").strip():
        raise ExternalEvidenceValidationError(
            "document retrieval rejected: redirect missing Location"
        )
    nxt = urljoin(current, location.strip())
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in nxt):
        raise ExternalEvidenceValidationError(
            "document retrieval rejected: control characters are not allowed"
        )
    host = assert_public_https_locator(nxt)
    if not hosts_equivalent(host, origin_host):
        raise ExternalEvidenceValidationError(
            "document retrieval rejected: source mismatch on redirect"
        )
    resolve_public_addresses(host, resolver=resolver)
    return nxt


def _header(headers: object, name: str) -> str:
    if not isinstance(headers, Mapping):
        return ""
    wanted = name.lower()
    for key, value in headers.items():
        if str(key).lower() == wanted:
            return str(value)
    return ""


def _reject_content_encoding(headers: object) -> None:
    encoding = _header(headers, "content-encoding").split(",", 1)[0].strip().lower()
    if encoding and encoding not in {"identity", "none"}:
        raise ExternalEvidenceValidationError(
            "document retrieval rejected: compressed responses are not accepted"
        )


def _media_type(headers: object) -> str:
    raw = _header(headers, "content-type")
    media = raw.split(";", 1)[0].strip().lower()
    if media in {"application/pdf", "application/x-pdf"}:
        raise ExternalEvidenceValidationError(
            "document retrieval rejected: PDF extraction is not supported"
        )
    if media not in ALLOWED_MEDIA_TYPES:
        raise ExternalEvidenceValidationError(
            "document retrieval rejected: unsupported content type"
        )
    return media


def _decode_body(body: bytes, *, media_type: str) -> str:
    text = body.decode("utf-8", errors="replace").replace("\x00", "")
    if media_type in {"text/html", "application/xhtml+xml"}:
        return html_to_visible_text(text)
    return text.strip()
