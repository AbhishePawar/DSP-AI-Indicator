"""Authenticated financial statements façade for DSPPlatform (EPIC-D002).

Thin wrapper over ``data_engine.financial_statement``. No scoring or valuation.
"""

from __future__ import annotations

from threading import Lock
from typing import Any

from contracts.domain.instrument import Instrument
from contracts.enums import AssetClass
from data_engine import (
    FinancialStatementService,
    StatementQuery,
    build_default_statement_adapter_from_env,
)

__all__ = [
    "get_authenticated_financial_statements",
    "financial_statement_health",
    "financial_statement_metrics",
    "resolve_company_identity",
    "reset_financial_statement_service_for_tests",
]

_LOCK = Lock()
_SERVICE: FinancialStatementService | None = None


def _service() -> FinancialStatementService:
    global _SERVICE
    with _LOCK:
        if _SERVICE is None:
            adapter = build_default_statement_adapter_from_env()
            # P1-09 CI fixture only — never production / never live vendor evidence.
            try:
                from dsp_platform.p109_e2e_fixture import (
                    build_p109_statements,
                    p109_fixture_enabled,
                )
                from data_engine import InMemoryAuthenticatedStatementAdapter

                if p109_fixture_enabled() and isinstance(
                    adapter, InMemoryAuthenticatedStatementAdapter
                ):
                    adapter.put(build_p109_statements())
            except Exception:  # noqa: BLE001
                pass
            _SERVICE = FinancialStatementService(adapter)
        return _SERVICE


def reset_financial_statement_service_for_tests(
    service: FinancialStatementService | None = None,
) -> None:
    """Replace or clear the process-local statement service (tests only)."""
    global _SERVICE
    with _LOCK:
        _SERVICE = service


def get_authenticated_financial_statements(
    symbol: str,
    *,
    exchange: str | None = None,
    currency: str = "USD",
    period_type: str | None = None,
    limit: int = 8,
    include_restated: bool = True,
) -> dict[str, Any] | None:
    """Fetch authenticated statements as a public dict, or ``None`` if unavailable."""
    instrument = Instrument(
        symbol=symbol.strip().upper(),
        asset_class=AssetClass.EQUITY,
        currency=currency,
        exchange=exchange,
    )
    query = StatementQuery(
        instrument=instrument,
        period_type=period_type,
        limit=limit,
        include_restated=include_restated,
    )
    bundle = _service().get_statements(query)
    if bundle is None:
        return None
    return bundle.to_public_dict()


def resolve_company_identity(
    symbol: str,
    *,
    exchange: str | None = None,
    currency: str = "USD",
) -> dict[str, Any] | None:
    """Resolve company identifiers via the authenticated statement provider."""
    instrument = Instrument(
        symbol=symbol.strip().upper(),
        asset_class=AssetClass.EQUITY,
        currency=currency,
        exchange=exchange,
    )
    identity = _service().resolve_company(instrument)
    if identity is None:
        return None
    return identity.to_dict()


def financial_statement_health() -> dict[str, Any]:
    return _service().health().to_dict()


def financial_statement_metrics() -> dict[str, int]:
    return _service().metrics.snapshot()
