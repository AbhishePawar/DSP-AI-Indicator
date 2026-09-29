"""Authenticated market index snapshots (Figma Dashboard market bar).

The Figma ``Dashboard`` market bar renders four Indian benchmark indices
(NIFTY 50 · SENSEX · NIFTY IT · NIFTY BANK) with last value, day change and a
12-point sparkline. This module is the *provider layer* for that contract:

- ``INDIA_BENCHMARK_INDICES`` — canonical index catalogue (label + canonical id).
  Provider-specific symbols live in the adapter, never in the browser.
- ``MarketIndexSnapshot`` — typed, provenance-carrying snapshot; every numeric
  field may be ``None`` (CV-001: missing provider values stay missing).
- ``NullMarketIndexAdapter`` — honest absence; no commercial index vendor.
- ``build_default_index_adapter_from_env`` — official evidence only; never FMP.

Nothing here computes or approximates a value: change / change_percent are
the provider's own fields and the sparkline is the provider's close series.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from contracts.domain.instrument import Instrument
from contracts.enums import AssetClass
from data_engine.exceptions import ProviderRequestError
from data_engine.market_quote.models import MarketQuoteProvenance

__all__ = [
    "INDIA_BENCHMARK_INDICES",
    "SPARKLINE_POINTS",
    "BenchmarkIndex",
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


def build_default_index_adapter_from_env() -> MarketIndexPort:
    """No commercial index feed. Official evidence does not invent index levels."""
    from data_engine.investment_data_provider import resolve_investment_data_provider

    resolve_investment_data_provider()
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
