"""U1 — Upstox company / instrument resolver (identity only).

Accepts human-friendly Indian equity symbols (e.g. ``TCS``) and resolves
them via the official Upstox Instrument Search API:

  GET /v2/instruments/search

Does NOT invent ``.NS`` / ``.BO``, ISIN, or ``instrument_key``.
Does NOT select silently among multiple legitimate securities.
Does NOT wire Upstox into valuation / Buffett / recommendation.
Does NOT clear G2.

Credential: ``DSP_UPSTOX_ANALYTICS_TOKEN`` (U0).
"""

from __future__ import annotations

import re
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal

from contracts.domain.instrument import Instrument
from contracts.enums import AssetClass
from data_engine.connector_framework.http import JsonHttpClient, UrllibJsonHttpClient
from data_engine.connector_framework.production_profile import is_production_environment
from data_engine.exceptions import ProviderRequestError
from data_engine.upstox_connectivity import (
    UPSTOX_ANALYTICS_TOKEN_ENV,
    redact_secret,
    resolve_u0_upstox_analytics_token,
)
from data_engine.upstox_investment import UPSTOX_BASE_URL

__all__ = [
    "UPSTOX_INSTRUMENT_SEARCH_ENDPOINT",
    "UpstoxInstrumentCandidate",
    "UpstoxInstrumentResolver",
    "UpstoxResolveRequest",
    "UpstoxResolveResult",
    "UpstoxResolveStatus",
    "normalize_user_symbol",
]

UPSTOX_INSTRUMENT_SEARCH_ENDPOINT = "instruments/search"

UpstoxResolveStatus = Literal[
    "RESOLVED",
    "AMBIGUOUS",
    "NOT_FOUND",
    "UNAVAILABLE",
    "REJECTED",
]

# Harmless user formatting only — never used as an authoritative exchange map.
_YAHOO_STYLE_SUFFIX = re.compile(r"\.(NS|BO)$", re.IGNORECASE)
_EQUITY_SEGMENTS = frozenset({"NSE_EQ", "BSE_EQ"})
_EQUITY_TYPES = frozenset({"EQ", "BE", "A", "B", "X"})


def normalize_user_symbol(raw: str) -> str:
    """Normalize harmless formatting; do not invent exchange suffixes."""
    text = str(raw or "").strip().upper()
    text = text.replace(" ", "")
    text = _YAHOO_STYLE_SUFFIX.sub("", text)
    return text


@dataclass(frozen=True, slots=True)
class UpstoxResolveRequest:
    """Server-side resolve input.

    Client-supplied ``isin`` / ``instrument_key`` / ``provider`` are rejected —
    those identifiers are server-authoritative after search.
    """

    symbol: str
    preferred_exchange: str | None = None
    # If a client attempts to assert these, the resolver REJECTS the request.
    client_isin: str | None = None
    client_instrument_key: str | None = None
    client_provider: str | None = None


@dataclass(frozen=True, slots=True)
class UpstoxInstrumentCandidate:
    """One server-resolved security identity from Upstox search."""

    display_symbol: str
    company_name: str | None
    exchange: str
    isin: str
    provider: str
    provider_instrument_id: str
    trading_symbol: str
    segment: str | None = None
    instrument_type: str | None = None

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "display_symbol": self.display_symbol,
            "company_name": self.company_name,
            "exchange": self.exchange,
            "isin": self.isin,
            "provider": self.provider,
            "provider_instrument_id": self.provider_instrument_id,
            "trading_symbol": self.trading_symbol,
            "segment": self.segment,
            "instrument_type": self.instrument_type,
        }

    def to_instrument(self) -> Instrument:
        return Instrument(
            symbol=self.trading_symbol,
            asset_class=AssetClass.EQUITY,
            currency="INR",
            name=self.company_name,
            exchange=self.exchange,
            country="IN",
            isin=self.isin,
        )


@dataclass(frozen=True, slots=True)
class UpstoxResolveResult:
    status: UpstoxResolveStatus
    query: str
    detail: str
    retrieved_at: datetime
    latency_ms: float | None = None
    identity: UpstoxInstrumentCandidate | None = None
    candidates: tuple[UpstoxInstrumentCandidate, ...] = ()
    instrument: Instrument | None = None
    http_status: int | None = None

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "query": self.query,
            "detail": self.detail,
            "retrieved_at": self.retrieved_at.isoformat(),
            "latency_ms": self.latency_ms,
            "http_status": self.http_status,
            "identity": None if self.identity is None else self.identity.to_public_dict(),
            "candidates": [c.to_public_dict() for c in self.candidates],
            "instrument": None
            if self.instrument is None
            else {
                "symbol": self.instrument.symbol,
                "name": self.instrument.name,
                "exchange": self.instrument.exchange,
                "isin": self.instrument.isin,
                "currency": self.instrument.currency,
                "country": self.instrument.country,
                "asset_class": self.instrument.asset_class.value,
            },
        }


@dataclass
class UpstoxInstrumentResolver:
    """Resolve human-friendly Indian equity symbols via Upstox Instrument Search."""

    access_token: str | None = None
    base_url: str = UPSTOX_BASE_URL
    timeout_seconds: float = 15.0
    http_client: JsonHttpClient | None = None
    provider_name: str = "upstox"

    def __post_init__(self) -> None:
        if self.access_token is None:
            object.__setattr__(
                self, "access_token", resolve_u0_upstox_analytics_token()
            )
        object.__setattr__(self, "access_token", str(self.access_token or "").strip())

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

    def resolve(self, request: UpstoxResolveRequest | str) -> UpstoxResolveResult:
        retrieved_at = datetime.now(tz=UTC)
        if isinstance(request, str):
            request = UpstoxResolveRequest(symbol=request)

        # --- reject client-forged provider identity ---
        if (
            str(request.client_isin or "").strip()
            or str(request.client_instrument_key or "").strip()
            or str(request.client_provider or "").strip()
        ):
            return UpstoxResolveResult(
                status="REJECTED",
                query=normalize_user_symbol(request.symbol),
                detail=(
                    "client-supplied ISIN / instrument_key / provider are not "
                    "authoritative; server resolver required"
                ),
                retrieved_at=retrieved_at,
            )

        query = normalize_user_symbol(request.symbol)
        if not query:
            return UpstoxResolveResult(
                status="NOT_FOUND",
                query="",
                detail="empty symbol",
                retrieved_at=retrieved_at,
            )

        if not self.configured():
            detail = (
                "production fail-closed: Upstox analytics token absent — "
                "no fixture company substitution"
                if is_production_environment()
                else f"provider unavailable: {UPSTOX_ANALYTICS_TOKEN_ENV} absent"
            )
            return UpstoxResolveResult(
                status="UNAVAILABLE",
                query=query,
                detail=detail,
                retrieved_at=retrieved_at,
            )

        url = f"{self.base_url.rstrip('/')}/{UPSTOX_INSTRUMENT_SEARCH_ENDPOINT}"
        if not url.lower().startswith("https://"):
            return UpstoxResolveResult(
                status="UNAVAILABLE",
                query=query,
                detail="HTTPS required for Upstox instrument search",
                retrieved_at=retrieved_at,
            )

        params = {
            "query": query,
            "exchanges": "NSE,BSE",
            "segments": "EQ",
            "page_number": "1",
            "records": "30",
        }
        started = time.perf_counter()
        try:
            payload = self._client().get_json(
                url, params=params, headers=self._headers()
            )
        except ProviderRequestError as exc:
            latency_ms = round((time.perf_counter() - started) * 1000.0, 2)
            safe = redact_secret(str(exc), self.access_token)
            return UpstoxResolveResult(
                status="UNAVAILABLE",
                query=query,
                detail=safe,
                retrieved_at=retrieved_at,
                latency_ms=latency_ms,
                http_status=_status_from_detail(safe),
            )
        except Exception as exc:  # noqa: BLE001
            latency_ms = round((time.perf_counter() - started) * 1000.0, 2)
            safe = redact_secret(f"{type(exc).__name__}", self.access_token)
            return UpstoxResolveResult(
                status="UNAVAILABLE",
                query=query,
                detail=safe,
                retrieved_at=retrieved_at,
                latency_ms=latency_ms,
            )

        latency_ms = round((time.perf_counter() - started) * 1000.0, 2)
        if not isinstance(payload, Mapping):
            return UpstoxResolveResult(
                status="UNAVAILABLE",
                query=query,
                detail="invalid Upstox search response",
                retrieved_at=retrieved_at,
                latency_ms=latency_ms,
                http_status=200,
            )

        rows = payload.get("data")
        if not isinstance(rows, list):
            return UpstoxResolveResult(
                status="NOT_FOUND",
                query=query,
                detail="no instruments in search response",
                retrieved_at=retrieved_at,
                latency_ms=latency_ms,
                http_status=200,
            )

        candidates = _candidates_from_rows(rows, provider=self.provider_name)
        exact = [
            c
            for c in candidates
            if c.trading_symbol == query or c.display_symbol == query
        ]
        pool = exact if exact else []

        preferred = str(request.preferred_exchange or "").strip().upper() or None
        if preferred:
            pool = [c for c in pool if c.exchange == preferred]

        if not pool:
            return UpstoxResolveResult(
                status="NOT_FOUND",
                query=query,
                detail=(
                    f"no exact equity match for {query!r}"
                    + (f" on exchange {preferred}" if preferred else "")
                ),
                retrieved_at=retrieved_at,
                latency_ms=latency_ms,
                http_status=200,
                candidates=tuple(candidates[:10]),
            )

        # Distinct securities by (exchange, instrument_key).
        unique_keys = {(c.exchange, c.provider_instrument_id) for c in pool}
        if len(unique_keys) > 1:
            return UpstoxResolveResult(
                status="AMBIGUOUS",
                query=query,
                detail=(
                    f"multiple securities match {query!r}; "
                    "select exchange from candidates (server will re-resolve)"
                ),
                retrieved_at=retrieved_at,
                latency_ms=latency_ms,
                http_status=200,
                candidates=tuple(pool),
            )

        chosen = pool[0]
        return UpstoxResolveResult(
            status="RESOLVED",
            query=query,
            detail="resolved via Upstox instruments/search",
            retrieved_at=retrieved_at,
            latency_ms=latency_ms,
            http_status=200,
            identity=chosen,
            candidates=(chosen,),
            instrument=chosen.to_instrument(),
        )


def _candidates_from_rows(
    rows: Sequence[Any], *, provider: str
) -> list[UpstoxInstrumentCandidate]:
    out: list[UpstoxInstrumentCandidate] = []
    seen: set[tuple[str, str]] = set()
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        segment = str(row.get("segment") or "").strip().upper()
        itype = str(row.get("instrument_type") or "").strip().upper()
        if segment not in _EQUITY_SEGMENTS:
            continue
        if itype not in _EQUITY_TYPES:
            continue
        trading = str(
            row.get("trading_symbol") or row.get("tradingsymbol") or ""
        ).strip().upper()
        if not trading:
            continue
        isin = str(row.get("isin") or "").strip().upper()
        key = str(row.get("instrument_key") or "").strip()
        exchange = str(row.get("exchange") or "").strip().upper()
        # Missing authoritative identifiers → skip (never invent).
        if not isin or not key or exchange not in {"NSE", "BSE"}:
            continue
        # Wrong exchange vs segment (e.g. NSE key but BSE label) → skip.
        if segment.startswith("NSE") and exchange != "NSE":
            continue
        if segment.startswith("BSE") and exchange != "BSE":
            continue
        dedupe = (exchange, key)
        if dedupe in seen:
            continue
        seen.add(dedupe)
        name = row.get("name") or row.get("short_name")
        out.append(
            UpstoxInstrumentCandidate(
                display_symbol=trading,
                company_name=str(name).strip() if name else None,
                exchange=exchange,
                isin=isin,
                provider=provider,
                provider_instrument_id=key,
                trading_symbol=trading,
                segment=segment,
                instrument_type=itype,
            )
        )
    return out


def _status_from_detail(detail: str) -> int | None:
    for code in (429, 401, 403, 404, 500, 502, 503):
        if str(code) in detail:
            return code
    return None
