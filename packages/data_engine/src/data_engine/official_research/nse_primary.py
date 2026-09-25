"""Official NSE primary financial / share / CA evidence.

Bounded to NSE public JSON endpoints already used for EOD (same transport).
Not a web crawler. LastPrice is never treated as EOD. Secondary/vendor
hosts cannot appear here.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any
from urllib.parse import quote

from data_engine.official_research.currentness import CapitalEvent
from data_engine.official_research.extraction import (
    ExtractedField,
    attack_corporate_actions,
    esop_changes_outstanding,
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
    "NSE_ANNUAL_REPORTS_URL",
    "NSE_FINANCIAL_RESULTS_URL",
    "NSE_QUOTE_EQUITY_URL",
    "NSE_SHAREHOLDING_URL",
    "NSE_SHAREHOLDING_MASTER_URL",
    "NSE_CORPORATE_ACTIONS_URL",
    "NseAnnouncementDocument",
    "NsePrimaryBundle",
    "NsePrimaryEvidenceService",
    "parse_announcement_capital_events",
    "parse_announcement_documents",
    "parse_annual_report_documents",
    "parse_corporate_action_calendar",
    "parse_financial_result_documents",
    "parse_financial_results",
    "parse_quote_equity_shares",
    "parse_shareholding_documents",
    "parse_shareholding_shares",
    "extract_nse_api_field",
]

NSE_QUOTE_EQUITY_URL = "https://www.nseindia.com/api/quote-equity"
NSE_FINANCIAL_RESULTS_URL = "https://www.nseindia.com/api/corporates-financial-results"
NSE_ANNOUNCEMENTS_URL = "https://www.nseindia.com/api/corporate-announcements"
NSE_ANNUAL_REPORTS_URL = "https://www.nseindia.com/api/annual-reports"
NSE_SHAREHOLDING_URL = "https://www.nseindia.com/api/corporate-share-holdings-master"
NSE_SHAREHOLDING_MASTER_URL = NSE_SHAREHOLDING_URL
NSE_SHAREHOLDING_PATTERN_URL = (
    "https://www.nseindia.com/api/corporate-shareholding-pattern"
)
NSE_CORPORATE_ACTIONS_URL = "https://www.nseindia.com/api/corporates-corporateActions"

_QUOTE_LAST_PRICE_KEYS = frozenset(
    {"lastprice", "last_price", "lastp", "ltp", "lasttradedprice"}
)

# Explicit P&L/JSON particulars only. Operating profit is not EBIT.
# These NSE result rows do not expose cash-flow PPE. DCF capex is taken from
# XBRL investing PPE concepts or classified cash-flow extraction, not from
# unlabeled JSON particulars.
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
    "total_assets": ("totalassets", "total assets"),
    "total_liabilities": ("totalliabilities", "total liabilities"),
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
    source: str = "nse_announcement"
    isin: str | None = None
    document_id: str | None = None
    period: str | None = None
    statement_basis: str | None = None


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
    if any(hint in lowered for hint in _ANNUAL_HINTS):
        return True
    if any(hint in lowered for hint in _QUARTER_HINTS):
        return False
    return None


def _statement_basis(blob: Any) -> str | None:
    if isinstance(blob, dict):
        explicit = str(
            blob.get("resultType") or blob.get("consolidated") or ""
        ).strip().lower()
        if explicit == "consolidated":
            return "consolidated"
        if explicit in {"standalone", "non-consolidated", "nonconsolidated"}:
            return "standalone"
    text = json.dumps(blob).lower() if not isinstance(blob, str) else blob.lower()
    has_consolidated = "consolidated" in text and "non-consolidated" not in text
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
    latest = dated[0]
    return ExtractedField(
        field=latest.field,
        value=latest.value,
        as_of=latest.as_of,
        locator=latest.locator,
        semantic_status=latest.semantic_status,
        unit_scale="actual",
        period_end=latest.as_of,
    )


def parse_shareholding_documents(
    payload: Any,
    *,
    ticker: str,
    isin: str | None = None,
) -> tuple[NseAnnouncementDocument, ...]:
    """Index rows are not share counts. SHP XBRL URLs are the filing layer."""
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
    found: list[NseAnnouncementDocument] = []
    seen: set[str] = set()
    expected = None if isin is None else isin.strip().upper()
    for row in rows:
        symbol = str(row.get("symbol") or row.get("symbolName") or "").strip().upper()
        if symbol and symbol != ticker.upper():
            continue
        url = str(row.get("xbrl") or row.get("xbrlFile") or "").strip()
        if not url.lower().startswith("http"):
            continue
        if url in seen:
            continue
        seen.add(url)
        as_of = (
            parse_nse_calendar_date(str(row.get("date") or ""))
            or parse_nse_calendar_date(str(row.get("asOnDate") or ""))
            or parse_nse_calendar_date(str(row.get("recordDate") or ""))
        )
        row_isin = str(row.get("isin") or "").strip().upper() or None
        if expected and row_isin and row_isin != expected:
            row_isin = None
        found.append(
            NseAnnouncementDocument(
                title=" ".join(
                    part
                    for part in (
                        str(row.get("name") or ""),
                        "Shareholding pattern XBRL",
                        str(row.get("date") or ""),
                    )
                    if part
                ),
                url=url,
                as_of=as_of,
                kind="shareholding",
                source="nse_shareholding",
                isin=row_isin,
                document_id=str(row.get("recordId") or "").strip() or None,
                period=str(row.get("date") or "") or None,
            )
        )
    found.sort(key=lambda item: item.as_of or date.min, reverse=True)
    return tuple(found)


def parse_corporate_action_calendar(
    payload: Any,
    *,
    ticker: str,
    isin: str | None = None,
) -> tuple[CapitalEvent, ...]:
    """NSE CA calendar. Dividend/AGM do not change outstanding shares."""
    rows: list[dict[str, Any]] = []
    if isinstance(payload, list):
        rows = [item for item in payload if isinstance(item, dict)]
    elif isinstance(payload, dict):
        maybe = payload.get("data") or payload.get("corporateActions")
        if isinstance(maybe, list):
            rows = [item for item in maybe if isinstance(item, dict)]
    found: list[CapitalEvent] = []
    seen: set[tuple[str, date]] = set()
    expected = None if isin is None else isin.strip().upper()
    for row in rows:
        symbol = str(row.get("symbol") or "").strip().upper()
        if symbol and symbol != ticker.upper():
            continue
        row_isin = str(row.get("isin") or "").strip().upper()
        if expected and row_isin and row_isin != expected:
            continue
        subject = str(row.get("subject") or row.get("purpose") or "")
        event_type = _calendar_event_type(subject)
        if event_type is None:
            continue
        as_of = (
            parse_nse_calendar_date(str(row.get("exDate") or ""))
            or parse_nse_calendar_date(str(row.get("recDate") or ""))
            or parse_nse_calendar_date(str(row.get("caBroadcastDate") or ""))
        )
        if as_of is None:
            continue
        key = (event_type, as_of)
        if key in seen:
            continue
        seen.add(key)
        effect = _calendar_share_effect(event_type, subject)
        found.append(
            CapitalEvent(
                event_type=event_type,
                event_date=as_of,
                source_url=NSE_CORPORATE_ACTIONS_URL,
                capital_changing=effect != "NONE",
            )
        )
    found.sort(key=lambda item: (item.event_date, item.event_type))
    return tuple(found)


def _calendar_event_type(subject: str) -> str | None:
    lowered = str(subject or "").lower()
    if "buy back" in lowered or "buyback" in lowered:
        return "buyback"
    if "bonus" in lowered:
        return "bonus"
    if re.search(r"\b(stock |share )?split\b", lowered):
        return "split"
    if "rights" in lowered:
        return "rights"
    if "qip" in lowered or "qualified institutional" in lowered:
        return "qip"
    if "fpo" in lowered or "follow-on" in lowered or "follow on public" in lowered:
        return "fpo"
    if "preferential" in lowered:
        return "preferential_issue"
    if "esop" in lowered or "employee stock" in lowered:
        return "esop"
    if "warrant" in lowered:
        return "warrants"
    if "convertible" in lowered:
        return "convertibles"
    if "capital reduction" in lowered:
        return "capital_reduction"
    if "extinguish" in lowered or "cancellation of share" in lowered:
        return "extinguishment"
    if "demerger" in lowered:
        return "demerger"
    if "merger" in lowered or "amalgamation" in lowered:
        return "merger"
    if "scheme of" in lowered:
        return "scheme"
    if "share swap" in lowered:
        return "share_swap"
    if "acquisition" in lowered:
        return "acquisition"
    return None


def _calendar_share_effect(event_type: str, subject: str) -> str:
    from data_engine.official_research.extraction import (
        classify_acquisition_consideration,
        classify_capital_effect,
    )

    if event_type == "acquisition":
        consider = classify_acquisition_consideration(subject)
        if consider == "CASH":
            return "NONE"
        if consider in {"SHARE_SWAP", "MIXED"}:
            return "UNKNOWN"
        return "UNKNOWN"
    if event_type in {"merger", "demerger", "scheme", "share_swap"}:
        return "UNKNOWN"
    if event_type == "buyback":
        lowered = str(subject or "").lower()
        if "extinguish" in lowered or "cancel" in lowered:
            return "DECREASE"
        return "UNKNOWN"
    if event_type == "esop":
        return "INCREASE" if esop_changes_outstanding(subject) else "NONE"
    return classify_capital_effect(event_type)


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
    annual_rows.sort(
        key=lambda item: str(item.get("toDate") or item.get("to_date") or ""),
        reverse=True,
    )
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
                currency="INR",
                raw_value=str(raw_value),
                unit_scale="actual",
                period_type="FY",
                period_end=as_of,
                statement_basis=basis,
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


def extract_nse_api_field(
    url: str,
    payload: Any,
    *,
    listing: SecurityListing,
    field: str,
) -> ExtractedField | None:
    """Parse an already-retrieved NSE JSON body for one planned field."""
    if isinstance(payload, (bytes, bytearray)):
        raw = bytes(payload)
        if not raw.lstrip().startswith(b"<"):
            try:
                payload = _json_loads(raw)
            except LookupError:
                return None
        else:
            payload = raw
    if isinstance(payload, str) and not payload.lstrip().startswith("<"):
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError:
            return None
    lowered = str(url or "").lower()
    if "xbrl" in lowered or lowered.split("?", 1)[0].endswith((".xml", ".xbrl")):
        from data_engine.official_research.xbrl import extract_xbrl_fields

        parsed = extract_xbrl_fields(payload, isin=listing.isin)
        return parsed.fields.get(field)
    if "corporates-financial-results" in lowered or "/financial-results" in lowered:
        fields, _basis, _unit, _issue = parse_financial_results(
            payload, ticker=listing.ticker
        )
        return fields.get(field)
    if "shareholding" in lowered or "share-holdings" in lowered:
        if field != "shares_outstanding":
            return None
        if isinstance(payload, (bytes, bytearray, str)) and (
            "xbrl" in lowered or str(payload)[:80].lstrip().startswith(("<", "<?xml"))
        ):
            from data_engine.official_research.xbrl import extract_shareholding_xbrl_fields

            parsed = extract_shareholding_xbrl_fields(payload, isin=listing.isin)
            return parsed.fields.get(field)
        return parse_shareholding_shares(payload, ticker=listing.ticker)
    if "quote-equity" in lowered:
        if field != "shares_outstanding":
            return None
        extracted, _ignored, _issue = parse_quote_equity_shares(
            payload, isin=listing.isin, ticker=listing.ticker
        )
        return extracted
    return None


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
            NseAnnouncementDocument(
                title=title,
                url=url,
                as_of=as_of,
                kind=kind,
                source="nse_announcement",
            )
        )
    return tuple(found)


def parse_financial_result_documents(
    payload: Any,
    *,
    ticker: str,
) -> tuple[NseAnnouncementDocument, ...]:
    """Index rows are not line items. XBRL/detail URLs are the filing layer."""
    rows: list[dict[str, Any]] = []
    if isinstance(payload, list):
        rows = [item for item in payload if isinstance(item, dict)]
    elif isinstance(payload, dict):
        for key in ("data", "results", "financialResults"):
            maybe = payload.get(key)
            if isinstance(maybe, list):
                rows = [item for item in maybe if isinstance(item, dict)]
                break
        if not rows:
            rows = [payload]
    found: list[NseAnnouncementDocument] = []
    seen: set[str] = set()
    for row in rows:
        symbol = str(row.get("symbol") or row.get("symbolName") or "").strip().upper()
        if symbol and symbol != ticker.upper():
            continue
        period_blob = " ".join(
            str(row.get(key) or "")
            for key in ("period", "relatingTo", "fromTo", "fromDate", "toDate", "financialYear")
        )
        annual = _is_annual(period_blob) if period_blob.strip() else None
        if annual is False:
            continue
        as_of = (
            parse_nse_calendar_date(str(row.get("toDate") or ""))
            or parse_nse_calendar_date(str(row.get("reDate") or ""))
            or _period_end_from_range(str(row.get("fromTo") or row.get("financialYear") or ""))
        )
        basis = _statement_basis(row)
        isin = str(row.get("isin") or "").strip().upper() or None
        seq = str(row.get("seqNumber") or row.get("seq_id") or "").strip() or None
        for key in ("xbrl", "xbrlFiling", "resultDetailedDataLink"):
            url = str(row.get(key) or "").strip()
            if not url.lower().startswith("http"):
                continue
            if url in seen:
                continue
            seen.add(url)
            kind = "xbrl" if "xbrl" in key.lower() or url.lower().endswith((".xml", ".xbrl")) else "financial_results"
            title = " ".join(
                part
                for part in (
                    str(row.get("companyName") or ""),
                    "Annual financial results",
                    "XBRL" if kind == "xbrl" else "filing",
                    period_blob,
                    str(row.get("consolidated") or row.get("resultType") or ""),
                )
                if part
            )
            found.append(
                NseAnnouncementDocument(
                    title=title,
                    url=url,
                    as_of=as_of,
                    kind=kind,
                    source="nse_financial_results",
                    isin=isin,
                    document_id=seq,
                    period=period_blob or None,
                    statement_basis=basis,
                )
            )
    found.sort(key=lambda item: item.as_of or date.min, reverse=True)
    return tuple(found)


def parse_annual_report_documents(payload: Any) -> tuple[NseAnnouncementDocument, ...]:
    """Official NSE annual-reports archive. fromYr/toYr are the FY labels."""
    rows: list[dict[str, Any]] = []
    if isinstance(payload, list):
        rows = [item for item in payload if isinstance(item, dict)]
    elif isinstance(payload, dict):
        maybe = payload.get("data") or payload.get("dataList")
        if isinstance(maybe, list):
            rows = [item for item in maybe if isinstance(item, dict)]
    found: list[NseAnnouncementDocument] = []
    for row in rows:
        url = str(row.get("fileName") or row.get("file_name") or "").strip()
        if not url.lower().startswith("http"):
            continue
        company = str(row.get("companyName") or row.get("company") or "").strip()
        from_y = str(row.get("fromYr") or "").strip()
        to_y = str(row.get("toYr") or "").strip()
        submission = str(row.get("submission_type") or "").strip()
        title = " ".join(
            part
            for part in (
                company,
                "Integrated Annual Report",
                f"{from_y}-{to_y}" if from_y or to_y else "",
                submission,
            )
            if part
        )
        found.append(
            NseAnnouncementDocument(
                title=title,
                url=url,
                as_of=None,
                kind="annual_report",
                source="nse_annual_reports",
            )
        )
    return tuple(found)


def parse_announcement_capital_events(payload: Any) -> tuple[CapitalEvent, ...]:
    """Date each CA from the announcement row. Undated titles do not stale shares."""
    rows: list[dict[str, Any]] = []
    if isinstance(payload, list):
        rows = [item for item in payload if isinstance(item, dict)]
    elif isinstance(payload, dict):
        maybe = payload.get("data") or payload.get("announcements")
        if isinstance(maybe, list):
            rows = [item for item in maybe if isinstance(item, dict)]
    found: list[CapitalEvent] = []
    seen: set[tuple[str, date]] = set()
    for row in rows:
        as_of = parse_nse_calendar_date(
            str(row.get("an_dt") or row.get("date") or "")
        )
        if as_of is None:
            continue
        blob = " ".join(
            str(row.get(key) or "")
            for key in ("desc", "subject", "headline", "attchmntText")
        )
        for event in attack_corporate_actions(blob, event_date=as_of):
            key = (event.event_type, event.event_date)
            if key in seen:
                continue
            seen.add(key)
            found.append(event)
    found.sort(key=lambda item: (item.event_date, item.event_type))
    return tuple(found)


class NsePrimaryEvidenceService:
    """Fetch official NSE JSON for shares, filings-style results, and CA titles."""

    def __init__(self, transport: NseHttpTransport, *, mode: str = "LIVE") -> None:
        self._transport = transport
        self._mode = mode

    @property
    def transport(self) -> NseHttpTransport:
        return self._transport

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
        hold_documents: tuple[NseAnnouncementDocument, ...] = ()
        try:
            hold_payload = _json_loads(
                self._transport.get_bytes(hold_url, referer=NSE_ALL_REPORTS)
            )
            hold = parse_shareholding_shares(hold_payload, ticker=listing.ticker)
            if hold is not None:
                fields["shares_outstanding"] = hold
            hold_documents = parse_shareholding_documents(
                hold_payload, ticker=listing.ticker, isin=listing.isin
            )
            if not hold_documents and hold is None:
                issues.append("NSE shareholding index returned no filing-detail URLs")
        except LookupError as exc:
            issues.append(str(exc))

        ca_url = f"{NSE_CORPORATE_ACTIONS_URL}?index=equities&symbol={symbol}"
        urls["corporate_actions"] = ca_url
        calendar_events: tuple[CapitalEvent, ...] = ()
        calendar_searched = False
        try:
            ca_payload = _json_loads(
                self._transport.get_bytes(ca_url, referer=NSE_ALL_REPORTS)
            )
            calendar_events = parse_corporate_action_calendar(
                ca_payload, ticker=listing.ticker, isin=listing.isin
            )
            calendar_searched = True
        except LookupError as exc:
            issues.append(str(exc))

        result_url = (
            f"{NSE_FINANCIAL_RESULTS_URL}?index=equities&symbol={symbol}&period=Annual"
        )
        urls["financial_results"] = result_url
        result_documents: tuple[NseAnnouncementDocument, ...] = ()
        try:
            result_payload = _json_loads(
                self._transport.get_bytes(result_url, referer=NSE_ALL_REPORTS)
            )
            parsed, statement_basis, unit_scale, result_issue = parse_financial_results(
                result_payload, ticker=listing.ticker
            )
            fields.update(parsed)
            result_documents = parse_financial_result_documents(
                result_payload, ticker=listing.ticker
            )
            if result_issue:
                issues.append(result_issue)
            if not result_documents:
                issues.append("NSE financial-results index returned no filing-detail URLs")
        except LookupError as exc:
            issues.append(str(exc))

        ar_url = f"{NSE_ANNUAL_REPORTS_URL}?index=equities&symbol={symbol}"
        urls["annual_reports"] = ar_url
        annual_documents: tuple[NseAnnouncementDocument, ...] = ()
        try:
            ar_payload = _json_loads(
                self._transport.get_bytes(ar_url, referer=NSE_ALL_REPORTS)
            )
            annual_documents = parse_annual_report_documents(ar_payload)
            if not annual_documents:
                issues.append("NSE annual-reports archive returned no PDF rows")
        except LookupError as exc:
            issues.append(str(exc))

        ann_url = f"{NSE_ANNOUNCEMENTS_URL}?index=equities&symbol={symbol}"
        urls["announcements"] = ann_url
        try:
            ann_payload = _json_loads(
                self._transport.get_bytes(ann_url, referer=NSE_ALL_REPORTS)
            )
            events = parse_announcement_capital_events(ann_payload)
            announcement_documents = parse_announcement_documents(ann_payload)
            existing = {item.url for item in announcement_documents}
            merged = list(announcement_documents)
            for item in (*result_documents, *annual_documents, *hold_documents):
                if item.url not in existing:
                    merged.append(item)
                    existing.add(item.url)
            announcement_documents = tuple(merged)
            announcement_payload = ann_payload
            announcements_searched = True
            seen_events = {(item.event_type, item.event_date) for item in events}
            extra_events = [
                item
                for item in calendar_events
                if (item.event_type, item.event_date) not in seen_events
            ]
            events = tuple(sorted((*events, *extra_events), key=lambda item: (item.event_date, item.event_type)))
        except LookupError as exc:
            issues.append(str(exc))
            leftover = tuple(
                item
                for item in (*result_documents, *annual_documents, *hold_documents)
                if item.url
            )
            if leftover:
                announcement_documents = leftover
            if calendar_events:
                events = calendar_events

        if calendar_searched:
            announcements_searched = True

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
