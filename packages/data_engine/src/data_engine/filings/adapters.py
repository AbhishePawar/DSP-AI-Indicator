"""Authenticated filings adapters.

Every vendor-specific field name lives in this file. Adapters:

- :class:`NullFilingsAdapter` / :class:`InMemoryFilingsAdapter` — safe
  defaults, mirroring every other domain.
- :class:`SecEdgarFilingsAdapter` — SEC EDGAR ``submissions`` API
  (ticker → CIK via ``company_tickers.json``, then
  ``data.sec.gov/submissions/CIK##########.json``). Free, but SEC's
  fair-access policy requires a descriptive ``User-Agent``; treated
  here as the adapter's "credential".
- :class:`FinancialModelingPrepFilingsAdapter` — FMP ``sec_filings``.
- :class:`NseFilingsAdapter` / :class:`BseFilingsAdapter` — India
  exchange corporate announcements/filings feeds.
- :class:`ScreenerFilingsAdapter` — Screener.in company document
  listings (annual reports).

NSE/BSE/Screener use unofficial public endpoints with schemas that can
change without notice; each is opt-in via an explicit env flag and
degrades to ``None`` (never raises fabricated data) on any shape it
does not recognize.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from threading import Lock
from typing import Any, Callable, Mapping

from contracts.domain.instrument import Instrument
from data_engine.connector_framework.http import JsonHttpClient, UrllibJsonHttpClient
from data_engine.connector_framework.models import (
    ConnectorCompanyIdentity,
    ConnectorProvenance,
    ProviderHealth,
    utc_now,
)
from data_engine.connector_framework.registry import PriorityProviderRegistry
from data_engine.exceptions import ProviderRequestError
from data_engine.filings.models import AuthenticatedFilings, Filing
from data_engine.filings.service import FilingsProviderPort, FilingsQuery
from data_engine.filings.validation import validate_authenticated_filings

__all__ = [
    "BseFilingsAdapter",
    "FinancialModelingPrepFilingsAdapter",
    "InMemoryFilingsAdapter",
    "NseFilingsAdapter",
    "NullFilingsAdapter",
    "ScreenerFilingsAdapter",
    "SecEdgarFilingsAdapter",
    "build_default_filings_registry_from_env",
    "build_filings_bundle_from_mapping",
]

_SEC_FORM_MAP = {
    "10-K": "10-K",
    "10-K/A": "10-K",
    "10-Q": "10-Q",
    "10-Q/A": "10-Q",
    "8-K": "8-K",
    "8-K/A": "8-K",
}


def build_filings_bundle_from_mapping(
    *, symbol: str, filings: list[Filing], provenance: ConnectorProvenance
) -> AuthenticatedFilings:
    bundle = AuthenticatedFilings(
        identity=ConnectorCompanyIdentity(symbol=symbol.strip().upper()),
        filings=tuple(filings),
        provenance=provenance,
    )
    validate_authenticated_filings(bundle)
    return bundle


def _apply_query_filters(filings: list[Filing], query: FilingsQuery) -> list[Filing]:
    result = filings
    if query.filing_types:
        wanted = set(query.filing_types)
        result = [f for f in result if f.filing_type in wanted]
    if query.start_date:
        result = [f for f in result if f.filed_at >= query.start_date]
    if query.end_date:
        result = [f for f in result if f.filed_at <= query.end_date]
    result.sort(key=lambda f: f.filed_at, reverse=True)
    return result[: max(1, query.limit)]


@dataclass
class NullFilingsAdapter(FilingsProviderPort):
    _provider_id: str = "null_filings"

    @property
    def provider_id(self) -> str:
        return self._provider_id

    def get_filings(self, query: FilingsQuery):
        return None

    def health(self) -> ProviderHealth:
        return ProviderHealth(
            provider_id=self.provider_id,
            healthy=True,
            authenticated=False,
            detail="null provider — no filings feed configured",
        )


@dataclass
class InMemoryFilingsAdapter(FilingsProviderPort):
    api_key: str | None = None
    _provider_id: str = "memory_filings"
    _bundles: dict[str, AuthenticatedFilings] = field(default_factory=dict)
    _lock: Lock = field(default_factory=Lock, repr=False)

    @property
    def provider_id(self) -> str:
        return self._provider_id

    def put(self, bundle: AuthenticatedFilings) -> None:
        validate_authenticated_filings(bundle)
        with self._lock:
            self._bundles[bundle.identity.symbol.upper()] = bundle

    def get_filings(self, query: FilingsQuery) -> AuthenticatedFilings | None:
        if not self.api_key:
            raise ProviderRequestError("memory filings adapter requires api_key (authentication)")
        with self._lock:
            bundle = self._bundles.get(query.instrument.symbol.strip().upper())
        if bundle is None:
            return None
        filings = _apply_query_filters(list(bundle.filings), query)
        if not filings:
            return None
        return AuthenticatedFilings(
            identity=bundle.identity, filings=tuple(filings), provenance=bundle.provenance
        )

    def health(self) -> ProviderHealth:
        return ProviderHealth(
            provider_id=self.provider_id,
            healthy=True,
            authenticated=bool(self.api_key),
            detail="seeded in-memory authenticated filings" if self.api_key else "missing api_key",
        )


@dataclass
class SecEdgarFilingsAdapter(FilingsProviderPort):
    """SEC EDGAR ``submissions`` feed — US-listed companies only."""

    user_agent: str
    """SEC's fair-access policy requires a descriptive User-Agent, e.g.
    ``"DSP AI Indicator research@example.com"``. Acts as this adapter's
    credential — treated as ``authenticated`` once non-empty."""
    tickers_url: str = "https://www.sec.gov/files/company_tickers.json"
    submissions_base_url: str = "https://data.sec.gov/submissions"
    archives_base_url: str = "https://www.sec.gov/Archives/edgar/data"
    timeout_seconds: float = 15.0
    http_client: JsonHttpClient | None = None
    _provider_id: str = "sec_edgar_filings"
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

    def get_filings(self, query: FilingsQuery) -> AuthenticatedFilings | None:
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
        recent = payload.get("filings", {}).get("recent") if isinstance(payload.get("filings"), Mapping) else None
        if not isinstance(recent, Mapping):
            return None
        forms = recent.get("form") or []
        filing_dates = recent.get("filingDate") or []
        accessions = recent.get("accessionNumber") or []
        primary_docs = recent.get("primaryDocument") or []
        report_dates = recent.get("reportDate") or []
        if not isinstance(forms, list) or not forms:
            return None

        cik_int = str(int(cik))
        filings: list[Filing] = []
        for i, form in enumerate(forms):
            form_str = str(form).strip()
            filing_type = _SEC_FORM_MAP.get(form_str, "other")
            filed_raw = filing_dates[i] if i < len(filing_dates) else None
            if not filed_raw:
                continue
            try:
                filed_at = date.fromisoformat(str(filed_raw)[:10])
            except ValueError:
                continue
            accession = str(accessions[i]) if i < len(accessions) and accessions[i] else None
            primary_doc = str(primary_docs[i]) if i < len(primary_docs) and primary_docs[i] else None
            url = self.archives_base_url + f"/{cik_int}"
            if accession and primary_doc:
                url += f"/{accession.replace('-', '')}/{primary_doc}"
            report_raw = report_dates[i] if i < len(report_dates) else None
            period_of_report = None
            if report_raw:
                try:
                    period_of_report = date.fromisoformat(str(report_raw)[:10])
                except ValueError:
                    period_of_report = None
            filings.append(
                Filing(
                    filing_id=accession or f"{symbol}-{form_str}-{filed_at.isoformat()}",
                    filing_type=filing_type,
                    title=f"{form_str} filed {filed_at.isoformat()}",
                    url=url,
                    filed_at=filed_at,
                    period_of_report=period_of_report,
                    accession_number=accession,
                    source="SEC EDGAR",
                    metadata={"form": form_str},
                )
            )
        filings = _apply_query_filters(filings, query)
        if not filings:
            return None
        provenance = ConnectorProvenance(
            provider_id=self.provider_id,
            provider_name="SEC EDGAR",
            source_type="regulatory_filing",
            retrieved_at=utc_now(),
            auth_mode="none",
            metadata={"cik": cik},
        )
        return build_filings_bundle_from_mapping(symbol=symbol, filings=filings, provenance=provenance)

    def health(self) -> ProviderHealth:
        ok = bool(self.user_agent.strip())
        return ProviderHealth(
            provider_id=self.provider_id,
            healthy=ok,
            authenticated=ok,
            detail="configured" if ok else "missing User-Agent (required by SEC fair-access policy)",
        )


@dataclass
class FinancialModelingPrepFilingsAdapter(FilingsProviderPort):
    api_key: str
    base_url: str = "https://financialmodelingprep.com/api/v3/sec_filings"
    timeout_seconds: float = 15.0
    http_client: JsonHttpClient | None = None
    _provider_id: str = "fmp_filings"

    @property
    def provider_id(self) -> str:
        return self._provider_id

    def _client(self) -> JsonHttpClient:
        return self.http_client or UrllibJsonHttpClient(timeout_seconds=self.timeout_seconds)

    def get_filings(self, query: FilingsQuery) -> AuthenticatedFilings | None:
        if not self.api_key.strip():
            raise ProviderRequestError("financial modeling prep filings adapter requires api_key")
        symbol = query.instrument.symbol.strip().upper()
        payload = self._client().get_json(
            f"{self.base_url}/{symbol}",
            params={"limit": str(max(1, min(query.limit, 250))), "apikey": self.api_key},
        )
        if not isinstance(payload, list) or not payload:
            return None
        filings: list[Filing] = []
        for item in payload:
            if not isinstance(item, Mapping):
                continue
            form_type = str(item.get("type") or "").strip().upper()
            filing_type = _SEC_FORM_MAP.get(form_type, "other")
            filed_raw = str(item.get("fillingDate") or "").strip()
            if not filed_raw:
                continue
            try:
                filed_at = date.fromisoformat(filed_raw[:10])
            except ValueError:
                continue
            url = str(item.get("finalLink") or item.get("link") or "").strip()
            if not url:
                continue
            filings.append(
                Filing(
                    filing_id=f"{symbol}-{form_type}-{filed_at.isoformat()}",
                    filing_type=filing_type,
                    title=f"{form_type} filed {filed_at.isoformat()}",
                    url=url,
                    filed_at=filed_at,
                    source="Financial Modeling Prep",
                    metadata={"form": form_type, "cik": str(item.get("cik") or "")},
                )
            )
        filings = _apply_query_filters(filings, query)
        if not filings:
            return None
        provenance = ConnectorProvenance(
            provider_id=self.provider_id,
            provider_name="Financial Modeling Prep",
            source_type="licensed_vendor",
            retrieved_at=utc_now(),
            auth_mode="api_key",
            metadata={"base_url": self.base_url},
        )
        return build_filings_bundle_from_mapping(symbol=symbol, filings=filings, provenance=provenance)

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
class NseFilingsAdapter(FilingsProviderPort):
    """NSE (India) corporate announcements feed.

    Uses NSE's public (unofficial) announcements endpoint. NSE's site
    generally requires a warm-up request to establish session cookies
    before ``/api/*`` calls succeed from a fresh client; production
    deployments should inject an ``http_client`` that performs that
    handshake. This adapter degrades to ``None`` rather than raising
    when NSE responds with anything unexpected (e.g. a bot challenge).
    """

    enabled: bool = False
    base_url: str = "https://www.nseindia.com/api/corporate-announcements"
    timeout_seconds: float = 15.0
    http_client: JsonHttpClient | None = None
    _provider_id: str = "nse_filings"

    @property
    def provider_id(self) -> str:
        return self._provider_id

    def _client(self) -> JsonHttpClient:
        return self.http_client or UrllibJsonHttpClient(
            timeout_seconds=self.timeout_seconds,
            default_headers={"User-Agent": "Mozilla/5.0 (dsp-data-engine)"},
        )

    def get_filings(self, query: FilingsQuery) -> AuthenticatedFilings | None:
        if not self.enabled:
            raise ProviderRequestError("NSE filings adapter is not enabled")
        symbol = query.instrument.symbol.strip().upper()
        payload = self._client().get_json(
            self.base_url, params={"index": "equities", "symbol": symbol}
        )
        if not isinstance(payload, list) or not payload:
            return None
        filings: list[Filing] = []
        for item in payload:
            if not isinstance(item, Mapping):
                continue
            desc = str(item.get("desc") or item.get("subject") or "").strip()
            attachment = str(item.get("attchmntFile") or item.get("attachment") or "").strip()
            date_raw = str(item.get("an_dt") or item.get("date") or "").strip()
            filed_at = _parse_indian_date(date_raw) if date_raw else None
            if not desc or not attachment or filed_at is None:
                continue
            filings.append(
                Filing(
                    filing_id=f"nse-{symbol}-{attachment.rsplit('/', 1)[-1]}",
                    filing_type="corporate_announcement",
                    title=desc,
                    url=attachment,
                    filed_at=filed_at,
                    source="NSE",
                )
            )
        filings = _apply_query_filters(filings, query)
        if not filings:
            return None
        provenance = ConnectorProvenance(
            provider_id=self.provider_id,
            provider_name="National Stock Exchange of India",
            source_type="exchange_feed",
            retrieved_at=utc_now(),
            auth_mode="none",
            metadata={"base_url": self.base_url},
        )
        return build_filings_bundle_from_mapping(symbol=symbol, filings=filings, provenance=provenance)

    def health(self) -> ProviderHealth:
        return ProviderHealth(
            provider_id=self.provider_id,
            healthy=self.enabled,
            authenticated=False,
            detail="enabled" if self.enabled else "disabled (set DSP_FILINGS_NSE_ENABLED=1)",
        )


@dataclass
class BseFilingsAdapter(FilingsProviderPort):
    """BSE (India) corporate announcements feed.

    BSE identifies companies by numeric "scrip code" rather than
    ticker symbol. ``scrip_code_resolver`` maps an ``Instrument``
    symbol to its BSE scrip code; the default resolver only succeeds
    when the symbol itself is already numeric, which is a real but
    narrow case — production deployments should inject a resolver
    backed by NSE/BSE's published symbol master.
    """

    enabled: bool = False
    base_url: str = "https://api.bseindia.com/BseIndiaAPI/api/AnnGetData/w"
    timeout_seconds: float = 15.0
    http_client: JsonHttpClient | None = None
    scrip_code_resolver: Callable[[str], str | None] | None = None
    _provider_id: str = "bse_filings"

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

    def get_filings(self, query: FilingsQuery) -> AuthenticatedFilings | None:
        if not self.enabled:
            raise ProviderRequestError("BSE filings adapter is not enabled")
        symbol = query.instrument.symbol.strip().upper()
        scrip_code = self._resolve_scrip_code(symbol)
        if scrip_code is None:
            return None
        payload = self._client().get_json(
            self.base_url,
            params={"strCat": "-1", "strScrip": scrip_code, "strSearch": "P", "strType": "C"},
        )
        if not isinstance(payload, Mapping):
            return None
        rows = payload.get("Table")
        if not isinstance(rows, list) or not rows:
            return None
        filings: list[Filing] = []
        for item in rows:
            if not isinstance(item, Mapping):
                continue
            subject = str(item.get("NEWSSUB") or item.get("HEADLINE") or "").strip()
            attachment = str(item.get("ATTACHMENTNAME") or "").strip()
            date_raw = str(item.get("NEWS_DT") or item.get("DissemDT") or "").strip()
            filed_at = _parse_indian_date(date_raw) if date_raw else None
            if not subject or filed_at is None:
                continue
            url = (
                f"https://www.bseindia.com/xml-data/corpfiling/AttachLive/{attachment}"
                if attachment
                else f"https://www.bseindia.com/stock-share-price/company/corp-announcements/{scrip_code}"
            )
            filings.append(
                Filing(
                    filing_id=f"bse-{scrip_code}-{filed_at.isoformat()}-{len(filings)}",
                    filing_type="corporate_announcement",
                    title=subject,
                    url=url,
                    filed_at=filed_at,
                    source="BSE",
                    metadata={"category": str(item.get("CATEGORYNAME") or "")},
                )
            )
        filings = _apply_query_filters(filings, query)
        if not filings:
            return None
        provenance = ConnectorProvenance(
            provider_id=self.provider_id,
            provider_name="BSE Limited",
            source_type="exchange_feed",
            retrieved_at=utc_now(),
            auth_mode="none",
            metadata={"base_url": self.base_url, "scrip_code": scrip_code},
        )
        return build_filings_bundle_from_mapping(symbol=symbol, filings=filings, provenance=provenance)

    def health(self) -> ProviderHealth:
        return ProviderHealth(
            provider_id=self.provider_id,
            healthy=self.enabled,
            authenticated=False,
            detail="enabled" if self.enabled else "disabled (set DSP_FILINGS_BSE_ENABLED=1)",
        )


@dataclass
class ScreenerFilingsAdapter(FilingsProviderPort):
    """Screener.in company document listing (annual reports).

    Uses Screener's unofficial company API. Where a document entry
    carries only a fiscal-year label (no explicit date), this adapter
    applies the standard Indian fiscal-year-end convention (31 March)
    as the nominal ``filed_at`` — a documented date convention, not a
    fabricated financial figure.
    """

    enabled: bool = False
    base_url: str = "https://www.screener.in/api/company"
    timeout_seconds: float = 15.0
    http_client: JsonHttpClient | None = None
    _provider_id: str = "screener_filings"
    _year_pattern = re.compile(r"(20\d{2}|19\d{2})")

    @property
    def provider_id(self) -> str:
        return self._provider_id

    def _client(self) -> JsonHttpClient:
        return self.http_client or UrllibJsonHttpClient(timeout_seconds=self.timeout_seconds)

    def get_filings(self, query: FilingsQuery) -> AuthenticatedFilings | None:
        if not self.enabled:
            raise ProviderRequestError("Screener filings adapter is not enabled")
        symbol = query.instrument.symbol.strip().upper()
        payload = self._client().get_json(f"{self.base_url}/{symbol}/")
        if not isinstance(payload, Mapping):
            return None
        documents = payload.get("documents")
        if not isinstance(documents, Mapping):
            return None
        annual_reports = documents.get("annual_reports")
        if not isinstance(annual_reports, list) or not annual_reports:
            return None
        filings: list[Filing] = []
        for item in annual_reports:
            if not isinstance(item, Mapping):
                continue
            title = str(item.get("title") or "").strip()
            link = str(item.get("link") or "").strip()
            if not title or not link:
                continue
            explicit_date = item.get("date")
            filed_at: date | None = None
            if explicit_date:
                try:
                    filed_at = date.fromisoformat(str(explicit_date)[:10])
                except ValueError:
                    filed_at = None
            if filed_at is None:
                match = self._year_pattern.search(title)
                if match:
                    filed_at = date(int(match.group(1)), 3, 31)
            if filed_at is None:
                continue
            filings.append(
                Filing(
                    filing_id=f"screener-{symbol}-{filed_at.isoformat()}",
                    filing_type="annual_report",
                    title=title,
                    url=link,
                    filed_at=filed_at,
                    source="Screener.in",
                )
            )
        filings = _apply_query_filters(filings, query)
        if not filings:
            return None
        provenance = ConnectorProvenance(
            provider_id=self.provider_id,
            provider_name="Screener.in",
            source_type="public_endpoint",
            retrieved_at=utc_now(),
            auth_mode="none",
            metadata={"base_url": self.base_url},
        )
        return build_filings_bundle_from_mapping(symbol=symbol, filings=filings, provenance=provenance)

    def health(self) -> ProviderHealth:
        return ProviderHealth(
            provider_id=self.provider_id,
            healthy=self.enabled,
            authenticated=False,
            detail="enabled" if self.enabled else "disabled (set DSP_FILINGS_SCREENER_ENABLED=1)",
        )


def build_default_filings_registry_from_env() -> PriorityProviderRegistry[FilingsProviderPort]:
    from data_engine.connector_framework.production_profile import (
        finalize_provider_registry,
        memory_adapter_allowed,
    )

    registry: PriorityProviderRegistry[FilingsProviderPort] = PriorityProviderRegistry()

    sec_ua = os.environ.get("DSP_FILINGS_SEC_EDGAR_USER_AGENT", "").strip()
    if sec_ua:
        registry.register(
            SecEdgarFilingsAdapter(user_agent=sec_ua), provider_id="sec_edgar_filings", priority=10
        )

    fmp_key = os.environ.get("DSP_FILINGS_FMP_API_KEY", "").strip()
    if fmp_key:
        registry.register(
            FinancialModelingPrepFilingsAdapter(api_key=fmp_key),
            provider_id="fmp_filings",
            priority=20,
        )

    if os.environ.get("DSP_FILINGS_NSE_ENABLED", "").lower() in {"1", "true", "yes"}:
        registry.register(
            NseFilingsAdapter(enabled=True), provider_id="nse_filings", priority=30
        )

    if os.environ.get("DSP_FILINGS_BSE_ENABLED", "").lower() in {"1", "true", "yes"}:
        registry.register(
            BseFilingsAdapter(enabled=True), provider_id="bse_filings", priority=40
        )

    if os.environ.get("DSP_FILINGS_SCREENER_ENABLED", "").lower() in {"1", "true", "yes"}:
        registry.register(
            ScreenerFilingsAdapter(enabled=True), provider_id="screener_filings", priority=50
        )

    if memory_adapter_allowed("DSP_FILINGS_MEMORY", connector="filings"):
        registry.register(
            InMemoryFilingsAdapter(api_key="dev-memory-key"),
            provider_id="memory_filings",
            priority=90,
        )

    return finalize_provider_registry(
        registry,
        connector="filings",
        null_factory=NullFilingsAdapter,
        null_provider_id="null_filings",
    )
