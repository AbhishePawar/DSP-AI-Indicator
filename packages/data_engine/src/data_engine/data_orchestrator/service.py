"""Unified Data Orchestrator (EPIC-D005).

Parallel read-only aggregation of authenticated D001–D004 services.
No calculations, valuation, scoring, or fabricated payloads.
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any, Callable

from data_engine.data_orchestrator.models import (
    SECTION_ORDER,
    DataSectionStatus,
    RetrievalStatus,
    SectionResult,
    UnifiedCompanyIdentity,
    UnifiedDataBundle,
    UnifiedHealthReport,
    utc_now,
)

__all__ = [
    "DataOrchestrator",
    "DataOrchestratorMetrics",
    "DataOrchestratorRequest",
    "UNAVAILABLE_MESSAGE",
]

_LOG = logging.getLogger("data_engine.data_orchestrator")
UNAVAILABLE_MESSAGE = "Data unavailable."

FetchFn = Callable[[], dict[str, Any] | None]
HealthFn = Callable[[], dict[str, Any]]
ResolveFn = Callable[[], dict[str, Any] | None]


@dataclass(frozen=True, slots=True)
class DataOrchestratorRequest:
    """Read-only orchestration request."""

    symbol: str
    exchange: str | None = None
    currency: str = "USD"
    include_market_quote: bool = True
    include_financial_statements: bool = True
    include_corporate_actions: bool = True
    include_historical_series: bool = True
    # Historical series options (pass-through — no calculation)
    historical_series_kind: str = "ohlcv"
    historical_frequency: str | None = "daily"
    historical_limit: int = 30
    statement_period_type: str | None = None
    statement_limit: int = 8
    corporate_actions_limit: int = 50
    max_workers: int = 4


@dataclass
class DataOrchestratorMetrics:
    requests: int = 0
    sections_ok: int = 0
    sections_unavailable: int = 0
    sections_error: int = 0
    partial_responses: int = 0

    def snapshot(self) -> dict[str, int]:
        return {
            "requests": self.requests,
            "sections_ok": self.sections_ok,
            "sections_unavailable": self.sections_unavailable,
            "sections_error": self.sections_error,
            "partial_responses": self.partial_responses,
        }


@dataclass
class DataOrchestrator:
    """Coordinates authenticated market / statements / actions / history services.

    Callables return public dicts or ``None`` (unavailable). Exceptions become
    section ``error`` status — never invented payloads.
    """

    fetch_market_quote: FetchFn
    fetch_financial_statements: FetchFn
    fetch_corporate_actions: FetchFn
    fetch_historical_series: FetchFn
    health_market_quote: HealthFn
    health_financial_statements: HealthFn
    health_corporate_actions: HealthFn
    health_historical_series: HealthFn
    resolve_company: ResolveFn | None = None
    metrics: DataOrchestratorMetrics = field(default_factory=DataOrchestratorMetrics)

    def health(self) -> UnifiedHealthReport:
        providers: dict[str, dict[str, Any]] = {}
        for key, fn in (
            ("market_quote", self.health_market_quote),
            ("financial_statements", self.health_financial_statements),
            ("corporate_actions", self.health_corporate_actions),
            ("historical_series", self.health_historical_series),
        ):
            try:
                providers[key] = dict(fn())
            except Exception as exc:  # noqa: BLE001
                providers[key] = {
                    "healthy": False,
                    "authenticated": False,
                    "detail": str(exc),
                    "provider_id": key,
                }
        overall_ok = all(bool(p.get("healthy", False)) for p in providers.values())
        overall_auth = any(
            bool(p.get("authenticated", False)) for p in providers.values()
        )
        return UnifiedHealthReport(
            overall_ok=overall_ok,
            overall_authenticated=overall_auth,
            providers=providers,
            checked_at=utc_now().isoformat(),
        )

    def get_bundle(self, request: DataOrchestratorRequest) -> UnifiedDataBundle:
        self.metrics.requests += 1
        requested_at = utc_now()
        symbol = request.symbol.strip().upper()

        identity = self._resolve_identity(request, symbol)

        planned: list[tuple[str, FetchFn]] = []
        if request.include_market_quote:
            planned.append(("market_quote", self.fetch_market_quote))
        if request.include_financial_statements:
            planned.append(("financial_statements", self.fetch_financial_statements))
        if request.include_corporate_actions:
            planned.append(("corporate_actions", self.fetch_corporate_actions))
        if request.include_historical_series:
            planned.append(("historical_series", self.fetch_historical_series))

        # Deterministic planning order
        order_index = {name: i for i, name in enumerate(SECTION_ORDER)}
        planned.sort(key=lambda item: order_index.get(item[0], 99))

        raw: dict[str, SectionResult] = {}
        workers = max(1, min(request.max_workers, len(planned) or 1))

        def _run(section: str, fn: FetchFn) -> tuple[str, SectionResult]:
            return section, self._fetch_section(section, fn)

        if not planned:
            completed_at = utc_now()
            empty = self._empty_section
            retrieval = RetrievalStatus(
                requested_at=requested_at.isoformat(),
                completed_at=completed_at.isoformat(),
                sections_requested=(),
                sections_ok=(),
                sections_unavailable=(),
                sections_error=(),
                partial=False,
                all_available=False,
                any_available=False,
            )
            health = self.health()
            return UnifiedDataBundle(
                identity=identity,
                market_quote=empty("market_quote"),
                financial_statements=empty("financial_statements"),
                corporate_actions=empty("corporate_actions"),
                historical_series=empty("historical_series"),
                retrieval=retrieval,
                health=health,
                provider_metadata=dict(health.providers),
            )

        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {
                pool.submit(_run, section, fn): section for section, fn in planned
            }
            for fut in as_completed(futures):
                section, result = fut.result()
                raw[section] = result

        # Fill unrequested sections as unavailable (deterministic full shape)
        for section in SECTION_ORDER:
            if section not in raw:
                raw[section] = self._empty_section(section)

        completed_at = utc_now()
        ok = tuple(s for s in SECTION_ORDER if raw[s].status.status == "ok")
        unavailable = tuple(
            s for s in SECTION_ORDER if raw[s].status.status == "unavailable"
        )
        errors = tuple(s for s in SECTION_ORDER if raw[s].status.status == "error")
        requested = tuple(s for s, _ in planned)

        for s in ok:
            self.metrics.sections_ok += 1
        for s in unavailable:
            if s in requested:
                self.metrics.sections_unavailable += 1
        for s in errors:
            self.metrics.sections_error += 1

        partial = bool(ok) and (bool(unavailable) or bool(errors))
        if partial:
            self.metrics.partial_responses += 1

        retrieval = RetrievalStatus(
            requested_at=requested_at.isoformat(),
            completed_at=completed_at.isoformat(),
            sections_requested=requested,
            sections_ok=tuple(s for s in SECTION_ORDER if s in ok),
            sections_unavailable=tuple(s for s in SECTION_ORDER if s in unavailable),
            sections_error=tuple(s for s in SECTION_ORDER if s in errors),
            partial=partial,
            all_available=len(ok) == len(requested) and len(requested) > 0,
            any_available=len(ok) > 0,
        )

        health = self.health()
        _LOG.info(
            "data_orchestrator_ok",
            extra={
                "symbol": symbol,
                "ok": list(retrieval.sections_ok),
                "unavailable": list(retrieval.sections_unavailable),
                "error": list(retrieval.sections_error),
                "partial": partial,
            },
        )

        return UnifiedDataBundle(
            identity=identity,
            market_quote=raw["market_quote"],
            financial_statements=raw["financial_statements"],
            corporate_actions=raw["corporate_actions"],
            historical_series=raw["historical_series"],
            retrieval=retrieval,
            health=health,
            provider_metadata=dict(health.providers),
        )

    def _resolve_identity(
        self, request: DataOrchestratorRequest, symbol: str
    ) -> UnifiedCompanyIdentity:
        if self.resolve_company is not None:
            try:
                resolved = self.resolve_company()
            except Exception as exc:  # noqa: BLE001
                _LOG.warning(
                    "data_orchestrator_resolve_failed",
                    extra={"symbol": symbol, "error": str(exc)},
                )
                resolved = None
            if isinstance(resolved, dict) and resolved.get("symbol"):
                return UnifiedCompanyIdentity(
                    symbol=str(resolved.get("symbol") or symbol).strip().upper(),
                    exchange=resolved.get("exchange") or request.exchange,
                    company_name=resolved.get("company_name"),
                    isin=resolved.get("isin"),
                    provider_company_id=resolved.get("provider_company_id"),
                    currency=resolved.get("currency") or request.currency,
                    resolved_by="financial_statements",
                )
        return UnifiedCompanyIdentity(
            symbol=symbol,
            exchange=request.exchange,
            currency=request.currency,
            resolved_by=None,
        )

    def _empty_section(self, section: str) -> SectionResult:
        return SectionResult(
            status=DataSectionStatus(
                section=section,
                available=False,
                authenticated=False,
                status="unavailable",
                message=UNAVAILABLE_MESSAGE,
            ),
            payload=None,
            provenance=None,
        )

    def _fetch_section(self, section: str, fn: FetchFn) -> SectionResult:
        retrieved_at = utc_now().isoformat()
        try:
            payload = fn()
        except Exception as exc:  # noqa: BLE001 — map to section error honestly
            _LOG.warning(
                "data_orchestrator_section_error",
                extra={"section": section, "error": str(exc)},
            )
            return SectionResult(
                status=DataSectionStatus(
                    section=section,
                    available=False,
                    authenticated=False,
                    status="error",
                    message=UNAVAILABLE_MESSAGE,
                    error=str(exc),
                    retrieved_at=retrieved_at,
                ),
                payload=None,
                provenance=None,
            )

        if payload is None:
            return SectionResult(
                status=DataSectionStatus(
                    section=section,
                    available=False,
                    authenticated=False,
                    status="unavailable",
                    message=UNAVAILABLE_MESSAGE,
                    retrieved_at=retrieved_at,
                ),
                payload=None,
                provenance=None,
            )

        provenance = None
        provider_id = None
        if isinstance(payload, dict):
            raw_prov = payload.get("provenance")
            if isinstance(raw_prov, dict):
                provenance = dict(raw_prov)
                provider_id = raw_prov.get("provider_id")
                if not provenance.get("retrieved_at"):
                    provenance = {**provenance, "retrieved_at": retrieved_at}

        return SectionResult(
            status=DataSectionStatus(
                section=section,
                available=True,
                authenticated=True,
                status="ok",
                message=None,
                retrieved_at=retrieved_at,
                provider_id=str(provider_id) if provider_id else None,
            ),
            payload=payload if isinstance(payload, dict) else None,
            provenance=provenance,
        )
