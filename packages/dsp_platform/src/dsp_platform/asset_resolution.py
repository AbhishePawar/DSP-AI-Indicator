"""Asset-First Dynamic Resolution and Classification Layer.

Expands DSP-AI-Indicator from a company-only catalog into an asset-first
platform that supports:
- Dynamically resolved NSE/BSE listed equities & dual-listed securities
- Numeric BSE scrip codes (e.g. 500570, 532540, 500325)
- Commodities (Gold, Silver, Crude Oil, Natural Gas, Copper) with contract & unit details
- Indices (Nifty 50, BSE Sensex, Bank Nifty)
- Ambiguity detection & candidate options for multi-match queries
- Safe fallback for arbitrary single-token market tickers
- Clear analytical eligibility separation (never pass commodities into equity DCF/Buffett valuation)
"""

from __future__ import annotations

import re
import threading
from dataclasses import dataclass, field
from typing import Any, Mapping

from contracts.enums import AssetClass

_BSE_CODE_RE = re.compile(r"^\d{5,6}$")
_TICKER_RE = re.compile(r"^[A-Za-z0-9.\-]{1,32}$")


@dataclass(frozen=True, slots=True)
class AssetIdentity:
    """Canonical identifier and classification for any researched asset."""

    query: str
    symbol: str
    name: str
    asset_class: AssetClass
    exchange: str
    currency: str
    unit: str = "shares"
    contract_type: str = "spot"
    bse_code: str | None = None
    isin: str | None = None
    dual_listed: bool = False
    sector: str | None = None
    macro_drivers: tuple[str, ...] = ()
    ambiguous: bool = False
    candidates: tuple[dict[str, Any], ...] = ()
    provenance: str = "dsp.asset_resolver.master"

    @property
    def allows_equity_valuation(self) -> bool:
        """Only equities are eligible for DCF, Owner Earnings, and Buffett indicator."""
        return self.asset_class is AssetClass.EQUITY

    @property
    def allows_buffett_analysis(self) -> bool:
        """Buffett indicator applies strictly to equities."""
        return self.asset_class is AssetClass.EQUITY

    @property
    def allows_commodity_research(self) -> bool:
        """Commodities use contract, inventory, volatility, and macro research."""
        return self.asset_class is AssetClass.COMMODITY

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "symbol": self.symbol,
            "name": self.name,
            "asset_class": self.asset_class.value,
            "exchange": self.exchange,
            "currency": self.currency,
            "unit": self.unit,
            "contract_type": self.contract_type,
            "bse_code": self.bse_code,
            "isin": self.isin,
            "dual_listed": self.dual_listed,
            "sector": self.sector,
            "macro_drivers": list(self.macro_drivers),
            "ambiguous": self.ambiguous,
            "candidates": list(self.candidates),
            "provenance": self.provenance,
            "analytical_eligibility": {
                "equity_valuation": self.allows_equity_valuation,
                "buffett_analysis": self.allows_buffett_analysis,
                "commodity_research": self.allows_commodity_research,
                "market_quote": True,
                "ai_research": True,
            },
        }


# --- Built-in Reference Commodity Master ---
_COMMODITIES_MASTER: tuple[AssetIdentity, ...] = (
    AssetIdentity(
        query="Gold",
        symbol="GOLD",
        name="Gold",
        asset_class=AssetClass.COMMODITY,
        exchange="MCX",
        currency="INR",
        unit="10 grams",
        contract_type="futures / spot",
        macro_drivers=(
            "US Real Yields & Federal Reserve interest rate path",
            "US Dollar Index (DXY) inverse relationship",
            "Global Central Bank gold reserves accumulation",
            "Geopolitical risk & safe-haven liquidity demand",
            "Physical retail & jewelry demand in India / China",
        ),
        provenance="dsp.asset_resolver.commodities_master",
    ),
    AssetIdentity(
        query="Silver",
        symbol="SILVER",
        name="Silver",
        asset_class=AssetClass.COMMODITY,
        exchange="MCX",
        currency="INR",
        unit="1 kilogram",
        contract_type="futures / spot",
        macro_drivers=(
            "Industrial demand in photovoltaic solar panels and electronics",
            "Gold-to-Silver price ratio (mean reversion)",
            "Global manufacturing PMI and green energy transition",
            "Monetary and inflation hedging demand",
        ),
        provenance="dsp.asset_resolver.commodities_master",
    ),
    AssetIdentity(
        query="Crude Oil",
        symbol="CRUDEOIL",
        name="Crude Oil (Brent / WTI / MCX)",
        asset_class=AssetClass.COMMODITY,
        exchange="MCX",
        currency="INR",
        unit="1 barrel (bbl)",
        contract_type="futures",
        macro_drivers=(
            "OPEC+ production quotas and compliance levels",
            "US Strategic Petroleum Reserve (SPR) & EIA weekly inventory data",
            "Global industrial growth, aviation, and transport fuel consumption",
            "Geopolitical supply disruptions across the Middle East & shipping straits",
            "Refining crack spreads and seasonal refinery maintenance",
        ),
        provenance="dsp.asset_resolver.commodities_master",
    ),
    AssetIdentity(
        query="Natural Gas",
        symbol="NATURALGAS",
        name="Natural Gas",
        asset_class=AssetClass.COMMODITY,
        exchange="MCX",
        currency="INR",
        unit="1 MMBtu",
        contract_type="futures",
        macro_drivers=(
            "Weather forecasts (heating and cooling degree days)",
            "EIA underground storage injections and withdrawal reports",
            "US liquefied natural gas (LNG) export terminal capacity and demand",
            "Power generation coal-to-gas switching economics",
            "Pipeline constraints and domestic basin production volumes",
        ),
        provenance="dsp.asset_resolver.commodities_master",
    ),
    AssetIdentity(
        query="Copper",
        symbol="COPPER",
        name="Copper (Doctor Copper)",
        asset_class=AssetClass.COMMODITY,
        exchange="MCX",
        currency="INR",
        unit="1 kilogram",
        contract_type="futures",
        macro_drivers=(
            "Global manufacturing and infrastructure spending barometer",
            "Electric vehicle (EV) grid electrification copper intensity",
            "LME and Shanghai Futures Exchange warehouse stock levels",
            "South American mining supply disruptions and labor negotiations",
        ),
        provenance="dsp.asset_resolver.commodities_master",
    ),
)

# --- Built-in Reference Indices Master ---
_INDICES_MASTER: tuple[AssetIdentity, ...] = (
    AssetIdentity(
        query="Nifty 50",
        symbol="NIFTY50",
        name="Nifty 50 Index",
        asset_class=AssetClass.INDEX,
        exchange="NSE",
        currency="INR",
        unit="index points",
        contract_type="index",
        sector="Broad Market Index",
        macro_drivers=(
            "Aggregate corporate earnings growth of top 50 Indian companies",
            "FII and DII institutional equity flows",
            "RBI monetary policy and domestic liquidity",
        ),
        provenance="dsp.asset_resolver.indices_master",
    ),
    AssetIdentity(
        query="BSE Sensex",
        symbol="SENSEX",
        name="S&P BSE Sensex Index",
        asset_class=AssetClass.INDEX,
        exchange="BSE",
        currency="INR",
        unit="index points",
        contract_type="index",
        sector="Broad Market Index",
        macro_drivers=(
            "Performance of 30 financially sound large-cap Indian companies",
            "FII investment trends in Indian equities",
            "Macroeconomic GDP growth and corporate tax revenues",
        ),
        provenance="dsp.asset_resolver.indices_master",
    ),
    AssetIdentity(
        query="Bank Nifty",
        symbol="BANKNIFTY",
        name="Nifty Bank Index",
        asset_class=AssetClass.INDEX,
        exchange="NSE",
        currency="INR",
        unit="index points",
        contract_type="index",
        sector="Banking / Financial Services",
        macro_drivers=(
            "Systemic credit growth and deposit accretion rates",
            "Net interest margins (NIM) and NPA asset quality cycles",
            "RBI repo rate and regulatory capital norms",
        ),
        provenance="dsp.asset_resolver.indices_master",
    ),
)

# --- Reference Master of Popular NSE/BSE Equities ---
_EQUITIES_REFERENCE: tuple[dict[str, Any], ...] = (
    {
        "symbol": "RELIANCE",
        "name": "Reliance Industries Limited",
        "exchange": "NSE",
        "bse_code": "500325",
        "isin": "INE002A01018",
        "dual_listed": True,
        "sector": "Energy / Conglomerate",
        "aliases": ("reliance", "ril", "reliance industries"),
    },
    {
        "symbol": "TCS",
        "name": "Tata Consultancy Services Limited",
        "exchange": "NSE",
        "bse_code": "532540",
        "isin": "INE467B01029",
        "dual_listed": True,
        "sector": "Technology",
        "aliases": ("tcs", "tata consultancy", "tata consultancy services"),
    },
    {
        "symbol": "HDFCBANK",
        "name": "HDFC Bank Limited",
        "exchange": "NSE",
        "bse_code": "500180",
        "isin": "INE040A01034",
        "dual_listed": True,
        "sector": "Financials / Banking",
        "aliases": ("hdfc bank", "hdfc", "hdfcbank"),
    },
    {
        "symbol": "INFY",
        "name": "Infosys Limited",
        "exchange": "NSE",
        "bse_code": "500209",
        "isin": "INE009A01021",
        "dual_listed": True,
        "sector": "Technology",
        "aliases": ("infosys", "infy", "infosys limited"),
    },
    {
        "symbol": "ICICIBANK",
        "name": "ICICI Bank Limited",
        "exchange": "NSE",
        "bse_code": "532174",
        "isin": "INE090A01021",
        "dual_listed": True,
        "sector": "Financials / Banking",
        "aliases": ("icici", "icici bank", "icicibank"),
    },
    {
        "symbol": "HINDUNILVR",
        "name": "Hindustan Unilever Limited",
        "exchange": "NSE",
        "bse_code": "500696",
        "isin": "INE030A01027",
        "dual_listed": True,
        "sector": "Consumer Staples / FMCG",
        "aliases": ("hul", "hindustan unilever", "hindunilvr"),
    },
    {
        "symbol": "ITC",
        "name": "ITC Limited",
        "exchange": "NSE",
        "bse_code": "500875",
        "isin": "INE154A01025",
        "dual_listed": True,
        "sector": "Consumer Staples",
        "aliases": ("itc", "itc limited"),
    },
    {
        "symbol": "SBIN",
        "name": "State Bank of India",
        "exchange": "NSE",
        "bse_code": "500112",
        "isin": "INE062A01020",
        "dual_listed": True,
        "sector": "Financials / Banking",
        "aliases": ("sbi", "state bank of india", "sbin"),
    },
    {
        "symbol": "BHARTIARTL",
        "name": "Bharti Airtel Limited",
        "exchange": "NSE",
        "bse_code": "532454",
        "isin": "INE397D01024",
        "dual_listed": True,
        "sector": "Telecommunications",
        "aliases": ("airtel", "bharti airtel", "bhartiartl"),
    },
    {
        "symbol": "KOTAKBANK",
        "name": "Kotak Mahindra Bank Limited",
        "exchange": "NSE",
        "bse_code": "500247",
        "isin": "INE237A01028",
        "dual_listed": True,
        "sector": "Financials / Banking",
        "aliases": ("kotak", "kotak bank", "kotak mahindra bank"),
    },
    {
        "symbol": "LT",
        "name": "Larsen & Toubro Limited",
        "exchange": "NSE",
        "bse_code": "500510",
        "isin": "INE018A01030",
        "dual_listed": True,
        "sector": "Capital Goods / Infrastructure",
        "aliases": ("l&t", "larsen & toubro", "larsen and toubro", "lt"),
    },
    {
        "symbol": "TATAMOTORS",
        "name": "Tata Motors Limited",
        "exchange": "NSE",
        "bse_code": "500570",
        "isin": "INE155A01022",
        "dual_listed": True,
        "sector": "Automotive",
        "aliases": ("tata motors", "tatamotors", "tml"),
    },
    {
        "symbol": "TATASTEEL",
        "name": "Tata Steel Limited",
        "exchange": "NSE",
        "bse_code": "500470",
        "isin": "INE081A01020",
        "dual_listed": True,
        "sector": "Materials / Steel",
        "aliases": ("tata steel", "tatasteel"),
    },
    {
        "symbol": "AXISBANK",
        "name": "Axis Bank Limited",
        "exchange": "NSE",
        "bse_code": "532215",
        "isin": "INE238A01034",
        "dual_listed": True,
        "sector": "Financials / Banking",
        "aliases": ("axis", "axis bank", "axisbank"),
    },
    {
        "symbol": "ASIANPAINT",
        "name": "Asian Paints Limited",
        "exchange": "NSE",
        "bse_code": "500820",
        "isin": "INE021A01026",
        "dual_listed": True,
        "sector": "Materials / Paints",
        "aliases": ("asian paints", "asianpaint"),
    },
    {
        "symbol": "TITAN",
        "name": "Titan Company Limited",
        "exchange": "NSE",
        "bse_code": "500114",
        "isin": "INE280A01028",
        "dual_listed": True,
        "sector": "Consumer Discretionary",
        "aliases": ("titan", "titan company"),
    },
    {
        "symbol": "MARUTI",
        "name": "Maruti Suzuki India Limited",
        "exchange": "NSE",
        "bse_code": "532500",
        "isin": "INE585B01010",
        "dual_listed": True,
        "sector": "Automotive",
        "aliases": ("maruti", "maruti suzuki"),
    },
    {
        "symbol": "SUNPHARMA",
        "name": "Sun Pharmaceutical Industries Limited",
        "exchange": "NSE",
        "bse_code": "524715",
        "isin": "INE044A01036",
        "dual_listed": True,
        "sector": "Healthcare / Pharmaceuticals",
        "aliases": ("sun pharma", "sun pharmaceutical", "sunpharma"),
    },
    {
        "symbol": "BAJFINANCE",
        "name": "Bajaj Finance Limited",
        "exchange": "NSE",
        "bse_code": "500034",
        "isin": "INE296A01024",
        "dual_listed": True,
        "sector": "Financials / NBFC",
        "aliases": ("bajaj finance", "bajfinance"),
    },
    {
        "symbol": "NESTLEIND",
        "name": "Nestle India Limited",
        "exchange": "NSE",
        "bse_code": "500790",
        "isin": "INE239A01024",
        "dual_listed": True,
        "sector": "Consumer Staples",
        "aliases": ("nestle", "nestle india", "nestleind"),
    },
    {
        "symbol": "WIPRO",
        "name": "Wipro Limited",
        "exchange": "NSE",
        "bse_code": "507685",
        "isin": "INE075A01022",
        "dual_listed": True,
        "sector": "Technology",
        "aliases": ("wipro", "wipro limited"),
    },
    {
        "symbol": "HCLTECH",
        "name": "HCL Technologies Limited",
        "exchange": "NSE",
        "bse_code": "532281",
        "isin": "INE860A01027",
        "dual_listed": True,
        "sector": "Technology",
        "aliases": ("hcl", "hcl tech", "hcl technologies", "hcltech"),
    },
    {
        "symbol": "TATACONSUM",
        "name": "Tata Consumer Products Limited",
        "exchange": "NSE",
        "bse_code": "500800",
        "isin": "INE192A01025",
        "dual_listed": True,
        "sector": "Consumer Staples",
        "aliases": ("tata consumer", "tata consumer products", "tataconsum"),
    },
    {
        "symbol": "TATAPOWER",
        "name": "Tata Power Company Limited",
        "exchange": "NSE",
        "bse_code": "500400",
        "isin": "INE245A01021",
        "dual_listed": True,
        "sector": "Utilities / Power",
        "aliases": ("tata power", "tatapower"),
    },
    {
        "symbol": "ZOMATO",
        "name": "Zomato Limited",
        "exchange": "NSE",
        "bse_code": "543320",
        "isin": "INE758T01015",
        "dual_listed": True,
        "sector": "Consumer Services",
        "aliases": ("zomato", "zomato limited"),
    },
    {
        "symbol": "POLYCAB",
        "name": "Polycab India Limited",
        "exchange": "NSE",
        "bse_code": "542651",
        "isin": "INE455K01017",
        "dual_listed": True,
        "sector": "Capital Goods / Cables",
        "aliases": ("polycab", "polycab india"),
    },
)


class AssetResolutionService:
    """Thread-safe dynamic asset resolution and classification service."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._dynamic_cache: dict[str, AssetIdentity] = {}

    @staticmethod
    def _normalize(text: str) -> str:
        t = text.lower().strip()
        t = re.sub(r"[^\w\s]", " ", t)
        return re.sub(r"\s+", " ", t).strip()

    def resolve(
        self,
        query: str,
        *,
        preferred_exchange: str | None = None,
        currency: str = "INR",
    ) -> AssetIdentity | None:
        raw = query.strip()
        if not raw:
            return None

        cache_key = f"{raw.upper()}:{preferred_exchange.upper() if preferred_exchange else ''}"
        with self._lock:
            cached = self._dynamic_cache.get(cache_key)
            if cached is not None:
                return cached

        norm = self._normalize(raw)
        upper = raw.upper()

        # 1. Match Commodities
        for comm in _COMMODITIES_MASTER:
            if norm == self._normalize(comm.name) or upper == comm.symbol or norm == self._normalize(comm.query):
                res = AssetIdentity(
                    query=raw,
                    symbol=comm.symbol,
                    name=comm.name,
                    asset_class=comm.asset_class,
                    exchange=preferred_exchange.strip().upper() if preferred_exchange else comm.exchange,
                    currency=comm.currency,
                    unit=comm.unit,
                    contract_type=comm.contract_type,
                    macro_drivers=comm.macro_drivers,
                    provenance=comm.provenance,
                )
                self._cache(cache_key, res)
                return res

        # 2. Match Indices
        for idx in _INDICES_MASTER:
            if norm == self._normalize(idx.name) or upper == idx.symbol or norm == self._normalize(idx.query):
                res = AssetIdentity(
                    query=raw,
                    symbol=idx.symbol,
                    name=idx.name,
                    asset_class=idx.asset_class,
                    exchange=preferred_exchange.strip().upper() if preferred_exchange else idx.exchange,
                    currency=idx.currency,
                    unit=idx.unit,
                    contract_type=idx.contract_type,
                    sector=idx.sector,
                    macro_drivers=idx.macro_drivers,
                    provenance=idx.provenance,
                )
                self._cache(cache_key, res)
                return res

        # 3. Numeric BSE Scrip Code
        if _BSE_CODE_RE.match(raw):
            for eq in _EQUITIES_REFERENCE:
                if eq.get("bse_code") == raw:
                    res = AssetIdentity(
                        query=raw,
                        symbol=eq["symbol"],
                        name=eq["name"],
                        asset_class=AssetClass.EQUITY,
                        exchange=preferred_exchange.strip().upper() if preferred_exchange else "BSE",
                        currency=currency,
                        bse_code=raw,
                        isin=eq.get("isin"),
                        dual_listed=eq.get("dual_listed", True),
                        sector=eq.get("sector"),
                        provenance="dsp.asset_resolver.bse_code_master",
                    )
                    self._cache(cache_key, res)
                    return res
            # Unknown BSE Code
            res = AssetIdentity(
                query=raw,
                symbol=raw,
                name=f"BSE Scrip {raw}",
                asset_class=AssetClass.EQUITY,
                exchange=preferred_exchange.strip().upper() if preferred_exchange else "BSE",
                currency=currency,
                bse_code=raw,
                dual_listed=False,
                provenance="dsp.asset_resolver.bse_code_fallback",
            )
            self._cache(cache_key, res)
            return res

        # 4. Exact Equity Ticker Match
        for eq in _EQUITIES_REFERENCE:
            if upper == eq["symbol"]:
                res = AssetIdentity(
                    query=raw,
                    symbol=eq["symbol"],
                    name=eq["name"],
                    asset_class=AssetClass.EQUITY,
                    exchange=preferred_exchange.strip().upper() if preferred_exchange else eq["exchange"],
                    currency=currency,
                    bse_code=eq.get("bse_code"),
                    isin=eq.get("isin"),
                    dual_listed=eq.get("dual_listed", True),
                    sector=eq.get("sector"),
                    provenance="dsp.asset_resolver.equity_ticker_master",
                )
                self._cache(cache_key, res)
                return res

        # 5. Exact Equity Company Name / Alias Match
        for eq in _EQUITIES_REFERENCE:
            clean_name = self._normalize(eq["name"])
            if norm == clean_name or any(norm == self._normalize(a) for a in eq.get("aliases", ())):
                res = AssetIdentity(
                    query=raw,
                    symbol=eq["symbol"],
                    name=eq["name"],
                    asset_class=AssetClass.EQUITY,
                    exchange=preferred_exchange.strip().upper() if preferred_exchange else eq["exchange"],
                    currency=currency,
                    bse_code=eq.get("bse_code"),
                    isin=eq.get("isin"),
                    dual_listed=eq.get("dual_listed", True),
                    sector=eq.get("sector"),
                    provenance="dsp.asset_resolver.equity_name_master",
                )
                self._cache(cache_key, res)
                return res

        # 6. Ambiguity Detection (e.g. "Tata" or "Oil")
        matching_equities: list[dict[str, Any]] = []
        for eq in _EQUITIES_REFERENCE:
            clean_name = self._normalize(eq["name"])
            if norm in clean_name or any(norm in self._normalize(a) for a in eq.get("aliases", ())):
                matching_equities.append(eq)

        matching_commodities: list[AssetIdentity] = []
        for comm in _COMMODITIES_MASTER:
            if norm in self._normalize(comm.name) or norm in self._normalize(comm.query):
                matching_commodities.append(comm)

        total_matches = len(matching_equities) + len(matching_commodities)
        if total_matches > 1:
            candidates: list[dict[str, Any]] = []
            for eq in matching_equities:
                candidates.append({
                    "symbol": eq["symbol"],
                    "name": eq["name"],
                    "asset_class": AssetClass.EQUITY.value,
                    "exchange": eq["exchange"],
                    "bse_code": eq.get("bse_code"),
                })
            for comm in matching_commodities:
                candidates.append({
                    "symbol": comm.symbol,
                    "name": comm.name,
                    "asset_class": comm.asset_class.value,
                    "exchange": comm.exchange,
                    "unit": comm.unit,
                })
            return AssetIdentity(
                query=raw,
                symbol=upper,
                name=raw,
                asset_class=AssetClass.EQUITY,
                exchange=preferred_exchange.strip().upper() if preferred_exchange else "NSE",
                currency=currency,
                ambiguous=True,
                candidates=tuple(candidates),
                provenance="dsp.asset_resolver.ambiguous",
            )

        # 7. Single Valid Alphanumeric Ticker Fallback
        if _TICKER_RE.match(upper) and not re.search(r"\s", raw):
            res = AssetIdentity(
                query=raw,
                symbol=upper,
                name=upper,
                asset_class=AssetClass.EQUITY,
                exchange=preferred_exchange.strip().upper() if preferred_exchange else "NSE",
                currency=currency,
                dual_listed=False,
                provenance="dsp.asset_resolver.dynamic_ticker_fallback",
            )
            self._cache(cache_key, res)
            return res

        return None

    def _cache(self, key: str, value: AssetIdentity) -> None:
        with self._lock:
            self._dynamic_cache[key] = value

    def register_dynamic_asset(self, asset: AssetIdentity) -> None:
        cache_key = f"{asset.query.upper()}:{asset.exchange.upper()}"
        self._cache(cache_key, asset)


_GLOBAL_RESOLVER = AssetResolutionService()


def get_asset_resolver() -> AssetResolutionService:
    return _GLOBAL_RESOLVER


def resolve_asset(
    query: str,
    *,
    preferred_exchange: str | None = None,
    currency: str = "INR",
) -> AssetIdentity | None:
    return _GLOBAL_RESOLVER.resolve(
        query,
        preferred_exchange=preferred_exchange,
        currency=currency,
    )
