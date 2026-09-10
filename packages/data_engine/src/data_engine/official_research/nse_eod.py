"""Official NSE EOD discovery via daily-reports index — no guessed filenames."""

from __future__ import annotations

import json
import zipfile
from dataclasses import dataclass
from datetime import date, datetime
from http.cookiejar import CookieJar
from io import BytesIO
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import HTTPCookieProcessor, Request, build_opener

from data_engine.official_research.models import UdiffCashRow, utc_now
from data_engine.official_research.udiff import parse_udiff_csv

__all__ = [
    "NSE_DAILY_REPORTS_URL",
    "NSE_MARKET_STATUS_URL",
    "NSE_UDIFF_FILE_KEY",
    "CapitalMarketState",
    "DiscoveredNseFile",
    "NseEodBundle",
    "NseHttpTransport",
    "NsePublicHttp",
    "discover_udiff_final",
    "join_archive_url",
    "parse_capital_market_state",
    "parse_nse_calendar_date",
    "unzip_udiff",
]

NSE_HOME = "https://www.nseindia.com/"
NSE_ALL_REPORTS = "https://www.nseindia.com/all-reports"
NSE_DAILY_REPORTS_URL = "https://www.nseindia.com/api/daily-reports?key=CM"
NSE_MARKET_STATUS_URL = "https://www.nseindia.com/api/marketStatus"
NSE_UDIFF_FILE_KEY = "CM-UDIFF-BHAVCOPY-CSV"

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)


class NseHttpTransport(Protocol):
    def get_bytes(self, url: str, *, referer: str | None = None) -> bytes: ...


class NsePublicHttp:
    """Session client for public NSE website/archive files. Not a vendor API."""

    def __init__(self, *, timeout_seconds: float = 30.0) -> None:
        self._timeout = timeout_seconds
        self._opener = build_opener(HTTPCookieProcessor(CookieJar()))
        self._warmed = False

    def _headers(self, referer: str | None) -> dict[str, str]:
        headers = {
            "User-Agent": _UA,
            "Accept": "*/*",
            "Accept-Language": "en-IN,en;q=0.9",
        }
        if referer:
            headers["Referer"] = referer
        return headers

    def warm(self) -> None:
        if self._warmed:
            return
        request = Request(NSE_ALL_REPORTS, headers=self._headers(NSE_HOME))
        try:
            with self._opener.open(request, timeout=self._timeout) as response:
                response.read(2048)
        except (HTTPError, URLError, OSError):
            pass
        self._warmed = True

    def get_bytes(self, url: str, *, referer: str | None = None) -> bytes:
        self.warm()
        request = Request(url, headers=self._headers(referer or NSE_ALL_REPORTS))
        try:
            with self._opener.open(request, timeout=self._timeout) as response:
                return response.read()
        except HTTPError as exc:
            raise LookupError(f"NSE HTTP {exc.code} for official URL") from None
        except (URLError, OSError) as exc:
            raise LookupError(f"NSE request failed: {type(exc).__name__}") from None


def parse_nse_calendar_date(raw: str | None) -> date | None:
    """Parse NSE daily-report / marketStatus dates. Do not guess a trading day."""
    text = str(raw or "").strip()
    if not text:
        return None
    head = text.split()[0]
    try:
        return date.fromisoformat(head[:10])
    except ValueError:
        pass
    for fmt in ("%d-%b-%Y", "%d-%B-%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(head, fmt).date()
        except ValueError:
            continue
    return None


@dataclass(frozen=True, slots=True)
class CapitalMarketState:
    market_open: bool
    trade_date_label: str | None
    status_message: str | None
    session_date: date | None = None


@dataclass(frozen=True, slots=True)
class DiscoveredNseFile:
    display_name: str
    file_key: str
    file_name: str
    file_path: str
    trading_date: str
    file_size: str | None
    bucket: str
    url: str


@dataclass(frozen=True, slots=True)
class NseEodBundle:
    discovered: DiscoveredNseFile
    rows: tuple[UdiffCashRow, ...]
    retrieved_at: datetime
    market: CapitalMarketState
    mode: str
    payload_size: int


def join_archive_url(file_path: str, file_name: str) -> str:
    base = str(file_path or "").strip()
    name = str(file_name or "").strip()
    if not base or not name:
        raise LookupError("daily-reports entry missing filePath or fileActlName")
    if not base.endswith("/"):
        base += "/"
    return urljoin(base, name)


def parse_capital_market_state(payload: Any) -> CapitalMarketState:
    rows = []
    if isinstance(payload, dict):
        rows = payload.get("marketState") or []
    for item in rows:
        if not isinstance(item, dict):
            continue
        if str(item.get("market") or "") != "Capital Market":
            continue
        status = str(item.get("marketStatus") or "").strip().lower()
        label = str(item.get("tradeDate") or "") or None
        return CapitalMarketState(
            market_open=status == "open",
            trade_date_label=label,
            status_message=str(item.get("marketStatusMessage") or "") or None,
            session_date=parse_nse_calendar_date(label),
        )
    return CapitalMarketState(
        market_open=False,
        trade_date_label=None,
        status_message=None,
        session_date=None,
    )


def _iter_report_entries(index: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    found: list[tuple[str, dict[str, Any]]] = []
    for bucket, value in index.items():
        if not isinstance(value, list):
            continue
        for item in value:
            if isinstance(item, dict):
                found.append((str(bucket), item))
    return found


def discover_udiff_final(
    index: dict[str, Any],
    *,
    market_open: bool,
    session_date: date | None = None,
) -> DiscoveredNseFile:
    """Use the daily-reports index as discovery authority. Do not guess names."""
    matches: list[DiscoveredNseFile] = []
    for bucket, item in _iter_report_entries(index):
        key = str(item.get("fileKey") or "")
        display = str(item.get("displayName") or "")
        if key != NSE_UDIFF_FILE_KEY and "UDiFF Common Bhavcopy Final" not in display:
            continue
        name = str(item.get("fileActlName") or "").strip()
        path = str(item.get("filePath") or "").strip()
        if not name or not path:
            continue
        matches.append(
            DiscoveredNseFile(
                display_name=display,
                file_key=key or NSE_UDIFF_FILE_KEY,
                file_name=name,
                file_path=path,
                trading_date=str(item.get("tradingDate") or ""),
                file_size=str(item.get("fileSize") or "") or None,
                bucket=bucket,
                url=join_archive_url(path, name),
            )
        )
    if not matches:
        raise LookupError("CM-UDiFF Common Bhavcopy Final not listed in daily-reports")

    def _prefer(item: DiscoveredNseFile) -> tuple[int, str]:
        bucket = item.bucket.lower()
        if market_open:
            rank = 0 if "previous" in bucket else 1
        else:
            rank = 0 if "current" in bucket else 1
        return (rank, item.trading_date)

    matches.sort(key=_prefer)
    chosen = matches[0]
    chosen_session = parse_nse_calendar_date(chosen.trading_date)
    if market_open and session_date is not None and chosen_session == session_date:
        raise LookupError("today's EOD does not exist yet while the market is open")
    if market_open and "current" in chosen.bucket.lower() and chosen_session is None:
        raise LookupError("today's EOD does not exist yet while the market is open")
    return chosen


def unzip_udiff(payload: bytes) -> bytes:
    if payload[:2] != b"PK":
        if payload.lstrip().startswith(b"TradDt,") or payload.lstrip().startswith(
            b"ISIN"
        ):
            return payload
        raise LookupError("downloaded object is not a UDiFF zip or CSV")
    with zipfile.ZipFile(BytesIO(payload)) as archive:
        names = [name for name in archive.namelist() if name.lower().endswith(".csv")]
        if not names:
            raise LookupError("UDiFF zip contains no CSV")
        return archive.read(names[0])


def _parse_size_hint(raw: str | None) -> int | None:
    if not raw:
        return None
    text = raw.strip().upper().replace(",", "")
    try:
        if text.endswith("KB"):
            return int(float(text[:-2].strip()) * 1024)
        if text.endswith("MB"):
            return int(float(text[:-2].strip()) * 1024 * 1024)
        if text.endswith("B"):
            return int(float(text[:-1].strip()))
        return int(float(text))
    except ValueError:
        return None


class NseEodService:
    """Discover + download + parse official NSE UDiFF Final EOD."""

    def __init__(self, transport: NseHttpTransport, *, mode: str = "LIVE") -> None:
        self._transport = transport
        self._mode = mode

    @property
    def transport(self) -> NseHttpTransport:
        return self._transport

    def fetch_latest(self, *, retrieved_at: datetime | None = None) -> NseEodBundle:
        retrieved = retrieved_at or utc_now()
        status_raw = self._transport.get_bytes(NSE_MARKET_STATUS_URL, referer=NSE_HOME)
        try:
            market = parse_capital_market_state(json.loads(status_raw.decode("utf-8")))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise LookupError("NSE marketStatus was not JSON") from exc
        index_raw = self._transport.get_bytes(
            NSE_DAILY_REPORTS_URL, referer=NSE_ALL_REPORTS
        )
        try:
            index = json.loads(index_raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise LookupError("NSE daily-reports was not JSON") from exc
        if not isinstance(index, dict):
            raise LookupError("NSE daily-reports JSON is not an object")
        discovered = discover_udiff_final(
            index,
            market_open=market.market_open,
            session_date=market.session_date,
        )
        blob = self._transport.get_bytes(discovered.url, referer=NSE_ALL_REPORTS)
        expected = _parse_size_hint(discovered.file_size)
        if self._mode == "LIVE" and expected is not None and expected > 0:
            ratio = len(blob) / expected
            if ratio < 0.25 or ratio > 4:
                raise LookupError(
                    f"UDiFF size {len(blob)} disagrees with index hint "
                    f"{discovered.file_size}"
                )
        csv_bytes = unzip_udiff(blob)
        rows = parse_udiff_csv(csv_bytes)
        nse_rows = tuple(row for row in rows if row.venue == "NSE")
        if not nse_rows:
            raise LookupError("UDiFF CSV contained no NSE cash rows")
        return NseEodBundle(
            discovered=discovered,
            rows=nse_rows,
            retrieved_at=retrieved,
            market=market,
            mode=self._mode,
            payload_size=len(blob),
        )
