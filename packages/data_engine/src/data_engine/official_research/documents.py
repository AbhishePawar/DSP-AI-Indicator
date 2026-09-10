"""Bounded official-document retrieval. Approved hosts only. Immutable records."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from http.cookiejar import CookieJar
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import HTTPCookieProcessor, HTTPRedirectHandler, Request, build_opener

from data_engine.official_research.company_sources import CompanySourceRegistry, host_of
from data_engine.official_research.models import utc_now
from data_engine.official_research.nse_eod import NseHttpTransport, NsePublicHttp
from data_engine.official_research.source_policy import SourcePolicy, classify_source_url

__all__ = [
    "DocumentRecord",
    "DocumentStore",
    "RetrievalFailure",
    "redirect_is_approved",
    "retrieve_official_document",
]

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)


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
    final_url: str | None = None


@dataclass(frozen=True, slots=True)
class RetrievalFailure:
    url: str
    reason: str
    http_status: int | None = None


class DocumentStore:
    """Immutable document cache keyed by ISIN+MIC+URL. Hash changes are new versions."""

    def __init__(self) -> None:
        self._by_url: dict[str, DocumentRecord] = {}
        self._versions: list[DocumentRecord] = []

    def get(self, *, isin: str, mic: str, url: str) -> DocumentRecord | None:
        return self._by_url.get(_store_key(isin, mic, url))

    def put(self, record: DocumentRecord) -> DocumentRecord:
        key = _store_key(record.company_isin, record.company_mic, record.url)
        previous = self._by_url.get(key)
        if previous is not None and previous.document_hash == record.document_hash:
            return previous
        self._versions.append(record)
        self._by_url[key] = record
        return record

    def versions(self) -> tuple[DocumentRecord, ...]:
        return tuple(self._versions)


def _store_key(isin: str, mic: str, url: str) -> str:
    return "|".join((isin.strip().upper(), mic.strip().upper(), url.strip()))


def redirect_is_approved(
    target: str,
    *,
    isin: str,
    registry: CompanySourceRegistry | None,
) -> bool:
    kind = classify_source_url(target)
    if kind == "primary":
        return True
    if kind in {"secondary", "forbidden"}:
        return False
    if registry is None:
        return False
    return registry.allows(isin, target)


class _ApprovedRedirectHandler(HTTPRedirectHandler):
    def __init__(self, allow) -> None:
        super().__init__()
        self._allow = allow

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        target = urljoin(req.full_url, str(newurl))
        if not self._allow(target):
            raise LookupError(f"RETRIEVAL REJECTED: unapproved redirect to {host_of(target)}")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _fetch_with_redirect_policy(url: str, *, allow) -> bytes:
    opener = build_opener(
        HTTPCookieProcessor(CookieJar()),
        _ApprovedRedirectHandler(allow),
    )
    request = Request(
        url,
        headers={
            "User-Agent": _UA,
            "Accept": "text/html,application/xhtml+xml,application/pdf,application/xhtml+xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-IN,en;q=0.9",
            "Referer": f"https://{host_of(url)}/",
        },
    )
    try:
        with opener.open(request, timeout=45.0) as response:
            return response.read()
    except HTTPError as exc:
        raise LookupError(f"HTTP {exc.code} for official URL") from None
    except LookupError:
        raise
    except (URLError, OSError) as exc:
        raise LookupError(f"request failed: {type(exc).__name__}") from None


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
    store: DocumentStore | None = None,
) -> DocumentRecord | RetrievalFailure:
    """Download one approved URL. Unapproved hosts never become evidence.

    LIVE retrieval does not treat arbitrary https + company_ir as approved.
    Exchange/regulator hosts are primary. Company IR hosts must be in the
    ISIN registry. Injected MOCK document_text is not retrieved here.
    Redirects that leave the approved host set are rejected.
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
    if store is not None:
        cached = store.get(isin=isin, mic=mic, url=url)
        if cached is not None:
            return cached
    allow = lambda target: redirect_is_approved(target, isin=isin, registry=registry)
    live_company = isinstance(transport, NsePublicHttp) and host_kind != "primary"
    try:
        if live_company:
            payload = _fetch_with_redirect_policy(url, allow=allow)
        else:
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
    record = DocumentRecord(
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
        final_url=url,
    )
    if store is not None:
        return store.put(record)
    return record
