"""Authenticated share-count façade for DSPPlatform.

Thin wrapper over ``data_engine.share_count``. No scoring or valuation.
No live vendor is selected — the env factory returns Null until a
governance-approved provider is explicitly connected.
"""

from __future__ import annotations

from threading import Lock
from typing import Any

from data_engine import (
    InMemoryShareCountAdapter,
    ShareCountService,
    ShareCountSnapshot,
    build_default_share_count_adapter_from_env,
)

__all__ = [
    "install_memory_share_count_for_tests",
    "reset_share_count_service_for_tests",
    "share_count_health",
    "share_count_metrics",
]

_LOCK = Lock()
_SERVICE: ShareCountService | None = None


def _service() -> ShareCountService:
    global _SERVICE
    with _LOCK:
        if _SERVICE is None:
            adapter = build_default_share_count_adapter_from_env()
            # P1-09 CI fixture only — never production / never live vendor evidence.
            try:
                from dsp_platform.p109_e2e_fixture import (
                    build_p109_share_count,
                    p109_fixture_enabled,
                )

                if p109_fixture_enabled():
                    if not isinstance(adapter, InMemoryShareCountAdapter):
                        adapter = InMemoryShareCountAdapter(api_key="p109-fixture-key")
                    adapter.put(build_p109_share_count())
            except Exception:  # noqa: BLE001
                pass
            _SERVICE = ShareCountService(adapter)
        return _SERVICE


def reset_share_count_service_for_tests(
    service: ShareCountService | None = None,
) -> None:
    """Replace or clear the process-local share-count service (tests only)."""
    global _SERVICE
    with _LOCK:
        _SERVICE = service


def install_memory_share_count_for_tests(
    snapshot: ShareCountSnapshot,
    *,
    api_key: str = "test-key",
) -> ShareCountService:
    """TEST-ONLY: seed an in-memory ShareCountPort and install it as the façade."""
    adapter = InMemoryShareCountAdapter(api_key=api_key)
    adapter.put(snapshot)
    service = ShareCountService(adapter)
    reset_share_count_service_for_tests(service)
    return service


def share_count_health() -> dict[str, Any]:
    return _service().health().to_dict()


def share_count_metrics() -> dict[str, int]:
    return _service().metrics.snapshot()
