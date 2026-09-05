"""Official exchange attachment retrieval and unresolved-event enrichment.

Fetches only allowlisted HTTPS locators from announcement records.
Does not persist cookies, authorization headers, or document bytes in artifacts.
"""

from __future__ import annotations

from collections.abc import Mapping, MutableMapping
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from typing import Any, Protocol
from urllib.parse import urljoin, urlparse

from dsp_platform.controlled_document_retrieval.html_text import html_to_visible_text
from dsp_platform.current_outstanding_protocol.ledger import classify_exchange_event
from dsp_platform.share_count_acquisition.live_http import (
    MAX_DOCUMENT_BYTES,
    AllowlistedLiveJsonHttp,
)
from dsp_platform.share_count_acquisition.models import ExchangeAcquisitionResult
from dsp_platform.share_count_acquisition.pdf_text import extract_pdf_text
from dsp_platform.share_count_acquisition.policy import EXCHANGE_DOCUMENT_HOSTS

__all__ = [
    "ALLOWED_ATTACHMENT_MEDIA",
    "RetrievedOfficialDocument",
    "enrich_unresolved_announcements",
    "official_attachment_url",
    "retrieve_official_document",
]

ALLOWED_ATTACHMENT_MEDIA = frozenset(
    {
        "application/pdf",
        "application/x-pdf",
        "text/html",
        "application/xhtml+xml",
        "text/plain",
    }
)
_URL_KEYS = (
    "attchmntFile",
    "attachment",
    "fileUrl",
    "file_url",
    "attachementFile",
)
_MAX_UNRESOLVED_FETCHES = 8
_NSE_ARCHIVE = "https://nsearchives.nseindia.com"


@dataclass(frozen=True, slots=True)
class RetrievedOfficialDocument:
    url: str
    announcement_identifier: str
    retrieved_at: str
    http_status: int | None
    content_type: str
    content_length: int
    document_hash: str | None
    text: str
    error: str | None
    ok: bool


class BytesHttpPort(Protocol):
    def get_bytes(
        self,
        url: str,
        *,
        referer: str | None = None,
        accept: str = "*/*",
        max_bytes: int | None = None,
    ) -> Mapping[str, Any]:
        ...


def official_attachment_url(record: Mapping[str, Any]) -> str | None:
    """Resolve an official HTTPS attachment locator from an exchange record."""
    for key in _URL_KEYS:
        raw = str(record.get(key) or "").strip()
        if not raw:
            continue
        resolved = _absolutize(raw)
        if resolved is not None:
            return resolved
    filename = str(record.get("fileName") or record.get("csvName") or "").strip()
    if filename.startswith("https://"):
        return _absolutize(filename)
    if filename.startswith("/corporate/"):
        return _absolutize(filename)
    return None


def retrieve_official_document(
    url: str,
    *,
    http: BytesHttpPort,
    announcement_identifier: str = "",
    referer: str | None = "https://www.nseindia.com/",
    allowed_hosts: frozenset[str] = EXCHANGE_DOCUMENT_HOSTS,
) -> RetrievedOfficialDocument:
    retrieved_at = datetime.now(tz=UTC).isoformat()
    host = (urlparse(url).hostname or "").strip().lower()
    if host not in allowed_hosts:
        return RetrievedOfficialDocument(
            url=url,
            announcement_identifier=announcement_identifier,
            retrieved_at=retrieved_at,
            http_status=None,
            content_type="",
            content_length=0,
            document_hash=None,
            text="",
            error=f"host not allowlisted: {host}",
            ok=False,
        )
    result = http.get_bytes(
        url,
        referer=referer,
        accept="application/pdf,text/html,text/plain,*/*",
        max_bytes=MAX_DOCUMENT_BYTES,
    )
    status = result.get("status") if isinstance(result.get("status"), int) else None
    ctype = str(result.get("content_type") or "").split(";", 1)[0].strip().lower()
    body = result.get("body")
    if not result.get("ok") or not isinstance(body, (bytes, bytearray)):
        error = "document retrieval failed"
        traces_error = None
        if isinstance(result, Mapping):
            traces_error = result.get("error")
        if result.get("truncated"):
            error = "response exceeds size limit"
        return RetrievedOfficialDocument(
            url=url,
            announcement_identifier=announcement_identifier,
            retrieved_at=str(result.get("retrieved_at") or retrieved_at),
            http_status=status,
            content_type=ctype,
            content_length=int(result.get("content_length") or 0),
            document_hash=None,
            text="",
            error=str(traces_error or error),
            ok=False,
        )
    if ctype not in ALLOWED_ATTACHMENT_MEDIA:
        if body.lstrip().startswith(b"%PDF"):
            ctype = "application/pdf"
        else:
            return RetrievedOfficialDocument(
                url=url,
                announcement_identifier=announcement_identifier,
                retrieved_at=str(result.get("retrieved_at") or retrieved_at),
                http_status=status,
                content_type=ctype,
                content_length=len(body),
                document_hash=str(result.get("sha256") or "") or None,
                text="",
                error="unsupported content type",
                ok=False,
            )
    text = _decode_document(bytes(body), ctype)
    return RetrievedOfficialDocument(
        url=url,
        announcement_identifier=announcement_identifier,
        retrieved_at=str(result.get("retrieved_at") or retrieved_at),
        http_status=status,
        content_type=ctype,
        content_length=len(body),
        document_hash=str(result.get("sha256") or "") or None,
        text=text,
        error=None if text.strip() else "document text could not be extracted",
        ok=bool(text.strip()),
    )


def enrich_unresolved_announcements(
    bundle: ExchangeAcquisitionResult,
    *,
    http: BytesHttpPort | None = None,
    allowed_hosts: frozenset[str] = EXCHANGE_DOCUMENT_HOSTS,
) -> ExchangeAcquisitionResult:
    """Fetch official attachments only when announcement classification is unresolved."""
    client = http or AllowlistedLiveJsonHttp(allowed_hosts=allowed_hosts)
    enriched: list[Mapping[str, Any]] = []
    fetches = 0
    for raw in bundle.announcements:
        if not isinstance(raw, Mapping):
            continue
        item: MutableMapping[str, Any] = dict(raw)
        blob = " ".join(
            str(item.get(key) or "")
            for key in ("desc", "attchmntText", "NEWSSUB", "MORE", "subject")
        )
        _event, changes = classify_exchange_event(blob)
        if changes is not None or fetches >= _MAX_UNRESOLVED_FETCHES:
            enriched.append(item)
            continue
        url = official_attachment_url(item)
        if url is None:
            enriched.append(item)
            continue
        document = retrieve_official_document(
            url,
            http=client,
            announcement_identifier=str(item.get("seq_id") or item.get("NEWSID") or ""),
            allowed_hosts=allowed_hosts,
        )
        fetches += 1
        item["attachment_url"] = document.url
        item["attachment_retrieved_at"] = document.retrieved_at
        item["attachment_http_status"] = document.http_status
        item["attachment_content_type"] = document.content_type
        item["attachment_content_length"] = document.content_length
        item["attachment_sha256"] = document.document_hash
        item["attachment_text"] = document.text
        if document.error:
            item["attachment_error"] = document.error
        enriched.append(item)
    return replace(bundle, announcements=tuple(enriched))


def _absolutize(raw: str) -> str | None:
    text = raw.strip()
    if not text or text.startswith(("javascript:", "data:", "file:")):
        return None
    if text.startswith("//"):
        text = "https:" + text
    if text.startswith("/corporate/"):
        text = urljoin(_NSE_ARCHIVE + "/", text.lstrip("/"))
    parsed = urlparse(text)
    if parsed.scheme != "https" or not parsed.netloc:
        return None
    host = (parsed.hostname or "").lower()
    if host not in EXCHANGE_DOCUMENT_HOSTS:
        return None
    return text.split("#", 1)[0]


def _decode_document(body: bytes, content_type: str) -> str:
    if content_type in {"application/pdf", "application/x-pdf"} or body.lstrip().startswith(
        b"%PDF"
    ):
        return extract_pdf_text(body)
    text = body.decode("utf-8", errors="replace").replace("\x00", "")
    if content_type in {"text/html", "application/xhtml+xml"}:
        return html_to_visible_text(text)
    return text.strip()
