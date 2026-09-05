"""Generic BSE announcement acquisition.

Not an outstanding-share observation source. Used as official disclosure
cross-check after DSP attestation. Live connector remains PENDING.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from dsp_platform.share_count_acquisition.http import JsonHttpPort
from dsp_platform.share_count_acquisition.models import (
    ExchangeAcquisitionRequest,
    ExchangeAcquisitionResult,
    bse_date,
)

__all__ = ["acquire_bse_disclosures"]

_PAGE_SIZE = 50
_URL = (
    "https://api.bseindia.com/BseIndiaAPI/api/AnnSubCategoryGetData/w"
    "?pageno={page}&strCat=-1&strPrevDate={start}&strScrip={scrip}"
    "&strSearch=P&strToDate={end}&strType=C&subcategory="
)
_REFERER = "https://www.bseindia.com/corporates/ann.html"
_MAX_PAGES = 20


def acquire_bse_disclosures(
    request: ExchangeAcquisitionRequest,
    http: JsonHttpPort,
) -> ExchangeAcquisitionResult:
    identity = request.identity.normalized()
    scrip = str(request.scrip_code or "").strip()
    if not scrip or not identity.isin:
        return ExchangeAcquisitionResult(
            identity=identity,
            source_id="bse_public_api_connector",
            requested_start=request.start,
            requested_end=request.end,
            retrieved_at=request.retrieved_at,
            corporate_actions=(),
            announcements=(),
            pagination_exhausted=False,
            date_range_explicit=True,
            truncated=True,
            page_count=0,
            record_count=0,
            source_url="",
            evidence_reference="BSE acquisition requires scrip code and ISIN",
            pages_fetched=0,
        )
    start = bse_date(request.start)
    end = bse_date(request.end)
    pages: list[Mapping[str, Any]] = []
    truncated = False
    for page in range(1, _MAX_PAGES + 1):
        url = _URL.format(page=page, start=start, scrip=scrip, end=end)
        raw = http.get_json(url, referer=_REFERER)
        items = _table(raw)
        if raw is None:
            truncated = True
            break
        pages.extend(
            item
            for item in items
            if _identity_ok(
                item,
                scrip,
                identity.isin,
                equivalent_isins=request.equivalent_isins,
            )
        )
        if len(items) < _PAGE_SIZE:
            break
        if page == _MAX_PAGES:
            truncated = True
    first_url = _URL.format(page=1, start=start, scrip=scrip, end=end)
    traces = _traces(http)
    pages_fetched = 0 if not pages and truncated else (
        (len(pages) // _PAGE_SIZE) + (1 if len(pages) % _PAGE_SIZE else 0) or 1
    )
    return ExchangeAcquisitionResult(
        identity=identity,
        source_id="bse_public_api_connector",
        requested_start=request.start,
        requested_end=request.end,
        retrieved_at=request.retrieved_at,
        corporate_actions=(),
        announcements=tuple(pages),
        pagination_exhausted=not truncated,
        date_range_explicit=True,
        truncated=truncated,
        page_count=pages_fetched,
        record_count=len(pages),
        source_url=first_url,
        evidence_reference=(
            f"BSE AnnSubCategoryGetData scrip={scrip} ISIN={identity.isin} "
            f"from {request.start.isoformat()} to {request.end.isoformat()}"
        ),
        pages_fetched=pages_fetched,
        http_status=_last_status(traces),
        rate_limited=any(
            bool(row.get("rate_limited")) for row in traces if isinstance(row, dict)
        ),
        fetch_traces=traces,
        equivalent_isins=request.equivalent_isins,
    )


def _identity_ok(
    item: Mapping[str, Any],
    scrip: str,
    isin: str,
    *,
    equivalent_isins: tuple[str, ...] = (),
) -> bool:
    got_isin = str(item.get("ISIN") or item.get("isin") or "").strip().upper()
    got_scrip = str(
        item.get("SCRIP_CD") or item.get("scrip_cd") or item.get("scrip_code") or ""
    ).strip()
    accepted = {isin, *(str(value).strip().upper() for value in equivalent_isins)}
    accepted.discard("")
    if got_isin and got_isin not in accepted:
        return False
    if got_scrip and got_scrip != scrip:
        return False
    return True


def _traces(http: JsonHttpPort) -> tuple[dict[str, Any], ...]:
    public = getattr(http, "public_traces", None)
    if callable(public):
        rows = public()
        if isinstance(rows, tuple):
            return rows
    return ()


def _last_status(traces: tuple[dict[str, Any], ...]) -> int | None:
    for row in reversed(traces):
        status = row.get("status")
        if isinstance(status, int):
            return status
    return None


def _table(raw: Mapping[str, Any] | list[Any] | None) -> list[Mapping[str, Any]]:
    if raw is None:
        return []
    if isinstance(raw, list):
        return [item for item in raw if isinstance(item, Mapping)]
    if isinstance(raw, Mapping):
        nested = raw.get("Table")
        if isinstance(nested, list):
            return [item for item in nested if isinstance(item, Mapping)]
    return []
