"""Deterministic annual-report / annual filing selection. Not a crawler."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from urllib.parse import urljoin

from data_engine.official_research.company_sources import CANONICAL_STATEMENT_BASIS
from data_engine.official_research.nse_primary import NseAnnouncementDocument

__all__ = [
    "AnnualDocumentCandidate",
    "html_document_links",
    "latest_completed_indian_fy",
    "normalize_financial_year",
    "rank_annual_candidates",
    "select_annual_documents",
]

_REJECT = re.compile(
    r"\b(quarter|q[1-4]|press release|presentation|transcript|earnings call|"
    r"newspaper|media article|investor presentation)\b",
    re.I,
)
_HREF = re.compile(r"""href\s*=\s*["']([^"']+)["']""", re.I)
_FY_LABEL = re.compile(r"\bfy\s*[-/]?\s*(\d{4})(?:\s*[-–/]\s*(\d{2,4}))?\b", re.I)
_YEAR_RANGE = re.compile(r"\b(20\d{2})\s*[-–/]\s*(\d{2,4})\b")
_YEAR_ENDED = re.compile(
    r"year ended\s+(\d{1,2}\s+\w+\s+\d{4}|\d{4}-\d{2}-\d{2})",
    re.I,
)


@dataclass(frozen=True, slots=True)
class AnnualDocumentCandidate:
    url: str
    title: str
    kind: str
    score: int
    financial_year: int | None
    prefers_consolidated: bool
    as_of: date | None
    source: str


def latest_completed_indian_fy(today: date | None = None) -> int:
    """FY ending 31 March. April–March year-end convention."""
    day = today or date.today()
    if day.month >= 4:
        return day.year
    return day.year - 1


def normalize_financial_year(text: str) -> int | None:
    """Map FY2026 / 2025-26 / year ended 31 March 2026 to the March year-end year."""
    raw = str(text or "")
    fy = _FY_LABEL.search(raw)
    if fy is not None:
        start = int(fy.group(1))
        second = fy.group(2)
        if second:
            end = int(second)
            if end < 100:
                end = (start // 100) * 100 + end
            return end
        ended = _YEAR_ENDED.search(raw)
        if ended is not None:
            year = _four_digit_year(ended.group(1))
            if year is not None:
                return year
        return start
    ended = _YEAR_ENDED.search(raw)
    if ended is not None:
        year = _four_digit_year(ended.group(1))
        if year is not None:
            return year
    ranged = _YEAR_RANGE.search(raw)
    if fy is None and ranged is not None:
        start = int(ranged.group(1))
        end = int(ranged.group(2))
        if end < 100:
            end = (start // 100) * 100 + end
        if end in {start, start + 1}:
            return end
    return None


def _four_digit_year(raw: str) -> int | None:
    match = re.search(r"(20\d{2})", raw)
    if match is None:
        return None
    return int(match.group(1))


def html_document_links(
    html: str,
    *,
    base_url: str,
    allow_url,
) -> tuple[tuple[str, str], ...]:
    """Collect same-page hrefs. Not recursive."""
    found: list[tuple[str, str]] = []
    seen: set[str] = set()
    for href in _HREF.findall(html or ""):
        absolute = urljoin(base_url, href.strip())
        if not absolute.lower().startswith("http"):
            continue
        if absolute.lower().startswith(("javascript:", "mailto:", "data:")):
            continue
        if ".pdf" not in absolute.lower():
            continue
        if absolute in seen:
            continue
        if not allow_url(absolute):
            continue
        label = href.split("/")[-1]
        seen.add(absolute)
        found.append((absolute, label))
    return tuple(found)


def rank_annual_candidates(
    items: tuple[AnnualDocumentCandidate, ...],
    *,
    financial_year: int | None = None,
    statement_basis: str = CANONICAL_STATEMENT_BASIS,
) -> tuple[AnnualDocumentCandidate, ...]:
    wanted = financial_year or latest_completed_indian_fy()
    ranked = list(items)
    ranked.sort(
        key=lambda item: (
            0 if item.financial_year == wanted else 1,
            0 if item.prefers_consolidated == (statement_basis == "consolidated") else 1,
            -item.score,
            item.title.lower(),
        )
    )
    return tuple(ranked)


def select_annual_documents(
    announcements: tuple[NseAnnouncementDocument, ...],
    *,
    ir_links: tuple[tuple[str, str], ...] = (),
    financial_year: int | None = None,
    statement_basis: str = CANONICAL_STATEMENT_BASIS,
    limit: int = 3,
) -> tuple[AnnualDocumentCandidate, ...]:
    """Rank annual documents. Quarterly / presentations are excluded."""
    candidates: list[AnnualDocumentCandidate] = []
    for item in announcements:
        candidate = _from_announcement(item)
        if candidate is not None:
            candidates.append(candidate)
    for url, label in ir_links:
        candidate = _from_label(url, label, source="company_ir")
        if candidate is not None:
            candidates.append(candidate)
    ranked = rank_annual_candidates(
        tuple(candidates),
        financial_year=financial_year,
        statement_basis=statement_basis,
    )
    return ranked[:limit]


def _from_announcement(item: NseAnnouncementDocument) -> AnnualDocumentCandidate | None:
    return _from_label(
        item.url,
        item.title,
        source="nse_announcement",
        kind=item.kind,
        as_of=item.as_of,
    )


def _from_label(
    url: str,
    title: str,
    *,
    source: str,
    kind: str | None = None,
    as_of: date | None = None,
) -> AnnualDocumentCandidate | None:
    filename = url.rstrip("/").rsplit("/", 1)[-1]
    score_blob = f"{title} {filename}"
    fy_blob = f"{title} {url}"
    normalized = re.sub(r"[-_./]+", " ", score_blob.lower())
    if _REJECT.search(normalized) and not re.search(
        r"annual report|integrated annual", normalized
    ):
        return None
    score, kind_name = _score(score_blob)
    if score <= 0:
        return None
    prefers = "consolidated" in normalized
    return AnnualDocumentCandidate(
        url=url,
        title=title,
        kind=kind or kind_name,
        score=score,
        financial_year=normalize_financial_year(fy_blob),
        prefers_consolidated=prefers,
        as_of=as_of,
        source=source,
    )


def _score(blob: str) -> tuple[int, str]:
    lowered = re.sub(r"[-_./]+", " ", blob.lower())
    if "integrated annual report" in lowered:
        return 100, "annual_report"
    if "annual report" in lowered:
        return 90, "annual_report"
    if "audited consolidated" in lowered and "financial" in lowered:
        return 80, "annual_report"
    if "audited financial statement" in lowered:
        return 70, "annual_report"
    if "year ended" in lowered and "quarter" not in lowered:
        return 50, "financial_results"
    return 0, "other"
