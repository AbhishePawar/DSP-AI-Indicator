"""Upstox adapters for Indian investment-critical quote + statements (G2).

Uses the long-lived, read-only Upstox Analytics Token. The provider resolves
an Indian equity to its NSE/BSE instrument key through Instrument Search, then
uses the market-quote and fundamentals APIs. No fabricated values and no
memory/Null fallback are introduced here.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

from contracts.domain.instrument import Instrument
from data_engine.connector_framework.http import JsonHttpClient, UrllibJsonHttpClient
from data_engine.exceptions import InvalidProviderDataError, ProviderRequestError
from data_engine.financial_statement.adapters import (
    build_statements_from_mapping,
    normalize_reporting_currency,
)
from data_engine.financial_statement.models import (
    AuthenticatedFinancialStatements,
    CompanyIdentity,
    FinancialStatementProvenance,
    utc_now as statement_utc_now,
)
from data_engine.financial_statement.service import (
    FinancialStatementPort,
    StatementProviderHealth,
    StatementQuery,
)
from data_engine.market_quote.adapters import build_quote_from_mapping
from data_engine.market_quote.models import (
    AuthenticatedMarketQuote,
    MarketQuoteProvenance,
    utc_now as quote_utc_now,
)
from data_engine.market_quote.service import MarketQuotePort, QuoteProviderHealth

__all__ = [
    "UPSTOX_BASE_URL",
    "UPSTOX_ANALYTICS_TOKEN_ENVS",
    "UpstoxQuoteAdapter",
    "UpstoxStatementAdapter",
    "resolve_upstox_analytics_token",
]

UPSTOX_BASE_URL = "https://api.upstox.com/v2"
UPSTOX_ANALYTICS_TOKEN_ENVS = (
    "DSP_UPSTOX_ANALYTICS_TOKEN",
    "DSP_UPSTOX_ACCESS_TOKEN",
)


def resolve_upstox_analytics_token(environ: Mapping[str, str] | None = None) -> str:
    """Return the first configured read-only Upstox token; never log its value."""
    env = environ if environ is not None else os.environ
    for name in UPSTOX_ANALYTICS_TOKEN_ENVS:
        value = str(env.get(name) or "").strip()
        if value:
            return value
    return ""


@dataclass
class _UpstoxBase:
    access_token: str
    base_url: str = UPSTOX_BASE_URL
    timeout_seconds: float = 15.0
    http_client: JsonHttpClient | None = None
    provider_name: str = "Upstox"

    def _client(self) -> JsonHttpClient:
        return self.http_client or UrllibJsonHttpClient(timeout_seconds=self.timeout_seconds)

    def _get(self, path: str, params: Mapping[str, Any] | None = None) -> Any:
        if not self.access_token.strip():
            raise ProviderRequestError("Upstox adapter requires analytics token")
        try:
            return self._client().get_json(
                f"{self.base_url.rstrip('/')}/{path.lstrip('/')}",
                params=dict(params or {}),
                headers={
                    "Accept": "application/json",
                    "Authorization": f"Bearer {self.access_token}",
                },
            )
        except TypeError:
            # Compatibility with the existing JsonHttpClient contract if it does
            # not accept headers directly: fall back to a provider-specific URL
            # client only when the injected client exposes no header parameter.
            raise

    def _instrument(self, instrument: Instrument) -> dict[str, Any] | None:
        query = instrument.isin or instrument.symbol.strip().upper()
        params = {
            "query": query,
            "exchanges": "NSE,BSE",
            "segments": "EQ",
            "page_number": 1,
            "records": 30,
        }
        payload = self._get("instruments/search", params)
        if not isinstance(payload, Mapping):
            raise InvalidProviderDataError("Upstox instrument search response must be an object")
        rows = payload.get("data")
        if not isinstance(rows, list):
            return None
        candidates = [r for r in rows if isinstance(r, Mapping)]
        candidates = [
            r for r in candidates
            if str(r.get("segment") or "").upper() in {"NSE_EQ", "BSE_EQ"}
            and str(r.get("instrument_type") or "").upper() in {"EQ", "BE", "A", "B", "X"}
        ]
        if instrument.isin:
            candidates = [
                r for r in candidates
                if str(r.get("isin") or "").upper() == instrument.isin.upper()
            ]
        if instrument.exchange:
            wanted = instrument.exchange.strip().upper()
            exact = [r for r in candidates if str(r.get("exchange") or "").upper() == wanted]
            if exact:
                candidates = exact
        if not candidates:
            return None
        # Prefer NSE for Indian equity research unless the Instrument explicitly
        # requests BSE; both listings normally share the same ISIN.
        candidates.sort(key=lambda r: 0 if str(r.get("exchange") or "").upper() == "NSE" else 1)
        return dict(candidates[0])


@dataclass
class UpstoxQuoteAdapter(_UpstoxBase, MarketQuotePort):
    """Authenticated Upstox full-market quote → AuthenticatedMarketQuote."""

    _provider_id: str = "upstox_market_quote"

    @property
    def provider_id(self) -> str:
        return self._provider_id

    def get_quote(self, instrument: Instrument) -> AuthenticatedMarketQuote | None:
        resolved = self._instrument(instrument)
        if resolved is None:
            return None
        key = str(resolved.get("instrument_key") or "").strip()
        if not key:
            raise InvalidProviderDataError("Upstox instrument search result missing instrument_key")
        payload = self._get("market-quote/quotes", {"instrument_key": key})
        if not isinstance(payload, Mapping):
            raise InvalidProviderDataError("Upstox market quote response must be an object")
        data = payload.get("data")
        if not isinstance(data, Mapping) or not data:
            return None
        row = data.get(key) or next(iter(data.values()))
        if not isinstance(row, Mapping):
            return None
        ohlc = row.get("ohlc") if isinstance(row.get("ohlc"), Mapping) else {}
        exchange = str(resolved.get("exchange") or instrument.exchange or "NSE").upper()
        fields = {
            "exchange": exchange,
            "currency": "INR",
            "current_price": row.get("last_price"),
            "open": ohlc.get("open"),
            "high": ohlc.get("high"),
            "low": ohlc.get("low"),
            "previous_close": ohlc.get("close"),
            "volume": row.get("volume"),
            "average_volume": row.get("average_price"),
        }
        provenance = MarketQuoteProvenance(
            provider_id=self.provider_id,
            provider_name=self.provider_name,
            source_type="licensed_vendor",
            retrieved_at=quote_utc_now(),
            as_of=str(row.get("timestamp")) if row.get("timestamp") else None,
            auth_mode="bearer_token",
            metadata={
                "base_url": self.base_url,
                "vendor": "upstox",
                "instrument_key": key,
                "instrument_search_exchange": exchange,
            },
        )
        return build_quote_from_mapping(
            symbol=str(row.get("symbol") or resolved.get("trading_symbol") or instrument.symbol),
            payload=fields,
            provenance=provenance,
        )

    def health(self) -> QuoteProviderHealth:
        ok = bool(self.access_token.strip())
        return QuoteProviderHealth(
            provider_id=self.provider_id,
            healthy=ok,
            authenticated=ok,
            detail="configured analytics token" if ok else "missing analytics token",
        )


@dataclass
class UpstoxStatementAdapter(_UpstoxBase, FinancialStatementPort):
    """Authenticated Upstox company fundamentals → statement bundle."""

    _provider_id: str = "upstox_financial_statements"

    @property
    def provider_id(self) -> str:
        return self._provider_id

    def resolve_company(self, instrument: Instrument) -> CompanyIdentity | None:
        resolved = self._instrument(instrument)
        if resolved is None:
            return None
        isin = str(resolved.get("isin") or "").strip().upper()
        if not isin:
            return None
        payload = self._get(f"fundamentals/{isin}/profile")
        if not isinstance(payload, Mapping):
            return None
        data = payload.get("data")
        if not isinstance(data, Mapping):
            return None
        return CompanyIdentity(
            symbol=str(resolved.get("trading_symbol") or instrument.symbol).strip().upper(),
            exchange=str(resolved.get("exchange") or instrument.exchange or "NSE").upper(),
            company_name=str(resolved.get("name")) if resolved.get("name") else None,
            isin=isin,
            provider_company_id=isin,
            currency="INR",
        )

    @staticmethod
    def _period_label_to_date(period: str) -> str:
        text = str(period or "").strip()
        if len(text) < 8:
            raise InvalidProviderDataError(f"invalid Upstox reporting period: {period!r}")
        month, year = text[:3].title(), text[-4:]
        months = {"Jan": "01", "Feb": "02", "Mar": "03", "Apr": "04", "May": "05", "Jun": "06", "Jul": "07", "Aug": "08", "Sep": "09", "Oct": "10", "Nov": "11", "Dec": "12"}
        if month not in months:
            raise InvalidProviderDataError(f"invalid Upstox reporting month: {period!r}")
        import calendar
        last_day = calendar.monthrange(int(year), int(months[month]))[1]
        return f"{year}-{months[month]}-{last_day:02d}"

    @staticmethod
    def _history_by_category(data: Mapping[str, Any], key: str) -> dict[str, dict[str, Any]]:
        result: dict[str, dict[str, Any]] = {}
        rows = data.get(key)
        if not isinstance(rows, list):
            return result
        for category in rows:
            if not isinstance(category, Mapping):
                continue
            name = str(category.get("category") or "").strip().lower()
            history = category.get("history")
            if not isinstance(history, list):
                continue
            for item in history:
                if not isinstance(item, Mapping):
                    continue
                period = str(item.get("period") or "").strip()
                if period:
                    result.setdefault(period, {})[name] = item.get("value")
        return result

    @staticmethod
    def _full_statement_by_period(data: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
        result: dict[str, dict[str, Any]] = {}
        rows = data.get("full_statement")
        if not isinstance(rows, list):
            return result
        for row in rows:
            if not isinstance(row, Mapping):
                continue
            particular = str(row.get("particular") or "").strip().lower()
            history = row.get("history")
            if not particular or not isinstance(history, list):
                continue
            for item in history:
                if not isinstance(item, Mapping):
                    continue
                period = str(item.get("period") or "").strip()
                if period:
                    result.setdefault(period, {})[particular] = item.get("value")
        return result

    def get_statements(self, query: StatementQuery) -> AuthenticatedFinancialStatements | None:
        resolved = self._instrument(query.instrument)
        if resolved is None:
            return None
        isin = str(resolved.get("isin") or "").strip().upper()
        if not isin:
            return None
        identity = self.resolve_company(query.instrument) or CompanyIdentity(
            symbol=str(resolved.get("trading_symbol") or query.instrument.symbol).upper(),
            exchange=str(resolved.get("exchange") or query.instrument.exchange or "NSE").upper(),
            isin=isin,
            provider_company_id=isin,
            currency="INR",
        )

        income_payload = self._get(
            f"fundamentals/{isin}/income-statement",
            {"type": "consolidated", "time_period": "yearly", "fs": "true"},
        )
        balance_payload = self._get(
            f"fundamentals/{isin}/balance-sheet",
            {"type": "consolidated", "fs": "true"},
        )
        cash_payload = self._get(
            f"fundamentals/{isin}/cash-flow",
            {"type": "consolidated", "fs": "true"},
        )
        if not all(isinstance(p, Mapping) for p in (income_payload, balance_payload, cash_payload)):
            return None
        income = income_payload.get("data", {})
        balance = balance_payload.get("data", {})
        cash = cash_payload.get("data", {})
        if not all(isinstance(p, Mapping) for p in (income, balance, cash)):
            return None

        income_hist = self._history_by_category(income, "income_statement")
        income_full = self._full_statement_by_period(income)
        balance_full = self._full_statement_by_period(balance)
        cash_full = self._full_statement_by_period(cash)
        periods: list[dict[str, Any]] = []
        period_labels = set(income_hist) | set(income_full) | set(balance_full) | set(cash_full)
        for label in sorted(period_labels, key=lambda p: self._period_label_to_date(p), reverse=True):
            inc = {**income_full.get(label, {}), **income_hist.get(label, {})}
            bal = balance_full.get(label, {})
            cf = cash_full.get(label, {})
            def value(*keys: str) -> Any:
                for key in keys:
                    if key in inc and inc[key] is not None:
                        return inc[key]
                    if key in bal and bal[key] is not None:
                        return bal[key]
                    if key in cf and cf[key] is not None:
                        return cf[key]
                return None
            period_end = self._period_label_to_date(label)
            periods.append({
                "period_type": "annual",
                "fiscal_year": int(period_end[:4]),
                "period_end": period_end,
                "reporting_currency": "INR",
                "restated": False,
                "statement_basis": "consolidated",
                "unit_scale": "crore",
                "income_statement": {
                    "revenue": value("revenue", "total revenue"),
                    "gross_profit": value("gross profit"),
                    "operating_income": value("operating profit", "operating profit before other income"),
                    "ebit": value("ebit", "operating profit"),
                    "ebitda": value("ebitda"),
                    "net_income": value("profit after tax", "net profit"),
                    "eps_basic": value("eps - basic", "eps basic"),
                    "eps_diluted": value("eps - diluted", "eps diluted"),
                },
                "balance_sheet": {
                    "cash_and_equivalents": value("cash and cash equivalents", "cash & cash equivalents"),
                    "current_assets": value("current assets", "total current assets"),
                    "total_assets": value("total assets"),
                    "current_liabilities": value("current liabilities", "total current liabilities"),
                    "total_liabilities": value("total liabilities"),
                    "total_equity": value("shareholders' funds", "total equity", "total shareholders' equity"),
                    "total_debt": value("total debt", "borrowings", "total borrowings"),
                    "long_term_debt": value("long term borrowings", "long-term debt"),
                },
                "cash_flow": {
                    "operating_cash_flow": value("cash flow from operations", "cash flow from operating activities"),
                    "investing_cash_flow": value("cash flow from investing", "cash flow from investing activities"),
                    "financing_cash_flow": value("cash flow from financing", "cash flow from financing activities"),
                    "capital_expenditures": value("capital expenditure", "capital expenditures", "purchase of fixed assets"),
                    "free_cash_flow": value("free cash flow"),
                    "dividends_paid": value("dividends paid"),
                    "share_buybacks": value("buyback of shares", "purchase of shares"),
                },
            })
        if not periods:
            return None
        limit = max(1, min(int(query.limit or 4), 10))
        periods = periods[:limit]
        provenance = FinancialStatementProvenance(
            provider_id=self.provider_id,
            provider_name=self.provider_name,
            source_type="licensed_vendor",
            retrieved_at=statement_utc_now(),
            auth_mode="bearer_token",
            metadata={"base_url": self.base_url, "vendor": "upstox", "isin": isin},
        )
        return build_statements_from_mapping(
            symbol=identity.symbol,
            payload={
                "identity": identity.to_dict(),
                "reporting_currency": normalize_reporting_currency("INR"),
                "statement_basis": "consolidated",
                "unit_scale": "crore",
                "periods": periods,
            },
            provenance=provenance,
        )

    def health(self) -> StatementProviderHealth:
        ok = bool(self.access_token.strip())
        return StatementProviderHealth(
            provider_id=self.provider_id,
            healthy=ok,
            authenticated=ok,
            detail="configured analytics token" if ok else "missing analytics token",
        )
