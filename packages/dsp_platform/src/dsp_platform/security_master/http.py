"""Allowlisted HTTPS fetch for frozen NSE/BSE security-master locators.

Does not accept caller-supplied URLs. Cookies stay in-memory and are never
logged. Response bodies are not written to traces.
"""

from __future__ import annotations

from datetime import UTC, datetime
from http.cookiejar import CookieJar
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import (
    HTTPCookieProcessor,
    HTTPRedirectHandler,
    HTTPSHandler,
    Request,
    build_opener,
)

from dsp_platform.controlled_document_retrieval.ssrf import assert_public_https_locator
from dsp_platform.external_evidence import ExternalEvidenceValidationError
from dsp_platform.security_master.sources import (
    BSE_LIST_SCRIPS_REFERER,
    NSE_SECURITIES_PAGE,
    OFFICIAL_SOURCES,
    SECURITY_MASTER_HOSTS,
    OfficialSource,
)
from dsp_platform.security_master.models import SourceDocument

__all__ = [
    "MAX_DOCUMENT_BYTES",
    "REQUEST_TIMEOUT_SECONDS",
    "SecurityMasterHttp",
    "fetch_official_documents",
]

REQUEST_TIMEOUT_SECONDS = 30.0
MAX_DOCUMENT_BYTES = 8_000_000
_MAX_RETRIES = 2
_BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)


class _SameHostRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        old_host = (urlparse(req.full_url).hostname or "").lower()
        new_host = (urlparse(newurl).hostname or "").lower()
        if old_host != new_host:
            raise ExternalEvidenceValidationError(
                f"cross-host redirect rejected: {old_host} -> {new_host}"
            )
        assert_public_https_locator(newurl.split("#", 1)[0])
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class SecurityMasterHttp:
    """Official-source GET. Host allowlist + SSRF check. No arbitrary URLs."""

    def __init__(
        self,
        *,
        timeout_seconds: float = REQUEST_TIMEOUT_SECONDS,
        max_bytes: int = MAX_DOCUMENT_BYTES,
    ) -> None:
        self._timeout_seconds = float(timeout_seconds)
        self._max_bytes = int(max_bytes)
        self._jar = CookieJar()
        self._opener = build_opener(
            HTTPSHandler(),
            HTTPCookieProcessor(self._jar),
            _SameHostRedirectHandler(),
        )

    def get_document(self, source: OfficialSource) -> SourceDocument:
        if source.uri not in {item.uri for item in OFFICIAL_SOURCES}:
            return SourceDocument(
                source_id=source.source_id,
                exchange=source.exchange,
                document_kind=source.document_kind,
                uri=source.uri,
                body=b"",
                retrieved_at=datetime.now(tz=UTC).isoformat(),
                last_modified="",
                content_type="",
                status=0,
                error="locator is not a frozen official source",
            )
        last: dict[str, Any] | None = None
        for _attempt in range(_MAX_RETRIES + 1):
            last = self._get(source.uri, referer=source.referer, accept=source.accept)
            if last.get("ok"):
                break
            if int(last.get("status") or 0) not in {0, 403, 429, 500, 502, 503, 504}:
                break
        assert last is not None
        return SourceDocument(
            source_id=source.source_id,
            exchange=source.exchange,
            document_kind=source.document_kind,
            uri=source.uri,
            body=last.get("body") or b"",
            retrieved_at=str(last.get("retrieved_at") or ""),
            last_modified=str(last.get("last_modified") or ""),
            content_type=str(last.get("content_type") or ""),
            status=int(last.get("status") or 0),
            error="" if last.get("ok") else str(last.get("error") or "fetch failed"),
        )

    def warmup(self) -> None:
        self._get(
            NSE_SECURITIES_PAGE,
            referer="https://www.nseindia.com/",
            accept="text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
            keep_body=False,
        )
        self._get(
            BSE_LIST_SCRIPS_REFERER,
            referer="https://www.bseindia.com/",
            accept="text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
            keep_body=False,
        )

    def _get(
        self,
        url: str,
        *,
        referer: str,
        accept: str,
        keep_body: bool = True,
    ) -> dict[str, Any]:
        retrieved_at = datetime.now(tz=UTC).isoformat()
        try:
            host = assert_public_https_locator(url)
        except ExternalEvidenceValidationError as exc:
            return {
                "ok": False,
                "status": 0,
                "body": b"",
                "retrieved_at": retrieved_at,
                "last_modified": "",
                "content_type": "",
                "error": str(exc),
            }
        if host not in SECURITY_MASTER_HOSTS:
            return {
                "ok": False,
                "status": 0,
                "body": b"",
                "retrieved_at": retrieved_at,
                "last_modified": "",
                "content_type": "",
                "error": f"host not allowlisted: {host}",
            }
        try:
            ref_host = assert_public_https_locator(referer)
        except ExternalEvidenceValidationError as exc:
            return {
                "ok": False,
                "status": 0,
                "body": b"",
                "retrieved_at": retrieved_at,
                "last_modified": "",
                "content_type": "",
                "error": f"referer rejected: {exc}",
            }
        if ref_host not in SECURITY_MASTER_HOSTS:
            return {
                "ok": False,
                "status": 0,
                "body": b"",
                "retrieved_at": retrieved_at,
                "last_modified": "",
                "content_type": "",
                "error": "referer host not allowlisted",
            }
        headers = {
            "User-Agent": _BROWSER_UA,
            "Accept": accept,
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": referer,
            "Connection": "close",
        }
        req = Request(url, headers=headers, method="GET")
        cap = self._max_bytes
        try:
            with self._opener.open(req, timeout=self._timeout_seconds) as resp:
                raw = resp.read(cap + 1)
                status = int(getattr(resp, "status", 200))
                ctype = str(resp.headers.get("Content-Type", "") or "")
                last_modified = str(resp.headers.get("Last-Modified", "") or "")
        except HTTPError as exc:
            body = exc.read(cap) if exc.fp is not None else b""
            return {
                "ok": False,
                "status": int(exc.code),
                "body": body[:cap],
                "retrieved_at": retrieved_at,
                "last_modified": "",
                "content_type": str(exc.headers.get("Content-Type", "") if exc.headers else ""),
                "error": f"HTTP {exc.code}",
            }
        except (URLError, TimeoutError, ExternalEvidenceValidationError) as exc:
            return {
                "ok": False,
                "status": 0,
                "body": b"",
                "retrieved_at": retrieved_at,
                "last_modified": "",
                "content_type": "",
                "error": str(exc),
            }
        truncated = len(raw) > cap
        stored = raw[:cap]
        html = _looks_like_html(stored, ctype)
        error = ""
        if truncated:
            error = "response exceeds size limit"
        elif html and keep_body:
            error = "HTML shell received instead of security file"
        ok = 200 <= status < 300 and not truncated and not error
        return {
            "ok": ok,
            "status": status,
            "body": stored if keep_body else b"",
            "retrieved_at": retrieved_at,
            "last_modified": last_modified,
            "content_type": ctype,
            "error": error,
        }


def fetch_official_documents(http: SecurityMasterHttp | None = None) -> tuple[SourceDocument, ...]:
    client = http or SecurityMasterHttp()
    client.warmup()
    return tuple(client.get_document(source) for source in OFFICIAL_SOURCES)


def _looks_like_html(body: bytes, ctype: str) -> bool:
    lowered = ctype.casefold()
    if "html" in lowered:
        return True
    head = body[:200].decode("utf-8", errors="replace").lstrip().casefold()
    return head.startswith("<!doctype html") or head.startswith("<html")
