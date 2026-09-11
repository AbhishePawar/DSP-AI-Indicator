"""Bounded official-document retrieval. Approved hosts only. Immutable records."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import date, datetime
from http.cookiejar import CookieJar
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import HTTPCookieProcessor, HTTPRedirectHandler, Request, build_opener

from data_engine.official_research.company_sources import CompanySourceRegistry, host_of
from data_engine.official_research.models import utc_now
from data_engine.official_research.nse_eod import NseHttpTransport, NsePublicHttp
from data_engine.official_research.source_policy import SourcePolicy, classify_source_url

__all__ = [
    "DocumentCandidate",
    "DocumentCharacteristics",
    "DocumentRecord",
    "DocumentStore",
    "RetrievalFailure",
    "classify_retrieval_reason",
    "document_version_relation",
    "identify_document_characteristics",
    "redirect_is_approved",
    "retrieve_official_document",
    "select_extraction_strategy",
]

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)


@dataclass(frozen=True, slots=True)
class DocumentCandidate:
    """Generic discovered document. Trust comes from host/identity, not URL words."""

    url: str
    host: str
    source_type: str
    document_type: str
    company: str
    isin: str
    period: str | None
    basis: str | None
    publication_date: date | None
    retrieved_at: datetime | None
    document_hash: str | None
    status: str


def document_version_relation(
    *,
    url_a: str,
    hash_a: str,
    url_b: str,
    hash_b: str,
) -> str:
    """URL + SHA256 versioning. Never silently replace an older payload."""
    if url_a == url_b and hash_a == hash_b:
        return "reuse"
    if url_a != url_b and hash_a == hash_b:
        return "alias"
    if url_a == url_b and hash_a != hash_b:
        return "new_version"
    return "distinct"


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
        same_hash = self.get_by_hash(record.document_hash)
        if same_hash is not None:
            self._by_url[key] = same_hash
            return same_hash
        self._versions.append(record)
        self._by_url[key] = record
        return record

    def versions(self) -> tuple[DocumentRecord, ...]:
        return tuple(self._versions)

    def get_by_hash(self, document_hash: str) -> DocumentRecord | None:
        digest = str(document_hash or "").strip()
        if not digest:
            return None
        for record in reversed(self._versions):
            if record.document_hash == digest:
                return record
        return None


def classify_retrieval_reason(reason: str, http_status: int | None = None) -> str:
    lowered = str(reason or "").lower()
    if http_status == 403 or "http 403" in lowered:
        return "403"
    if http_status == 404 or "http 404" in lowered:
        return "404"
    if http_status == 429 or "http 429" in lowered:
        return "429"
    if http_status is not None and http_status >= 500:
        return "5xx"
    if "unapproved redirect" in lowered:
        return "redirect_rejection"
    if "ssl" in lowered or "tls" in lowered or "certificate" in lowered:
        return "tls_failure"
    if "getaddrinfo" in lowered or "nameresolution" in lowered or "dns" in lowered:
        return "dns_failure"
    if "timed out" in lowered or "timeout" in lowered:
        return "timeout"
    if "empty document" in lowered:
        return "empty_document"
    if "html instead of pdf" in lowered:
        return "html_instead_of_pdf"
    if "invalid pdf" in lowered:
        return "invalid_pdf"
    if "no text layer" in lowered:
        return "pdf_parse_failure"
    return "other"


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
    if host_kind == "approved_research":
        return RetrievalFailure(
            url=url,
            reason="approved research cannot be retrieved as primary truth",
        )
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


@dataclass(frozen=True, slots=True)
class DocumentCharacteristics:
    url: str
    content_hash: str | None
    retrieved_at: datetime | None
    document_type: str | None
    reporting_period: str | None
    document_date: date | None
    statement_basis: str | None
    audit_status: str | None
    currency: str | None
    units: str | None
    extraction_strategy: str
    evidence_locator: str | None = None


def select_extraction_strategy(
    *,
    payload: bytes | None = None,
    text: str | None = None,
    has_coordinate_spans: bool = False,
) -> str:
    """Choose a generic extractor from document characteristics, never an issuer parser."""
    if has_coordinate_spans:
        return "coordinate"
    raw = payload or b""
    body = str(text or "").strip()
    if raw.lstrip().startswith(b"%PDF"):
        if not body:
            return "ocr_required"
        if "revenue from operations" in body.lower() or "\t" in body:
            return "table"
        return "native_pdf_text"
    if not body:
        return "unavailable"
    if "|" in body or "\t" in body:
        return "table"
    return "plain_text"


def identify_document_characteristics(
    *,
    url: str,
    payload: bytes | None = None,
    text: str | None = None,
    retrieved_at: datetime | None = None,
    content_hash: str | None = None,
    document_date: date | str | None = None,
    has_coordinate_spans: bool = False,
) -> DocumentCharacteristics:
    """Generic document identity. Unknown attributes stay UNKNOWN, never guessed."""
    from data_engine.official_research.extraction import parse_document_context
    from data_engine.official_research.pdf_text import document_text_from_payload

    body = text
    if body is None and payload:
        body = document_text_from_payload(payload) or ""
    body = body or ""
    digest = content_hash
    if digest is None and payload:
        digest = hashlib.sha256(payload).hexdigest()
    context = parse_document_context(body) if body else None
    lowered = body.lower()
    document_type = _document_type(lowered)
    audit_status = _audit_status(lowered)
    parsed_date = _coerce_document_date(document_date)
    if parsed_date is None and context is not None:
        parsed_date = context.period_end
    period = None
    if context is not None and context.period_end is not None:
        period = context.period_end.isoformat()
    elif context is not None and context.period_type:
        period = None if context.period_type == "unknown" else context.period_type
    basis = context.statement_basis if context is not None else None
    currency = context.currency if context is not None else None
    units = context.unit_scale if context is not None else None
    strategy = select_extraction_strategy(
        payload=payload, text=body, has_coordinate_spans=has_coordinate_spans
    )
    return DocumentCharacteristics(
        url=url,
        content_hash=digest,
        retrieved_at=retrieved_at,
        document_type=document_type,
        reporting_period=period,
        document_date=parsed_date,
        statement_basis=basis,
        audit_status=audit_status,
        currency=currency,
        units=units,
        extraction_strategy=strategy,
        evidence_locator=url,
    )


def _document_type(lowered: str) -> str | None:
    if not lowered:
        return None
    if "annual report" in lowered or "integrated report" in lowered:
        return "annual_report"
    if "financial statement" in lowered or "statement of profit" in lowered:
        return "financial_statements"
    if "shareholding" in lowered:
        return "shareholding"
    return None


def _audit_status(lowered: str) -> str | None:
    if not lowered:
        return None
    unaudited = "unaudited" in lowered
    audited = bool(re.search(r"\baudited\b", lowered)) and not unaudited
    if audited and unaudited:
        return None
    if audited:
        return "audited"
    if unaudited:
        return "unaudited"
    return None


def _coerce_document_date(value: date | str | None) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, date):
        return value
    text = str(value).strip()[:10]
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None
