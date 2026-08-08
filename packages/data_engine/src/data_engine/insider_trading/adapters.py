"""Authenticated insider trading adapters.

Every vendor-specific field name lives in this file. Adapters:

- :class:`NullInsiderTradingAdapter` / :class:`InMemoryInsiderTradingAdapter`
  — safe defaults.
- :class:`SecEdgarInsiderTradingAdapter` — parses actual SEC Form 4
  (``ownershipDocument`` XML) filings: resolves ticker → CIK, lists
  recent Form 4 filings from the submissions API, then fetches and
  parses each filing's XML to extract reporting-owner name/role and
  each non-derivative transaction (code, shares, price, date).
- :class:`FinancialModelingPrepInsiderTradingAdapter` — FMP
  ``insider-trading`` endpoint (already-normalized Form 4 data).
- :class:`NseInsiderTradingAdapter` / :class:`BseInsiderTradingAdapter`
  — India exchange insider-trading (SAST/PIT) disclosures.
- :class:`YahooFinanceInsiderTradingAdapter` — Yahoo's
  ``insiderTransactions`` quoteSummary module.
"""

from __future__ import annotations

import os
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from threading import Lock
from typing import Callable, Mapping

from contracts.domain.instrument import Instrument
from data_engine.connector_framework.http import JsonHttpClient, UrllibJsonHttpClient
from data_engine.connector_framework.models import (
    ConnectorCompanyIdentity,
    ConnectorField,
    ConnectorProvenance,
    ProviderHealth,
    utc_now,
)
from data_engine.connector_framework.registry import PriorityProviderRegistry
from data_engine.exceptions import ProviderRequestError
from data_engine.insider_trading.models import AuthenticatedInsiderActivity, InsiderTransaction
from data_engine.insider_trading.service import InsiderTradingProviderPort, InsiderTradingQuery
from data_engine.insider_trading.validation import validate_authenticated_insider_activity

__all__ = [
    "BseInsiderTradingAdapter",
    "FinancialModelingPrepInsiderTradingAdapter",
    "InMemoryInsiderTradingAdapter",
    "NseInsiderTradingAdapter",
    "NullInsiderTradingAdapter",
    "SecEdgarInsiderTradingAdapter",
    "YahooFinanceInsiderTradingAdapter",
    "build_default_insider_trading_registry_from_env",
    "build_insider_activity_from_mapping",
]

_SEC_TRANSACTION_CODE_MAP = {
    "P": "buy",
    "S": "sell",
    "A": "grant",
    "M": "exercise",
    "G": "gift",
    "F": "other",
    "D": "other",
    "C": "other",
    "X": "exercise",
}


def build_insider_activity_from_mapping(
    *,
    symbol: str,
    transactions: list[InsiderTransaction],
    provenance: ConnectorProvenance,
) -> AuthenticatedInsiderActivity:
    bundle = AuthenticatedInsiderActivity(
        identity=ConnectorCompanyIdentity(symbol=symbol.strip().upper()),
        transactions=tuple(transactions),
        provenance=provenance,
    )
    validate_authenticated_insider_activity(bundle)
    return bundle


def _apply_query_filters(
    transactions: list[InsiderTransaction], query: InsiderTradingQuery
) -> list[InsiderTransaction]:
    result = transactions
    if query.start_date:
        result = [t for t in result if t.transaction_date >= query.start_date]
    if query.end_date:
        result = [t for t in result if t.transaction_date <= query.end_date]
    result.sort(key=lambda t: t.transaction_date, reverse=True)
    return result[: max(1, query.limit)]


@dataclass
class NullInsiderTradingAdapter(InsiderTradingProviderPort):
    _provider_id: str = "null_insider_trading"

    @property
    def provider_id(self) -> str:
        return self._provider_id

    def get_insider_activity(self, query: InsiderTradingQuery) -> AuthenticatedInsiderActivity | None:
        return None

    def health(self) -> ProviderHealth:
        return ProviderHealth(
            provider_id=self.provider_id,
            healthy=True,
            authenticated=False,
            detail="null provider — no insider trading feed configured",
        )


@dataclass
class InMemoryInsiderTradingAdapter(InsiderTradingProviderPort):
    api_key: str | None = None
    _provider_id: str = "memory_insider_trading"
    _bundles: dict[str, AuthenticatedInsiderActivity] = field(default_factory=dict)
    _lock: Lock = field(default_factory=Lock, repr=False)

    @property
    def provider_id(self) -> str:
        return self._provider_id

    def put(self, bundle: AuthenticatedInsiderActivity) -> None:
        validate_authenticated_insider_activity(bundle)
        with self._lock:
            self._bundles[bundle.identity.symbol.upper()] = bundle

    def get_insider_activity(self, query: InsiderTradingQuery) -> AuthenticatedInsiderActivity | None:
        if not self.api_key:
            raise ProviderRequestError(
                "memory insider trading adapter requires api_key (authentication)"
            )
        with self._lock:
            bundle = self._bundles.get(query.instrument.symbol.strip().upper())
        if bundle is None:
            return None
        transactions = _apply_query_filters(list(bundle.transactions), query)
        if not transactions:
            return None
        return AuthenticatedInsiderActivity(
            identity=bundle.identity, transactions=tuple(transactions), provenance=bundle.provenance
        )

    def health(self) -> ProviderHealth:
        return ProviderHealth(
            provider_id=self.provider_id,
            healthy=True,
            authenticated=bool(self.api_key),
            detail="seeded in-memory authenticated insider trading" if self.api_key else "missing api_key",
        )


@dataclass
class SecEdgarInsiderTradingAdapter(InsiderTradingProviderPort):
    """SEC Form 4 (``ownershipDocument`` XML) insider trading adapter."""

    user_agent: str
    tickers_url: str = "https://www.sec.gov/files/company_tickers.json"
    submissions_base_url: str = "https://data.sec.gov/submissions"
    archives_base_url: str = "https://www.sec.gov/Archives/edgar/data"
    timeout_seconds: float = 20.0
    max_filings_to_parse: int = 10
    http_client: JsonHttpClient | None = None
    _provider_id: str = "sec_edgar_insider_trading"
    _cik_map: dict[str, str] = field(default_factory=dict, repr=False)
    _lock: Lock = field(default_factory=Lock, repr=False)

    @property
    def provider_id(self) -> str:
        return self._provider_id

    def _client(self) -> JsonHttpClient:
        return self.http_client or UrllibJsonHttpClient(timeout_seconds=self.timeout_seconds)

    def _headers(self) -> dict[str, str]:
        return {"User-Agent": self.user_agent, "Accept": "application/json"}

    def _resolve_cik(self, symbol: str) -> str | None:
        with self._lock:
            if not self._cik_map:
                payload = self._client().get_json(self.tickers_url, headers=self._headers())
                if isinstance(payload, Mapping):
                    for entry in payload.values():
                        if not isinstance(entry, Mapping):
                            continue
                        ticker = str(entry.get("ticker") or "").strip().upper()
                        cik = entry.get("cik_str")
                        if ticker and cik is not None:
                            self._cik_map[ticker] = str(cik).zfill(10)
            return self._cik_map.get(symbol.upper())

    def _fetch_xml(self, url: str) -> ET.Element | None:
        request = urllib.request.Request(
            url, headers={"User-Agent": self.user_agent, "Accept": "application/xml"}, method="GET"
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                raw = response.read()
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return None
            raise ProviderRequestError(f"SEC EDGAR Form 4 fetch failed: HTTP {exc.code}") from exc
        except OSError as exc:
            raise ProviderRequestError(f"SEC EDGAR Form 4 fetch failed: {exc}") from exc
        try:
            return ET.fromstring(raw)
        except ET.ParseError:
            return None

    def _parse_form4(
        self, root: ET.Element, *, filed_at: date, accession: str
    ) -> list[InsiderTransaction]:
        def _text(el: ET.Element | None) -> str | None:
            if el is None or el.text is None:
                return None
            text = el.text.strip()
            return text or None

        owner_name = _text(root.find("./reportingOwner/reportingOwnerId/rptOwnerName")) or "Unknown"
        relationship = root.find("./reportingOwner/reportingOwnerRelationship")
        role_parts: list[str] = []
        if relationship is not None:
            if _text(relationship.find("isDirector")) == "1":
                role_parts.append("Director")
            if _text(relationship.find("isOfficer")) == "1":
                title = _text(relationship.find("officerTitle")) or "Officer"
                role_parts.append(title)
            if _text(relationship.find("isTenPercentOwner")) == "1":
                role_parts.append("10% Owner")
        role = ", ".join(role_parts) or None

        transactions: list[InsiderTransaction] = []
        for i, txn_el in enumerate(root.findall("./nonDerivativeTable/nonDerivativeTransaction")):
            code = _text(txn_el.find("./transactionCoding/transactionCode"))
            txn_type = _SEC_TRANSACTION_CODE_MAP.get((code or "").upper(), "other")
            txn_date_raw = _text(txn_el.find("./transactionDate/value"))
            if not txn_date_raw:
                continue
            try:
                txn_date = date.fromisoformat(txn_date_raw[:10])
            except ValueError:
                continue
            shares_raw = _text(txn_el.find("./transactionAmounts/transactionShares/value"))
            price_raw = _text(txn_el.find("./transactionAmounts/transactionPricePerShare/value"))
            shares_field = ConnectorField.of(shares_raw)
            price_field = ConnectorField.of(price_raw)
            value_field = ConnectorField.missing()
            if shares_field.available and price_field.available:
                value_field = ConnectorField.of(float(shares_field.value) * float(price_field.value))
            transactions.append(
                InsiderTransaction(
                    transaction_id=f"{accession}-{i}",
                    insider_name=owner_name,
                    role=role,
                    transaction_type=txn_type,
                    shares=shares_field,
                    price=price_field,
                    value=value_field,
                    transaction_date=txn_date,
                    filed_at=filed_at,
                    source="SEC EDGAR (Form 4)",
                    metadata={"transaction_code": code or ""},
                )
            )
        return transactions

    def get_insider_activity(
        self, query: InsiderTradingQuery
    ) -> AuthenticatedInsiderActivity | None:
        if not self.user_agent.strip():
            raise ProviderRequestError("SEC EDGAR adapter requires a descriptive User-Agent")
        symbol = query.instrument.symbol.strip().upper()
        cik = self._resolve_cik(symbol)
        if cik is None:
            return None
        payload = self._client().get_json(
            f"{self.submissions_base_url}/CIK{cik}.json", headers=self._headers()
        )
        if not isinstance(payload, Mapping):
            return None
        filings_obj = payload.get("filings")
        recent = filings_obj.get("recent") if isinstance(filings_obj, Mapping) else None
        if not isinstance(recent, Mapping):
            return None
        forms = recent.get("form") or []
        filing_dates = recent.get("filingDate") or []
        accessions = recent.get("accessionNumber") or []
        primary_docs = recent.get("primaryDocument") or []
        if not isinstance(forms, list) or not forms:
            return None

        cik_int = str(int(cik))
        candidates: list[tuple[str, str, str]] = []
        for i, form in enumerate(forms):
            if str(form).strip().upper() not in {"4", "4/A"}:
                continue
            accession = str(accessions[i]) if i < len(accessions) and accessions[i] else None
            primary_doc = str(primary_docs[i]) if i < len(primary_docs) and primary_docs[i] else None
            filed_raw = str(filing_dates[i]) if i < len(filing_dates) else None
            if not accession or not primary_doc or not filed_raw:
                continue
            candidates.append((accession, primary_doc, filed_raw))
            if len(candidates) >= self.max_filings_to_parse:
                break

        transactions: list[InsiderTransaction] = []
        for accession, primary_doc, filed_raw in candidates:
            try:
                filed_at = date.fromisoformat(filed_raw[:10])
            except ValueError:
                continue
            url = f"{self.archives_base_url}/{cik_int}/{accession.replace('-', '')}/{primary_doc}"
            root = self._fetch_xml(url)
            if root is None:
                continue
            transactions.extend(self._parse_form4(root, filed_at=filed_at, accession=accession))

        transactions = _apply_query_filters(transactions, query)
        if not transactions:
            return None
        provenance = ConnectorProvenance(
            provider_id=self.provider_id,
            provider_name="SEC EDGAR",
            source_type="regulatory_filing",
            retrieved_at=utc_now(),
            auth_mode="none",
            metadata={"cik": cik},
        )
        return build_insider_activity_from_mapping(symbol=symbol, transactions=transactions, provenance=provenance)

    def health(self) -> ProviderHealth:
        ok = bool(self.user_agent.strip())
        return ProviderHealth(
            provider_id=self.provider_id,
            healthy=ok,
            authenticated=ok,
            detail="configured" if ok else "missing User-Agent (required by SEC fair-access policy)",
        )


@dataclass
class FinancialModelingPrepInsiderTradingAdapter(InsiderTradingProviderPort):
    api_key: str
    base_url: str = "https://financialmodelingprep.com/api/v4/insider-trading"
    timeout_seconds: float = 15.0
    http_client: JsonHttpClient | None = None
    _provider_id: str = "fmp_insider_trading"

    @property
    def provider_id(self) -> str:
        return self._provider_id

    def _client(self) -> JsonHttpClient:
        return self.http_client or UrllibJsonHttpClient(timeout_seconds=self.timeout_seconds)

    def get_insider_activity(
        self, query: InsiderTradingQuery
    ) -> AuthenticatedInsiderActivity | None:
        if not self.api_key.strip():
            raise ProviderRequestError("financial modeling prep insider trading adapter requires api_key")
        symbol = query.instrument.symbol.strip().upper()
        payload = self._client().get_json(
            self.base_url, params={"symbol": symbol, "page": "0", "apikey": self.api_key}
        )
        if not isinstance(payload, list) or not payload:
            return None
        transactions: list[InsiderTransaction] = []
        for i, item in enumerate(payload[: max(1, min(query.limit, 200))]):
            if not isinstance(item, Mapping):
                continue
            name = str(item.get("reportingName") or "").strip()
            date_raw = str(item.get("transactionDate") or "").strip()
            if not name or not date_raw:
                continue
            try:
                txn_date = date.fromisoformat(date_raw[:10])
            except ValueError:
                continue
            transaction_type_raw = str(item.get("transactionType") or "").strip()
            code = transaction_type_raw.split("-", 1)[0].strip().upper()
            txn_type = _SEC_TRANSACTION_CODE_MAP.get(code, "other")
            shares_field = ConnectorField.of(item.get("securitiesTransacted"))
            price_field = ConnectorField.of(item.get("price"))
            value_field = ConnectorField.missing()
            if shares_field.available and price_field.available:
                value_field = ConnectorField.of(float(shares_field.value) * float(price_field.value))
            filed_raw = str(item.get("filingDate") or "").strip()
            filed_at = None
            if filed_raw:
                try:
                    filed_at = date.fromisoformat(filed_raw[:10])
                except ValueError:
                    filed_at = None
            transactions.append(
                InsiderTransaction(
                    transaction_id=f"fmp-{symbol}-{i}-{txn_date.isoformat()}",
                    insider_name=name,
                    role=str(item.get("typeOfOwner")) if item.get("typeOfOwner") else None,
                    transaction_type=txn_type,
                    shares=shares_field,
                    price=price_field,
                    value=value_field,
                    transaction_date=txn_date,
                    filed_at=filed_at,
                    source="Financial Modeling Prep",
                    metadata={"raw_transaction_type": transaction_type_raw},
                )
            )
        transactions = _apply_query_filters(transactions, query)
        if not transactions:
            return None
        provenance = ConnectorProvenance(
            provider_id=self.provider_id,
            provider_name="Financial Modeling Prep",
            source_type="licensed_vendor",
            retrieved_at=utc_now(),
            auth_mode="api_key",
            metadata={"base_url": self.base_url},
        )
        return build_insider_activity_from_mapping(symbol=symbol, transactions=transactions, provenance=provenance)

    def health(self) -> ProviderHealth:
        ok = bool(self.api_key.strip())
        return ProviderHealth(
            provider_id=self.provider_id, healthy=ok, authenticated=ok,
            detail="configured" if ok else "missing api_key",
        )


def _parse_indian_date(value: str) -> date | None:
    value = value.strip()
    for fmt in ("%d-%b-%Y %H:%M:%S", "%d-%b-%Y", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(value[: len(fmt) + 4], fmt).date()
        except ValueError:
            continue
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


@dataclass
class NseInsiderTradingAdapter(InsiderTradingProviderPort):
    """NSE (India) insider trading (SAST/PIT) disclosure feed."""

    enabled: bool = False
    base_url: str = "https://www.nseindia.com/api/corporate-insider-trading"
    timeout_seconds: float = 15.0
    http_client: JsonHttpClient | None = None
    _provider_id: str = "nse_insider_trading"

    @property
    def provider_id(self) -> str:
        return self._provider_id

    def _client(self) -> JsonHttpClient:
        return self.http_client or UrllibJsonHttpClient(
            timeout_seconds=self.timeout_seconds,
            default_headers={"User-Agent": "Mozilla/5.0 (dsp-data-engine)"},
        )

    def get_insider_activity(
        self, query: InsiderTradingQuery
    ) -> AuthenticatedInsiderActivity | None:
        if not self.enabled:
            raise ProviderRequestError("NSE insider trading adapter is not enabled")
        symbol = query.instrument.symbol.strip().upper()
        payload = self._client().get_json(self.base_url, params={"index": "equities", "symbol": symbol})
        if not isinstance(payload, list) or not payload:
            return None
        transactions: list[InsiderTransaction] = []
        for i, item in enumerate(payload):
            if not isinstance(item, Mapping):
                continue
            name = str(item.get("acquirerName") or "").strip()
            date_raw = str(item.get("intimDt") or item.get("acqfromDt") or "").strip()
            txn_date = _parse_indian_date(date_raw) if date_raw else None
            if not name or txn_date is None:
                continue
            txn_type_raw = str(item.get("tdpTransactionType") or "").strip().lower()
            txn_type = "buy" if "buy" in txn_type_raw or "acqu" in txn_type_raw else (
                "sell" if "sell" in txn_type_raw or "disp" in txn_type_raw else "other"
            )
            transactions.append(
                InsiderTransaction(
                    transaction_id=f"nse-{symbol}-{i}-{txn_date.isoformat()}",
                    insider_name=name,
                    role=str(item.get("personCategory")) if item.get("personCategory") else None,
                    transaction_type=txn_type,
                    shares=ConnectorField.of(item.get("secAcq")),
                    price=ConnectorField.missing(),
                    value=ConnectorField.of(item.get("secVal")),
                    transaction_date=txn_date,
                    source="NSE",
                )
            )
        transactions = _apply_query_filters(transactions, query)
        if not transactions:
            return None
        provenance = ConnectorProvenance(
            provider_id=self.provider_id,
            provider_name="National Stock Exchange of India",
            source_type="exchange_feed",
            retrieved_at=utc_now(),
            auth_mode="none",
            metadata={"base_url": self.base_url},
        )
        return build_insider_activity_from_mapping(symbol=symbol, transactions=transactions, provenance=provenance)

    def health(self) -> ProviderHealth:
        return ProviderHealth(
            provider_id=self.provider_id,
            healthy=self.enabled,
            authenticated=False,
            detail="enabled" if self.enabled else "disabled (set DSP_INSIDER_NSE_ENABLED=1)",
        )


@dataclass
class BseInsiderTradingAdapter(InsiderTradingProviderPort):
    """BSE (India) insider trading disclosure feed (numeric scrip code)."""

    enabled: bool = False
    base_url: str = "https://api.bseindia.com/BseIndiaAPI/api/AnnSubCategoryGetData/w"
    timeout_seconds: float = 15.0
    http_client: JsonHttpClient | None = None
    scrip_code_resolver: Callable[[str], str | None] | None = None
    _provider_id: str = "bse_insider_trading"

    @property
    def provider_id(self) -> str:
        return self._provider_id

    def _client(self) -> JsonHttpClient:
        return self.http_client or UrllibJsonHttpClient(
            timeout_seconds=self.timeout_seconds,
            default_headers={"User-Agent": "Mozilla/5.0 (dsp-data-engine)"},
        )

    def _resolve_scrip_code(self, symbol: str) -> str | None:
        if self.scrip_code_resolver is not None:
            return self.scrip_code_resolver(symbol)
        return symbol if symbol.isdigit() else None

    def get_insider_activity(
        self, query: InsiderTradingQuery
    ) -> AuthenticatedInsiderActivity | None:
        if not self.enabled:
            raise ProviderRequestError("BSE insider trading adapter is not enabled")
        symbol = query.instrument.symbol.strip().upper()
        scrip_code = self._resolve_scrip_code(symbol)
        if scrip_code is None:
            return None
        payload = self._client().get_json(self.base_url, params={"scripcode": scrip_code, "strType": "SAST"})
        if not isinstance(payload, Mapping):
            return None
        rows = payload.get("Table")
        if not isinstance(rows, list) or not rows:
            return None
        transactions: list[InsiderTransaction] = []
        for i, item in enumerate(rows):
            if not isinstance(item, Mapping):
                continue
            name = str(item.get("NAME") or "").strip()
            date_raw = str(item.get("DATEOFTRANSACTION") or item.get("NEWS_DT") or "").strip()
            txn_date = _parse_indian_date(date_raw) if date_raw else None
            if not name or txn_date is None:
                continue
            txn_type_raw = str(item.get("TRANSACTIONTYPE") or "").strip().lower()
            txn_type = "buy" if "buy" in txn_type_raw or "acqu" in txn_type_raw else (
                "sell" if "sale" in txn_type_raw or "sell" in txn_type_raw or "disp" in txn_type_raw else "other"
            )
            transactions.append(
                InsiderTransaction(
                    transaction_id=f"bse-{scrip_code}-{i}-{txn_date.isoformat()}",
                    insider_name=name,
                    role=str(item.get("CATEGORY")) if item.get("CATEGORY") else None,
                    transaction_type=txn_type,
                    shares=ConnectorField.of(item.get("NOOFSHTRANSACTED")),
                    price=ConnectorField.missing(),
                    value=ConnectorField.missing(),
                    transaction_date=txn_date,
                    source="BSE",
                )
            )
        transactions = _apply_query_filters(transactions, query)
        if not transactions:
            return None
        provenance = ConnectorProvenance(
            provider_id=self.provider_id,
            provider_name="BSE Limited",
            source_type="exchange_feed",
            retrieved_at=utc_now(),
            auth_mode="none",
            metadata={"base_url": self.base_url, "scrip_code": scrip_code},
        )
        return build_insider_activity_from_mapping(symbol=symbol, transactions=transactions, provenance=provenance)

    def health(self) -> ProviderHealth:
        return ProviderHealth(
            provider_id=self.provider_id,
            healthy=self.enabled,
            authenticated=False,
            detail="enabled" if self.enabled else "disabled (set DSP_INSIDER_BSE_ENABLED=1)",
        )


@dataclass
class YahooFinanceInsiderTradingAdapter(InsiderTradingProviderPort):
    """Yahoo Finance ``insiderTransactions`` quoteSummary module."""

    enabled: bool = False
    base_url: str = "https://query1.finance.yahoo.com/v10/finance/quoteSummary"
    timeout_seconds: float = 10.0
    http_client: JsonHttpClient | None = None
    _provider_id: str = "yahoo_finance_insider_trading"

    @property
    def provider_id(self) -> str:
        return self._provider_id

    def _client(self) -> JsonHttpClient:
        return self.http_client or UrllibJsonHttpClient(timeout_seconds=self.timeout_seconds)

    def get_insider_activity(
        self, query: InsiderTradingQuery
    ) -> AuthenticatedInsiderActivity | None:
        if not self.enabled:
            raise ProviderRequestError("yahoo finance insider trading adapter is not enabled")
        symbol = query.instrument.symbol.strip().upper()
        payload = self._client().get_json(
            f"{self.base_url}/{symbol}", params={"modules": "insiderTransactions"}
        )
        if not isinstance(payload, Mapping):
            return None
        result_list = (payload.get("quoteSummary") or {}).get("result") if isinstance(
            payload.get("quoteSummary"), Mapping
        ) else None
        if not isinstance(result_list, list) or not result_list:
            return None
        insider_module = result_list[0].get("insiderTransactions") if isinstance(result_list[0], Mapping) else None
        if not isinstance(insider_module, Mapping):
            return None
        raw_transactions = insider_module.get("transactions")
        if not isinstance(raw_transactions, list) or not raw_transactions:
            return None

        transactions: list[InsiderTransaction] = []
        for i, item in enumerate(raw_transactions):
            if not isinstance(item, Mapping):
                continue
            name = str(item.get("filerName") or "").strip()
            start_date_raw = item.get("startDate")
            ts = start_date_raw.get("raw") if isinstance(start_date_raw, Mapping) else start_date_raw
            if not name or ts is None:
                continue
            try:
                txn_date = datetime.fromtimestamp(float(ts), tz=UTC).date()
            except (TypeError, ValueError):
                continue
            text = str(item.get("transactionText") or "").lower()
            if "sale" in text or "sell" in text:
                txn_type = "sell"
            elif "purchase" in text or "buy" in text:
                txn_type = "buy"
            elif "award" in text or "grant" in text:
                txn_type = "grant"
            elif "gift" in text:
                txn_type = "gift"
            elif "exercise" in text:
                txn_type = "exercise"
            else:
                txn_type = "other"
            shares_raw = item.get("shares")
            shares_val = shares_raw.get("raw") if isinstance(shares_raw, Mapping) else shares_raw
            value_raw = item.get("value")
            value_val = value_raw.get("raw") if isinstance(value_raw, Mapping) else value_raw
            transactions.append(
                InsiderTransaction(
                    transaction_id=f"yahoo-{symbol}-{i}-{txn_date.isoformat()}",
                    insider_name=name,
                    role=str(item.get("filerRelation")) if item.get("filerRelation") else None,
                    transaction_type=txn_type,
                    shares=ConnectorField.of(shares_val),
                    price=ConnectorField.missing(),
                    value=ConnectorField.of(value_val),
                    transaction_date=txn_date,
                    source="Yahoo Finance",
                    metadata={"transaction_text": str(item.get("transactionText") or "")},
                )
            )
        transactions = _apply_query_filters(transactions, query)
        if not transactions:
            return None
        provenance = ConnectorProvenance(
            provider_id=self.provider_id,
            provider_name="Yahoo Finance",
            source_type="public_endpoint",
            retrieved_at=utc_now(),
            auth_mode="none",
            metadata={"base_url": self.base_url},
        )
        return build_insider_activity_from_mapping(symbol=symbol, transactions=transactions, provenance=provenance)

    def health(self) -> ProviderHealth:
        return ProviderHealth(
            provider_id=self.provider_id,
            healthy=self.enabled,
            authenticated=False,
            detail="enabled" if self.enabled else "disabled (set DSP_INSIDER_YAHOO_ENABLED=1)",
        )


def build_default_insider_trading_registry_from_env() -> PriorityProviderRegistry[InsiderTradingProviderPort]:
    from data_engine.connector_framework.production_profile import (
        finalize_provider_registry,
        memory_adapter_allowed,
    )

    registry: PriorityProviderRegistry[InsiderTradingProviderPort] = PriorityProviderRegistry()

    sec_ua = os.environ.get("DSP_INSIDER_SEC_EDGAR_USER_AGENT", "").strip()
    if sec_ua:
        registry.register(
            SecEdgarInsiderTradingAdapter(user_agent=sec_ua),
            provider_id="sec_edgar_insider_trading",
            priority=10,
        )

    fmp_key = os.environ.get("DSP_INSIDER_FMP_API_KEY", "").strip()
    if fmp_key:
        registry.register(
            FinancialModelingPrepInsiderTradingAdapter(api_key=fmp_key),
            provider_id="fmp_insider_trading",
            priority=20,
        )

    if os.environ.get("DSP_INSIDER_NSE_ENABLED", "").lower() in {"1", "true", "yes"}:
        registry.register(
            NseInsiderTradingAdapter(enabled=True), provider_id="nse_insider_trading", priority=30
        )

    if os.environ.get("DSP_INSIDER_BSE_ENABLED", "").lower() in {"1", "true", "yes"}:
        registry.register(
            BseInsiderTradingAdapter(enabled=True), provider_id="bse_insider_trading", priority=40
        )

    if os.environ.get("DSP_INSIDER_YAHOO_ENABLED", "").lower() in {"1", "true", "yes"}:
        registry.register(
            YahooFinanceInsiderTradingAdapter(enabled=True),
            provider_id="yahoo_finance_insider_trading",
            priority=50,
        )

    if memory_adapter_allowed("DSP_INSIDER_MEMORY", connector="insider_trading"):
        registry.register(
            InMemoryInsiderTradingAdapter(api_key="dev-memory-key"),
            provider_id="memory_insider_trading",
            priority=90,
        )

    return finalize_provider_registry(
        registry,
        connector="insider_trading",
        null_factory=NullInsiderTradingAdapter,
        null_provider_id="null_insider_trading",
    )
