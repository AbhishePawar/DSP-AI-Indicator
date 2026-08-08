"""Financial Modeling Prep adapters for investment-critical quote + statements (G2).

One authenticated API key can satisfy both contracts. Selected when
``DSP_FMP_API_KEY`` or ``DSP_INVESTMENT_FMP_API_KEY`` is set.

Maps FMP JSON → existing MarketQuotePort / FinancialStatementPort models.
No fabricated values. No silent Null/memory fallback.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from typing import Any

from contracts.domain.instrument import Instrument
from data_engine.connector_framework.http import JsonHttpClient, UrllibJsonHttpClient
from data_engine.exceptions import ProviderRequestError
from data_engine.financial_statement.adapters import (
    build_statements_from_mapping,
    normalize_reporting_currency,
)
from data_engine.financial_statement.models import (
    AuthenticatedFinancialStatements,
    CompanyIdentity,
    FinancialStatementProvenance,
    utc_now as stmt_utc_now,
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
    "FMP_API_KEY_ENVS",
    "FMP_BASE_URL",
    "FinancialModelingPrepQuoteAdapter",
    "FinancialModelingPrepStatementAdapter",
    "resolve_fmp_api_key",
]

FMP_BASE_URL = "https://financialmodelingprep.com/api/v3"
FMP_API_KEY_ENVS = (
    "DSP_FMP_API_KEY",
    "DSP_INVESTMENT_FMP_API_KEY",
)


def resolve_fmp_api_key(environ: Mapping[str, str] | None = None) -> str:
    """Return first configured FMP investment API key (never log the value)."""
    env = environ if environ is not None else os.environ
    for name in FMP_API_KEY_ENVS:
        value = str(env.get(name) or "").strip()
        if value:
            return value
    return ""


@dataclass
class FinancialModelingPrepQuoteAdapter(MarketQuotePort):
    """Authenticated FMP ``/quote/{symbol}`` → AuthenticatedMarketQuote."""

    api_key: str
    base_url: str = FMP_BASE_URL
    timeout_seconds: float = 15.0
    http_client: JsonHttpClient | None = None
    _provider_id: str = "fmp_market_quote"
    provider_name: str = "Financial Modeling Prep"

    @property
    def provider_id(self) -> str:
        return self._provider_id

    def _client(self) -> JsonHttpClient:
        return self.http_client or UrllibJsonHttpClient(
            timeout_seconds=self.timeout_seconds
        )

    def get_quote(self, instrument: Instrument) -> AuthenticatedMarketQuote | None:
        if not self.api_key.strip():
            raise ProviderRequestError("FMP quote adapter requires api_key")
        symbol = instrument.symbol.strip().upper()
        payload = self._client().get_json(
            f"{self.base_url.rstrip('/')}/quote/{symbol}",
            params={"apikey": self.api_key},
        )
        if not isinstance(payload, list) or not payload:
            return None
        row = payload[0]
        if not isinstance(row, Mapping):
            return None
        fields = {
            "exchange": row.get("exchange"),
            "currency": row.get("currency") or instrument.currency or "USD",
            "current_price": row.get("price"),
            "open": row.get("open"),
            "high": row.get("dayHigh"),
            "low": row.get("dayLow"),
            "previous_close": row.get("previousClose"),
            "week_52_high": row.get("yearHigh"),
            "week_52_low": row.get("yearLow"),
            "volume": row.get("volume"),
            "average_volume": row.get("avgVolume"),
            "market_cap": row.get("marketCap"),
            "enterprise_value": row.get("enterpriseValue"),
            "shares_outstanding": row.get("sharesOutstanding"),
            "dividend_yield": row.get("dividendYield")
            if row.get("dividendYield") is not None
            else row.get("dividend"),
            "beta": row.get("beta"),
        }
        provenance = MarketQuoteProvenance(
            provider_id=self.provider_id,
            provider_name=self.provider_name,
            source_type="licensed_vendor",
            retrieved_at=quote_utc_now(),
            auth_mode="api_key",
            metadata={"base_url": self.base_url, "vendor": "fmp"},
        )
        return build_quote_from_mapping(
            symbol=symbol, payload=fields, provenance=provenance
        )

    def health(self) -> QuoteProviderHealth:
        ok = bool(self.api_key.strip())
        return QuoteProviderHealth(
            provider_id=self.provider_id,
            healthy=ok,
            authenticated=ok,
            detail="configured" if ok else "missing api_key",
        )


@dataclass
class FinancialModelingPrepStatementAdapter(FinancialStatementPort):
    """Authenticated FMP statements → AuthenticatedFinancialStatements."""

    api_key: str
    base_url: str = FMP_BASE_URL
    timeout_seconds: float = 20.0
    http_client: JsonHttpClient | None = None
    _provider_id: str = "fmp_financial_statements"
    provider_name: str = "Financial Modeling Prep"

    @property
    def provider_id(self) -> str:
        return self._provider_id

    def _client(self) -> JsonHttpClient:
        return self.http_client or UrllibJsonHttpClient(
            timeout_seconds=self.timeout_seconds
        )

    def _get_list(self, path: str, *, symbol: str, limit: int) -> list[dict[str, Any]]:
        payload = self._client().get_json(
            f"{self.base_url.rstrip('/')}/{path}/{symbol}",
            params={"apikey": self.api_key, "limit": str(max(1, min(limit, 40)))},
        )
        if not isinstance(payload, list):
            return []
        return [row for row in payload if isinstance(row, Mapping)]

    def resolve_company(self, instrument: Instrument) -> CompanyIdentity | None:
        if not self.api_key.strip():
            raise ProviderRequestError("FMP statements adapter requires api_key")
        symbol = instrument.symbol.strip().upper()
        payload = self._client().get_json(
            f"{self.base_url.rstrip('/')}/profile/{symbol}",
            params={"apikey": self.api_key},
        )
        if not isinstance(payload, list) or not payload:
            return None
        row = payload[0]
        if not isinstance(row, Mapping):
            return None
        return CompanyIdentity(
            symbol=str(row.get("symbol") or symbol).strip().upper(),
            exchange=str(row["exchangeShortName"])
            if row.get("exchangeShortName")
            else (str(row["exchange"]) if row.get("exchange") else instrument.exchange),
            company_name=str(row["companyName"]) if row.get("companyName") else None,
            isin=str(row["isin"]) if row.get("isin") else None,
            cik=str(row["cik"]) if row.get("cik") else None,
            provider_company_id=str(row.get("symbol") or symbol).strip().upper(),
            currency=normalize_reporting_currency(
                row.get("currency"), default=instrument.currency or "USD"
            ),
        )

    def get_statements(
        self, query: StatementQuery
    ) -> AuthenticatedFinancialStatements | None:
        if not self.api_key.strip():
            raise ProviderRequestError("FMP statements adapter requires api_key")
        symbol = query.instrument.symbol.strip().upper()
        limit = max(1, min(int(query.limit or 4), 10))
        income = self._get_list("income-statement", symbol=symbol, limit=limit)
        balance = self._get_list("balance-sheet-statement", symbol=symbol, limit=limit)
        cash = self._get_list("cash-flow-statement", symbol=symbol, limit=limit)
        if not income:
            return None

        bal_by_date = {str(r.get("date")): r for r in balance if r.get("date")}
        cash_by_date = {str(r.get("date")): r for r in cash if r.get("date")}

        identity = self.resolve_company(query.instrument) or CompanyIdentity(
            symbol=symbol,
            exchange=query.instrument.exchange,
            currency=normalize_reporting_currency(query.instrument.currency),
        )

        periods: list[dict[str, Any]] = []
        for row in income:
            period_end = str(row.get("date") or "").strip()
            if not period_end:
                continue
            b = bal_by_date.get(period_end, {})
            c = cash_by_date.get(period_end, {})
            calendar_year = row.get("calendarYear") or period_end[:4]
            try:
                fiscal_year = int(calendar_year)
            except (TypeError, ValueError):
                fiscal_year = date.fromisoformat(period_end).year
            period_label = str(row.get("period") or "FY").strip().upper()
            period_type = "annual" if period_label in {"FY", "ANNUAL"} else "quarterly"
            fiscal_quarter = None
            if period_type == "quarterly" and period_label.startswith("Q"):
                try:
                    fiscal_quarter = int(period_label[1:])
                except ValueError:
                    fiscal_quarter = None
            currency = normalize_reporting_currency(
                row.get("reportedCurrency") or identity.currency or "USD"
            )
            periods.append(
                {
                    "period_type": period_type,
                    "fiscal_year": fiscal_year,
                    "fiscal_quarter": fiscal_quarter,
                    "period_end": period_end,
                    "filing_date": row.get("fillingDate") or row.get("acceptedDate"),
                    "reporting_currency": currency,
                    "restated": False,
                    "statement_basis": "consolidated",
                    "unit_scale": "actual",
                    "income_statement": {
                        "revenue": row.get("revenue"),
                        "cost_of_revenue": row.get("costOfRevenue"),
                        "gross_profit": row.get("grossProfit"),
                        "operating_income": row.get("operatingIncome"),
                        "ebit": row.get("ebit") or row.get("operatingIncome"),
                        "ebitda": row.get("ebitda"),
                        "net_income": row.get("netIncome"),
                        "eps_basic": row.get("eps"),
                        "eps_diluted": row.get("epsdiluted"),
                    },
                    "balance_sheet": {
                        "cash_and_equivalents": b.get("cashAndCashEquivalents"),
                        "current_assets": b.get("totalCurrentAssets"),
                        "total_assets": b.get("totalAssets"),
                        "current_liabilities": b.get("totalCurrentLiabilities"),
                        "total_liabilities": b.get("totalLiabilities"),
                        "total_equity": b.get("totalStockholdersEquity")
                        or b.get("totalEquity"),
                        "total_debt": b.get("totalDebt"),
                        "long_term_debt": b.get("longTermDebt"),
                    },
                    "cash_flow": {
                        "operating_cash_flow": c.get("operatingCashFlow")
                        or c.get("netCashProvidedByOperatingActivities"),
                        "investing_cash_flow": c.get("netCashUsedForInvestingActivites")
                        or c.get("netCashUsedForInvestingActivities"),
                        "financing_cash_flow": c.get(
                            "netCashUsedProvidedByFinancingActivities"
                        ),
                        "capital_expenditures": c.get("capitalExpenditure"),
                        "free_cash_flow": c.get("freeCashFlow"),
                        "dividends_paid": c.get("dividendsPaid"),
                        "share_buybacks": c.get("commonStockRepurchased"),
                    },
                }
            )
        if not periods:
            return None

        provenance = FinancialStatementProvenance(
            provider_id=self.provider_id,
            provider_name=self.provider_name,
            source_type="licensed_vendor",
            retrieved_at=stmt_utc_now(),
            auth_mode="api_key",
            metadata={"base_url": self.base_url, "vendor": "fmp"},
        )
        envelope = {
            "identity": identity.to_dict(),
            "reporting_currency": identity.currency or "USD",
            "statement_basis": "consolidated",
            "unit_scale": "actual",
            "periods": periods,
        }
        return build_statements_from_mapping(
            symbol=symbol, payload=envelope, provenance=provenance
        )

    def health(self) -> StatementProviderHealth:
        ok = bool(self.api_key.strip())
        return StatementProviderHealth(
            provider_id=self.provider_id,
            healthy=ok,
            authenticated=ok,
            detail="configured" if ok else "missing api_key",
        )
