"""Parse official NSE CSV and BSE List-of-Scrips JSON into raw listing rows.

Malformed rows are retained with parse errors. They are never silently dropped.
"""

from __future__ import annotations

import csv
import io
import json
import re
from dataclasses import dataclass

__all__ = [
    "ParsedListing",
    "is_valid_isin",
    "parse_bse_json",
    "parse_nse_csv",
    "source_date_from_last_modified",
]

_ISIN_RE = re.compile(r"^[A-Z]{2}[A-Z0-9]{9}[0-9]$")


@dataclass(frozen=True, slots=True)
class ParsedListing:
    exchange: str
    mic: str
    trading_symbol: str
    company_name: str
    legal_name: str
    isin: str
    exchange_security_code: str
    series: str
    document_kind: str
    listing_status: str
    trading_status: str
    source_id: str
    parse_error: str = ""


def is_valid_isin(value: str) -> bool:
    return bool(_ISIN_RE.match(value.strip().upper()))


def source_date_from_last_modified(last_modified: str) -> str:
    """HTTP Last-Modified → YYYY-MM-DD, or UNKNOWN.

    retrieved_at is not used. A download on 2026-09-07 with Last-Modified
    2026-09-06 remains source_date=2026-09-06.
    """
    text = (last_modified or "").strip()
    if not text:
        return "UNKNOWN"
    try:
        from email.utils import parsedate_to_datetime

        parsed = parsedate_to_datetime(text)
        if parsed is None:
            return "UNKNOWN"
        return parsed.date().isoformat()
    except (TypeError, ValueError, IndexError, OverflowError):
        return "UNKNOWN"


def parse_nse_csv(
    body: bytes,
    *,
    source_id: str,
    document_kind: str,
) -> tuple[tuple[str, ...], tuple[ParsedListing, ...], str]:
    text, encoding_error = _decode(body)
    if encoding_error and not text.strip():
        return ((), (), encoding_error)
    reader = csv.DictReader(io.StringIO(text))
    fields = tuple(str(name or "").strip() for name in (reader.fieldnames or ()))
    if not fields:
        return ((), (), "CSV header missing")
    required = _nse_required_columns(document_kind)
    missing = [name for name in required if not _has_column(fields, name)]
    if missing:
        return (fields, (), f"schema drift: missing columns {missing}")
    rows: list[ParsedListing] = []
    for raw in reader:
        if not isinstance(raw, dict):
            rows.append(_nse_error(source_id, document_kind, "non-object row"))
            continue
        row = {str(k or "").strip(): str(v or "").strip() for k, v in raw.items()}
        symbol = _first(row, "SYMBOL", "SM_SYMBOL", "scrip_id")
        name = _first(row, "NAME OF COMPANY", "COMPANY NAME", "NAME", "SM_COMPANY_NAME")
        series = _first(row, "SERIES", "SM_SERIES")
        isin = _first(row, "ISIN NUMBER", "ISIN_NUMBER", "ISIN")
        code = _first(row, "SECURITY CODE", "SCRIP CODE")
        error = ""
        if not any(row.values()):
            error = "empty row"
        rows.append(
            ParsedListing(
                exchange="NSE",
                mic="XNSE",
                trading_symbol=symbol.upper(),
                company_name=name,
                legal_name=name,
                isin=isin.upper(),
                exchange_security_code=code,
                series=series.upper(),
                document_kind=document_kind,
                listing_status="ACTIVE",
                trading_status="ACTIVE",
                source_id=source_id,
                parse_error=error,
            )
        )
    return (fields, tuple(rows), "")


def parse_bse_json(
    body: bytes,
    *,
    source_id: str,
    document_kind: str,
    listing_status: str,
) -> tuple[tuple[ParsedListing, ...], str]:
    text, encoding_error = _decode(body)
    if encoding_error and not text.strip():
        return ((), encoding_error)
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        return ((), f"invalid JSON: {exc}")
    if payload is None:
        return ((), "empty JSON")
    if isinstance(payload, dict):
        for key in ("Table", "data", "Data", "list"):
            inner = payload.get(key)
            if isinstance(inner, list):
                payload = inner
                break
        else:
            return ((), "schema drift: BSE payload is not a list")
    if not isinstance(payload, list):
        return ((), "schema drift: BSE payload is not a list")
    rows: list[ParsedListing] = []
    for item in payload:
        if not isinstance(item, dict):
            rows.append(
                ParsedListing(
                    exchange="BSE",
                    mic="XBOM",
                    trading_symbol="",
                    company_name="",
                    legal_name="",
                    isin="",
                    exchange_security_code="",
                    series="",
                    document_kind=document_kind,
                    listing_status=listing_status,
                    trading_status=listing_status,
                    source_id=source_id,
                    parse_error="non-object row",
                )
            )
            continue
        symbol = str(item.get("scrip_id") or item.get("Scrip_Name") or "").strip()
        name = str(item.get("Issuer_Name") or item.get("Scrip_Name") or "").strip()
        legal = str(item.get("Issuer_Name") or "").strip() or name
        isin = str(item.get("ISIN_NUMBER") or item.get("ISIN") or "").strip()
        code = str(item.get("SCRIP_CD") or item.get("Scripcode") or "").strip()
        group = str(item.get("GROUP") or item.get("Group") or "").strip()
        status = str(item.get("Status") or listing_status).strip() or listing_status
        rows.append(
            ParsedListing(
                exchange="BSE",
                mic="XBOM",
                trading_symbol=symbol.upper(),
                company_name=name,
                legal_name=legal,
                isin=isin.upper(),
                exchange_security_code=code,
                series=group.upper(),
                document_kind=document_kind,
                listing_status=listing_status.upper(),
                trading_status=status.upper(),
                source_id=source_id,
                parse_error="",
            )
        )
    return (tuple(rows), "")


def _nse_required_columns(document_kind: str) -> tuple[str, ...]:
    if document_kind in {"preference", "warrant"}:
        return ("SYMBOL",)
    return ("SYMBOL",)


def _has_column(fields: tuple[str, ...], name: str) -> bool:
    upper = {item.upper() for item in fields}
    if name.upper() in upper:
        return True
    if name.upper() == "SYMBOL":
        return bool(upper & {"SYMBOL", "SM_SYMBOL"})
    return False


def _first(row: dict[str, str], *names: str) -> str:
    upper_map = {key.upper(): value for key, value in row.items()}
    for name in names:
        value = upper_map.get(name.upper())
        if value:
            return value
    for key, value in row.items():
        key_u = key.upper()
        for name in names:
            if name.upper() in key_u and value:
                return value
    return ""


def _nse_error(source_id: str, document_kind: str, error: str) -> ParsedListing:
    return ParsedListing(
        exchange="NSE",
        mic="XNSE",
        trading_symbol="",
        company_name="",
        legal_name="",
        isin="",
        exchange_security_code="",
        series="",
        document_kind=document_kind,
        listing_status="ACTIVE",
        trading_status="ACTIVE",
        source_id=source_id,
        parse_error=error,
    )


def _decode(body: bytes) -> tuple[str, str]:
    if not body:
        return ("", "empty body")
    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            return (body.decode(encoding), "")
        except UnicodeDecodeError:
            continue
    return (body.decode("utf-8", errors="replace"), "undecodable bytes replaced")
