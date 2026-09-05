"""Generic NSE corporate-action / announcement acquisition.

Not a share-count observation source. Live connector remains PENDING for
promotion. No issuer/ticker hardcodes.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from dsp_platform.share_count_acquisition.http import JsonHttpPort
from dsp_platform.share_count_acquisition.models import (
    ExchangeAcquisitionRequest,
    ExchangeAcquisitionResult,
    nse_date,
)

__all__ = ["acquire_nse_disclosures"]

_CA = "https://www.nseindia.com/api/corporates-corporateActions"
_ANN = "https://www.nseindia.com/api/corporate-announcements"
_REFERER = "https://www.nseindia.com/companies-listing/corporate-filings-actions"


def acquire_nse_disclosures(
    request: ExchangeAcquisitionRequest,
    http: JsonHttpPort,
) -> ExchangeAcquisitionResult:
    identity = request.identity.normalized()
    if not identity.symbol or not identity.isin:
        return _empty(request, exhausted=False, reason="identity requires symbol and ISIN")
    start = nse_date(request.start)
    end = nse_date(request.end)
    ca_url = (
        f"{_CA}?index=equities&symbol={identity.symbol}"
        f"&from_date={start}&to_date={end}"
    )
    ann_url = (
        f"{_ANN}?index=equities&symbol={identity.symbol}"
        f"&from_date={start}&to_date={end}"
    )
    ca_raw = http.get_json(ca_url, referer=_REFERER)
    ann_raw = http.get_json(ann_url, referer=_REFERER)
    actions, ca_truncated, ca_ok = _records(ca_raw)
    anns, ann_truncated, ann_ok = _records(ann_raw)
    truncated = ca_truncated or ann_truncated
    exhausted = ca_ok and ann_ok and not truncated
    matched_actions = tuple(
        item for item in actions if _identity_ok(item, identity.symbol, identity.isin)
    )
    matched_anns = tuple(
        item for item in anns if _identity_ok(item, identity.symbol, identity.isin)
    )
    return ExchangeAcquisitionResult(
        identity=identity,
        source_id="nse_public_api_connector",
        requested_start=request.start,
        requested_end=request.end,
        retrieved_at=request.retrieved_at,
        corporate_actions=matched_actions,
        announcements=matched_anns,
        pagination_exhausted=exhausted,
        date_range_explicit=True,
        truncated=truncated,
        page_count=2,
        record_count=len(matched_actions) + len(matched_anns),
        source_url=ca_url,
        evidence_reference=(
            f"NSE corporates-corporateActions and corporate-announcements "
            f"for {identity.isin} from {request.start.isoformat()} to "
            f"{request.end.isoformat()}"
        ),
        pages_fetched=2,
    )


def _empty(
    request: ExchangeAcquisitionRequest, *, exhausted: bool, reason: str
) -> ExchangeAcquisitionResult:
    identity = request.identity.normalized()
    return ExchangeAcquisitionResult(
        identity=identity,
        source_id="nse_public_api_connector",
        requested_start=request.start,
        requested_end=request.end,
        retrieved_at=request.retrieved_at,
        corporate_actions=(),
        announcements=(),
        pagination_exhausted=exhausted,
        date_range_explicit=True,
        truncated=not exhausted,
        page_count=0,
        record_count=0,
        source_url="",
        evidence_reference=reason,
        pages_fetched=0,
    )


def _records(
    raw: Mapping[str, Any] | list[Any] | None,
) -> tuple[tuple[Mapping[str, Any], ...], bool, bool]:
    if raw is None:
        return (), False, False
    if isinstance(raw, list):
        items = tuple(item for item in raw if isinstance(item, Mapping))
        return items, False, True
    if isinstance(raw, Mapping):
        nested = None
        for key in ("Table", "data", "records"):
            value = raw.get(key)
            if isinstance(value, list):
                nested = value
                break
        if nested is None:
            return (), bool(raw.get("truncated")), False
        items = tuple(item for item in nested if isinstance(item, Mapping))
        truncated = bool(raw.get("truncated"))
        if raw.get("next") not in (None, "", False):
            truncated = True
        return items, truncated, not truncated
    return (), False, False


def _identity_ok(item: Mapping[str, Any], symbol: str, isin: str) -> bool:
    got_symbol = str(item.get("symbol") or item.get("sm_name") or "").strip().upper()
    got_isin = str(item.get("isin") or item.get("sm_isin") or "").strip().upper()
    if got_isin and got_isin != isin:
        return False
    if got_symbol and got_symbol == symbol:
        return True
    return bool(got_isin) and got_isin == isin
