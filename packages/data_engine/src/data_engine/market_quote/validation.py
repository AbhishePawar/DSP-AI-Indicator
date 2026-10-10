"""Validate authenticated market quotes — reject invalid / fabricated envelopes."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from contracts.domain.instrument import Instrument
from data_engine.exceptions import InvalidProviderDataError
from data_engine.market_quote.models import AuthenticatedMarketQuote, QuoteField

__all__ = ["QuoteFreshnessPolicy", "validate_authenticated_quote"]

_DISALLOWED_SOURCE = frozenset(
    {"", "example", "dummy", "placeholder", "fabricated", "estimated"}
)

QUOTE_NUMERIC_FIELDS = (
    "current_price",
    "open",
    "high",
    "low",
    "previous_close",
    "week_52_high",
    "week_52_low",
    "volume",
    "average_volume",
    "market_cap",
    "enterprise_value",
    "shares_outstanding",
    "dividend_yield",
    "beta",
)


@dataclass(frozen=True, slots=True)
class QuoteFreshnessPolicy:
    """Configurable freshness policy for market quotes."""

    max_age_seconds: float | None = None
    allow_market_closed: bool = True
    max_closed_age_seconds: float | None = 604800.0  # 7 days max for market-closed/weekend data
    max_future_seconds: float = 300.0  # 5 minutes clock skew tolerance
    require_timestamp: bool = False


def _check_field(name: str, field: QuoteField) -> None:
    if field.available and field.value is None:
        raise InvalidProviderDataError(
            f"quote field '{name}' marked available with null value"
        )
    if not field.available and field.value is not None:
        raise InvalidProviderDataError(
            f"quote field '{name}' has value but marked unavailable"
        )


def validate_authenticated_quote(
    quote: AuthenticatedMarketQuote,
    *,
    requested_instrument: Instrument | None = None,
    freshness_policy: QuoteFreshnessPolicy | None = None,
) -> None:
    """Reject structurally invalid quotes. Never invent replacements."""
    if not quote.symbol or not str(quote.symbol).strip():
        raise InvalidProviderDataError("quote missing symbol")
    if not quote.provenance.provider_id.strip():
        raise InvalidProviderDataError("quote missing provider_id provenance")
    if not quote.provenance.provider_name.strip():
        raise InvalidProviderDataError("quote missing provider_name provenance")
    if quote.provenance.source_type.strip().lower() in _DISALLOWED_SOURCE:
        raise InvalidProviderDataError(
            f"disallowed provenance source_type={quote.provenance.source_type!r}"
        )

    # 1. Instrument Identity & Exchange Matching
    if requested_instrument is not None:
        req_sym = (requested_instrument.symbol or "").strip().upper()
        quote_sym = (quote.symbol or "").strip().upper()
        if req_sym and quote_sym != req_sym:
            raise InvalidProviderDataError(
                f"quote symbol '{quote_sym}' does not match requested symbol '{req_sym}'"
            )

        if requested_instrument.exchange:
            req_ex = requested_instrument.exchange.strip().upper()
            quote_ex = (quote.exchange or "").strip().upper()
            if quote_ex and quote_ex != req_ex:
                raise InvalidProviderDataError(
                    f"quote exchange '{quote_ex}' does not match requested exchange '{req_ex}'"
                )

        if requested_instrument.currency:
            req_cur = requested_instrument.currency.strip().upper()
            quote_cur = (quote.currency or "").strip().upper()
            if quote_cur and quote_cur != req_cur:
                raise InvalidProviderDataError(
                    f"quote currency '{quote_cur}' does not match requested currency '{req_cur}'"
                )

    # 2. Currency check for Indian exchanges
    quote_ex_upper = (quote.exchange or "").strip().upper()
    if quote.provenance.provider_id == "upstox" and quote_ex_upper in ("NSE", "BSE"):
        quote_cur = (quote.currency or "").strip().upper()
        if quote_cur and quote_cur not in ("INR", "₹"):
            raise InvalidProviderDataError(
                f"invalid currency '{quote.currency}' for Indian exchange {quote.exchange}; expected INR"
            )

    # 3. Unambiguous association with instrument_key in metadata
    if quote.provenance.metadata and isinstance(quote.provenance.metadata, dict):
        key = quote.provenance.metadata.get("instrument_key")
        if key and "|" in key and requested_instrument and requested_instrument.exchange:
            segment = key.split("|")[0].upper()
            req_ex = requested_instrument.exchange.strip().upper()
            if req_ex == "NSE" and not segment.startswith("NSE"):
                raise InvalidProviderDataError(
                    f"instrument key segment '{segment}' does not match requested exchange 'NSE'"
                )
            if req_ex == "BSE" and not segment.startswith("BSE"):
                raise InvalidProviderDataError(
                    f"instrument key segment '{segment}' does not match requested exchange 'BSE'"
                )
            if req_ex == "MCX" and not segment.startswith("MCX"):
                raise InvalidProviderDataError(
                    f"instrument key segment '{segment}' does not match requested exchange 'MCX'"
                )

    # 4. Check all fields for available/null consistency & numeric validity
    for name in QUOTE_NUMERIC_FIELDS:
        qf = getattr(quote, name)
        _check_field(name, qf)
        if qf.available:
            val = qf.value
            if not isinstance(val, Decimal) or not val.is_finite():
                raise InvalidProviderDataError(
                    f"quote field '{name}' must be a finite Decimal, got {val}"
                )
            fval = float(val)
            if math.isnan(fval) or math.isinf(fval):
                raise InvalidProviderDataError(
                    f"quote field '{name}' value {val} is NaN or infinite"
                )
            if name == "current_price":
                if val <= Decimal(0):
                    raise InvalidProviderDataError(
                        f"quote current_price must be positive, got {val}"
                    )
            elif name in (
                "open",
                "high",
                "low",
                "previous_close",
                "week_52_high",
                "week_52_low",
                "volume",
                "average_volume",
                "market_cap",
                "enterprise_value",
                "shares_outstanding",
            ):
                if val < Decimal(0):
                    raise InvalidProviderDataError(
                        f"quote field '{name}' cannot be negative, got {val}"
                    )

    # 5. OHLC Consistency
    if quote.high.available and quote.low.available:
        if quote.high.value is not None and quote.low.value is not None:
            if quote.high.value < quote.low.value:
                raise InvalidProviderDataError(
                    f"quote high ({quote.high.value}) cannot be lower than low ({quote.low.value})"
                )

    if quote.high.available and quote.open.available:
        if quote.high.value is not None and quote.open.value is not None:
            if quote.open.value > quote.high.value:
                raise InvalidProviderDataError(
                    f"quote open ({quote.open.value}) exceeds high ({quote.high.value})"
                )

    if quote.low.available and quote.open.available:
        if quote.low.value is not None and quote.open.value is not None:
            if quote.open.value < quote.low.value:
                raise InvalidProviderDataError(
                    f"quote open ({quote.open.value}) is below low ({quote.low.value})"
                )

    if quote.current_price.available and quote.high.available and quote.low.available:
        cp = quote.current_price.value
        h = quote.high.value
        l = quote.low.value
        if cp is not None and h is not None and cp > h:
            raise InvalidProviderDataError(
                f"quote current price ({cp}) exceeds high ({h})"
            )
        if cp is not None and l is not None and cp < l:
            raise InvalidProviderDataError(
                f"quote current price ({cp}) is below low ({l})"
            )

    if quote.week_52_high.available and quote.week_52_low.available:
        w_h = quote.week_52_high.value
        w_l = quote.week_52_low.value
        if w_h is not None and w_l is not None and w_h < w_l:
            raise InvalidProviderDataError(
                f"quote 52-week high ({w_h}) cannot be lower than 52-week low ({w_l})"
            )

    # 6. Timestamps & Freshness Policy
    policy = freshness_policy or QuoteFreshnessPolicy()
    retrieved_at = quote.provenance.retrieved_at
    if retrieved_at is None or not isinstance(retrieved_at, datetime):
        raise InvalidProviderDataError("quote missing valid retrieved_at timestamp")

    as_of = quote.provenance.as_of
    if policy.require_timestamp and as_of is None:
        raise InvalidProviderDataError("quote missing required as_of timestamp")

    if as_of is not None:
        if not isinstance(as_of, datetime):
            raise InvalidProviderDataError("quote as_of timestamp must be a datetime")
        r_tz = retrieved_at if retrieved_at.tzinfo else retrieved_at.replace(tzinfo=UTC)
        a_tz = as_of if as_of.tzinfo else as_of.replace(tzinfo=UTC)

        # Future timestamp check
        if a_tz > r_tz + timedelta(seconds=policy.max_future_seconds):
            raise InvalidProviderDataError(
                f"quote as_of timestamp {as_of.isoformat()} is in the future"
            )

        # Freshness threshold check
        if policy.max_age_seconds is not None:
            age = (r_tz - a_tz).total_seconds()
            if age > policy.max_age_seconds:
                if not policy.allow_market_closed:
                    raise InvalidProviderDataError(
                        f"quote timestamp is stale: age {age:.1f}s exceeds max_age {policy.max_age_seconds}s"
                    )
                if policy.max_closed_age_seconds is not None and age > policy.max_closed_age_seconds:
                    raise InvalidProviderDataError(
                        f"quote timestamp exceeds maximum market-closed age: age {age:.1f}s exceeds {policy.max_closed_age_seconds}s"
                    )
