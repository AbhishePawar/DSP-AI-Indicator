"""Optional, server-side Upstox V3 market-data adapters.

Market quotes are read from Upstox's V3 Full Market Quote API. Instrument keys
are resolved before requests; raw symbols are never converted by string
concatenation in the quote adapter. Credentials are read only from the server
environment and are never returned or logged.
"""
from __future__ import annotations

import math

import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from contracts.domain.instrument import Instrument
from contracts.enums import AssetClass
from data_engine.exceptions import InvalidProviderDataError, ProviderRequestError
from data_engine.market_quote.models import (
    AuthenticatedMarketQuote,
    MarketQuoteProvenance,
    QuoteField,
    utc_now,
)
from data_engine.market_quote.service import MarketQuotePort, QuoteProviderHealth
from data_engine.market_quote.validation import validate_authenticated_quote
from data_engine.upstox.instrument_resolver import (
    UpstoxInstrumentResolver,
    get_upstox_resolver,
)

DEFAULT_UPSTOX_BASE_URL = "https://api.upstox.com"
_UPSTOX_KEY_RE = re.compile(r"^[A-Z0-9_]+[|][A-Z0-9_.:-]+$", re.IGNORECASE)


def _parse_timestamp(ts: Any) -> datetime | None:
    if isinstance(ts, bool):
        return None
    if isinstance(ts, (int, float, Decimal)):
        try:
            if float(ts) > 1e11:
                return datetime.fromtimestamp(float(ts) / 1000.0, tz=UTC)
            return datetime.fromtimestamp(float(ts), tz=UTC)
        except (OverflowError, OSError, ValueError):
            return None
    if isinstance(ts, str):
        try:
            parsed = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
        except ValueError:
            return None
    return None


def _parse_number(value: Any) -> float | None:
    if value is None:
        return None
    try:
        val = float(value)
        return val if math.isfinite(val) else None
    except (ValueError, TypeError):
        return None


def _number(value: Any) -> Decimal | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        out = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None
    return out if out.is_finite() else None


def _field(value: Any) -> QuoteField:
    number = _number(value)
    return QuoteField.of(number) if number is not None else QuoteField.missing()


@dataclass
class UpstoxQuoteAdapter(MarketQuotePort):
    """Optional Upstox V3 Full Market Quote provider."""

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
    timeout_seconds: float = 8.0
    max_retries: int = 1
    resolver: UpstoxInstrumentResolver = field(default_factory=get_upstox_resolver)
    _provider_id: str = "upstox"
    provider_name: str = "Upstox V3 Full Market Quote"

    @property
    def provider_id(self) -> str:
        return self._provider_id

    def is_configured(self) -> bool:
        return bool((self.access_token or "").strip())

    def health(self) -> QuoteProviderHealth:
        return QuoteProviderHealth(
            provider_id=self.provider_id,
            healthy=self.is_configured(),
            authenticated=self.is_configured(),
            detail="configured" if self.is_configured() else "optional provider unavailable: UPSTOX_ACCESS_TOKEN not set",
        )

    def format_instrument_key(self, instrument: Instrument) -> str:
        """Resolve an instrument via reference data / asset identity, or fail."""
        result = self.resolver.resolve(instrument)
        if result.status == "ambiguous":
            raise ProviderRequestError("Upstox instrument identity is ambiguous")
        if not result.is_resolved or not result.instrument_key:
            raise ProviderRequestError("Upstox instrument identity could not be resolved")
        if not _UPSTOX_KEY_RE.fullmatch(result.instrument_key):
            raise ProviderRequestError("Resolved Upstox instrument key is invalid")
        return result.instrument_key

    @staticmethod
    def _quote_data(
        payload: Any,
        instrument_key: str,
        symbol: str | None = None,
        exchange: str | None = None,
    ) -> Mapping[str, Any] | None:
        if not isinstance(payload, Mapping):
            raise InvalidProviderDataError("Upstox quote response must be a JSON object")
        if payload.get("status") != "success":
            msg = payload.get("message")
            if not msg and isinstance(payload.get("errors"), list) and payload["errors"]:
                msg = payload["errors"][0].get("message")
            raise ProviderRequestError(msg or "Upstox quote response status not success")

        data = payload.get("data")
        if not isinstance(data, Mapping):
            raise InvalidProviderDataError("Upstox quote response data must be an object")

        # 1. Match by instrument_token
        for value in data.values():
            if isinstance(value, Mapping) and str(value.get("instrument_token", "")).strip() == instrument_key:
                return value

        # 2. Direct key lookup
        direct = data.get(instrument_key)
        if isinstance(direct, Mapping):
            return direct

        # 3. Match by segment:symbol key (e.g. NSE_EQ:NHPC, BSE_EQ:TATAMOTORS)
        sym = (symbol or "").strip().upper()
        ex = (exchange or "").strip().upper()
        if sym:
            possible_keys = [
                f"{ex}_EQ:{sym}",
                f"{ex}:{sym}",
                f"NSE_EQ:{sym}",
                f"BSE_EQ:{sym}",
                f"MCX_COMM:{sym}",
                f"MCX_FO:{sym}",
                sym,
            ]
            for pk in possible_keys:
                if pk in data and isinstance(data[pk], Mapping):
                    return data[pk]

            # Check if any key ends with :symbol
            for k, val in data.items():
                if isinstance(val, Mapping):
                    if k.upper().endswith(f":{sym}") or k.upper() == sym:
                        return val

        # Strict match only — never accept an unrelated single quote
        return None

    def get_quote(self, instrument: Instrument) -> AuthenticatedMarketQuote | None:
        if not self.is_configured():
            return None
        res = self.resolver.resolve(instrument)
        if not res.is_resolved or not res.instrument_key:
            return None
        instrument_key = res.instrument_key
        if not _UPSTOX_KEY_RE.fullmatch(instrument_key):
            raise ProviderRequestError(f"Resolved Upstox instrument key is invalid: {instrument_key}")
        query = urllib.parse.urlencode({"instrument_key": instrument_key})
        url = f"{self.base_url.rstrip('/')}/v3/market-quote/quotes?{query}"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json",
            "User-Agent": "dsp-ai-indicator/1.0",
        }
        raw: str | None = None
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            request = urllib.request.Request(url, headers=headers, method="GET")
            try:
                with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                    raw = response.read().decode("utf-8")
                break
            except urllib.error.HTTPError as exc:
                if exc.code == 404:
                    return None
                if exc.code == 429 and attempt < self.max_retries:
                    time.sleep(min(0.5 * (attempt + 1), 2.0))
                    continue
                if exc.code in (401, 403):
                    raise ProviderRequestError(f"Upstox authentication failed: HTTP {exc.code}") from exc
                raise ProviderRequestError(f"Upstox quote request failed: HTTP {exc.code}") from exc
            except TimeoutError as exc:
                last_error = exc
                if attempt < self.max_retries:
                    continue
                raise ProviderRequestError("Upstox quote request timed out") from exc
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                if attempt < self.max_retries:
                    continue
                raise ProviderRequestError("Upstox quote request failed") from exc
        if raw is None:
            if last_error:
                raise ProviderRequestError("Upstox quote request failed") from last_error
            return None
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise InvalidProviderDataError("Upstox quote response is not valid JSON") from exc
        quote_data = self._quote_data(
            payload,
            instrument_key,
            symbol=instrument.symbol,
            exchange=instrument.exchange or res.exchange,
        )
        if quote_data is None:
            return None
        ohlc = quote_data.get("ohlc")
        if ohlc is not None and not isinstance(ohlc, Mapping):
            raise InvalidProviderDataError("Upstox quote OHLC must be an object")
        ohlc = ohlc if isinstance(ohlc, Mapping) else {}
        raw_ts = quote_data.get("timestamp")
        if raw_ts is not None:
            as_of = _parse_timestamp(raw_ts)
            if as_of is None:
                raise InvalidProviderDataError(f"malformed timestamp in quote: {raw_ts!r}")
        else:
            raw_ohlc_ts = ohlc.get("ts")
            if raw_ohlc_ts is not None:
                as_of = _parse_timestamp(raw_ohlc_ts)
                if as_of is None:
                    raise InvalidProviderDataError(f"malformed ohlc.ts in quote: {raw_ohlc_ts!r}")
            else:
                as_of = None
        ret_token = quote_data.get("instrument_token")
        if ret_token is not None:
            str_ret = str(ret_token).strip()
            valid_tokens = {instrument_key}
            if getattr(res, "isin", None):
                valid_tokens.add(res.isin)
            if "|" in instrument_key:
                valid_tokens.add(instrument_key.split("|")[-1])
            if str_ret not in valid_tokens:
                raise InvalidProviderDataError(
                    f"Upstox instrument token mismatch: expected '{instrument_key}', got '{str_ret}'"
                )
            token_identity = str_ret
        else:
            token_identity = instrument_key

        raw_ohlc_ts = ohlc.get("ts") if isinstance(ohlc, Mapping) else None
        ohlc_as_of = _parse_timestamp(raw_ohlc_ts) if raw_ohlc_ts else None
        q_ts_str = as_of.isoformat() if as_of else None
        meta: dict[str, Any] = {
            "instrument_key": instrument_key,
            "instrument_token": token_identity,
            "quote_timestamp": q_ts_str,
            "ohlc_timestamp": ohlc_as_of.isoformat() if ohlc_as_of else None,
        }
        if quote_data.get("average_price") is not None:
            meta["average_price"] = _parse_number(quote_data.get("average_price"))
        if quote_data.get("net_change") is not None:
            meta["net_change"] = _parse_number(quote_data.get("net_change"))
        if quote_data.get("oi") is not None:
            meta["open_interest"] = _parse_number(quote_data.get("oi"))
        if quote_data.get("depth") is not None:
            meta["depth"] = quote_data.get("depth")
        lower_c = _parse_number(quote_data.get("lower_circuit_limit"))
        upper_c = _parse_number(quote_data.get("upper_circuit_limit"))
        if lower_c is not None or upper_c is not None:
            meta["circuit_limits"] = {"lower": lower_c, "upper": upper_c}

        provenance = MarketQuoteProvenance(
            provider_id=self.provider_id,
            provider_name=self.provider_name,
            source_type="licensed_vendor",
            retrieved_at=utc_now(),
            as_of=as_of,
            auth_mode="oauth_bearer",
            metadata=meta,
        )
        def first(*keys: str) -> Any:
            for key in keys:
                if key in quote_data and quote_data[key] is not None:
                    return quote_data[key]
            return None

        # Determine clean symbol and previous close
        clean_symbol = instrument.symbol.strip().upper()
        prev_close_val = quote_data.get("prev_close_price")

        resp_sym = quote_data.get("symbol")
        if resp_sym is not None:
            clean_resp_sym = str(resp_sym).split(":")[-1].strip().upper()
            if clean_resp_sym != clean_symbol:
                raise InvalidProviderDataError(
                    f"Upstox quote symbol mismatch: expected '{clean_symbol}', got '{resp_sym}'"
                )

        quote = AuthenticatedMarketQuote(
            symbol=clean_symbol,
            exchange=instrument.exchange or res.exchange,
            currency=instrument.currency or "INR",
            current_price=_field(quote_data.get("last_price")),
            open=_field(ohlc.get("open")),
            high=_field(ohlc.get("high")),
            low=_field(ohlc.get("low")),
            previous_close=_field(prev_close_val),
            week_52_high=_field(quote_data.get("year_high")),
            week_52_low=_field(quote_data.get("year_low")),
            volume=_field(first("volume") if first("volume") is not None else ohlc.get("volume")),
            average_volume=QuoteField.missing(),
            market_cap=QuoteField.missing(),
            enterprise_value=QuoteField.missing(),
            shares_outstanding=QuoteField.missing(),
            dividend_yield=QuoteField.missing(),
            beta=QuoteField.missing(),
            provenance=provenance,
        )
        validate_authenticated_quote(quote, requested_instrument=instrument)
        return quote


def build_upstox_quote_adapter_from_env() -> UpstoxQuoteAdapter | None:
    """Build optional adapter only when a server-side access token exists."""
    token = os.environ.get("UPSTOX_ACCESS_TOKEN", "").strip()
    if not token:
        return None
    return UpstoxQuoteAdapter(access_token=token)
