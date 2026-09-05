"""Allowlisted live JSON HTTPS for exchange connectors.

Cookies are used in-memory for NSE WAF warmup and never serialized.
This transport is TESTABLE. Production promotion still uses DSP-attested
corpora, not this connector id.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
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
from dsp_platform.share_count_acquisition.policy import EXCHANGE_DOCUMENT_HOSTS

__all__ = [
    "MAX_DOCUMENT_BYTES",
    "MAX_JSON_BYTES",
    "REQUEST_TIMEOUT_SECONDS",
    "AllowlistedLiveJsonHttp",
    "FetchTrace",
]

REQUEST_TIMEOUT_SECONDS = 20.0
MAX_JSON_BYTES = 1_048_576
MAX_DOCUMENT_BYTES = 8_000_000
_BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)


@dataclass(frozen=True, slots=True)
class FetchTrace:
    url: str
    retrieved_at: str
    status: int | None
    ok: bool
    content_type: str
    body_chars: int
    rate_limited: bool
    truncated: bool
    html_shell: bool
    error: str | None

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "retrieved_at": self.retrieved_at,
            "status": self.status,
            "ok": self.ok,
            "content_type": self.content_type,
            "body_chars": self.body_chars,
            "rate_limited": self.rate_limited,
            "truncated": self.truncated,
            "html_shell": self.html_shell,
            "error": self.error,
        }


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


class AllowlistedLiveJsonHttp:
    """Real HTTPS GET for official exchange JSON. Does not persist cookies."""

    def __init__(
        self,
        *,
        allowed_hosts: frozenset[str] = EXCHANGE_DOCUMENT_HOSTS,
        timeout_seconds: float = REQUEST_TIMEOUT_SECONDS,
        max_bytes: int = MAX_JSON_BYTES,
    ) -> None:
        self._allowed_hosts = allowed_hosts
        self._timeout_seconds = float(timeout_seconds)
        self._max_bytes = int(max_bytes)
        self._jar = CookieJar()
        self._opener = build_opener(
            HTTPSHandler(),
            HTTPCookieProcessor(self._jar),
            _SameHostRedirectHandler(),
        )
        self.traces: list[FetchTrace] = []
        self.warmed_nse = False

    def public_traces(self) -> tuple[dict[str, Any], ...]:
        return tuple(trace.to_public_dict() for trace in self.traces)

    def warmup_nse(self, symbol: str) -> bool:
        ticker = str(symbol or "").strip().upper()
        if not ticker:
            return False
        home = self._get_raw(
            "https://www.nseindia.com/",
            accept="text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
            parse_json=False,
        )
        quote = self._get_raw(
            f"https://www.nseindia.com/get-quotes/equity?symbol={ticker}",
            accept="text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
            referer="https://www.nseindia.com/",
            parse_json=False,
        )
        filings = self._get_raw(
            "https://www.nseindia.com/companies-listing/corporate-filings-actions",
            accept="text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
            referer="https://www.nseindia.com/",
            parse_json=False,
        )
        self.warmed_nse = bool(home.get("ok") or quote.get("ok") or filings.get("ok"))
        return self.warmed_nse

    def get_json(
        self, url: str, *, referer: str | None = None
    ) -> Mapping[str, Any] | list[Any] | None:
        result = self._get_raw(url, referer=referer, parse_json=True)
        parsed = result.get("json")
        if isinstance(parsed, (dict, list)):
            return parsed
        return None

    def get_bytes(
        self,
        url: str,
        *,
        referer: str | None = None,
        accept: str = "*/*",
        max_bytes: int | None = None,
    ) -> dict[str, Any]:
        """Fetch raw bytes. Body is never written to traces."""
        return self._get_raw(
            url,
            accept=accept,
            referer=referer,
            parse_json=False,
            keep_body=True,
            max_bytes=max_bytes,
        )

    def _get_raw(
        self,
        url: str,
        *,
        accept: str = "application/json, text/plain, */*",
        referer: str | None = None,
        parse_json: bool = True,
        keep_body: bool = False,
        max_bytes: int | None = None,
    ) -> dict[str, Any]:
        retrieved_at = datetime.now(tz=UTC).isoformat()
        try:
            host = assert_public_https_locator(url)
        except ExternalEvidenceValidationError as exc:
            return self._trace_error(url, retrieved_at, str(exc), status=None)
        if host not in self._allowed_hosts:
            return self._trace_error(
                url, retrieved_at, f"host not allowlisted: {host}", status=None
            )
        headers = {
            "User-Agent": _BROWSER_UA,
            "Accept": accept,
            "Accept-Language": "en-US,en;q=0.9",
            "Connection": "close",
        }
        if referer:
            ref_host = urlparse(referer).hostname or ""
            if ref_host.lower() not in self._allowed_hosts:
                return self._trace_error(
                    url, retrieved_at, "referer host not allowlisted", status=None
                )
            headers["Referer"] = referer
        req = Request(url, headers=headers, method="GET")
        cap = int(max_bytes) if max_bytes is not None else self._max_bytes
        try:
            with self._opener.open(req, timeout=self._timeout_seconds) as resp:
                raw = resp.read(cap + 1)
                status = int(getattr(resp, "status", 200))
                ctype = str(resp.headers.get("Content-Type", "") or "")
        except HTTPError as exc:
            body = exc.read(cap) if exc.fp is not None else b""
            return self._finish(
                url,
                retrieved_at,
                int(exc.code),
                str(exc.headers.get("Content-Type", "") if exc.headers else ""),
                body,
                parse_json=parse_json,
                error=f"HTTP {exc.code}",
                keep_body=keep_body,
                max_bytes=cap,
            )
        except (URLError, TimeoutError, ExternalEvidenceValidationError) as exc:
            return self._trace_error(url, retrieved_at, str(exc), status=None)
        return self._finish(
            url,
            retrieved_at,
            status,
            ctype,
            raw,
            parse_json=parse_json,
            error=None,
            keep_body=keep_body,
            max_bytes=cap,
        )

    def _finish(
        self,
        url: str,
        retrieved_at: str,
        status: int,
        ctype: str,
        raw: bytes,
        *,
        parse_json: bool,
        error: str | None,
        keep_body: bool = False,
        max_bytes: int | None = None,
    ) -> dict[str, Any]:
        cap = self._max_bytes if max_bytes is None else int(max_bytes)
        truncated = len(raw) > cap
        stored = raw[:cap] if truncated else raw
        text = stored.decode("utf-8", errors="replace") if parse_json or not keep_body else ""
        if keep_body and not parse_json:
            sniff = stored[:200]
            html_shell = _looks_like_html(
                sniff.decode("utf-8", errors="replace"), ctype
            )
        else:
            html_shell = _looks_like_html(text, ctype)
        rate_limited = status == 429
        parsed: Any = None
        parse_error = error
        if truncated:
            parse_error = parse_error or "response exceeds size limit"
        if parse_json and not truncated and not html_shell and 200 <= status < 300:
            lowered = ctype.casefold()
            if lowered and "json" not in lowered and "javascript" not in lowered:
                if not text.lstrip()[:1] in "{[":
                    parse_error = parse_error or "unexpected content type"
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError as exc:
                parse_error = str(exc)
                parsed = None
        ok = (
            200 <= status < 300
            and not truncated
            and not rate_limited
            and (not parse_json or isinstance(parsed, (dict, list)))
        )
        digest = hashlib.sha256(stored).hexdigest() if keep_body and not truncated else None
        trace = FetchTrace(
            url=url.split("?")[0],
            retrieved_at=retrieved_at,
            status=status,
            ok=ok,
            content_type=ctype.split(";")[0].strip(),
            body_chars=len(stored),
            rate_limited=rate_limited,
            truncated=truncated,
            html_shell=html_shell,
            error=parse_error,
        )
        self.traces.append(trace)
        payload: dict[str, Any] = {
            "ok": ok,
            "json": parsed if ok else None,
            "status": status,
            "content_type": ctype,
            "retrieved_at": retrieved_at,
            "truncated": truncated,
        }
        if keep_body:
            payload["body"] = stored if ok else None
            payload["sha256"] = digest
            payload["content_length"] = len(stored)
        return payload

    def _trace_error(
        self, url: str, retrieved_at: str, error: str, *, status: int | None
    ) -> dict[str, Any]:
        trace = FetchTrace(
            url=url.split("?")[0],
            retrieved_at=retrieved_at,
            status=status,
            ok=False,
            content_type="",
            body_chars=0,
            rate_limited=status == 429,
            truncated=False,
            html_shell=False,
            error=error,
        )
        self.traces.append(trace)
        return {
            "ok": False,
            "json": None,
            "status": status,
            "content_type": "",
            "retrieved_at": retrieved_at,
            "body": None,
            "sha256": None,
            "content_length": 0,
            "truncated": False,
        }


def _looks_like_html(text: str, ctype: str) -> bool:
    lowered = ctype.casefold()
    if "html" in lowered:
        return True
    head = text.lstrip()[:200].casefold()
    return head.startswith("<!doctype html") or head.startswith("<html")
