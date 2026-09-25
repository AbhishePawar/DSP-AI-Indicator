"""Authenticated market index snapshots (Figma Dashboard market bar).

The Figma ``Dashboard`` market bar renders four Indian benchmark indices
(NIFTY 50 · SENSEX · NIFTY IT · NIFTY BANK) with last value, day change and a
12-point sparkline. This module is the *provider layer* for that contract:

- ``INDIA_BENCHMARK_INDICES`` — canonical index catalogue (label + canonical id).
  Provider-specific symbols live in the adapter, never in the browser.
- ``MarketIndexSnapshot`` — typed, provenance-carrying snapshot; every numeric
  field may be ``None`` (CV-001: missing provider values stay missing).
- ``FinancialModelingPrepIndexAdapter`` — canonical authenticated provider.
- ``NullMarketIndexAdapter`` — honest absence when no approved feed exists.
- ``build_default_index_adapter_from_env`` — follows the *same* provider
  selection policy as ``build_default_quote_adapter_from_env`` (P1-03).

Nothing here computes or approximates a value: change / change_percent are
the provider's own fields and the sparkline is the provider's close series.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol

from contracts.domain.instrument import Instrument
from contracts.enums import AssetClass
from data_engine.connector_framework.http import JsonHttpClient, UrllibJsonHttpClient
from data_engine.exceptions import ProviderRequestError
from data_engine.market_quote.models import MarketQuoteProvenance

__all__ = [
    "INDIA_BENCHMARK_INDICES",
    "SPARKLINE_POINTS",
    "BenchmarkIndex",
    "FinancialModelingPrepIndexAdapter",
    "MarketIndexPort",
    "MarketIndexService",
    "MarketIndexSnapshot",
    "NullMarketIndexAdapter",
    "build_default_index_adapter_from_env",
]

SPARKLINE_POINTS = 12


@dataclass(frozen=True, slots=True)
class BenchmarkIndex:
    """Canonical index identity — provider agnostic."""

    index_id: str
    label: str
    exchange: str
    currency: str = "INR"

    def to_dict(self) -> dict[str, Any]:
        return {
            "index_id": self.index_id,
            "label": self.label,
            "exchange": self.exchange,
            "currency": self.currency,
        }


INDIA_BENCHMARK_INDICES: tuple[BenchmarkIndex, ...] = (
    BenchmarkIndex(index_id="NIFTY50", label="NIFTY 50", exchange="NSE"),
    BenchmarkIndex(index_id="SENSEX", label="SENSEX", exchange="BSE"),
    BenchmarkIndex(index_id="NIFTYIT", label="NIFTY IT", exchange="NSE"),
    BenchmarkIndex(index_id="NIFTYBANK", label="NIFTY BANK", exchange="NSE"),
)


def _f(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    if out != out:  # NaN
        return None
    return out


@dataclass(frozen=True, slots=True)
class MarketIndexSnapshot:
    """Provider-reported index snapshot. ``authenticated`` is False for Null."""

    index: BenchmarkIndex
    value: float | None
    change: float | None
    change_percent: float | None
    previous_close: float | None
    sparkline: tuple[float, ...]
    as_of: str | None
    provenance: MarketQuoteProvenance | None
    authenticated: bool = True

    @property
    def available(self) -> bool:
        return self.authenticated and self.value is not None

    def to_public_dict(self) -> dict[str, Any]:
        return {
            **self.index.to_dict(),
            "available": self.available,
            "authenticated": self.authenticated,
            "value": self.value,
            "change": self.change,
            "change_percent": self.change_percent,
            "previous_close": self.previous_close,
            "sparkline": list(self.sparkline),
            "as_of": self.as_of,
            "provenance": self.provenance.to_dict() if self.provenance else None,
        }


def unavailable_snapshot(index: BenchmarkIndex) -> MarketIndexSnapshot:
    return MarketIndexSnapshot(
        index=index,
        value=None,
        change=None,
        change_percent=None,
        previous_close=None,
        sparkline=(),
        as_of=None,
        provenance=None,
        authenticated=False,
    )


class MarketIndexPort(Protocol):
    """Provider boundary for benchmark index snapshots."""

    @property
    def provider_id(self) -> str: ...

    @property
    def authenticated(self) -> bool: ...

    def get_snapshot(self, index: BenchmarkIndex) -> MarketIndexSnapshot | None: ...


@dataclass
class NullMarketIndexAdapter:
    """No approved feed — every index is honestly unavailable."""

    _provider_id: str = "null_market_index"

    @property
    def provider_id(self) -> str:
        return self._provider_id

    @property
    def authenticated(self) -> bool:
        return False

    def get_snapshot(self, index: BenchmarkIndex) -> MarketIndexSnapshot | None:
        return None


# Provider symbol map — adapter-private. The browser never sees these.
_FMP_INDEX_SYMBOLS: Mapping[str, str] = {
    "NIFTY50": "^NSEI",
    "SENSEX": "^BSESN",
    "NIFTYIT": "^CNXIT",
    "NIFTYBANK": "^NSEBANK",
}


@dataclass
class FinancialModelingPrepIndexAdapter:
    """Authenticated FMP ``/quote`` + ``/historical-price-full`` for indices."""

    api_key: str
    base_url: str = "https://financialmodelingprep.com/api/v3"
    timeout_seconds: float = 15.0
    http_client: JsonHttpClient | None = None
    symbols: Mapping[str, str] = field(default_factory=lambda: dict(_FMP_INDEX_SYMBOLS))
    _provider_id: str = "fmp_market_index"
    provider_name: str = "Financial Modeling Prep"

    @property
    def provider_id(self) -> str:
        return self._provider_id

    @property
    def authenticated(self) -> bool:
        return bool(self.api_key.strip())

    def _client(self) -> JsonHttpClient:
        return self.http_client or UrllibJsonHttpClient(
            timeout_seconds=self.timeout_seconds
        )

    def provider_symbol(self, index: BenchmarkIndex) -> str | None:
        return self.symbols.get(index.index_id)

    def get_snapshot(self, index: BenchmarkIndex) -> MarketIndexSnapshot | None:
        if not self.authenticated:
            raise ProviderRequestError("FMP index adapter requires api_key")
        symbol = self.provider_symbol(index)
        if not symbol:
            return None
        base = self.base_url.rstrip("/")
        client = self._client()

        quote_payload = client.get_json(
            f"{base}/quote/{symbol}", params={"apikey": self.api_key}
        )
        if not isinstance(quote_payload, list) or not quote_payload:
            return None
        row = quote_payload[0]
        if not isinstance(row, Mapping):
            return None

        sparkline: tuple[float, ...] = ()
        try:
            history = client.get_json(
                f"{base}/historical-price-full/{symbol}",
                params={"apikey": self.api_key, "timeseries": str(SPARKLINE_POINTS)},
            )
            rows: Any = (
                history.get("historical") if isinstance(history, Mapping) else history
            )
            if isinstance(rows, list):
                closes = [
                    _f(r.get("close"))
                    for r in rows
                    if isinstance(r, Mapping) and _f(r.get("close")) is not None
                ]
                # FMP returns newest-first; sparkline reads oldest → newest.
                sparkline = tuple(
                    c for c in reversed(closes[:SPARKLINE_POINTS]) if c is not None
                )
        except ProviderRequestError:
            sparkline = ()

        ts = _f(row.get("timestamp"))
        as_of = (
            datetime.fromtimestamp(ts, tz=UTC).isoformat() if ts is not None else None
        )
        provenance = MarketQuoteProvenance(
            provider_id=self.provider_id,
            provider_name=self.provider_name,
            source_type="licensed_vendor",
            retrieved_at=datetime.now(tz=UTC),
            auth_mode="api_key",
            metadata={"base_url": self.base_url, "vendor": "fmp"},
        )
        return MarketIndexSnapshot(
            index=index,
            value=_f(row.get("price")),
            change=_f(row.get("change")),
            change_percent=_f(row.get("changesPercentage")),
            previous_close=_f(row.get("previousClose")),
            sparkline=sparkline,
            as_of=as_of,
            provenance=provenance,
            authenticated=True,
        )


def build_default_index_adapter_from_env() -> MarketIndexPort:
    """Same P1-03 selection policy as the quote adapter (no fabricated feed)."""
    from data_engine.fmp_investment import resolve_fmp_api_key
    from data_engine.investment_data_provider import resolve_investment_data_provider

    provider = resolve_investment_data_provider()
    if provider == "unavailable":
        return NullMarketIndexAdapter()
    fmp_key = resolve_fmp_api_key()
    if fmp_key:
        return FinancialModelingPrepIndexAdapter(api_key=fmp_key)
    # ConfiguredHttp quote vendors do not publish an index contract; without
    # an approved authenticated key the market bar is honestly unavailable.
    return NullMarketIndexAdapter()


class MarketIndexService:
    """Catalogue-driven snapshot fan-out; per-index failures stay per-index."""

    def __init__(
        self,
        adapter: MarketIndexPort,
        catalogue: tuple[BenchmarkIndex, ...] = INDIA_BENCHMARK_INDICES,
    ) -> None:
        self._adapter = adapter
        self._catalogue = catalogue

    @property
    def provider_id(self) -> str:
        return self._adapter.provider_id

    @property
    def authenticated(self) -> bool:
        return self._adapter.authenticated

    def catalogue(self) -> tuple[BenchmarkIndex, ...]:
        return self._catalogue

    def get_snapshots(self) -> list[MarketIndexSnapshot]:
        out: list[MarketIndexSnapshot] = []
        for index in self._catalogue:
            if not self._adapter.authenticated:
                out.append(unavailable_snapshot(index))
                continue
            try:
                snap = self._adapter.get_snapshot(index)
            except ProviderRequestError:
                snap = None
            out.append(snap if snap is not None else unavailable_snapshot(index))
        return out

    def instrument_for(self, index: BenchmarkIndex) -> Instrument:
        return Instrument(
            symbol=index.index_id,
            asset_class=AssetClass.INDEX,
            currency=index.currency,
            exchange=index.exchange,
        )
