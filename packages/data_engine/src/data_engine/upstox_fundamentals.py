"""U4 — Authenticated Upstox company fundamentals via U1 identity.

Flow:
  human symbol → U1 resolver → ISIN
  → GET /v2/fundamentals/{isin}/income-statement|balance-sheet|cash-flow
  → AuthenticatedFinancialStatements + field-coverage report

Official endpoints (Company Fundamentals suite):
  GET /fundamentals/{isin}/profile
  GET /fundamentals/{isin}/income-statement  (?type=&time_period=&fs=)
  GET /fundamentals/{isin}/balance-sheet     (?type=&fs=)
  GET /fundamentals/{isin}/cash-flow         (?type=&fs=)
  (also exist, not required for DSP statements: key-ratios, share-holdings,
   corporate-actions, competitors)

Period semantics (official docs):
  - income-statement time_period: yearly | quarterly (category history)
  - full_statement is ALWAYS annual, even when time_period=quarterly
  - NEVER merge annual full_statement into quarterly category periods
  - period labels like ``Mar 2025`` → period_end = last calendar day of month
  - monetary units: INR Crore (data.units_in == ``crore``)

Does NOT calculate EPS CAGR, operating WC, or FCF from OCF−|capex|.
Does NOT invent AR / Inventory / AP / weighted_shares (not in official samples).
Does NOT wire into /analyse, valuation, Buffett, MoS, or recommendation.
Does NOT clear G2.

Credential: DSP_UPSTOX_ANALYTICS_TOKEN (U0).
"""

from __future__ import annotations

import calendar
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from typing import Any, Literal

from contracts.domain.instrument import Instrument
from data_engine.connector_framework.http import JsonHttpClient, UrllibJsonHttpClient
from data_engine.connector_framework.production_profile import is_production_environment
from data_engine.exceptions import InvalidProviderDataError, ProviderRequestError
from data_engine.financial_statement.adapters import (
    build_statements_from_mapping,
    normalize_reporting_currency,
)
from data_engine.financial_statement.models import (
    AuthenticatedFinancialStatements,
    CompanyIdentity,
    FinancialStatementProvenance,
    StatementField,
    utc_now as statement_utc_now,
)
from data_engine.financial_statement.service import (
    FinancialStatementPort,
    StatementProviderHealth,
    StatementQuery,
)
from data_engine.upstox_connectivity import (
    UPSTOX_ANALYTICS_TOKEN_ENV,
    redact_secret,
    resolve_u0_upstox_analytics_token,
)
from data_engine.upstox_instrument_resolver import (
    UpstoxInstrumentCandidate,
    UpstoxInstrumentResolver,
    UpstoxResolveRequest,
    UpstoxResolveResult,
)
from data_engine.upstox_investment import UPSTOX_BASE_URL

__all__ = [
    "UPSTOX_FUNDAMENTALS_PREFIX",
    "UpstoxFieldCoverage",
    "UpstoxFundamentalsClient",
    "UpstoxFundamentalsRequest",
    "UpstoxFundamentalsResult",
    "UpstoxFundamentalsStatus",
    "UpstoxStatementAdapterU4",
]

UPSTOX_FUNDAMENTALS_PREFIX = "fundamentals"

UpstoxFundamentalsStatus = Literal[
    "OK",
    "AMBIGUOUS",
    "NOT_FOUND",
    "UNAVAILABLE",
    "REJECTED",
    "EMPTY",
]

# Official documented full_statement particulars (samples). Extra vendor keys
# may appear live; we map only known aliases and never invent missing lines.
_AR_ALIASES = (
    "trade receivables",
    "trade receivable",
    "accounts receivable",
    "sundry debtors",
    "receivables",
)
_INVENTORY_ALIASES = ("inventories", "inventory", "stock-in-trade", "stock in trade")
_AP_ALIASES = (
    "trade payables",
    "trade payable",
    "accounts payable",
    "sundry creditors",
    "payables",
)
_WEIGHTED_SHARES_ALIASES = (
    "weighted average shares",
    "weighted average number of shares",
    "weighted average shares outstanding",
    "weighted shares",
    "no. of shares",
    "number of shares",
)
# Never map these to operating WC components / COGS / FCF substitutes
_FORBIDDEN_WC_SUBSTITUTES = frozenset(
    {
        "net current asset",
        "net current assets",
        "current assets",
        "current liabilities",
        "change in wc",
    }
)


@dataclass(frozen=True, slots=True)
class UpstoxFieldCoverage:
    """Honest field coverage — available only when vendor value observed & mappable."""

    field: str
    upstox_available: bool
    dsp_mapped: bool
    notes: str

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "field": self.field,
            "upstox_available": self.upstox_available,
            "dsp_mapped": self.dsp_mapped,
            "notes": self.notes,
        }


@dataclass(frozen=True, slots=True)
class UpstoxFundamentalsRequest:
    symbol: str
    period_type: str = "annual"  # annual | quarterly
    limit: int = 4
    preferred_exchange: str | None = None
    statement_type: str = "consolidated"  # consolidated | standalone
    client_isin: str | None = None
    client_instrument_key: str | None = None
    client_provider: str | None = None
    client_currency: str | None = None
    client_statements: Sequence[Any] | None = None


@dataclass(frozen=True, slots=True)
class UpstoxFundamentalsResult:
    status: UpstoxFundamentalsStatus
    query: str
    detail: str
    retrieved_at: datetime
    latency_ms: float | None = None
    http_status: int | None = None
    resolve: UpstoxResolveResult | None = None
    identity: UpstoxInstrumentCandidate | None = None
    statements: AuthenticatedFinancialStatements | None = None
    coverage: tuple[UpstoxFieldCoverage, ...] = ()
    eps_cagr_basis: str = "unavailable"  # diluted | basic | unavailable (no CAGR calc)
    annual_period_count: int = 0
    quarterly_period_count: int = 0
    currency: str | None = None
    endpoints: tuple[str, ...] = ()

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "query": self.query,
            "detail": self.detail,
            "retrieved_at": self.retrieved_at.isoformat(),
            "latency_ms": self.latency_ms,
            "http_status": self.http_status,
            "identity": None if self.identity is None else self.identity.to_public_dict(),
            "statements": None
            if self.statements is None
            else self.statements.to_public_dict(),
            "coverage": [c.to_public_dict() for c in self.coverage],
            "eps_cagr_basis": self.eps_cagr_basis,
            "annual_period_count": self.annual_period_count,
            "quarterly_period_count": self.quarterly_period_count,
            "currency": self.currency,
            "endpoints": list(self.endpoints),
            "resolve_status": None if self.resolve is None else self.resolve.status,
        }


@dataclass
class UpstoxFundamentalsClient:
    """U1 identity → authenticated Upstox fundamentals → DSP statements."""

    access_token: str | None = None
    base_url: str = UPSTOX_BASE_URL
    timeout_seconds: float = 15.0
    http_client: JsonHttpClient | None = None
    max_attempts: int = 2
    provider_id: str = "upstox_financial_statements"
    provider_name: str = "Upstox"
    resolver: UpstoxInstrumentResolver | None = None

    def __post_init__(self) -> None:
        if self.access_token is None:
            object.__setattr__(
                self, "access_token", resolve_u0_upstox_analytics_token()
            )
        object.__setattr__(self, "access_token", str(self.access_token or "").strip())
        object.__setattr__(self, "max_attempts", max(1, min(int(self.max_attempts), 3)))
        if self.resolver is None:
            object.__setattr__(
                self,
                "resolver",
                UpstoxInstrumentResolver(
                    access_token=self.access_token,
                    base_url=self.base_url,
                    timeout_seconds=self.timeout_seconds,
                    http_client=self.http_client,
                ),
            )

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

    def get_fundamentals(
        self, request: UpstoxFundamentalsRequest | str, **kwargs: Any
    ) -> UpstoxFundamentalsResult:
        retrieved_at = datetime.now(tz=UTC)
        if isinstance(request, str):
            request = UpstoxFundamentalsRequest(
                symbol=request,
                period_type=str(kwargs.get("period_type") or "annual"),
                limit=int(kwargs.get("limit") or 4),
                preferred_exchange=kwargs.get("preferred_exchange"),
            )

        query = str(request.symbol or "").strip().upper()

        if (
            str(request.client_isin or "").strip()
            or str(request.client_instrument_key or "").strip()
            or str(request.client_provider or "").strip()
            or str(request.client_currency or "").strip()
            or request.client_statements is not None
        ):
            return UpstoxFundamentalsResult(
                status="REJECTED",
                query=query,
                detail=(
                    "client-supplied isin / instrument_key / provider / currency / "
                    "statements are not authoritative"
                ),
                retrieved_at=retrieved_at,
            )

        period_kind = str(request.period_type or "annual").strip().lower()
        if period_kind in {"yearly", "year", "annual"}:
            period_kind = "annual"
            upstox_time = "yearly"
        elif period_kind in {"quarterly", "quarter"}:
            period_kind = "quarterly"
            upstox_time = "quarterly"
        elif period_kind in {"ttm"}:
            return UpstoxFundamentalsResult(
                status="REJECTED",
                query=query,
                detail="TTM not supported by Upstox income-statement time_period",
                retrieved_at=retrieved_at,
            )
        else:
            return UpstoxFundamentalsResult(
                status="REJECTED",
                query=query,
                detail=f"unknown period_type {request.period_type!r}",
                retrieved_at=retrieved_at,
            )

        stmt_type = str(request.statement_type or "consolidated").strip().lower()
        if stmt_type not in {"consolidated", "standalone"}:
            return UpstoxFundamentalsResult(
                status="REJECTED",
                query=query,
                detail=f"invalid statement type {request.statement_type!r}",
                retrieved_at=retrieved_at,
            )

        if not self.configured():
            detail = (
                "production fail-closed: Upstox analytics token absent — "
                "no fixture fundamentals substitution"
                if is_production_environment()
                else f"provider unavailable: {UPSTOX_ANALYTICS_TOKEN_ENV} absent"
            )
            return UpstoxFundamentalsResult(
                status="UNAVAILABLE",
                query=query,
                detail=detail,
                retrieved_at=retrieved_at,
            )

        if not self.base_url.lower().startswith("https://"):
            return UpstoxFundamentalsResult(
                status="UNAVAILABLE",
                query=query,
                detail="HTTPS required for Upstox fundamentals",
                retrieved_at=retrieved_at,
            )

        started = time.perf_counter()
        assert self.resolver is not None
        resolve = self.resolver.resolve(
            UpstoxResolveRequest(
                symbol=request.symbol,
                preferred_exchange=request.preferred_exchange,
            )
        )
        latency = lambda: round((time.perf_counter() - started) * 1000.0, 2)

        if resolve.status == "AMBIGUOUS":
            return UpstoxFundamentalsResult(
                status="AMBIGUOUS",
                query=resolve.query,
                detail=(
                    "instrument identity ambiguous; supply preferred_exchange "
                    "(NSE or BSE) — no silent exchange selection"
                ),
                retrieved_at=retrieved_at,
                latency_ms=latency(),
                http_status=resolve.http_status,
                resolve=resolve,
            )
        if resolve.status == "NOT_FOUND":
            return UpstoxFundamentalsResult(
                status="NOT_FOUND",
                query=resolve.query,
                detail=resolve.detail,
                retrieved_at=retrieved_at,
                latency_ms=latency(),
                http_status=resolve.http_status,
                resolve=resolve,
            )
        if resolve.status in {"UNAVAILABLE", "REJECTED"}:
            return UpstoxFundamentalsResult(
                status="UNAVAILABLE" if resolve.status == "UNAVAILABLE" else "REJECTED",
                query=resolve.query,
                detail=resolve.detail,
                retrieved_at=retrieved_at,
                latency_ms=latency(),
                http_status=resolve.http_status,
                resolve=resolve,
            )
        if resolve.status != "RESOLVED" or resolve.identity is None:
            return UpstoxFundamentalsResult(
                status="UNAVAILABLE",
                query=resolve.query,
                detail="instrument not resolved",
                retrieved_at=retrieved_at,
                latency_ms=latency(),
                resolve=resolve,
            )

        identity = resolve.identity
        isin = str(identity.isin or "").strip().upper()
        if not isin:
            return UpstoxFundamentalsResult(
                status="UNAVAILABLE",
                query=resolve.query,
                detail="resolved identity missing ISIN",
                retrieved_at=retrieved_at,
                latency_ms=latency(),
                resolve=resolve,
                identity=identity,
            )

        endpoints = (
            f"{UPSTOX_FUNDAMENTALS_PREFIX}/{isin}/income-statement",
            f"{UPSTOX_FUNDAMENTALS_PREFIX}/{isin}/balance-sheet",
            f"{UPSTOX_FUNDAMENTALS_PREFIX}/{isin}/cash-flow",
        )

        income_payload, st1, err1 = self._get_json(
            endpoints[0],
            {
                "type": stmt_type,
                "time_period": upstox_time,
                "fs": "true",
            },
        )
        if err1 is not None:
            return UpstoxFundamentalsResult(
                status="UNAVAILABLE",
                query=resolve.query,
                detail=err1,
                retrieved_at=retrieved_at,
                latency_ms=latency(),
                http_status=st1,
                resolve=resolve,
                identity=identity,
                endpoints=endpoints,
            )

        # Balance sheet / cash flow: official docs have no time_period query;
        # full_statement is annual. Only attach to annual requests.
        balance_payload: Any = {"status": "success", "data": {}}
        cash_payload: Any = {"status": "success", "data": {}}
        st_last = st1
        if period_kind == "annual":
            balance_payload, st2, err2 = self._get_json(
                endpoints[1], {"type": stmt_type, "fs": "true"}
            )
            if err2 is not None:
                return UpstoxFundamentalsResult(
                    status="UNAVAILABLE",
                    query=resolve.query,
                    detail=err2,
                    retrieved_at=retrieved_at,
                    latency_ms=latency(),
                    http_status=st2,
                    resolve=resolve,
                    identity=identity,
                    endpoints=endpoints,
                )
            cash_payload, st3, err3 = self._get_json(
                endpoints[2], {"type": stmt_type, "fs": "true"}
            )
            if err3 is not None:
                return UpstoxFundamentalsResult(
                    status="UNAVAILABLE",
                    query=resolve.query,
                    detail=err3,
                    retrieved_at=retrieved_at,
                    latency_ms=latency(),
                    http_status=st3,
                    resolve=resolve,
                    identity=identity,
                    endpoints=endpoints,
                )
            st_last = st3

        try:
            periods, currency, unit_scale, observed = _build_period_dicts(
                income_payload=income_payload,
                balance_payload=balance_payload,
                cash_payload=cash_payload,
                period_kind=period_kind,
                statement_type=stmt_type,
                limit=max(1, min(int(request.limit or 4), 10)),
            )
        except InvalidProviderDataError as exc:
            return UpstoxFundamentalsResult(
                status="UNAVAILABLE",
                query=resolve.query,
                detail=redact_secret(str(exc), self.access_token),
                retrieved_at=retrieved_at,
                latency_ms=latency(),
                http_status=st_last,
                resolve=resolve,
                identity=identity,
                endpoints=endpoints,
            )

        if not periods:
            return UpstoxFundamentalsResult(
                status="EMPTY",
                query=resolve.query,
                detail="empty fundamentals for requested period type",
                retrieved_at=retrieved_at,
                latency_ms=latency(),
                http_status=st_last or 200,
                resolve=resolve,
                identity=identity,
                endpoints=endpoints,
                coverage=_coverage_from_observed(observed, mapped_periods=()),
            )

        company = CompanyIdentity(
            symbol=identity.trading_symbol,
            exchange=identity.exchange,
            company_name=identity.company_name,
            isin=isin,
            provider_company_id=isin,
            currency=currency,
        )
        provenance = FinancialStatementProvenance(
            provider_id=self.provider_id,
            provider_name=self.provider_name,
            source_type="licensed_vendor",
            retrieved_at=statement_utc_now(),
            auth_mode="bearer_token",
            metadata={
                "base_url": self.base_url,
                "vendor": "upstox",
                "isin": isin,
                "instrument_key": identity.provider_instrument_id,
                "u1_resolution": "RESOLVED",
                "upstox_time_period": upstox_time,
                "units_in": unit_scale or "",
                "note": (
                    "full_statement is annual-only per Upstox docs; "
                    "quarterly uses category history only"
                ),
            },
        )
        try:
            statements = build_statements_from_mapping(
                symbol=company.symbol,
                payload={
                    "identity": company.to_dict(),
                    "reporting_currency": currency,
                    "statement_basis": stmt_type,
                    "unit_scale": unit_scale,
                    "periods": periods,
                },
                provenance=provenance,
            )
        except InvalidProviderDataError as exc:
            return UpstoxFundamentalsResult(
                status="UNAVAILABLE",
                query=resolve.query,
                detail=redact_secret(str(exc), self.access_token),
                retrieved_at=retrieved_at,
                latency_ms=latency(),
                http_status=st_last or 200,
                resolve=resolve,
                identity=identity,
                endpoints=endpoints,
            )

        annual_n = sum(1 for p in statements.periods if p.period_type == "annual")
        quarterly_n = sum(1 for p in statements.periods if p.period_type == "quarterly")
        eps_basis = _eps_cagr_basis(statements)
        coverage = _coverage_from_observed(observed, mapped_periods=statements.periods)

        return UpstoxFundamentalsResult(
            status="OK",
            query=resolve.query,
            detail="authenticated Upstox fundamentals",
            retrieved_at=retrieved_at,
            latency_ms=latency(),
            http_status=st_last or 200,
            resolve=resolve,
            identity=identity,
            statements=statements,
            coverage=coverage,
            eps_cagr_basis=eps_basis,
            annual_period_count=annual_n,
            quarterly_period_count=quarterly_n,
            currency=currency,
            endpoints=endpoints,
        )

    def _get_json(
        self, path: str, params: dict[str, str]
    ) -> tuple[Any | None, int | None, str | None]:
        url = f"{self.base_url.rstrip('/')}/{path.lstrip('/')}"
        last_error = "Upstox fundamentals request failed"
        status_code: int | None = None
        for attempt in range(1, self.max_attempts + 1):
            try:
                payload = self._client().get_json(
                    url, params=params, headers=self._headers()
                )
                return payload, 200, None
            except ProviderRequestError as exc:
                safe = redact_secret(str(exc), self.access_token)
                last_error = safe
                status_code = _status_from_detail(safe)
                msg = safe.lower()
                if "401" in msg or "403" in msg or "authentication failed" in msg:
                    break
                if "404" in msg:
                    break
                if "429" in msg or "rate limited" in msg:
                    if attempt >= self.max_attempts:
                        break
                    continue
                if attempt >= self.max_attempts:
                    break
            except Exception as exc:  # noqa: BLE001
                last_error = redact_secret(type(exc).__name__, self.access_token)
                break
        return None, status_code, last_error


@dataclass
class UpstoxStatementAdapterU4(FinancialStatementPort):
    """FinancialStatementPort thin wrapper over U4 — optional; not default env provider."""

    access_token: str | None = None
    base_url: str = UPSTOX_BASE_URL
    timeout_seconds: float = 15.0
    http_client: JsonHttpClient | None = None
    provider_name: str = "Upstox"
    _provider_id: str = "upstox_financial_statements"

    @property
    def provider_id(self) -> str:
        return self._provider_id

    def _client(self) -> UpstoxFundamentalsClient:
        return UpstoxFundamentalsClient(
            access_token=self.access_token,
            base_url=self.base_url,
            timeout_seconds=self.timeout_seconds,
            http_client=self.http_client,
            provider_id=self.provider_id,
            provider_name=self.provider_name,
        )

    def resolve_company(self, instrument: Instrument) -> CompanyIdentity | None:
        result = self._client().get_fundamentals(
            UpstoxFundamentalsRequest(
                symbol=instrument.symbol,
                preferred_exchange=instrument.exchange,
                limit=1,
            )
        )
        if result.status != "OK" or result.statements is None:
            return None
        return result.statements.identity

    def get_statements(
        self, query: StatementQuery
    ) -> AuthenticatedFinancialStatements | None:
        period = str(query.period_type or "annual").strip().lower()
        result = self._client().get_fundamentals(
            UpstoxFundamentalsRequest(
                symbol=query.instrument.symbol,
                preferred_exchange=query.instrument.exchange,
                period_type=period,
                limit=int(query.limit or 4),
            )
        )
        return result.statements if result.status == "OK" else None

    def health(self) -> StatementProviderHealth:
        token = str(
            self.access_token or resolve_u0_upstox_analytics_token() or ""
        ).strip()
        ok = bool(token)
        return StatementProviderHealth(
            provider_id=self.provider_id,
            healthy=ok,
            authenticated=ok,
            detail="configured analytics token" if ok else "missing analytics token",
        )


# --- mapping helpers ---------------------------------------------------------


@dataclass
class _ObservedFields:
    """Track which vendor keys were seen (not necessarily mapped to DSP)."""

    keys: set[str] = field(default_factory=set)
    values: dict[str, Any] = field(default_factory=dict)

    def note(self, key: str, value: Any) -> None:
        k = str(key or "").strip().lower()
        if not k:
            return
        self.keys.add(k)
        if value is not None and k not in self.values:
            self.values[k] = value


def _build_period_dicts(
    *,
    income_payload: Any,
    balance_payload: Any,
    cash_payload: Any,
    period_kind: str,
    statement_type: str,
    limit: int,
) -> tuple[list[dict[str, Any]], str, str, _ObservedFields]:
    if not isinstance(income_payload, Mapping):
        raise InvalidProviderDataError("malformed income-statement response")
    income_data = income_payload.get("data")
    if not isinstance(income_data, Mapping):
        raise InvalidProviderDataError("malformed income-statement data")

    units = str(income_data.get("units_in") or "").strip().lower()
    if units != "crore":
        # Official contract is INR Crore; missing/unknown units → fail closed
        raise InvalidProviderDataError(
            f"Upstox fundamentals currency/units unavailable or unsupported: {units!r}"
        )
    currency = normalize_reporting_currency("INR")
    unit_scale = "crore"

    observed = _ObservedFields()
    income_cat = _history_by_category(income_data, "income_statement", observed)
    # full_statement is annual-only per Upstox docs — use only for annual requests
    income_full: dict[str, dict[str, Any]] = {}
    balance_full: dict[str, dict[str, Any]] = {}
    cash_full: dict[str, dict[str, Any]] = {}
    cash_cat: dict[str, dict[str, Any]] = {}
    balance_hist: dict[str, dict[str, Any]] = {}

    if period_kind == "annual":
        income_full = _full_statement_by_period(income_data, observed)
        if isinstance(balance_payload, Mapping) and isinstance(
            balance_payload.get("data"), Mapping
        ):
            bal_data = balance_payload["data"]
            bal_units = str(bal_data.get("units_in") or units).strip().lower()
            if bal_units and bal_units != "crore":
                raise InvalidProviderDataError(
                    f"balance-sheet units mismatch: {bal_units!r}"
                )
            balance_full = _full_statement_by_period(bal_data, observed)
            balance_hist = _balance_summary_history(bal_data, observed)
        if isinstance(cash_payload, Mapping) and isinstance(
            cash_payload.get("data"), Mapping
        ):
            cf_data = cash_payload["data"]
            cf_units = str(cf_data.get("units_in") or units).strip().lower()
            if cf_units and cf_units != "crore":
                raise InvalidProviderDataError(
                    f"cash-flow units mismatch: {cf_units!r}"
                )
            cash_full = _full_statement_by_period(cf_data, observed)
            cash_cat = _history_by_category(cf_data, "cash_flow", observed)

    if period_kind == "quarterly":
        # Category history only — do not use annual full_statement
        labels = set(income_cat.keys())
    else:
        labels = (
            set(income_cat)
            | set(income_full)
            | set(balance_full)
            | set(cash_full)
            | set(balance_hist)
            | set(cash_cat)
        )

    periods: list[dict[str, Any]] = []
    for label in sorted(labels, key=_period_label_sort_key, reverse=True):
        try:
            period_end = _period_label_to_date(label)
        except InvalidProviderDataError:
            # Unknown / unparseable period label — skip, do not invent
            continue

        if period_kind == "quarterly":
            inc = dict(income_cat.get(label, {}))
            bal: dict[str, Any] = {}
            cf: dict[str, Any] = {}
            fiscal_quarter = _fiscal_quarter_from_month(period_end.month)
        else:
            inc = {**income_full.get(label, {}), **income_cat.get(label, {})}
            bal = {**balance_hist.get(label, {}), **balance_full.get(label, {})}
            cf = {**cash_full.get(label, {}), **cash_cat.get(label, {})}
            fiscal_quarter = None

        def pick(store: Mapping[str, Any], *aliases: str) -> Any:
            for a in aliases:
                if a in store and store[a] is not None:
                    return store[a]
            return None

        # Explicitly refuse WC substitutes and Total Expenses → COGS
        for banned in _FORBIDDEN_WC_SUBSTITUTES:
            if banned in bal:
                observed.note(f"seen_but_not_mapped_wc:{banned}", bal.get(banned))

        periods.append(
            {
                "period_type": period_kind,
                "fiscal_year": period_end.year,
                "fiscal_quarter": fiscal_quarter,
                "period_end": period_end.isoformat(),
                "reporting_currency": currency,
                "restated": False,
                "statement_basis": statement_type,
                "unit_scale": unit_scale,
                "income_statement": {
                    "revenue": pick(inc, "revenue", "total revenue"),
                    # COGS: not in official samples — only map explicit aliases
                    "cost_of_revenue": pick(
                        inc,
                        "cost of revenue",
                        "cost of goods sold",
                        "cogs",
                        "cost of materials consumed",
                    ),
                    "gross_profit": pick(inc, "gross profit"),
                    "operating_income": pick(
                        inc,
                        "operating_profit",
                        "operating profit",
                        "operating profit before other income",
                    ),
                    "ebit": pick(inc, "ebit", "operating profit", "operating_profit"),
                    "ebitda": pick(inc, "ebitda"),
                    "net_income": pick(
                        inc,
                        "net_profit",
                        "profit after tax",
                        "net profit",
                        "profit after tax (pat)",
                    ),
                    "eps_basic": pick(inc, "eps - basic", "eps basic", "eps"),
                    "eps_diluted": pick(inc, "eps - diluted", "eps diluted"),
                },
                "balance_sheet": {
                    "cash_and_equivalents": pick(
                        bal,
                        "cash and cash equivalents",
                        "cash & cash equivalents",
                        "cash",
                    )
                    if pick(
                        bal,
                        "cash and cash equivalents",
                        "cash & cash equivalents",
                        "cash",
                    )
                    is not None
                    else pick(
                        cf,
                        "cash (end of the year)",
                        "cash and cash equivalents",
                        "cash & cash equivalents",
                        "cash",
                    ),
                    "current_assets": pick(
                        bal, "current assets", "total current assets"
                    ),
                    "total_assets": pick(bal, "total assets", "total_asset"),
                    "current_liabilities": pick(
                        bal, "current liabilities", "total current liabilities"
                    ),
                    "total_liabilities": pick(
                        bal, "total liabilities", "total_liability"
                    ),
                    "total_equity": pick(
                        bal,
                        "equity capital",
                        "shareholders' funds",
                        "total equity",
                        "total shareholders' equity",
                    ),
                    "total_debt": pick(
                        bal, "total debt", "borrowings", "total borrowings"
                    ),
                    "long_term_debt": pick(
                        bal, "long term borrowings", "long-term debt", "long term debt"
                    ),
                },
                "cash_flow": {
                    "operating_cash_flow": pick(
                        cf,
                        "operating",
                        "cash flow from operations",
                        "cash flow from operating activities",
                    ),
                    "investing_cash_flow": pick(
                        cf,
                        "investing",
                        "cash flow from investing",
                        "cash flow from investing activities",
                    ),
                    "financing_cash_flow": pick(
                        cf,
                        "financing",
                        "cash flow from financing",
                        "cash flow from financing activities",
                    ),
                    # Capex / FCF: not in official samples — map only if present
                    "capital_expenditures": pick(
                        cf,
                        "capital expenditure",
                        "capital expenditures",
                        "purchase of fixed assets",
                        "capex",
                    ),
                    "free_cash_flow": pick(cf, "free cash flow", "fcf"),
                    "dividends_paid": pick(cf, "dividends paid"),
                    "share_buybacks": pick(
                        cf, "buyback of shares", "purchase of shares"
                    ),
                },
                # Ratios left empty — never calculate WC / margins here
            }
        )

    return periods[:limit], currency, unit_scale, observed


def _history_by_category(
    data: Mapping[str, Any], key: str, observed: _ObservedFields
) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    rows = data.get(key)
    if not isinstance(rows, list):
        return result
    for category in rows:
        if not isinstance(category, Mapping):
            continue
        name = str(category.get("category") or "").strip().lower()
        history = category.get("history")
        if not name or not isinstance(history, list):
            continue
        for item in history:
            if not isinstance(item, Mapping):
                continue
            period = str(item.get("period") or "").strip()
            if not period:
                continue
            value = item.get("value")
            observed.note(name, value)
            result.setdefault(period, {})[name] = value
    return result


def _full_statement_by_period(
    data: Mapping[str, Any], observed: _ObservedFields
) -> dict[str, dict[str, Any]]:
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
            if not period:
                continue
            value = item.get("value")
            observed.note(particular, value)
            result.setdefault(period, {})[particular] = value
    return result


def _balance_summary_history(
    data: Mapping[str, Any], observed: _ObservedFields
) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    rows = data.get("history")
    if not isinstance(rows, list):
        return result
    for item in rows:
        if not isinstance(item, Mapping):
            continue
        period = str(item.get("period") or "").strip()
        if not period:
            continue
        for key in ("total_asset", "total_liability"):
            if key in item and item[key] is not None:
                observed.note(key, item[key])
                result.setdefault(period, {})[key] = item[key]
    return result


def _period_label_to_date(period: str) -> date:
    text = str(period or "").strip()
    if len(text) < 8:
        raise InvalidProviderDataError(f"invalid Upstox reporting period: {period!r}")
    month, year = text[:3].title(), text[-4:]
    months = {
        "Jan": 1,
        "Feb": 2,
        "Mar": 3,
        "Apr": 4,
        "May": 5,
        "Jun": 6,
        "Jul": 7,
        "Aug": 8,
        "Sep": 9,
        "Oct": 10,
        "Nov": 11,
        "Dec": 12,
    }
    if month not in months or not year.isdigit():
        raise InvalidProviderDataError(f"invalid Upstox reporting period: {period!r}")
    m = months[month]
    y = int(year)
    last_day = calendar.monthrange(y, m)[1]
    return date(y, m, last_day)


def _period_label_sort_key(period: str) -> str:
    try:
        return _period_label_to_date(period).isoformat()
    except InvalidProviderDataError:
        return ""


def _fiscal_quarter_from_month(month: int) -> int:
    # Calendar-quarter of period-end month — not inventing fiscal calendars
    return (month - 1) // 3 + 1


def _eps_cagr_basis(statements: AuthenticatedFinancialStatements) -> str:
    """Report preferred EPS series basis — does NOT compute CAGR."""
    annual = [p for p in statements.periods if p.period_type == "annual"]
    diluted_ok = [
        p
        for p in annual
        if p.eps_diluted.available
        and p.eps_diluted.value is not None
        and p.eps_diluted.value > 0
    ]
    if len(diluted_ok) >= 2:
        return "diluted"
    basic_ok = [
        p
        for p in annual
        if p.eps_basic.available
        and p.eps_basic.value is not None
        and p.eps_basic.value > 0
    ]
    if len(basic_ok) >= 2:
        return "basic"
    return "unavailable"


def _any_mapped(periods: Sequence[Any], attr: str) -> bool:
    for p in periods:
        field = getattr(p, attr, None)
        if isinstance(field, StatementField) and field.available:
            return True
    return False


def _vendor_hit(observed: _ObservedFields, aliases: Sequence[str]) -> bool:
    return any(a in observed.values for a in aliases)


def _coverage_from_observed(
    observed: _ObservedFields,
    *,
    mapped_periods: Sequence[Any],
) -> tuple[UpstoxFieldCoverage, ...]:
    """Build honest coverage matrix from observed vendor keys + DSP mapping."""

    specs: list[tuple[str, tuple[str, ...], str | None, str]] = [
        (
            "revenue",
            ("revenue", "total revenue"),
            "revenue",
            "category + full_statement Total Revenue / Revenue",
        ),
        (
            "COGS",
            (
                "cost of revenue",
                "cost of goods sold",
                "cogs",
                "cost of materials consumed",
            ),
            "cost_of_revenue",
            "not in official samples; Total Expenses is NOT mapped to COGS",
        ),
        (
            "net income",
            ("net_profit", "profit after tax", "net profit"),
            "net_income",
            "category net_profit / Profit After Tax",
        ),
        (
            "basic EPS",
            ("eps - basic", "eps basic", "eps"),
            "eps_basic",
            "full_statement EPS - Basic (annual only)",
        ),
        (
            "diluted EPS",
            ("eps - diluted", "eps diluted"),
            "eps_diluted",
            "full_statement EPS - Diluted (annual only); bases never mixed",
        ),
        (
            "weighted shares",
            _WEIGHTED_SHARES_ALIASES,
            None,
            "no AuthenticatedStatementPeriod slot; not in official samples — never substitute shares outstanding",
        ),
        (
            "OCF",
            (
                "operating",
                "cash flow from operations",
                "cash flow from operating activities",
            ),
            "operating_cash_flow",
            "cash_flow category operating / Cash flow from Operations",
        ),
        (
            "FCF",
            ("free cash flow", "fcf"),
            "free_cash_flow",
            "not in official samples; adapter does not compute OCF−|capex|",
        ),
        (
            "capex",
            (
                "capital expenditure",
                "capital expenditures",
                "purchase of fixed assets",
                "capex",
            ),
            "capital_expenditures",
            "not in official samples",
        ),
        (
            "cash",
            (
                "cash and cash equivalents",
                "cash & cash equivalents",
                "cash (end of the year)",
                "cash",
            ),
            "cash_and_equivalents",
            "not in BS official sample particulars; CF has Cash (End of the year)",
        ),
        (
            "debt",
            ("total debt", "borrowings", "total borrowings"),
            "total_debt",
            "not in official BS sample particulars",
        ),
        (
            "current assets",
            ("current assets", "total current assets"),
            "current_assets",
            "full_statement Current Assets",
        ),
        (
            "current liabilities",
            ("current liabilities", "total current liabilities"),
            "current_liabilities",
            "full_statement Current Liabilities",
        ),
        (
            "total assets",
            ("total assets", "total_asset"),
            "total_assets",
            "history.total_asset + full_statement Total Assets",
        ),
        (
            "total liabilities",
            ("total liabilities", "total_liability"),
            "total_liabilities",
            "history.total_liability",
        ),
        (
            "equity",
            ("equity capital", "shareholders' funds", "total equity"),
            "total_equity",
            "full_statement Equity Capital",
        ),
        (
            "AR",
            _AR_ALIASES,
            None,
            "no AuthenticatedStatementPeriod slot; not in official BS samples — never derive",
        ),
        (
            "inventory",
            _INVENTORY_ALIASES,
            None,
            "no AuthenticatedStatementPeriod slot; not in official BS samples — never derive",
        ),
        (
            "AP",
            _AP_ALIASES,
            None,
            "no AuthenticatedStatementPeriod slot; not in official BS samples — never derive",
        ),
        (
            "currency",
            ("units_in",),
            None,
            "official: INR Crore (units_in=crore); missing units → fail closed",
        ),
    ]
    out: list[UpstoxFieldCoverage] = []
    for name, aliases, attr, notes in specs:
        if name == "currency":
            out.append(
                UpstoxFieldCoverage(
                    field=name,
                    upstox_available=True,
                    dsp_mapped=bool(mapped_periods),
                    notes=notes,
                )
            )
            continue
        hit = _vendor_hit(observed, aliases)
        mapped = _any_mapped(mapped_periods, attr) if attr else False
        out.append(
            UpstoxFieldCoverage(
                field=name,
                upstox_available=hit,
                dsp_mapped=mapped,
                notes=notes,
            )
        )
    return tuple(out)


def _status_from_detail(detail: str) -> int | None:
    for code in (429, 401, 403, 404, 500, 502, 503):
        if str(code) in detail:
            return code
    return None
