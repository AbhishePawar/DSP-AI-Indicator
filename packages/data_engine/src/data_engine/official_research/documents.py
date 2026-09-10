"""Bounded official-document retrieval. Approved hosts only. Immutable records."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime

from data_engine.official_research.company_sources import CompanySourceRegistry
from data_engine.official_research.models import utc_now
from data_engine.official_research.nse_eod import NseHttpTransport
from data_engine.official_research.source_policy import SourcePolicy, classify_source_url

__all__ = [
    "DocumentRecord",
    "RetrievalFailure",
    "retrieve_official_document",
]


@dataclass(frozen=True, slots=True)
class DocumentRecord:
    url: str
    retrieved_at: datetime
    http_status: int
    content_type: str
    content_length: int
    document_hash: str
    payload: bytes
    company_isin: str
    company_mic: str
    document_date: str | None = None


@dataclass(frozen=True, slots=True)
class RetrievalFailure:
    url: str
    reason: str
    http_status: int | None = None


def retrieve_official_document(
    url: str,
    *,
    transport: NseHttpTransport,
    isin: str,
    mic: str,
    source_type: str,
    policy: SourcePolicy | None = None,
    document_date: str | None = None,
    registry: CompanySourceRegistry | None = None,
) -> DocumentRecord | RetrievalFailure:
    """Download one approved URL. Unapproved hosts never become evidence.

    LIVE retrieval does not treat arbitrary https + company_ir as approved.
    Exchange/regulator hosts are primary. Company IR hosts must be in the
    ISIN registry. Injected MOCK document_text is not retrieved here.
    """
    policy = policy or SourcePolicy()
    host_kind = classify_source_url(url)
    if host_kind == "forbidden":
        return RetrievalFailure(url=url, reason="forbidden source")
    if host_kind == "secondary":
        return RetrievalFailure(url=url, reason="secondary source cannot be retrieved as truth")
    if host_kind != "primary":
        allowed = registry is not None and registry.allows(isin, url)
        if not allowed:
            return RetrievalFailure(
                url=url,
                reason="unapproved host (not exchange/regulator and not ISIN IR registry)",
            )
    kind = classify_source_url(url, source_type=source_type)
    if not policy.may_verify(url, source_type=source_type):
        if kind != "primary":
            return RetrievalFailure(url=url, reason=f"unapproved source class={kind}")
    try:
        payload = transport.get_bytes(url)
    except LookupError as exc:
        status = None
        message = str(exc)
        if "HTTP " in message:
            try:
                status = int(message.split("HTTP ", 1)[1].split()[0])
            except ValueError:
                status = None
        return RetrievalFailure(url=url, reason=message, http_status=status)
    digest = hashlib.sha256(payload).hexdigest()
    content_type = "application/pdf" if payload[:5] == b"%PDF-" else "application/octet-stream"
    if payload.lstrip()[:1] in {b"<", b"{"}:
        content_type = "text/html" if payload.lstrip().startswith(b"<") else "application/json"
    return DocumentRecord(
        url=url,
        retrieved_at=utc_now(),
        http_status=200,
        content_type=content_type,
        content_length=len(payload),
        document_hash=digest,
        payload=payload,
        company_isin=isin,
        company_mic=mic,
        document_date=document_date,
    )
