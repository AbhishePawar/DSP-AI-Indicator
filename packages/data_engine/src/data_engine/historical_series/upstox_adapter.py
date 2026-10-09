"""Upstox V3 Authenticated Historical Candle Adapter.

Implements Upstox V3 Historical Candle endpoint:
GET https://api.upstox.com/v3/historical-candle/{instrument_key}/{unit}/{interval}/{to_date}/{from_date}

Supports documented units:
- minutes
- hours
- days
- weeks
- months

Validates interval values, date formats, chronological ordering, and maximum retrieval windows.
Preserves timestamps, chronological order, units, and provenance.
Credentials remain strictly server-side (UPSTOX_ACCESS_TOKEN).
"""

from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from typing import Any

from contracts.domain.instrument import Instrument
from contracts.enums import AssetClass
from data_engine.exceptions import InvalidProviderDataError, ProviderRequestError
from data_engine.historical_series.models import (
    AuthenticatedHistoricalBundle,
    AuthenticatedOhlcvBar,
    HistoricalCompanyIdentity,
    HistoricalField,
    HistoricalProvenance,
    utc_now,
)
from data_engine.historical_series.service import (
    HistoricalProviderHealth,
    HistoricalSeriesPort,
    HistoricalSeriesQuery,
)
from data_engine.historical_series.validation import (
    validate_authenticated_historical_bundle,
)
from data_engine.upstox.instrument_resolver import (
    UpstoxInstrumentResolver,
    get_upstox_resolver,
)

DEFAULT_UPSTOX_BASE_URL = "https://api.upstox.com"

# Documented valid units
VALID_UNITS = frozenset({"minutes", "hours", "days", "weeks", "months"})

# Valid intervals per unit
VALID_INTERVALS: dict[str, set[str | int]] = {
    "minutes": {1, 3, 5, 10, 15, 30, 60, "1", "3", "5", "10", "15", "30", "60", "1minute", "30minute"},
    "hours": {1, 2, 3, 4, "1", "2", "3", "4", "1hour"},
    "days": {1, "1", "1day", "day"},
    "weeks": {1, "1", "1week", "week"},
    "months": {1, "1", "1month", "month"},
}

# Maximum allowed retrieval window per unit
MAX_WINDOW_DAYS: dict[str, int] = {
    "minutes": 100,
    "hours": 365,
    "days": 3650,    # 10 years
    "weeks": 3650,   # 10 years
    "months": 7300,  # 20 years
}

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _normalize_date_str(val: date | datetime | str) -> tuple[str, date]:
    """Convert input date/datetime/string to (YYYY-MM-DD, date_obj)."""
    if isinstance(val, datetime):
        d = val.date()
        return d.isoformat(), d
    if isinstance(val, date):
        return val.isoformat(), val
    s = str(val).strip()
    if not s:
        raise ProviderRequestError("Date string cannot be empty")
    iso_prefix = s[:10]
    if not _DATE_RE.match(iso_prefix):
        raise ProviderRequestError(f"Invalid date format: {val!r}, expected YYYY-MM-DD")
    try:
        d = date.fromisoformat(iso_prefix)
    except Exception as exc:
        raise ProviderRequestError(f"Invalid date value: {val!r}") from exc
    return iso_prefix, d


def _parse_candle_timestamp(ts: Any) -> tuple[datetime | None, date | None]:
    """Parse candle timestamp into datetime and date."""
    if isinstance(ts, (int, float)):
        try:
            if ts > 1e11:
                dt = datetime.fromtimestamp(ts / 1000.0, tz=UTC)
            else:
                dt = datetime.fromtimestamp(ts, tz=UTC)
            return dt, dt.date()
        except Exception:
            return None, None
    if isinstance(ts, str):
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            return dt, dt.date()
        except Exception:
            try:
                d = date.fromisoformat(ts[:10])
                return datetime.combine(d, datetime.min.time(), tzinfo=UTC), d
            except Exception:
                return None, None
    return None, None


@dataclass(frozen=True, slots=True)
class UpstoxCandle:
    """Individual parsed Upstox historical candle."""

    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    open_interest: float | None = None
    bar_date: date | None = None
    datetime_utc: datetime | None = None


@dataclass
class UpstoxHistoricalAdapter(HistoricalSeriesPort):
    """Authenticated Upstox V3 Historical Candle Adapter."""

    base_url: str = field(
        default_factory=lambda: os.environ.get("UPSTOX_BASE_URL", DEFAULT_UPSTOX_BASE_URL)
    )
    access_token: str | None = field(
        default_factory=lambda: os.environ.get(
            "UPSTOX_ACCESS_TOKEN",
            os.environ.get("DSP_UPSTOX_ACCESS_TOKEN", os.environ.get("DSP_UPSTOX_ANALYTICS_TOKEN")),
        ),
        repr=False,
    )
    timeout_seconds: float = 12.0
    max_retries: int = 2
    resolver: UpstoxInstrumentResolver = field(default_factory=get_upstox_resolver)
    _provider_id: str = "upstox"
    provider_name: str = "Upstox V3 Historical Candle"

    @property
    def provider_id(self) -> str:
        return self._provider_id

    def is_configured(self) -> bool:
        return bool((self.access_token or "").strip())

    def health(self) -> HistoricalProviderHealth:
        if not self.is_configured():
            return HistoricalProviderHealth(
                provider_id=self.provider_id,
                healthy=False,
                authenticated=False,
                detail="Upstox credentials not configured (UPSTOX_ACCESS_TOKEN not set)",
            )
        return HistoricalProviderHealth(
            provider_id=self.provider_id,
            healthy=True,
            authenticated=True,
            detail="Upstox V3 historical candles active and authenticated",
        )

    def validate_request_parameters(
        self,
        *,
        unit: str,
        interval: str | int,
        to_date: date | datetime | str,
        from_date: date | datetime | str,
    ) -> tuple[str, str, str, str]:
        """Validate unit, interval, date format, date ordering, and max windows."""
        norm_unit = str(unit).strip().lower()
        if norm_unit not in VALID_UNITS:
            raise ProviderRequestError(
                f"Unsupported candle unit '{unit}'. Documented units: {sorted(VALID_UNITS)}"
            )

        valid_ints = VALID_INTERVALS[norm_unit]
        if interval not in valid_ints and str(interval) not in valid_ints:
            raise ProviderRequestError(
                f"Invalid interval {interval!r} for unit {norm_unit!r}. Valid intervals: {sorted(str(x) for x in valid_ints)}"
            )

        norm_interval = str(interval)
        if norm_unit in ("days", "weeks", "months"):
            norm_interval = "1"
        elif norm_unit == "minutes":
            norm_interval = re.sub(r"[^\d]", "", norm_interval) or "1"
        elif norm_unit == "hours":
            norm_interval = re.sub(r"[^\d]", "", norm_interval) or "1"

        to_str, to_d = _normalize_date_str(to_date)
        from_str, from_d = _normalize_date_str(from_date)

        if from_d > to_d:
            raise ProviderRequestError(
                f"Date ordering violation: from_date ({from_str}) is after to_date ({to_str})"
            )

        window_days = (to_d - from_d).days
        max_days = MAX_WINDOW_DAYS.get(norm_unit, 3650)
        if window_days > max_days:
            raise ProviderRequestError(
                f"Requested window of {window_days} days exceeds maximum retrieval window of {max_days} days for unit '{norm_unit}'"
            )

        return norm_unit, norm_interval, to_str, from_str

    def get_candles(
        self,
        instrument_key: str,
        *,
        unit: str = "days",
        interval: str | int = 1,
        to_date: date | datetime | str,
        from_date: date | datetime | str,
    ) -> list[UpstoxCandle]:
        """Fetch historical candles from Upstox V3 endpoint."""
        if not self.is_configured():
            return []

        key = str(instrument_key).strip()
        if not key:
            raise ProviderRequestError("Empty instrument_key")

        norm_unit, norm_interval, to_str, from_str = self.validate_request_parameters(
            unit=unit,
            interval=interval,
            to_date=to_date,
            from_date=from_date,
        )

        encoded_key = urllib.parse.quote(key, safe="")
        # Path: /v3/historical-candle/{instrument_key}/{unit}/{interval}/{to_date}/{from_date}
        path = f"/v3/historical-candle/{encoded_key}/{norm_unit}/{norm_interval}/{to_str}/{from_str}"
        url = f"{self.base_url.rstrip('/')}{path}"

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json",
            "User-Agent": "dsp-ai-indicator/1.0",
        }

        last_error: Exception | None = None
        raw: str | None = None

        for attempt in range(self.max_retries + 1):
            req = urllib.request.Request(url, headers=headers, method="GET")
            try:
                with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
                    raw = resp.read().decode("utf-8")
                    status = getattr(resp, "status", 200)
                break
            except urllib.error.HTTPError as exc:
                if exc.code == 404:
                    return []
                if exc.code == 429 and attempt < self.max_retries:
                    time.sleep(0.5 * (attempt + 1))
                    continue
                last_error = exc
                break
            except Exception as exc:
                last_error = exc
                if attempt < self.max_retries:
                    time.sleep(0.3 * (attempt + 1))
                    continue
                break

        if last_error is not None:
            if isinstance(last_error, urllib.error.HTTPError):
                if last_error.code in (401, 403):
                    raise ProviderRequestError(f"Upstox authentication failed: HTTP {last_error.code}")
                if last_error.code == 404:
                    return []
            raise ProviderRequestError(f"Upstox historical candle request failed: {last_error}")

        if not raw:
            return []

        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise InvalidProviderDataError("Upstox historical candle response is not valid JSON") from exc

        if not isinstance(payload, dict):
            raise InvalidProviderDataError("Upstox response must be a JSON object")

        if payload.get("status") != "success":
            err_msg = payload.get("message") or payload.get("error") or "status not success"
            raise ProviderRequestError(f"Upstox candle request error: {err_msg}")

        data_obj = payload.get("data")
        if not isinstance(data_obj, dict):
            return []

        raw_candles = data_obj.get("candles")
        if raw_candles is None:
            return []
        if not isinstance(raw_candles, list):
            raise InvalidProviderDataError("data.candles must be a list")

        parsed_candles: list[UpstoxCandle] = []
        for i, c in enumerate(raw_candles):
            if not isinstance(c, (list, tuple)) or len(c) < 5:
                raise InvalidProviderDataError(f"Candle at index {i} has invalid structure: {c!r}")
            ts_str = str(c[0])
            dt, d = _parse_candle_timestamp(c[0])
            try:
                op = float(c[1])
                hi = float(c[2])
                lo = float(c[3])
                cl = float(c[4])
                vol = int(c[5]) if len(c) > 5 and c[5] is not None else 0
                oi = float(c[6]) if len(c) > 6 and c[6] is not None else None
            except (ValueError, TypeError) as exc:
                raise InvalidProviderDataError(f"Candle values at index {i} are invalid: {c!r}") from exc

            candle = UpstoxCandle(
                timestamp=ts_str,
                open=op,
                high=hi,
                low=lo,
                close=cl,
                volume=vol,
                open_interest=oi,
                bar_date=d,
                datetime_utc=dt,
            )
            parsed_candles.append(candle)

        # Upstox returns candles in reverse-chronological order (newest first).
        # We must sort them in ascending chronological order.
        parsed_candles.sort(key=lambda c: (c.bar_date or date.min, c.timestamp))
        return parsed_candles

    def resolve_company(self, instrument: Instrument) -> HistoricalCompanyIdentity | None:
        """Resolve company identity for historical series."""
        res = self.resolver.resolve(instrument)
        if not res.is_resolved:
            return None
        return HistoricalCompanyIdentity(
            symbol=instrument.symbol.strip().upper(),
            exchange=instrument.exchange or res.exchange,
            isin=res.isin,
            currency=instrument.currency or "INR",
        )

    def get_series(self, query: HistoricalSeriesQuery) -> AuthenticatedHistoricalBundle | None:
        """Implement HistoricalSeriesPort for 'ohlcv' series."""
        if not self.is_configured():
            return None

        kind = query.series_kind.strip().lower()
        if kind != "ohlcv":
            # Upstox market data does not provide financial statement snapshots or ratios
            return None

        # Resolve instrument key dynamically
        res = self.resolver.resolve(query.instrument)
        if not res.is_resolved or not res.instrument_key:
            return None

        freq = (query.frequency or "daily").strip().lower()
        if freq == "daily":
            unit = "days"
        elif freq == "weekly":
            unit = "weeks"
        elif freq == "monthly":
            unit = "months"
        else:
            unit = "days"

        end_d = query.end_date or date.today()
        start_d = query.start_date or (end_d - timedelta(days=365))

        try:
            candles = self.get_candles(
                instrument_key=res.instrument_key,
                unit=unit,
                interval=1,
                to_date=end_d,
                from_date=start_d,
            )
        except Exception:
            raise

        if not candles:
            return None

        # Convert to AuthenticatedOhlcvBar
        bars: list[AuthenticatedOhlcvBar] = []
        for c in candles:
            bar_date = c.bar_date or date.fromisoformat(c.timestamp[:10])
            bar = AuthenticatedOhlcvBar(
                bar_date=bar_date,
                open=HistoricalField.of(c.open),
                high=HistoricalField.of(c.high),
                low=HistoricalField.of(c.low),
                close=HistoricalField.of(c.close),
                volume=HistoricalField.of(c.volume),
                frequency=freq,
            )
            bars.append(bar)

        # Enforce chronological ordering ascending
        bars.sort(key=lambda b: b.bar_date)
        if query.limit and len(bars) > query.limit:
            bars = bars[-query.limit:]

        identity = HistoricalCompanyIdentity(
            symbol=query.instrument.symbol.strip().upper(),
            exchange=query.instrument.exchange or res.exchange,
            isin=res.isin,
            currency=query.instrument.currency or "INR",
        )

        provenance = HistoricalProvenance(
            provider_id=self.provider_id,
            provider_name=self.provider_name,
            source_type="licensed_vendor",
            retrieved_at=utc_now(),
            auth_mode="oauth_bearer",
            metadata={
                "instrument_key": res.instrument_key,
                "unit": unit,
                "interval": "1",
                "endpoint": "/v3/historical-candle",
            },
        )

        bundle = AuthenticatedHistoricalBundle(
            identity=identity,
            series_kind="ohlcv",
            frequency=freq,
            start_date=bars[0].bar_date if bars else None,
            end_date=bars[-1].bar_date if bars else None,
            bars=tuple(bars),
            points=(),
            snapshots=(),
            provenance=provenance,
            currency=identity.currency,
        )

        validate_authenticated_historical_bundle(bundle)
        return bundle
