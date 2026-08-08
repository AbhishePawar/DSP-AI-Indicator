"""Authenticated financial statement adapters (EPIC-D002).

Retrieval only — never invents or calculates line items / ratios.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import date, datetime
from threading import Lock
from typing import Any, Mapping
from urllib.parse import urlencode

from contracts.domain.instrument import Instrument
from data_engine.exceptions import InvalidProviderDataError, ProviderRequestError
from data_engine.financial_statement.models import (
    AuthenticatedFinancialStatements,
    AuthenticatedStatementPeriod,
    CompanyIdentity,
    FinancialStatementProvenance,
    StatementField,
    utc_now,
)
from data_engine.financial_statement.service import (
    FinancialStatementPort,
    StatementProviderHealth,
    StatementQuery,
)
from data_engine.financial_statement.validation import validate_authenticated_statements

__all__ = [
    "ConfiguredHttpStatementAdapter",
    "InMemoryAuthenticatedStatementAdapter",
    "NullAuthenticatedStatementAdapter",
    "build_default_statement_adapter_from_env",
    "build_period_from_mapping",
    "build_statements_from_mapping",
    "normalize_reporting_currency",
]


def normalize_reporting_currency(currency: str | None, *, default: str = "USD") -> str:
    """Normalize to uppercase ISO 4217 — no FX conversion (identity only)."""
    if currency is None or not str(currency).strip():
        return default.strip().upper()
    code = str(currency).strip().upper()
    if len(code) != 3:
        raise InvalidProviderDataError(f"invalid reporting currency: {currency!r}")
    return code


def _parse_date(value: Any) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    text = str(value).strip()
    if not text:
        return None
    return date.fromisoformat(text[:10])


def _sf(payload: Mapping[str, Any], *keys: str) -> StatementField:
    for key in keys:
        if key in payload and payload[key] is not None:
            return StatementField.of(payload[key])
    return StatementField.missing()


def build_period_from_mapping(payload: Mapping[str, Any]) -> AuthenticatedStatementPeriod:
    """Deterministic map of vendor-neutral period dict → AuthenticatedStatementPeriod."""
    income = payload.get("income_statement")
    balance = payload.get("balance_sheet")
    cash = payload.get("cash_flow")
    ratios = payload.get("ratios")
    income_m = income if isinstance(income, Mapping) else payload
    balance_m = balance if isinstance(balance, Mapping) else payload
    cash_m = cash if isinstance(cash, Mapping) else payload
    ratios_m = ratios if isinstance(ratios, Mapping) else payload

    period_end = _parse_date(payload.get("period_end"))
    if period_end is None:
        raise InvalidProviderDataError("period missing period_end")

    period_type = str(payload.get("period_type", "annual")).strip().lower()
    fiscal_year = int(payload.get("fiscal_year") or period_end.year)
    fq = payload.get("fiscal_quarter")
    fiscal_quarter = int(fq) if fq is not None and str(fq).strip() != "" else None
    currency = normalize_reporting_currency(
        payload.get("reporting_currency") or payload.get("currency")
    )

    return AuthenticatedStatementPeriod(
        period_type=period_type,
        fiscal_year=fiscal_year,
        fiscal_quarter=fiscal_quarter,
        period_end=period_end,
        filing_date=_parse_date(payload.get("filing_date")),
        reporting_currency=currency,
        restated=bool(payload.get("restated", False)),
        revenue=_sf(income_m, "revenue"),
        cost_of_revenue=_sf(income_m, "cost_of_revenue", "cogs"),
        gross_profit=_sf(income_m, "gross_profit"),
        operating_income=_sf(income_m, "operating_income"),
        ebit=_sf(income_m, "ebit"),
        ebitda=_sf(income_m, "ebitda"),
        net_income=_sf(income_m, "net_income"),
        eps_basic=_sf(income_m, "eps_basic", "eps"),
        eps_diluted=_sf(income_m, "eps_diluted"),
        cash_and_equivalents=_sf(balance_m, "cash_and_equivalents", "cash"),
        current_assets=_sf(balance_m, "current_assets"),
        total_assets=_sf(balance_m, "total_assets"),
        current_liabilities=_sf(balance_m, "current_liabilities"),
        total_liabilities=_sf(balance_m, "total_liabilities"),
        total_equity=_sf(balance_m, "total_equity", "equity"),
        total_debt=_sf(balance_m, "total_debt"),
        long_term_debt=_sf(balance_m, "long_term_debt"),
        operating_cash_flow=_sf(cash_m, "operating_cash_flow"),
        investing_cash_flow=_sf(cash_m, "investing_cash_flow"),
        financing_cash_flow=_sf(cash_m, "financing_cash_flow"),
        capital_expenditures=_sf(cash_m, "capital_expenditures", "capex"),
        free_cash_flow=_sf(cash_m, "free_cash_flow"),
        dividends_paid=_sf(cash_m, "dividends_paid"),
        share_buybacks=_sf(cash_m, "share_buybacks"),
        roe=_sf(ratios_m, "roe"),
        roce=_sf(ratios_m, "roce"),
        debt_to_equity=_sf(ratios_m, "debt_to_equity", "debt_equity"),
        working_capital=_sf(ratios_m, "working_capital"),
        gross_margin=_sf(ratios_m, "gross_margin"),
        operating_margin=_sf(ratios_m, "operating_margin"),
        net_margin=_sf(ratios_m, "net_margin"),
        revenue_growth=_sf(ratios_m, "revenue_growth"),
        eps_growth=_sf(ratios_m, "eps_growth"),
    )


def build_statements_from_mapping(
    *,
    symbol: str,
    payload: Mapping[str, Any],
    provenance: FinancialStatementProvenance,
) -> AuthenticatedFinancialStatements:
    """Map vendor-neutral envelope → AuthenticatedFinancialStatements."""
    identity_raw = payload.get("identity")
    if isinstance(identity_raw, Mapping):
        identity = CompanyIdentity(
            symbol=str(identity_raw.get("symbol") or symbol).strip().upper(),
            exchange=(
                str(identity_raw["exchange"])
                if identity_raw.get("exchange")
                else None
            ),
            company_name=(
                str(identity_raw["company_name"])
                if identity_raw.get("company_name")
                else None
            ),
            isin=str(identity_raw["isin"]) if identity_raw.get("isin") else None,
            cik=str(identity_raw["cik"]) if identity_raw.get("cik") else None,
            provider_company_id=(
                str(identity_raw["provider_company_id"])
                if identity_raw.get("provider_company_id")
                else None
            ),
            currency=normalize_reporting_currency(
                identity_raw.get("currency") or payload.get("reporting_currency"),
                default="USD",
            ),
        )
    else:
        identity = CompanyIdentity(
            symbol=symbol.strip().upper(),
            exchange=str(payload["exchange"]) if payload.get("exchange") else None,
            currency=normalize_reporting_currency(
                payload.get("reporting_currency") or payload.get("currency")
            ),
        )

    periods_raw = payload.get("periods")
    if not isinstance(periods_raw, list) or not periods_raw:
        raise InvalidProviderDataError("statements payload missing periods")

    periods = tuple(build_period_from_mapping(p) for p in periods_raw if isinstance(p, Mapping))
    if not periods:
        raise InvalidProviderDataError("statements payload has no valid periods")

    reporting_currency = normalize_reporting_currency(
        payload.get("reporting_currency") or identity.currency
    )
    # Currency normalization: ensure all periods share reporting currency label
    # (no FX conversion — reject mixed currencies)
    currencies = {p.reporting_currency for p in periods}
    if len(currencies) > 1:
        raise InvalidProviderDataError(
            f"mixed reporting currencies in periods: {sorted(currencies)}"
        )
    if currencies and reporting_currency not in currencies:
        reporting_currency = next(iter(currencies))

    bundle = AuthenticatedFinancialStatements(
        identity=identity,
        periods=periods,
        provenance=provenance,
        reporting_currency=reporting_currency,
    )
    validate_authenticated_statements(bundle)
    return bundle


@dataclass
class NullAuthenticatedStatementAdapter(FinancialStatementPort):
    """Always unavailable — safe default when no feed is configured."""

    _provider_id: str = "null_financial_statement"

    @property
    def provider_id(self) -> str:
        return self._provider_id

    def resolve_company(self, instrument: Instrument) -> CompanyIdentity | None:
        return None

    def get_statements(
        self, query: StatementQuery
    ) -> AuthenticatedFinancialStatements | None:
        return None

    def health(self) -> StatementProviderHealth:
        return StatementProviderHealth(
            provider_id=self.provider_id,
            healthy=True,
            authenticated=False,
            detail="null provider — no financial statement feed configured",
        )


@dataclass
class InMemoryAuthenticatedStatementAdapter(FinancialStatementPort):
    """Explicitly seeded authenticated statements only — never invents symbols."""

    api_key: str | None = None
    _provider_id: str = "memory_authenticated_statements"
    _bundles: dict[str, AuthenticatedFinancialStatements] = field(default_factory=dict)
    _identities: dict[str, CompanyIdentity] = field(default_factory=dict)
    _lock: Lock = field(default_factory=Lock, repr=False)

    @property
    def provider_id(self) -> str:
        return self._provider_id

    def put(self, bundle: AuthenticatedFinancialStatements) -> None:
        validate_authenticated_statements(bundle)
        with self._lock:
            key = bundle.identity.symbol.upper()
            self._bundles[key] = bundle
            self._identities[key] = bundle.identity

    def resolve_company(self, instrument: Instrument) -> CompanyIdentity | None:
        if not self.api_key:
            raise ProviderRequestError(
                "memory statement adapter requires api_key (authentication)"
            )
        with self._lock:
            return self._identities.get(instrument.symbol.strip().upper())

    def get_statements(
        self, query: StatementQuery
    ) -> AuthenticatedFinancialStatements | None:
        if not self.api_key:
            raise ProviderRequestError(
                "memory statement adapter requires api_key (authentication)"
            )
        with self._lock:
            bundle = self._bundles.get(query.instrument.symbol.strip().upper())
        if bundle is None:
            return None

        periods = list(bundle.periods)
        if not query.include_restated:
            periods = [p for p in periods if not p.restated]
        if query.period_type:
            want = query.period_type.strip().lower()
            periods = [p for p in periods if p.period_type == want]
        # Deterministic order: newest period_end first
        periods.sort(key=lambda p: (p.period_end, p.fiscal_year), reverse=True)
        limit = max(1, min(int(query.limit), 40))
        periods = periods[:limit]
        if not periods:
            return None
        return AuthenticatedFinancialStatements(
            identity=bundle.identity,
            periods=tuple(periods),
            provenance=bundle.provenance,
            reporting_currency=bundle.reporting_currency,
        )

    def health(self) -> StatementProviderHealth:
        return StatementProviderHealth(
            provider_id=self.provider_id,
            healthy=True,
            authenticated=bool(self.api_key),
            detail=(
                "seeded in-memory authenticated statements"
                if self.api_key
                else "missing api_key"
            ),
        )


@dataclass
class ConfiguredHttpStatementAdapter(FinancialStatementPort):
    """Authenticated HTTP JSON statements adapter.

    Expects vendor-neutral JSON with ``periods`` (+ optional ``identity``).
    Requires ``api_key``. Rejects invalid payloads. No calculations.
    """

    base_url: str
    api_key: str
    timeout_seconds: float = 15.0
    _provider_id: str = "configured_http_statements"
    provider_name: str = "Configured HTTP Financial Statements"
    header_name: str = "Authorization"
    header_template: str = "Bearer {api_key}"

    @property
    def provider_id(self) -> str:
        return self._provider_id

    def _request(self, path_query: str) -> dict[str, Any] | None:
        if not self.api_key.strip():
            raise ProviderRequestError("financial statement api_key required")
        url = f"{self.base_url.rstrip('/')}{path_query}"
        req = urllib.request.Request(
            url,
            headers={
                self.header_name: self.header_template.format(api_key=self.api_key),
                "Accept": "application/json",
                "User-Agent": "dsp-data-engine-financial-statement/1.0",
            },
            method="GET",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
                raw = resp.read().decode("utf-8")
                status = getattr(resp, "status", 200)
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return None
            raise ProviderRequestError(
                f"financial statement HTTP {exc.code}: {exc.reason}"
            ) from exc
        except Exception as exc:  # noqa: BLE001
            raise ProviderRequestError(
                f"financial statement request failed: {exc}"
            ) from exc

        if status == 204:
            return None
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ProviderRequestError(
                "financial statement response is not JSON"
            ) from exc
        if not isinstance(payload, dict):
            raise ProviderRequestError("financial statement JSON must be an object")
        if payload.get("unavailable") is True:
            return None
        return payload

    def resolve_company(self, instrument: Instrument) -> CompanyIdentity | None:
        symbol = instrument.symbol.strip().upper()
        params = urlencode({"symbol": symbol})
        payload = self._request(f"/resolve?{params}")
        if payload is None:
            return None
        identity_raw = payload.get("identity") if isinstance(payload, dict) else None
        if isinstance(identity_raw, Mapping):
            return CompanyIdentity(
                symbol=str(identity_raw.get("symbol") or symbol).strip().upper(),
                exchange=(
                    str(identity_raw["exchange"])
                    if identity_raw.get("exchange")
                    else instrument.exchange
                ),
                company_name=(
                    str(identity_raw["company_name"])
                    if identity_raw.get("company_name")
                    else None
                ),
                isin=str(identity_raw["isin"]) if identity_raw.get("isin") else None,
                cik=str(identity_raw["cik"]) if identity_raw.get("cik") else None,
                provider_company_id=(
                    str(identity_raw["provider_company_id"])
                    if identity_raw.get("provider_company_id")
                    else None
                ),
                currency=normalize_reporting_currency(
                    identity_raw.get("currency"), default=instrument.currency or "USD"
                ),
            )
        return CompanyIdentity(
            symbol=symbol,
            exchange=instrument.exchange,
            currency=normalize_reporting_currency(instrument.currency),
        )

    def get_statements(
        self, query: StatementQuery
    ) -> AuthenticatedFinancialStatements | None:
        symbol = query.instrument.symbol.strip().upper()
        params: dict[str, str] = {"symbol": symbol, "limit": str(query.limit)}
        if query.period_type:
            params["period_type"] = query.period_type
        if query.instrument.exchange:
            params["exchange"] = query.instrument.exchange
        params["include_restated"] = "true" if query.include_restated else "false"
        payload = self._request(f"?{urlencode(params)}")
        if payload is None:
            return None
        provenance = FinancialStatementProvenance(
            provider_id=self.provider_id,
            provider_name=self.provider_name,
            source_type="licensed_vendor",
            retrieved_at=utc_now(),
            auth_mode="api_key",
            metadata={"base_url": self.base_url},
        )
        return build_statements_from_mapping(
            symbol=symbol, payload=payload, provenance=provenance
        )

    def health(self) -> StatementProviderHealth:
        ok = bool(self.api_key.strip() and self.base_url.strip())
        return StatementProviderHealth(
            provider_id=self.provider_id,
            healthy=ok,
            authenticated=bool(self.api_key.strip()),
            detail="configured" if ok else "missing base_url or api_key",
        )


def build_default_statement_adapter_from_env() -> FinancialStatementPort:
    """Select statement adapter from environment (no fabricated data).

    P1-03: production requires authenticated HTTP credentials; Null/memory
    cannot silently become the production provider.
    """
    from data_engine.connector_framework.production_profile import (
        memory_adapter_allowed,
        require_authenticated_http_adapter,
    )

    api_key = os.environ.get("DSP_FINANCIAL_STATEMENT_API_KEY", "").strip()
    base_url = os.environ.get("DSP_FINANCIAL_STATEMENT_BASE_URL", "").strip()
    if api_key and base_url:
        return ConfiguredHttpStatementAdapter(base_url=base_url, api_key=api_key)
    if memory_adapter_allowed(
        "DSP_FINANCIAL_STATEMENT_MEMORY", connector="financial_statement"
    ):
        return InMemoryAuthenticatedStatementAdapter(
            api_key=api_key or "dev-memory-key"
        )
    require_authenticated_http_adapter(
        connector="financial_statement",
        api_key=api_key,
        base_url=base_url,
        api_key_env="DSP_FINANCIAL_STATEMENT_API_KEY",
        base_url_env="DSP_FINANCIAL_STATEMENT_BASE_URL",
    )
    return NullAuthenticatedStatementAdapter()
