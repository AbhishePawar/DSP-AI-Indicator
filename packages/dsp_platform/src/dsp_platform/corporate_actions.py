"""Authenticated corporate actions façade for DSPPlatform (EPIC-D003).

Thin wrapper over ``data_engine.corporate_actions``. No scoring, valuation,
or price adjustments.
"""

from __future__ import annotations

from datetime import date
from threading import Lock
from typing import Any

from contracts.domain.instrument import Instrument
from contracts.enums import AssetClass
from data_engine import (
    CorporateActionQuery,
    CorporateActionService,
    build_default_corporate_action_adapter_from_env,
)

__all__ = [
    "get_authenticated_corporate_actions",
    "corporate_actions_health",
    "corporate_actions_metrics",
    "resolve_corporate_action_company",
    "reset_corporate_actions_service_for_tests",
]

_LOCK = Lock()
_SERVICE: CorporateActionService | None = None


def _service() -> CorporateActionService:
    global _SERVICE
    with _LOCK:
        if _SERVICE is None:
            adapter = build_default_corporate_action_adapter_from_env()
            _SERVICE = CorporateActionService(adapter)
        return _SERVICE


def reset_corporate_actions_service_for_tests(
    service: CorporateActionService | None = None,
) -> None:
    """Replace or clear the process-local corporate actions service (tests only)."""
    global _SERVICE
    with _LOCK:
        _SERVICE = service


def get_authenticated_corporate_actions(
    symbol: str,
    *,
    exchange: str | None = None,
    currency: str = "USD",
    action_type: str | None = None,
    start_date: date | str | None = None,
    end_date: date | str | None = None,
    limit: int = 50,
) -> dict[str, Any] | None:
    """Fetch authenticated corporate actions as a public dict, or ``None``."""
    instrument = Instrument(
        symbol=symbol.strip().upper(),
        asset_class=AssetClass.EQUITY,
        currency=currency,
        exchange=exchange,
    )

    def _d(value: date | str | None) -> date | None:
        if value is None or value == "":
            return None
        if isinstance(value, date):
            return value
        return date.fromisoformat(str(value)[:10])

    query = CorporateActionQuery(
        instrument=instrument,
        action_type=action_type,
        start_date=_d(start_date),
        end_date=_d(end_date),
        limit=limit,
    )
    bundle = _service().get_actions(query)
    if bundle is None:
        return None
    return bundle.to_public_dict()


def resolve_corporate_action_company(
    symbol: str,
    *,
    exchange: str | None = None,
    currency: str = "USD",
) -> dict[str, Any] | None:
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


def corporate_actions_health() -> dict[str, Any]:
    return _service().health().to_dict()


def corporate_actions_metrics() -> dict[str, int]:
    return _service().metrics.snapshot()
