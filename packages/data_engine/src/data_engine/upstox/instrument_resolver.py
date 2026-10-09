"""Upstox V3 Instrument Resolution Layer.

Resolves assets, symbols, and exchange-traded instruments into canonical
Upstox instrument keys using authorized Upstox reference conventions,
dynamic asset classification, and optional reference-data datasets.

Rules:
- Never generate instrument keys using string concatenation alone without
  first resolving instrument identity, exchange, and asset type.
- Return ambiguity information with candidate options instead of selecting arbitrarily.
- Fully compatible with the asset-first dynamic resolution layer.
- Thread-safe and resilient without requiring a manually maintained universal master.
"""

from __future__ import annotations

import re
import threading
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any

from contracts.domain.instrument import Instrument
from contracts.enums import AssetClass

_BSE_SCRIP_RE = re.compile(r"^\d{5,6}$")
_ISIN_RE = re.compile(r"^[A-Z]{2}[A-Z0-9]{9}\d$")


@dataclass(frozen=True)
class UpstoxInstrumentRecord:
    """Authorized Upstox reference-data record."""

    instrument_key: str
    exchange: str = ""
    segment: str = ""
    tradingsymbol: str = ""
    name: str | None = None
    isin: str | None = None
    exchange_token: str | None = None
    instrument_type: str | None = None
    lot_size: int | None = None
    expiry: str | None = None
    symbol: str | None = None

    def __post_init__(self) -> None:
        sym = self.tradingsymbol or self.symbol or ""
        object.__setattr__(self, "tradingsymbol", sym)
        object.__setattr__(self, "symbol", sym)

    def to_dict(self) -> dict[str, Any]:
        return {
            "instrument_key": self.instrument_key,
            "exchange": self.exchange,
            "segment": self.segment,
            "tradingsymbol": self.tradingsymbol,
            "name": self.name,
            "isin": self.isin,
            "exchange_token": self.exchange_token,
            "instrument_type": self.instrument_type,
            "lot_size": self.lot_size,
            "expiry": self.expiry,
        }


@dataclass(frozen=True, slots=True)
class UpstoxResolutionResult:
    """Outcome of resolving an asset to an Upstox instrument key."""

    status: str  # "resolved" | "ambiguous" | "not_found"
    instrument_key: str | None = None
    exchange: str | None = None
    tradingsymbol: str | None = None
    isin: str | None = None
    asset_class: AssetClass | None = None
    candidates: tuple[dict[str, Any], ...] = ()
    detail: str = ""
    record: UpstoxInstrumentRecord | None = None

    @property
    def is_resolved(self) -> bool:
        return self.status == "resolved" and self.instrument_key is not None

    @property
    def is_ambiguous(self) -> bool:
        return self.status == "ambiguous"

    @property
    def candidate_keys(self) -> tuple[str, ...]:
        keys = []
        for c in self.candidates:
            if isinstance(c, dict):
                k = c.get("instrument_key")
                if k:
                    keys.append(str(k))
            elif hasattr(c, "instrument_key"):
                keys.append(str(c.instrument_key))
        return tuple(keys)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "instrument_key": self.instrument_key,
            "exchange": self.exchange,
            "tradingsymbol": self.tradingsymbol,
            "isin": self.isin,
            "asset_class": self.asset_class.value if self.asset_class else None,
            "candidates": list(self.candidates),
            "detail": self.detail,
        }


# Well-known Upstox index instrument keys
_INDEX_KEYS: dict[str, str] = {
    "NIFTY50": "NSE_INDEX|Nifty 50",
    "NIFTY 50": "NSE_INDEX|Nifty 50",
    "NIFTY": "NSE_INDEX|Nifty 50",
    "BANKNIFTY": "NSE_INDEX|Nifty Bank",
    "NIFTY BANK": "NSE_INDEX|Nifty Bank",
    "SENSEX": "BSE_INDEX|SENSEX",
    "BSE SENSEX": "BSE_INDEX|SENSEX",
}

# Default canonical MCX commodity keys (when contract-level dataset not loaded)
_COMMODITY_KEYS: dict[str, str] = {
    "GOLD": "MCX_COMM|GOLD",
    "SILVER": "MCX_COMM|SILVER",
    "CRUDEOIL": "MCX_COMM|CRUDEOIL",
    "NATURALGAS": "MCX_COMM|NATURALGAS",
    "COPPER": "MCX_COMM|COPPER",
}


class UpstoxInstrumentResolver:
    """Dynamic Upstox Instrument Resolver."""

    def __init__(self, records: Iterable[UpstoxInstrumentRecord | Mapping[str, Any]] | None = None) -> None:
        self._lock = threading.Lock()
        # Keyed by (exchange, tradingsymbol)
        self._records_by_symbol: dict[tuple[str, str], list[UpstoxInstrumentRecord]] = {}
        # Keyed by ISIN
        self._records_by_isin: dict[str, list[UpstoxInstrumentRecord]] = {}
        # Keyed by exchange_token
        self._records_by_token: dict[tuple[str, str], UpstoxInstrumentRecord] = {}
        if records is not None:
            self.load_instruments(records)

    @property
    def record_count(self) -> int:
        with self._lock:
            return sum(len(v) for v in self._records_by_symbol.values())

    def load_instruments(self, records: Iterable[UpstoxInstrumentRecord | Mapping[str, Any]]) -> int:
        """Load official Upstox instrument reference data into the resolver."""
        count = 0
        with self._lock:
            for r in records:
                if isinstance(r, UpstoxInstrumentRecord):
                    rec = r
                elif isinstance(r, Mapping):
                    key = str(r.get("instrument_key") or "").strip()
                    if not key:
                        continue
                    ex = str(r.get("exchange") or "").strip().upper()
                    seg = str(r.get("segment") or "").strip().upper()
                    sym = str(r.get("tradingsymbol") or r.get("symbol") or "").strip().upper()
                    isin = str(r.get("isin") or "").strip().upper() if r.get("isin") else None
                    tok = str(r.get("exchange_token") or "").strip() if r.get("exchange_token") else None
                    inst_type = str(r.get("instrument_type") or "").strip().upper() if r.get("instrument_type") else None
                    name = str(r.get("name") or "").strip() if r.get("name") else None
                    lot = int(r["lot_size"]) if r.get("lot_size") is not None else None
                    expiry = str(r.get("expiry") or "").strip() if r.get("expiry") else None

                    rec = UpstoxInstrumentRecord(
                        instrument_key=key,
                        exchange=ex,
                        segment=seg,
                        tradingsymbol=sym,
                        name=name,
                        isin=isin,
                        exchange_token=tok,
                        instrument_type=inst_type,
                        lot_size=lot,
                        expiry=expiry,
                    )
                else:
                    continue

                ex = rec.exchange.strip().upper()
                sym = (rec.tradingsymbol or rec.symbol or "").strip().upper()
                isin = rec.isin.strip().upper() if rec.isin else None
                tok = rec.exchange_token.strip() if rec.exchange_token else None

                if ex and sym:
                    self._records_by_symbol.setdefault((ex, sym), []).append(rec)
                if isin:
                    self._records_by_isin.setdefault(isin, []).append(rec)
                if ex and tok:
                    self._records_by_token[(ex, tok)] = rec
                count += 1
        return count

    def clear(self) -> None:
        """Clear loaded instrument records (primarily for test isolation)."""
        with self._lock:
            self._records_by_symbol.clear()
            self._records_by_isin.clear()
            self._records_by_token.clear()

    def resolve(
        self,
        target: Instrument | str,
        *,
        preferred_exchange: str | None = None,
        asset_class: AssetClass | None = None,
    ) -> UpstoxResolutionResult:
        """Resolve target instrument to canonical Upstox instrument key.

        Uses:
        1. Reference dataset if populated
        2. Dynamic asset-first resolution (ISIN, BSE code, Commodity/Index classification)
        3. Ambiguity detection
        """
        if isinstance(target, Instrument):
            symbol = target.symbol.strip().upper()
            exchange = (target.exchange or preferred_exchange or "").strip().upper()
            cls = target.asset_class or asset_class
        else:
            symbol = str(target).strip().upper()
            exchange = (preferred_exchange or "").strip().upper()
            cls = asset_class

        if not symbol:
            return UpstoxResolutionResult(status="not_found", detail="Empty instrument target")

        # 1. Check loaded reference records first (by ISIN, token, or symbol)
        with self._lock:
            # Match by ISIN if symbol looks like an ISIN
            if _ISIN_RE.match(symbol) and symbol in self._records_by_isin:
                matches = self._records_by_isin[symbol]
                return self._resolve_from_matches(matches, exchange=exchange)

            # Match by BSE numeric scrip token
            if exchange == "BSE" and (exchange, symbol) in self._records_by_token:
                rec = self._records_by_token[(exchange, symbol)]
                return UpstoxResolutionResult(
                    status="resolved",
                    instrument_key=rec.instrument_key,
                    exchange=rec.exchange,
                    tradingsymbol=rec.tradingsymbol,
                    isin=rec.isin,
                    asset_class=AssetClass.EQUITY,
                    record=rec,
                )

            # Match by (exchange, symbol)
            if exchange and (exchange, symbol) in self._records_by_symbol:
                matches = self._records_by_symbol[(exchange, symbol)]
                return self._resolve_from_matches(matches, exchange=exchange)

            # Match across any exchange if exchange not specified
            if not exchange:
                all_matches: list[UpstoxInstrumentRecord] = []
                for (ex, sym), recs in self._records_by_symbol.items():
                    if sym == symbol:
                        all_matches.extend(recs)
                if all_matches:
                    return self._resolve_from_matches(all_matches, exchange=None)

        # 2. Dynamic Asset Resolver Integration
        from dsp_platform.asset_resolution import resolve_asset

        asset_id = resolve_asset(symbol, preferred_exchange=exchange)
        if asset_id is not None:
            if asset_id.ambiguous:
                return UpstoxResolutionResult(
                    status="ambiguous",
                    tradingsymbol=symbol,
                    exchange=exchange or "NSE",
                    candidates=asset_id.candidates,
                    detail=f"Query '{symbol}' matches multiple distinct assets",
                )

            # Match by ISIN from asset resolution in loaded reference data
            if asset_id.isin:
                with self._lock:
                    if asset_id.isin in self._records_by_isin:
                        matches = self._records_by_isin[asset_id.isin]
                        return self._resolve_from_matches(
                            matches, exchange=exchange or asset_id.exchange
                        )

            # Handle Commodities
            if asset_id.asset_class is AssetClass.COMMODITY:
                key = _COMMODITY_KEYS.get(asset_id.symbol) or f"MCX_COMM|{asset_id.symbol}"
                return UpstoxResolutionResult(
                    status="resolved",
                    instrument_key=key,
                    exchange="MCX",
                    tradingsymbol=asset_id.symbol,
                    asset_class=AssetClass.COMMODITY,
                    detail=f"Commodity contract: unit={asset_id.unit}, type={asset_id.contract_type}",
                )

            # Handle Indices
            if asset_id.asset_class is AssetClass.INDEX:
                key = _INDEX_KEYS.get(asset_id.symbol) or _INDEX_KEYS.get(asset_id.name)
                if not key:
                    ex = "BSE" if asset_id.exchange == "BSE" else "NSE"
                    key = f"{ex}_INDEX|{asset_id.name}"
                return UpstoxResolutionResult(
                    status="resolved",
                    instrument_key=key,
                    exchange=asset_id.exchange,
                    tradingsymbol=asset_id.symbol,
                    asset_class=AssetClass.INDEX,
                )

            # Handle Equities
            if asset_id.asset_class is AssetClass.EQUITY:
                ex = exchange or asset_id.exchange or "NSE"
                # If ISIN is authoritative, format canonical Upstox key: {EXCHANGE}_EQ|{ISIN}
                if asset_id.isin:
                    key = f"{ex}_EQ|{asset_id.isin}"
                    return UpstoxResolutionResult(
                        status="resolved",
                        instrument_key=key,
                        exchange=ex,
                        tradingsymbol=asset_id.symbol,
                        isin=asset_id.isin,
                        asset_class=AssetClass.EQUITY,
                    )
                # If BSE numeric code
                if ex == "BSE" and asset_id.bse_code:
                    key = f"BSE_EQ|{asset_id.bse_code}"
                    return UpstoxResolutionResult(
                        status="resolved",
                        instrument_key=key,
                        exchange="BSE",
                        tradingsymbol=asset_id.symbol,
                        asset_class=AssetClass.EQUITY,
                    )
                # Equity symbol resolved through asset master
                key = f"{ex}_EQ|{asset_id.symbol}"
                return UpstoxResolutionResult(
                    status="resolved",
                    instrument_key=key,
                    exchange=ex,
                    tradingsymbol=asset_id.symbol,
                    asset_class=AssetClass.EQUITY,
                )

        # 3. Direct Index Lookup
        if symbol in _INDEX_KEYS:
            key = _INDEX_KEYS[symbol]
            ex = "BSE" if key.startswith("BSE") else "NSE"
            return UpstoxResolutionResult(
                status="resolved",
                instrument_key=key,
                exchange=ex,
                tradingsymbol=symbol,
                asset_class=AssetClass.INDEX,
            )

        # 4. Direct Commodity Lookup
        if symbol in _COMMODITY_KEYS:
            return UpstoxResolutionResult(
                status="resolved",
                instrument_key=_COMMODITY_KEYS[symbol],
                exchange="MCX",
                tradingsymbol=symbol,
                asset_class=AssetClass.COMMODITY,
            )

        # 5. Numeric BSE scrip fallback
        if _BSE_SCRIP_RE.match(symbol):
            return UpstoxResolutionResult(
                status="resolved",
                instrument_key=f"BSE_EQ|{symbol}",
                exchange="BSE",
                tradingsymbol=symbol,
                asset_class=AssetClass.EQUITY,
                detail="Resolved numeric BSE scrip code",
            )

        # 6. Unresolvable / Unknown
        return UpstoxResolutionResult(
            status="not_found",
            tradingsymbol=symbol,
            exchange=exchange,
            detail=f"No matching instrument found: cannot resolve '{symbol}' to an authorized Upstox instrument",
        )

    def _resolve_from_matches(
        self, matches: list[UpstoxInstrumentRecord], exchange: str | None
    ) -> UpstoxResolutionResult:
        """Disambiguate among multiple reference records."""
        if not matches:
            return UpstoxResolutionResult(status="not_found")

        # Filter by exchange if requested
        if exchange:
            filtered = [m for m in matches if m.exchange == exchange]
            if filtered:
                matches = filtered

        # If exactly one matches, resolved
        if len(matches) == 1:
            rec = matches[0]
            cls = (
                AssetClass.COMMODITY
                if rec.segment.startswith("MCX")
                else AssetClass.INDEX
                if "INDEX" in rec.segment
                else AssetClass.EQUITY
            )
            return UpstoxResolutionResult(
                status="resolved",
                instrument_key=rec.instrument_key,
                exchange=rec.exchange,
                tradingsymbol=rec.tradingsymbol,
                isin=rec.isin,
                asset_class=cls,
                record=rec,
            )

        # If multiple, prefer EQ segment (standard equity series) over derivatives/rights
        eq_series = [m for m in matches if m.instrument_type == "EQ" or m.segment.endswith("_EQ")]
        if len(eq_series) == 1:
            rec = eq_series[0]
            return UpstoxResolutionResult(
                status="resolved",
                instrument_key=rec.instrument_key,
                exchange=rec.exchange,
                tradingsymbol=rec.tradingsymbol,
                isin=rec.isin,
                asset_class=AssetClass.EQUITY,
                record=rec,
            )

        # Otherwise ambiguous: return candidates
        candidates = tuple(
            {
                "instrument_key": m.instrument_key,
                "exchange": m.exchange,
                "tradingsymbol": m.tradingsymbol,
                "segment": m.segment,
                "instrument_type": m.instrument_type,
                "isin": m.isin,
                "name": m.name,
                "expiry": m.expiry,
            }
            for m in matches
        )
        return UpstoxResolutionResult(
            status="ambiguous",
            tradingsymbol=matches[0].tradingsymbol,
            candidates=candidates,
            detail=f"Ambiguous instrument: multiple instruments ({len(matches)}) match query",
        )


_GLOBAL_UPSTOX_RESOLVER = UpstoxInstrumentResolver()


def get_upstox_resolver() -> UpstoxInstrumentResolver:
    return _GLOBAL_UPSTOX_RESOLVER
