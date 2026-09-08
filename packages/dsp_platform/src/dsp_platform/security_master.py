"""Security Master façade for DSPPlatform.

Thin wrapper over ``data_engine.security_master``. No scoring, valuation,
or vendor instrument keys.
"""

from __future__ import annotations

from threading import Lock
from typing import Any

from data_engine.security_master import (
    SecurityMasterCatalog,
    SecurityMasterService,
    load_default_catalog,
)

__all__ = [
    "resolve_security_identity",
    "reset_security_master_for_tests",
    "search_securities",
    "security_master_authority",
]

_LOCK = Lock()
_SERVICE: SecurityMasterService | None = None


def _service() -> SecurityMasterService:
    global _SERVICE
    with _LOCK:
        if _SERVICE is None:
            _SERVICE = SecurityMasterService(load_default_catalog())
        return _SERVICE


def reset_security_master_for_tests(
    service: SecurityMasterService | None = None,
    *,
    catalog: SecurityMasterCatalog | None = None,
) -> None:
    """Replace or clear the process-local Security Master (tests only)."""
    global _SERVICE
    with _LOCK:
        if service is not None:
            _SERVICE = service
        elif catalog is not None:
            _SERVICE = SecurityMasterService(catalog)
        else:
            _SERVICE = None


def search_securities(
    query: str,
    *,
    exchange: str | None = None,
    limit: int = 25,
) -> dict[str, Any]:
    return _service().search(query, exchange=exchange, limit=limit).to_public_dict()


def resolve_security_identity(
    query: str,
    *,
    exchange: str | None = None,
    isin: str | None = None,
    mic: str | None = None,
) -> dict[str, Any]:
    return _service().resolve(
        query, exchange=exchange, isin=isin, mic=mic
    ).to_public_dict()


def security_master_authority() -> dict[str, Any]:
    return _service().catalog.authority.to_public_dict()
