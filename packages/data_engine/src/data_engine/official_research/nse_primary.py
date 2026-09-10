"""Official NSE primary financial / share / CA evidence.

Bounded to NSE public JSON endpoints already used for EOD (same transport).
Not a web crawler. LastPrice is never treated as EOD. Secondary/vendor
hosts cannot appear here.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any
from urllib.parse import quote

from data_engine.official_research.currentness import CapitalEvent
from data_engine.official_research.extraction import (
    ExtractedField,
    attack_corporate_actions,
)
from data_engine.official_research.nse_eod import (
    NSE_ALL_REPORTS,
    NseHttpTransport,
    parse_nse_calendar_date,
)
from data_engine.official_research.semantics import semantic_field_status
from data_engine.security_master.models import SecurityListing

__all__ = [
    "NSE_ANNOUNCEMENTS_URL",
    "NSE_FINANCIAL_RESULTS_URL",
    "NSE_QUOTE_EQUITY_URL",
    "NSE_SHAREHOLDING_URL",
    "NseAnnouncementDocument",
    "NsePrimaryBundle",
    "NsePrimaryEvidenceService",
    "parse_announcement_documents",
    "parse_financial_results",
    "parse_quote_equity_shares",
    "parse_shareholding_shares",
]

NSE_QUOTE_EQUITY_URL = "https://www.nseindia.com/api/quote-equity"
NSE_FINANCIAL_RESULTS_URL = "https://www.nseindia.com/api/corporates-financial-results"
NSE_ANNOUNCEMENTS_URL = "https://www.nseindia.com/api/corporate-announcements"
NSE_SHAREHOLDING_URL = "https://www.nseindia.com/api/corporate-shareholding-pattern"

_QUOTE_LAST_PRICE_KEYS = frozenset(
    {"lastprice", "last_price", "lastp", "ltp", "lasttradedprice"}
)

# Explicit particulars only. Operating profit is not EBIT. PPE purchase is not capex.
_PARTICULAR_LABELS: dict[str, tuple[str, ...]] = {
    "revenue": (
        "revenuefromoperations",
        "revenue from operations",
        "total revenue from operations",
    ),
    "net_income": (
        "profitaftertax",
        "profit after tax",
        "profit for the year",
        "profit for the period",
        "profitfortheyear",
        "profitfortheperiod",
        "net income",
    ),
    "equity": (
        "totalequity",
        "total equity",
        "shareholdersequity",
        "shareholders equity",
        "equityattributabletoowners",
        "equity attributable to owners of the company",
    ),
    "cfo": (
        "netcashflowsfromoperatingactivities",
        "net cash from operating activities",
        "net cash generated from operating activities",
        "net cash from operating activities",
        "cfo",
    ),
    "capex": ("capitalexpenditure", "capital expenditure", "capex"),
    "ebit": ("ebit",),
    "operating_profit": ("operatingprofit", "operating profit"),
    "cash": ("cashandcashequivalents", "cash and cash equivalents"),
    "debt": ("borrowings", "total borrowings"),
}

_FORBIDDEN_EQUITY_LABELS = frozenset(
    {"equitysharecapital", "equity share capital", "paidupcapital"}
)
_ANNUAL_HINTS = ("annual", "yearly", "year ended", "yearended", "fy ")
_QUARTER_HINTS = (
    "quarter",
    "q1",
    "q2",
    "q3",
    "q4",
    "quarterly",
    "half year",
    "half-year",
)
_CRORE_HINTS = ("crore", "crs", "rs. cr", "rs cr")
_LAKH_HINTS = ("lakh", "lac")


@dataclass(frozen=True, slots=True)
class NseAnnouncementDocument:
    title: str
    url: str
    as_of: date | None
    kind: str


@dataclass(frozen=True, slots=True)
class NsePrimaryBundle:
    fields: dict[str, ExtractedField]
    capital_events: tuple[CapitalEvent, ...]
    announcements_searched: bool
    last_price_ignored: bool
    source_urls: dict[str, str]
    issues: tuple[str, ...]
    statement_basis: str | None = None
    unit_scale: str | None = None
    announcement_documents: tuple[NseAnnouncementDocument, ...] = ()
    announcement_payload: object | None = None


def _norm(label: str) -> str:
    return "".join(
        ch for ch in str(label or "").lower() if ch.isalnum() or ch.isspace()
    ).strip()


def _compact(label: str) -> str:
    return "".join(ch for ch in str(label or "").lower() if ch.isalnum())


def _json_loads(payload: bytes) -> Any:
    try:
        return json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise LookupError("NSE primary payload was not JSON") from exc


def _decimal(raw: Any) -> str | None:
    if raw is None or raw == "":
        return None
    text = str(raw).strip().replace(",", "")
    if not text or text in {"-", "NA", "N.A.", "nil"}:
        return None
    try:
        value = Decimal(text)
    except (InvalidOperation, ValueError):
        return None
    return format(value, "f")


def _is_annual(period_text: str) -> bool | None:
    lowered = str(period_text or "").lower()
    if any(hint in lowered for hint in _QUARTER_HINTS):
        return False
    if any(hint in lowered for hint in _ANNUAL_HINTS):
        return True
    return None


def _statement_basis(blob: Any) -> str | None:
    text = json.dumps(blob).lower() if not isinstance(blob, str) else blob.lower()
    has_consolidated = "consolidated" in text
    has_standalone = "standalone" in text
    if has_consolidated and not has_standalone:
        return "consolidated"
    if has_standalone and not has_consolidated:
        return "standalone"
    if has_consolidated and has_standalone:
        return None
    return None


def _unit_multiplier(blob: Any) -> tuple[Decimal, str] | None:
    text = json.dumps(blob).lower() if not isinstance(blob, str) else blob.lower()
    if any(hint in text for hint in _CRORE_HINTS):
        return Decimal("10000000"), "crore_to_actual"
    if any(hint in text for hint in _LAKH_HINTS):
        return Decimal("100000"), "lakh_to_actual"
    if "million" in text:
        return Decimal("1000000"), "million_to_actual"
    return None


def _walk_particulars(payload: Any) -> list[tuple[str, Any]]:
    found: list[tuple[str, Any]] = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            key_text = str(key)
            if key_text.lower() in {
                "particulars",
                "particular",
                "name",
                "item",
                "lineitem",
                "concept",
            }:
                continue
            if isinstance(value, (dict, list)):
                found.extend(_walk_particulars(value))
            else:
                found.append((key_text, value))
            if key_text.lower() in {"particulars", "particular"} and isinstance(
                value, str
            ):
                nested_val = (
                    payload.get("value")
                    or payload.get("amount")
                    or payload.get("consolidated")
                )
                if nested_val is not None:
                    found.append((value, nested_val))
        name = (
            payload.get("particulars")
            or payload.get("particular")
            or payload.get("name")
        )
        amount = (
            payload.get("value") or payload.get("amount") or payload.get("consolidated")
        )
        if (
            isinstance(name, str)
            and amount is not None
            and not isinstance(amount, (dict, list))
        ):
            found.append((name, amount))
    elif isinstance(payload, list):
        for item in payload:
            found.extend(_walk_particulars(item))
    return found


def parse_quote_equity_shares(
    payload: Any,
    *,
    isin: str,
    ticker: str,
) -> tuple[ExtractedField | None, bool, str | None]:
    """issuedSize only, and only after ISIN match. lastPrice is ignored."""
    if not isinstance(payload, dict):
        return (
            None,
            _payload_has_last_price(payload),
            "quote-equity JSON is not an object",
        )
    info = payload.get("info") if isinstance(payload.get("info"), dict) else {}
    payload_isin = str(info.get("isin") or payload.get("isin") or "").strip().upper()
    payload_symbol = (
        str(info.get("symbol") or payload.get("symbol") or "").strip().upper()
    )
    last_price_present = _payload_has_last_price(payload)
    if payload_isin and payload_isin != isin.upper():
        return None, last_price_present, "quote-equity ISIN mismatch"
    if payload_symbol and payload_symbol != ticker.upper():
        return None, last_price_present, "quote-equity symbol mismatch"
    issued = info.get("issuedSize")
    if issued is None:
        security = (
            payload.get("securityInfo")
            if isinstance(payload.get("securityInfo"), dict)
            else {}
        )
        issued = security.get("issuedSize")
    value = _decimal(issued)
    if value is None:
        return None, last_price_present, "issuedSize unavailable"
    # lastUpdateTime is a quote clock, not shares as_of — leave as_of empty.
    return (
        ExtractedField(
            field="shares_outstanding",
            value=value,
            as_of=None,
            locator="info.issuedSize",
            semantic_status="VERIFIED",
        ),
        last_price_present,
        None,
    )


def parse_shareholding_shares(payload: Any, *, ticker: str) -> ExtractedField | None:
    rows: list[dict[str, Any]] = []
    if isinstance(payload, list):
        rows = [item for item in payload if isinstance(item, dict)]
    elif isinstance(payload, dict):
        for key in ("data", "shareholdingPattern", "dataList"):
            maybe = payload.get(key)
            if isinstance(maybe, list):
                rows = [item for item in maybe if isinstance(item, dict)]
                break
        if not rows:
            rows = [payload]
    dated: list[ExtractedField] = []
    for row in rows:
        symbol = str(row.get("symbol") or row.get("symbolName") or "").strip().upper()
        if symbol and symbol != ticker.upper():
            continue
        as_of = (
            parse_nse_calendar_date(str(row.get("date") or ""))
            or parse_nse_calendar_date(str(row.get("asOnDate") or ""))
            or parse_nse_calendar_date(str(row.get("recordDate") or ""))
            or parse_nse_calendar_date(str(row.get("as_of") or ""))
        )
        shares = None
        for key in (
            "totalNoOfShares",
            "total_no_of_shares",
            "noOfShares",
            "totalShares",
            "total_shares",
            "shares",
        ):
            shares = _decimal(row.get(key))
            if shares is not None:
                locator = key
                break
        else:
            locator = "unknown"
        if shares is None or as_of is None:
            continue
        dated.append(
            ExtractedField(
                field="shares_outstanding",
                value=shares,
                as_of=as_of,
                locator=locator,
                semantic_status="VERIFIED",
            )
        )
    if not dated:
        return None
    dated.sort(key=lambda item: item.as_of or date.min, reverse=True)
    return dated[0]


def parse_financial_results(
    payload: Any,
    *,
    ticker: str,
) -> tuple[dict[str, ExtractedField], str | None, str | None, str | None]:
    """Annual labeled fields only. Quarterly and unlabeled units stay UNKNOWN."""
    candidates: list[Any] = []
    if isinstance(payload, list):
        candidates = list(payload)
    elif isinstance(payload, dict):
        for key in ("data", "results", "financialResults"):
            maybe = payload.get(key)
            if isinstance(maybe, list):
                candidates = list(maybe)
                break
        if not candidates:
            candidates = [payload]
    annual_rows: list[Any] = []
    for row in candidates:
        if not isinstance(row, dict):
            continue
        symbol = str(row.get("symbol") or row.get("symbolName") or "").strip().upper()
        if symbol and symbol != ticker.upper():
            continue
        period_blob = " ".join(
            str(row.get(key) or "")
            for key in (
                "period",
                "relatingTo",
                "fromTo",
                "fromDate",
                "toDate",
                "reDate",
            )
        )
        annual = _is_annual(period_blob) if period_blob.strip() else None
        if annual is False:
            continue
        if annual is None and period_blob.strip():
            continue
        if annual is None and not period_blob.strip():
            # Unlabeled period cannot be treated as annual.
            continue
        annual_rows.append(row)
    if not annual_rows:
        return {}, None, None, "no annual NSE financial result row"
    row = annual_rows[0]
    basis = _statement_basis(row)
    if basis is None:
        return {}, None, None, "statement basis (standalone vs consolidated) unlabeled"
    unit = _unit_multiplier(row)
    if unit is None:
        return {}, basis, None, "NSE result unit (actual/crore/lakh) unlabeled"
    multiplier, unit_scale = unit
    as_of = (
        parse_nse_calendar_date(str(row.get("toDate") or ""))
        or parse_nse_calendar_date(str(row.get("reDate") or ""))
        or parse_nse_calendar_date(str(row.get("to_date") or ""))
        or _period_end_from_range(str(row.get("fromTo") or ""))
    )
    fields: dict[str, ExtractedField] = {}
    for label, raw_value in _walk_particulars(row):
        compact = _compact(label)
        if compact in _FORBIDDEN_EQUITY_LABELS:
            continue
        for field, allowed in _PARTICULAR_LABELS.items():
            if (
                compact not in {_compact(item) for item in allowed}
                and _norm(label) not in allowed
            ):
                continue
            semantic = semantic_field_status(
                requested_field=field, document_label=label
            )
            if semantic != "VERIFIED":
                fields[field] = ExtractedField(
                    field=field,
                    value="",
                    as_of=as_of,
                    locator=label,
                    semantic_status="UNKNOWN",
                )
                break
            amount = _decimal(raw_value)
            if amount is None:
                break
            scaled = Decimal(amount) * multiplier
            fields[field] = ExtractedField(
                field=field,
                value=format(scaled, "f"),
                as_of=as_of,
                locator=label,
                semantic_status="VERIFIED",
            )
            break
    if not fields:
        return (
            {},
            basis,
            unit_scale,
            "no explicitly labeled annual financial particulars",
        )
    return fields, basis, unit_scale, None


def _period_end_from_range(raw: str) -> date | None:
    text = str(raw or "").strip()
    if " to " in text.lower():
        tail = text.lower().split(" to ")[-1]
        return parse_nse_calendar_date(tail)
    return parse_nse_calendar_date(text)


def _payload_has_last_price(payload: Any) -> bool:
    if isinstance(payload, dict):
        for key, value in payload.items():
            if _compact(str(key)) in _QUOTE_LAST_PRICE_KEYS:
                return True
            if _payload_has_last_price(value):
                return True
    elif isinstance(payload, list):
        return any(_payload_has_last_price(item) for item in payload)
    return False


def _announcement_text(payload: Any) -> str:
    rows: list[dict[str, Any]] = []
    if isinstance(payload, list):
        rows = [item for item in payload if isinstance(item, dict)]
    elif isinstance(payload, dict):
        maybe = payload.get("data") or payload.get("announcements")
        if isinstance(maybe, list):
            rows = [item for item in maybe if isinstance(item, dict)]
    parts: list[str] = []
    for row in rows:
        desc = str(row.get("desc") or row.get("subject") or row.get("headline") or "")
        dt = str(row.get("an_dt") or row.get("date") or "")
        if desc:
            as_of = parse_nse_calendar_date(dt)
            dated = f"as_of: {as_of.isoformat()}" if as_of else ""
            parts.append(f"{dated}\n{desc}".strip())
    return "\n".join(parts)


def parse_announcement_documents(payload: Any) -> tuple[NseAnnouncementDocument, ...]:
    rows: list[dict[str, Any]] = []
    if isinstance(payload, list):
        rows = [item for item in payload if isinstance(item, dict)]
    elif isinstance(payload, dict):
        maybe = payload.get("data") or payload.get("announcements")
        if isinstance(maybe, list):
            rows = [item for item in maybe if isinstance(item, dict)]
    found: list[NseAnnouncementDocument] = []
    for row in rows:
        title = str(row.get("desc") or row.get("subject") or row.get("headline") or "").strip()
        url = str(
            row.get("attchmntFile")
            or row.get("attachment")
            or row.get("attchmntfile")
            or ""
        ).strip()
        if not url or url in {"-", "N/A", "null", "None"}:
            continue
        if not url.lower().startswith("http"):
            continue
        as_of = parse_nse_calendar_date(
            str(row.get("an_dt") or row.get("date") or "")
        )
        lowered = title.lower()
        kind = "other"
        if "shareholding" in lowered:
            kind = "shareholding"
        elif "annual report" in lowered or "integrated report" in lowered:
            kind = "annual_report"
        elif (
            "financial result" in lowered
            or "audited" in lowered
            or "year ended" in lowered
        ):
            kind = "financial_results"
        elif any(
            token in lowered
            for token in (
                "buyback",
                "bonus",
                "split",
                "rights",
                "qip",
                "fpo",
                "esop",
            )
        ):
            kind = "corporate_action"
        found.append(
            NseAnnouncementDocument(title=title, url=url, as_of=as_of, kind=kind)
        )
    return tuple(found)


class NsePrimaryEvidenceService:
    """Fetch official NSE JSON for shares, filings-style results, and CA titles."""

    def __init__(self, transport: NseHttpTransport, *, mode: str = "LIVE") -> None:
        self._transport = transport
        self._mode = mode

    def fetch(self, listing: SecurityListing) -> NsePrimaryBundle:
        if listing.mic != "XNSE":
            return NsePrimaryBundle(
                fields={},
                capital_events=(),
                announcements_searched=False,
                last_price_ignored=True,
                source_urls={},
                issues=("BSE venue is separate; NSE primary MVP requires MIC=XNSE",),
            )
        symbol = quote(listing.ticker, safe="")
        issues: list[str] = []
        urls: dict[str, str] = {}
        fields: dict[str, ExtractedField] = {}
        events: tuple[CapitalEvent, ...] = ()
        announcements_searched = False
        last_price_ignored = True
        statement_basis = None
        unit_scale = None
        announcement_documents: tuple[NseAnnouncementDocument, ...] = ()
        announcement_payload: object | None = None

        quote_url = f"{NSE_QUOTE_EQUITY_URL}?symbol={symbol}"
        urls["quote_equity"] = quote_url
        try:
            quote_payload = _json_loads(
                self._transport.get_bytes(quote_url, referer=NSE_ALL_REPORTS)
            )
            extracted, last_price_ignored, quote_issue = parse_quote_equity_shares(
                quote_payload, isin=listing.isin, ticker=listing.ticker
            )
            if quote_issue:
                issues.append(quote_issue)
            # issuedSize without as_of cannot be VERIFIED; keep only as discovery.
            if extracted is not None and extracted.as_of is not None:
                fields["shares_outstanding"] = extracted
            elif extracted is not None:
                issues.append("issuedSize present but shares as_of unlabeled")
        except LookupError as exc:
            issues.append(str(exc))

        hold_url = f"{NSE_SHAREHOLDING_URL}?index=equities&symbol={symbol}"
        urls["shareholding"] = hold_url
        try:
            hold_payload = _json_loads(
                self._transport.get_bytes(hold_url, referer=NSE_ALL_REPORTS)
            )
            hold = parse_shareholding_shares(hold_payload, ticker=listing.ticker)
            if hold is not None:
                fields["shares_outstanding"] = hold
        except LookupError as exc:
            issues.append(str(exc))

        result_url = (
            f"{NSE_FINANCIAL_RESULTS_URL}?index=equities&symbol={symbol}&period=Annual"
        )
        urls["financial_results"] = result_url
        try:
            result_payload = _json_loads(
                self._transport.get_bytes(result_url, referer=NSE_ALL_REPORTS)
            )
            parsed, statement_basis, unit_scale, result_issue = parse_financial_results(
                result_payload, ticker=listing.ticker
            )
            fields.update(parsed)
            if result_issue:
                issues.append(result_issue)
        except LookupError as exc:
            issues.append(str(exc))

        ann_url = f"{NSE_ANNOUNCEMENTS_URL}?index=equities&symbol={symbol}"
        urls["announcements"] = ann_url
        try:
            ann_payload = _json_loads(
                self._transport.get_bytes(ann_url, referer=NSE_ALL_REPORTS)
            )
            events = attack_corporate_actions(_announcement_text(ann_payload))
            announcement_documents = parse_announcement_documents(ann_payload)
            announcement_payload = ann_payload
            announcements_searched = True
        except LookupError as exc:
            issues.append(str(exc))

        return NsePrimaryBundle(
            fields=fields,
            capital_events=events,
            announcements_searched=announcements_searched,
            last_price_ignored=last_price_ignored,
            source_urls=urls,
            issues=tuple(issues),
            statement_basis=statement_basis,
            unit_scale=unit_scale,
            announcement_documents=announcement_documents,
            announcement_payload=announcement_payload,
        )
