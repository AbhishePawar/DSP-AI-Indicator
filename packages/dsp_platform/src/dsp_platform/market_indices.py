"""Benchmark index façade for DSPPlatform (Figma Dashboard market bar).

Thin wrapper over ``data_engine.market_indices``. No scoring or valuation.
"""

from __future__ import annotations

from threading import Lock
from typing import Any

from data_engine import (
    MarketIndexService,
    build_default_index_adapter_from_env,
)

__all__ = [
    "get_market_indices",
    "reset_market_index_service_for_tests",
]

_LOCK = Lock()
_SERVICE: MarketIndexService | None = None


def _service() -> MarketIndexService:
    global _SERVICE
    with _LOCK:
        if _SERVICE is None:
            _SERVICE = MarketIndexService(build_default_index_adapter_from_env())
        return _SERVICE


def reset_market_index_service_for_tests(
    service: MarketIndexService | None = None,
) -> None:
    """Replace or clear the process-local index service (tests only)."""
    global _SERVICE
    with _LOCK:
        _SERVICE = service


def get_market_indices() -> dict[str, Any]:
    """Public dict: catalogue snapshots with provenance; never fabricated."""
    service = _service()
    snapshots = service.get_snapshots()
    payload: dict[str, Any] = {
        "provider_id": service.provider_id,
        "authenticated": service.authenticated,
        "indices": [snap.to_public_dict() for snap in snapshots],
    }
    if not service.authenticated:
        # No approved authenticated index feed → same capability code as quotes.
        payload["capability"] = "INVESTMENT_DATA_UNAVAILABLE"
    return payload
