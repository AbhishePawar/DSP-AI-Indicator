"""U2 — Authenticated Upstox market quote via U1-resolved identity.

Flow:
  human symbol → U1 resolver → instrument_key → GET /v2/market-quote/quotes
  → AuthenticatedMarketQuote

Does NOT silently prefer NSE on AMBIGUOUS.
Does NOT accept client price / instrument_key / provider overrides.
Does NOT wire into /analyse factories, valuation, Buffett, or recommendation.
Does NOT clear G2.

Credential: DSP_UPSTOX_ANALYTICS_TOKEN (U0).
"""

from __future__ import annotations

import time
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal

from contracts.domain.instrument import Instrument
from data_engine.connector_framework.http import JsonHttpClient, UrllibJsonHttpClient
from data_engine.connector_framework.production_profile import is_production_environment
from data_engine.exceptions import ProviderRequestError
from data_engine.market_quote.adapters import build_quote_from_mapping
from data_engine.market_quote.models import (
    AuthenticatedMarketQuote,
    MarketQuoteProvenance,
    utc_now as quote_utc_now,
)
from data_engine.upstox_connectivity import (
    UPSTOX_ANALYTICS_TOKEN_ENV,
    redact_secret,
    resolve_u0_upstox_analytics_token,
)
from data_engine.upstox_instrument_resolver import (
    UpstoxInstrumentCandidate,
    UpstoxInstrumentResolver,
    UpstoxResolveRequest,
    UpstoxResolveResult,
)
from data_engine.upstox_investment import UPSTOX_BASE_URL

__all__ = [
    "UPSTOX_MARKET_QUOTE_ENDPOINT",
    "UpstoxMarketQuoteClient",
    "UpstoxMarketQuoteRequest",
    "UpstoxMarketQuoteResult",
    "UpstoxMarketQuoteStatus",
]

UPSTOX_MARKET_QUOTE_ENDPOINT = "market-quote/quotes"

UpstoxMarketQuoteStatus = Literal[
    "OK",
    "AMBIGUOUS",
    "NOT_FOUND",
    "UNAVAILABLE",
    "REJECTED",
]


@dataclass(frozen=True, slots=True)
class UpstoxMarketQuoteRequest:
    """Server-side quote request.

    Client-supplied price / instrument_key / provider / isin are rejected.
    ``preferred_exchange`` may disambiguate NSE vs BSE after U1 AMBIGUOUS.
    """

    symbol: str
    preferred_exchange: str | None = None
    client_price: float | None = None
    client_instrument_key: str | None = None
    client_isin: str | None = None
    client_provider: str | None = None
    client_currency: str | None = None


@dataclass(frozen=True, slots=True)
class UpstoxMarketQuoteResult:
    status: UpstoxMarketQuoteStatus
    query: str
    detail: str
    retrieved_at: datetime
    latency_ms: float | None = None
    http_status: int | None = None
    resolve: UpstoxResolveResult | None = None
    identity: UpstoxInstrumentCandidate | None = None
    quote: AuthenticatedMarketQuote | None = None

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "query": self.query,
            "detail": self.detail,
            "retrieved_at": self.retrieved_at.isoformat(),
            "latency_ms": self.latency_ms,
            "http_status": self.http_status,
            "identity": None if self.identity is None else self.identity.to_public_dict(),
            "quote": None if self.quote is None else self.quote.to_public_dict(),
            # Never expose raw resolve payload secrets; resolve.to_public_dict is safe.
            "resolve_status": None if self.resolve is None else self.resolve.status,
        }


@dataclass
class UpstoxMarketQuoteClient:
    """U1 identity → authenticated Upstox full market quote."""

    access_token: str | None = None
    base_url: str = UPSTOX_BASE_URL
    timeout_seconds: float = 15.0
    http_client: JsonHttpClient | None = None
    max_attempts: int = 2
    provider_id: str = "upstox_market_quote"
    provider_name: str = "Upstox"
    resolver: UpstoxInstrumentResolver | None = None

    def __post_init__(self) -> None:
        if self.access_token is None:
            object.__setattr__(
                self, "access_token", resolve_u0_upstox_analytics_token()
            )
        object.__setattr__(self, "access_token", str(self.access_token or "").strip())
        object.__setattr__(self, "max_attempts", max(1, min(int(self.max_attempts), 3)))
        if self.resolver is None:
            object.__setattr__(
                self,
                "resolver",
                UpstoxInstrumentResolver(
                    access_token=self.access_token,
                    base_url=self.base_url,
                    timeout_seconds=self.timeout_seconds,
                    http_client=self.http_client,
                ),
            )

    def configured(self) -> bool:
        return bool(self.access_token)

    def _client(self) -> JsonHttpClient:
        return self.http_client or UrllibJsonHttpClient(
            timeout_seconds=self.timeout_seconds
        )

    def _headers(self) -> dict[str, str]:
        return {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.access_token}",
        }

    def get_quote(self, request: UpstoxMarketQuoteRequest | str) -> UpstoxMarketQuoteResult:
        retrieved_at = datetime.now(tz=UTC)
        if isinstance(request, str):
            request = UpstoxMarketQuoteRequest(symbol=request)

        # --- reject client authority ---
        if (
            request.client_price is not None
            or str(request.client_instrument_key or "").strip()
            or str(request.client_isin or "").strip()
            or str(request.client_provider or "").strip()
            or str(request.client_currency or "").strip()
        ):
            return UpstoxMarketQuoteResult(
                status="REJECTED",
                query=str(request.symbol or "").strip().upper(),
                detail=(
                    "client-supplied price / instrument_key / isin / provider / "
                    "currency are not authoritative"
                ),
                retrieved_at=retrieved_at,
            )

        if not self.configured():
            detail = (
                "production fail-closed: Upstox analytics token absent — "
                "no fixture quote substitution"
                if is_production_environment()
                else f"provider unavailable: {UPSTOX_ANALYTICS_TOKEN_ENV} absent"
            )
            return UpstoxMarketQuoteResult(
                status="UNAVAILABLE",
                query=str(request.symbol or "").strip().upper(),
                detail=detail,
                retrieved_at=retrieved_at,
            )

        started = time.perf_counter()
        assert self.resolver is not None
        resolve = self.resolver.resolve(
            UpstoxResolveRequest(
                symbol=request.symbol,
                preferred_exchange=request.preferred_exchange,
            )
        )

        if resolve.status == "AMBIGUOUS":
            return UpstoxMarketQuoteResult(
                status="AMBIGUOUS",
                query=resolve.query,
                detail=(
                    "instrument identity ambiguous; supply preferred_exchange "
                    "(NSE or BSE) — no silent exchange selection"
                ),
                retrieved_at=retrieved_at,
                latency_ms=round((time.perf_counter() - started) * 1000.0, 2),
                http_status=resolve.http_status,
                resolve=resolve,
            )
        if resolve.status == "NOT_FOUND":
            return UpstoxMarketQuoteResult(
                status="NOT_FOUND",
                query=resolve.query,
                detail=resolve.detail,
                retrieved_at=retrieved_at,
                latency_ms=round((time.perf_counter() - started) * 1000.0, 2),
                http_status=resolve.http_status,
                resolve=resolve,
            )
        if resolve.status in {"UNAVAILABLE", "REJECTED"}:
            return UpstoxMarketQuoteResult(
                status="UNAVAILABLE" if resolve.status == "UNAVAILABLE" else "REJECTED",
                query=resolve.query,
                detail=resolve.detail,
                retrieved_at=retrieved_at,
                latency_ms=round((time.perf_counter() - started) * 1000.0, 2),
                http_status=resolve.http_status,
                resolve=resolve,
            )
        if resolve.status != "RESOLVED" or resolve.identity is None:
            return UpstoxMarketQuoteResult(
                status="UNAVAILABLE",
                query=resolve.query,
                detail="instrument not resolved",
                retrieved_at=retrieved_at,
                latency_ms=round((time.perf_counter() - started) * 1000.0, 2),
                resolve=resolve,
            )

        identity = resolve.identity
        key = identity.provider_instrument_id
        url = f"{self.base_url.rstrip('/')}/{UPSTOX_MARKET_QUOTE_ENDPOINT}"
        if not url.lower().startswith("https://"):
            return UpstoxMarketQuoteResult(
                status="UNAVAILABLE",
                query=resolve.query,
                detail="HTTPS required for Upstox market quote",
                retrieved_at=retrieved_at,
                resolve=resolve,
                identity=identity,
            )

        last_error = "Upstox market quote failed"
        status_code: int | None = None
        for attempt in range(1, self.max_attempts + 1):
            try:
                payload = self._client().get_json(
                    url,
                    params={"instrument_key": key},
                    headers=self._headers(),
                )
                quote = _map_quote_payload(
                    payload,
                    identity=identity,
                    provider_id=self.provider_id,
                    provider_name=self.provider_name,
                    base_url=self.base_url,
                )
                if quote is None:
                    return UpstoxMarketQuoteResult(
                        status="UNAVAILABLE",
                        query=resolve.query,
                        detail="market quote missing price or currency",
                        retrieved_at=retrieved_at,
                        latency_ms=round((time.perf_counter() - started) * 1000.0, 2),
                        http_status=200,
                        resolve=resolve,
                        identity=identity,
                    )
                return UpstoxMarketQuoteResult(
                    status="OK",
                    query=resolve.query,
                    detail="authenticated Upstox market quote",
                    retrieved_at=retrieved_at,
                    latency_ms=round((time.perf_counter() - started) * 1000.0, 2),
                    http_status=200,
                    resolve=resolve,
                    identity=identity,
                    quote=quote,
                )
            except ProviderRequestError as exc:
                safe = redact_secret(str(exc), self.access_token)
                last_error = safe
                status_code = _status_from_detail(safe)
                msg = safe.lower()
                if "401" in msg or "403" in msg or "authentication failed" in msg:
                    break
                if "404" in msg:
                    break
                if "429" in msg or "rate limited" in msg:
                    if attempt >= self.max_attempts:
                        break
                    continue
                if attempt >= self.max_attempts:
                    break
            except Exception as exc:  # noqa: BLE001
                last_error = redact_secret(type(exc).__name__, self.access_token)
                break

        return UpstoxMarketQuoteResult(
            status="UNAVAILABLE",
            query=resolve.query,
            detail=last_error,
            retrieved_at=retrieved_at,
            latency_ms=round((time.perf_counter() - started) * 1000.0, 2),
            http_status=status_code,
            resolve=resolve,
            identity=identity,
        )


def _map_quote_payload(
    payload: Any,
    *,
    identity: UpstoxInstrumentCandidate,
    provider_id: str,
    provider_name: str,
    base_url: str,
) -> AuthenticatedMarketQuote | None:
    if not isinstance(payload, Mapping):
        return None
    data = payload.get("data")
    if not isinstance(data, Mapping) or not data:
        return None
    key = identity.provider_instrument_id
    row = data.get(key)
    if not isinstance(row, Mapping):
        # Some Upstox responses key by alternate forms; take sole row only.
        if len(data) == 1:
            sole = next(iter(data.values()))
            row = sole if isinstance(sole, Mapping) else None
        else:
            row = None
    if not isinstance(row, Mapping):
        return None

    price = row.get("last_price")
    if price is None:
        return None

    exchange = identity.exchange
    # Exchange-implied INR for Indian equity listings — not a free-floating invent.
    if exchange in {"NSE", "BSE"}:
        currency = "INR"
    else:
        return None

    ohlc = row.get("ohlc") if isinstance(row.get("ohlc"), Mapping) else {}
    fields = {
        "exchange": exchange,
        "currency": currency,
        "current_price": price,
        "open": ohlc.get("open"),
        "high": ohlc.get("high"),
        "low": ohlc.get("low"),
        "previous_close": ohlc.get("close"),
        "volume": row.get("volume"),
        "average_volume": row.get("average_price"),
    }
    provenance = MarketQuoteProvenance(
        provider_id=provider_id,
        provider_name=provider_name,
        source_type="licensed_vendor",
        retrieved_at=quote_utc_now(),
        as_of=None,
        auth_mode="bearer_token",
        metadata={
            "base_url": base_url,
            "vendor": "upstox",
            "instrument_key": key,
            "exchange": exchange,
            "isin": identity.isin,
            "u1_resolution": "RESOLVED",
        },
    )
    # as_of from vendor timestamp when present (string kept in metadata only if parse fails)
    ts = row.get("timestamp")
    if ts is not None:
        provenance = MarketQuoteProvenance(
            provider_id=provenance.provider_id,
            provider_name=provenance.provider_name,
            source_type=provenance.source_type,
            retrieved_at=provenance.retrieved_at,
            as_of=_parse_as_of(ts),
            auth_mode=provenance.auth_mode,
            metadata={**provenance.metadata, "vendor_timestamp": str(ts)},
        )

    symbol = str(
        row.get("symbol") or identity.trading_symbol or identity.display_symbol
    ).strip().upper()
    return build_quote_from_mapping(symbol=symbol, payload=fields, provenance=provenance)


def _parse_as_of(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        # Support trailing Z
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _status_from_detail(detail: str) -> int | None:
    for code in (429, 401, 403, 404, 500, 502, 503):
        if str(code) in detail:
            return code
    return None


def instrument_from_u2_identity(identity: UpstoxInstrumentCandidate) -> Instrument:
    """Build contracts.Instrument from U1/U2 server identity."""
    return identity.to_instrument()
