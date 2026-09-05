"""Official issuer filing discovery from an IR index.

Landing-page HTML is not the whole corpus. This module follows allowlisted
hrefs to annual/quarterly/capital documents on the same official hosts.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from datetime import datetime
from typing import Any
from urllib.parse import urljoin, urlparse

from dsp_platform.controlled_document_retrieval.html_text import (
    extract_html_hrefs,
    html_to_visible_text,
)
from dsp_platform.share_count_acquisition.attachments import BytesHttpPort
from dsp_platform.share_count_acquisition.issuer import (
    IssuerEvidenceSource,
    extract_outstanding_observation,
)
from dsp_platform.share_count_acquisition.live_http import MAX_DOCUMENT_BYTES
from dsp_platform.share_count_acquisition.pdf_text import extract_pdf_text
from dsp_platform.share_count_acquisition.universe import ListedEquityInstrument
from dsp_platform.share_count_refresh import ShareCountObservation

__all__ = [
    "discover_issuer_document_urls",
    "fetch_issuer_documents_outstanding",
]

_FILING_HINTS = (
    "annual-report",
    "annual_report",
    "annualreport",
    "integrated-report",
    "quarterly",
    "financial-result",
    "financial_result",
    "financial-statement",
    "finstatement",
    "shareholding",
    "share-capital",
    "share_capital",
    "capital-structure",
    "outstanding",
    "audited",
    "results",
    "filings",
    "investor-presentation",
)
_HIGH_VALUE_HINTS = (
    "finstatement",
    "financial-results",
    "financial_results",
    "share-capital",
    "share_capital",
    "annual-report",
)
_REJECT_HINTS = (
    "press-release",
    "press_release",
    "media-release",
    "transcript",
    "career",
    "blog",
    "podcast",
    "video",
    "javascript:",
    "mailto:",
    "modern-slavery",
)
_BROWSER_ACCEPT = (
    "text/html,application/xhtml+xml,application/pdf;q=0.9,*/*;q=0.8"
)
_ALLOWED_MEDIA = frozenset(
    {
        "application/pdf",
        "application/x-pdf",
        "text/html",
        "application/xhtml+xml",
        "text/plain",
    }
)
_MAX_DOCUMENTS = 12
_MAX_FETCHES = 16
_OLD_YEAR = re.compile(r"/20(?:0\d|1\d)/")


def discover_issuer_document_urls(
    html: str,
    *,
    base_url: str,
    allowed_hosts: frozenset[str],
) -> tuple[str, ...]:
    """Return ranked official document locators from an IR index page."""
    scored: list[tuple[int, str]] = []
    seen: set[str] = set()
    for href, label in extract_html_hrefs(html):
        absolute = _absolutize(href, base_url=base_url, allowed_hosts=allowed_hosts)
        if absolute is None or absolute in seen:
            continue
        blob = f"{absolute} {label}".casefold()
        if any(token in blob for token in _REJECT_HINTS):
            continue
        score = sum(4 for hint in _FILING_HINTS if hint in blob)
        score += sum(8 for hint in _HIGH_VALUE_HINTS if hint in blob)
        if "finstatement" in blob:
            score += 40
        if re.search(r"20\d{2}-20\d{2}/q[1-4]", blob):
            score += 30
        if "quarterly-results" in blob:
            score += 16
        if absolute.casefold().endswith(".pdf"):
            score += 6
        if any(year in blob for year in ("2027", "2026", "2025", "2024")):
            score += 8
        if "/annual/documents/" in blob and "finstatement" not in blob:
            score -= 20
        if _OLD_YEAR.search(blob):
            score -= 40
        if score <= 0:
            continue
        seen.add(absolute)
        scored.append((score, absolute))
    scored.sort(key=lambda item: (-item[0], item[1]))
    return tuple(url for _score, url in scored[:_MAX_DOCUMENTS])


def fetch_issuer_documents_outstanding(
    instrument: ListedEquityInstrument,
    *,
    http: BytesHttpPort,
    retrieved_at: datetime,
) -> ShareCountObservation | None:
    """IR landing page first, then official documents on the same hosts."""
    identity = instrument.identity.normalized()
    queue: list[str] = list(instrument.ir_urls)
    seen: set[str] = set()
    fetches = 0
    while queue and fetches < _MAX_FETCHES:
        url = queue.pop(0)
        if url in seen:
            continue
        host = (urlparse(url).hostname or "").strip().lower()
        if host not in instrument.ir_hosts:
            continue
        seen.add(url)
        document = _retrieve_text(
            url, http=http, allowed_hosts=instrument.ir_hosts
        )
        fetches += 1
        if document is None:
            continue
        observation = extract_outstanding_observation(
            IssuerEvidenceSource(
                identity=identity,
                ir_url=url,
                issuer_name=identity.issuer,
            ),
            document_text=document["text"],
            retrieved_at=retrieved_at,
        )
        if observation is not None:
            return observation
        if document["html"]:
            ranked = discover_issuer_document_urls(
                document["html"],
                base_url=url,
                allowed_hosts=instrument.ir_hosts,
            )
            for child in reversed(ranked[:6]):
                if child not in seen:
                    queue.insert(0, child)
    return None


def _retrieve_text(
    url: str,
    *,
    http: BytesHttpPort,
    allowed_hosts: frozenset[str],
) -> dict[str, str] | None:
    host = (urlparse(url).hostname or "").strip().lower()
    if host not in allowed_hosts:
        return None
    result = http.get_bytes(
        url,
        accept=_BROWSER_ACCEPT,
        max_bytes=MAX_DOCUMENT_BYTES,
    )
    body = result.get("body") if isinstance(result, Mapping) else None
    if not result.get("ok") or not isinstance(body, (bytes, bytearray)):
        return None
    ctype = str(result.get("content_type") or "").split(";", 1)[0].strip().lower()
    if ctype not in _ALLOWED_MEDIA:
        if body.lstrip().startswith(b"%PDF"):
            ctype = "application/pdf"
        else:
            return None
    raw_text = body.decode("utf-8", errors="replace").replace("\x00", "")
    if ctype in {"application/pdf", "application/x-pdf"} or body.lstrip().startswith(
        b"%PDF"
    ):
        text = extract_pdf_text(bytes(body))
        return {"html": "", "text": text} if text.strip() else None
    visible = html_to_visible_text(raw_text) if "html" in ctype else raw_text
    return {"html": raw_text, "text": visible}


def _absolutize(
    href: str, *, base_url: str, allowed_hosts: frozenset[str]
) -> str | None:
    raw = str(href or "").strip()
    if not raw or raw.startswith(("#", "javascript:", "data:", "mailto:")):
        return None
    absolute = urljoin(base_url, raw).split("#", 1)[0]
    parsed = urlparse(absolute)
    if parsed.scheme != "https":
        return None
    host = (parsed.hostname or "").strip().lower()
    if host not in allowed_hosts:
        return None
    return absolute
