"""UDiFF CM bhavcopy parser — preserve official field names."""

from __future__ import annotations

import csv
import io
from datetime import date
from decimal import Decimal, InvalidOperation

from data_engine.official_research.models import UdiffCashRow

__all__ = ["UDIFF_REQUIRED_FIELDS", "parse_udiff_csv"]

UDIFF_REQUIRED_FIELDS: tuple[str, ...] = (
    "ISIN",
    "TckrSymb",
    "SctySrs",
    "TradDt",
    "BizDt",
    "ClsPric",
    "LastPric",
    "PrvsClsgPric",
    "SttlmPric",
)


def _cell(row: dict[str, str], name: str) -> str:
    for key, value in row.items():
        if key is not None and str(key).strip() == name:
            return str(value or "").strip()
    return ""


def _date(raw: str) -> date | None:
    text = raw.strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def _decimal(raw: str) -> Decimal | None:
    text = raw.strip()
    if not text:
        return None
    try:
        return Decimal(text)
    except (InvalidOperation, ValueError):
        return None


def parse_udiff_csv(payload: str | bytes) -> tuple[UdiffCashRow, ...]:
    """Parse an official UDiFF CM CSV. Does not invent missing prices."""
    if isinstance(payload, bytes):
        text = payload.decode("utf-8-sig", errors="replace")
    else:
        text = payload
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        return ()
    headers = {str(name).strip() for name in reader.fieldnames if name}
    missing = [name for name in UDIFF_REQUIRED_FIELDS if name not in headers]
    if missing:
        msg = f"UDiFF CSV missing official fields: {', '.join(missing)}"
        raise ValueError(msg)
    rows: list[UdiffCashRow] = []
    for raw in reader:
        cleaned = {
            str(key).strip(): str(value or "").strip()
            for key, value in raw.items()
            if key is not None
        }
        src = cleaned.get("Src", "").upper()
        if src not in {"NSE", "BSE"}:
            continue
        trad = _date(cleaned.get("TradDt", ""))
        biz = _date(cleaned.get("BizDt", ""))
        isin = cleaned.get("ISIN", "").upper()
        ticker = cleaned.get("TckrSymb", "").upper()
        if trad is None or biz is None or not isin or not ticker:
            continue
        rows.append(
            UdiffCashRow(
                isin=isin,
                tckr_symb=ticker,
                scty_srs=cleaned.get("SctySrs", "").upper(),
                trad_dt=trad,
                biz_dt=biz,
                cls_pric=_decimal(cleaned.get("ClsPric", "")),
                last_pric=_decimal(cleaned.get("LastPric", "")),
                prvs_clsg_pric=_decimal(cleaned.get("PrvsClsgPric", "")),
                sttlm_pric=_decimal(cleaned.get("SttlmPric", "")),
                src=src,
                fin_instrm_tp=cleaned.get("FinInstrmTp", ""),
                fin_instrm_nm=cleaned.get("FinInstrmNm", ""),
                venue="NSE" if src == "NSE" else "BSE",
                raw=cleaned,
            )
        )
    return tuple(rows)
