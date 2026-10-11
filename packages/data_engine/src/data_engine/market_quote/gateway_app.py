"""Private vendor-neutral market-data gateway for the DSP production quote interface.

The DSP API calls this service through ConfiguredHttpQuoteAdapter (P1-03).
Upstox is preferred for Indian equity quotes; an independently configured,
approved HTTP quote source is used when Upstox is unavailable or returns
unusable data. This service never exposes upstream credentials.
"""
from __future__ import annotations

import hmac
import logging
import os
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Query, status

from contracts.domain.instrument import Instrument
from contracts.enums import AssetClass
from data_engine.exceptions import DataEngineError
from data_engine.market_quote.adapters import ConfiguredHttpQuoteAdapter
from data_engine.market_quote.upstox_adapter import UpstoxQuoteAdapter

_LOG = logging.getLogger("dsp.market_data_gateway")
app = FastAPI(
    title="DSP Internal Market Data Gateway",
    version="1.0.0",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)


def _gateway_key() -> str:
    return os.environ.get("DSP_MARKET_GATEWAY_API_KEY", "").strip()


def _upstox() -> UpstoxQuoteAdapter:
    return UpstoxQuoteAdapter()


def _fallback() -> ConfiguredHttpQuoteAdapter | None:
    base_url = os.environ.get("DSP_MARKET_GATEWAY_FALLBACK_BASE_URL", "").strip()
    api_key = os.environ.get("DSP_MARKET_GATEWAY_FALLBACK_API_KEY", "").strip()
    if not base_url or not api_key:
        return None
    return ConfiguredHttpQuoteAdapter(base_url=base_url, api_key=api_key)


def _public_quote(quote: Any, *, selected_source: str, fallback_reason: str | None) -> dict[str, Any]:
    result = quote.to_public_dict()
    # Preserve the upstream provider in nested provenance, while exposing the
    # gateway's selected source and fallback reason as explicit top-level metadata.
    result["gateway"] = {
        "selected_source": selected_source,
        "fallback_used": fallback_reason is not None,
        "fallback_reason": fallback_reason,
    }
    return result


@app.get("/health/ready")
def readiness() -> dict[str, Any]:
    configured = bool(_gateway_key()) and (
        bool((os.environ.get("UPSTOX_ACCESS_TOKEN") or "").strip())
        or _fallback() is not None
    )
    if not configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="market data gateway is not configured",
        )
    return {"status": "ready", "service": "market-data-gateway"}


@app.get("/quote")
def get_quote(
    symbol: str = Query(min_length=1, max_length=32),
    exchange: str = Query(default="NSE", min_length=2, max_length=16),
    currency: str = Query(default="INR", min_length=3, max_length=3),
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> dict[str, Any]:
    expected = _gateway_key()
    supplied = (authorization or "").removeprefix("Bearer ").strip()
    if not expected or not supplied or not hmac.compare_digest(supplied, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid gateway credentials",
        )

    exchange_code = exchange.strip().upper()
    exchange_code = {"NSE_EQ": "NSE", "BSE_EQ": "BSE"}.get(exchange_code, exchange_code)
    try:
        instrument = Instrument(
            symbol=symbol,
            asset_class=AssetClass.EQUITY,
            currency=currency,
            exchange=exchange_code,
            country="IN",
        )
    except Exception as exc:
        raise HTTPException(status_code=422, detail="invalid instrument identity") from exc

    fallback_reason: str | None = None
    try:
        quote = _upstox().get_quote(instrument)
        if quote is not None and quote.has_any_price():
            return _public_quote(quote, selected_source="upstox", fallback_reason=None)
        fallback_reason = "upstox_quote_unavailable"
    except DataEngineError as exc:
        # Do not expose provider errors, URLs, or credential-adjacent details to callers.
        fallback_reason = type(exc).__name__
        _LOG.warning("upstox_quote_unavailable", extra={"symbol": instrument.symbol, "reason": fallback_reason})
    except Exception as exc:  # noqa: BLE001
        fallback_reason = type(exc).__name__
        _LOG.warning("upstox_quote_unavailable", extra={"symbol": instrument.symbol, "reason": fallback_reason})

    fallback = _fallback()
    if fallback is not None:
        try:
            quote = fallback.get_quote(instrument)
            if quote is not None and quote.has_any_price():
                return _public_quote(
                    quote,
                    selected_source="approved_http_fallback",
                    fallback_reason=fallback_reason,
                )
        except Exception as exc:  # noqa: BLE001
            _LOG.warning(
                "fallback_quote_unavailable",
                extra={"symbol": instrument.symbol, "reason": type(exc).__name__},
            )

    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail={
            "code": "market_quote_unavailable",
            "message": "No approved source returned a usable market quote.",
            "fallback_attempted": fallback is not None,
        },
    )
