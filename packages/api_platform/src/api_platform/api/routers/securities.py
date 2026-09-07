"""Official Security Master HTTP boundary.

Search and identity only. Does not run valuation, share-count research,
or provider lookups. Ingest uses frozen official locators only.
"""

from __future__ import annotations

import logging
import time
from threading import Lock
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from api_platform.api.dependencies import require_admin_access, require_authenticated_actor
from api_platform.api.security_master_schemas import (
    SecurityIngestResponse,
    SecuritySearchResponse,
    SecurityUniverseResponse,
)
from dsp_platform.security_master import (
    get_security_master_store,
    ingest_official_universe,
    resolve_exact,
    search_snapshot,
)
from dsp_platform.security_master.models import ResolutionStatus, SearchOutcome

router = APIRouter(tags=["securities"])
_LOG = logging.getLogger("dsp.api.securities")
_INGEST_LOCK = Lock()

_Actor = dict[str, Any]


def _load_current():
    store = get_security_master_store()
    try:
        return store.current_snapshot()
    except Exception:
        _LOG.warning("security_master_read_failed")
        raise HTTPException(status_code=503, detail="Data unavailable.") from None


@router.get("/securities/search", response_model=SecuritySearchResponse)
def search_securities(
    request: Request,
    q: str = Query(default="", max_length=128),
    limit: int = Query(default=20, ge=1, le=50),
    _actor: _Actor = Depends(require_authenticated_actor),  # noqa: B008
) -> SecuritySearchResponse:
    started = time.perf_counter()
    snapshot = _load_current()
    outcome = search_snapshot(snapshot, q, limit=limit)
    _LOG.info(
        "securities_search resolution=%s candidates=%s snapshot=%s latency_ms=%s",
        outcome.resolution,
        len(outcome.candidates),
        outcome.snapshot_id or "none",
        int((time.perf_counter() - started) * 1000),
    )
    return SecuritySearchResponse(
        ok=outcome.available,
        query=outcome.query,
        resolution=str(outcome.resolution),
        available=outcome.available,
        message=outcome.message,
        snapshot_id=outcome.snapshot_id or None,
        source_date=outcome.source_date or None,
        retrieved_at=outcome.retrieved_at or None,
        candidates=[hit.to_dict() for hit in outcome.candidates],
    )


@router.get("/securities/resolve", response_model=SecuritySearchResponse)
def resolve_security(
    request: Request,
    listing_id: str = Query(default="", max_length=128),
    isin: str = Query(default="", max_length=16),
    exchange: str = Query(default="", max_length=16),
    symbol: str = Query(default="", max_length=32),
    _actor: _Actor = Depends(require_authenticated_actor),  # noqa: B008
) -> SecuritySearchResponse:
    snapshot = _load_current()
    outcome = resolve_exact(
        snapshot,
        listing_id=listing_id,
        isin=isin,
        exchange=exchange,
        symbol=symbol,
    )
    return SecuritySearchResponse(
        ok=outcome.available and str(outcome.resolution) == "EXACT",
        query=outcome.query,
        resolution=str(outcome.resolution),
        available=outcome.available,
        message=outcome.message,
        snapshot_id=outcome.snapshot_id or None,
        source_date=outcome.source_date or None,
        retrieved_at=outcome.retrieved_at or None,
        candidates=[hit.to_dict() for hit in outcome.candidates],
    )


@router.get("/securities/universe", response_model=SecurityUniverseResponse)
def security_universe(
    request: Request,
    _actor: _Actor = Depends(require_authenticated_actor),  # noqa: B008
) -> SecurityUniverseResponse:
    store = get_security_master_store()
    try:
        snapshot = store.current_snapshot()
        history = list(store.list_snapshots(limit=10))
    except Exception:
        _LOG.warning("security_master_universe_read_failed")
        return SecurityUniverseResponse(
            ok=False,
            available=False,
            message="Data unavailable.",
            snapshot=None,
            history=[],
        )
    if snapshot is None:
        return SecurityUniverseResponse(
            ok=False,
            available=False,
            message="Data unavailable.",
            snapshot=None,
            history=history,
        )
    return SecurityUniverseResponse(
        ok=True,
        available=True,
        message="",
        snapshot=snapshot.to_metadata_dict(),
        history=history,
    )


@router.post("/securities/universe/ingest", response_model=SecurityIngestResponse)
def ingest_security_universe(
    request: Request,
    _admin: _Actor = Depends(require_admin_access),  # noqa: B008
) -> SecurityIngestResponse:
    if not _INGEST_LOCK.acquire(blocking=False):
        raise HTTPException(status_code=409, detail="Security universe ingest already running")
    started = time.perf_counter()
    try:
        snapshot = ingest_official_universe(store=get_security_master_store())
    except Exception as exc:
        _LOG.warning(
            "security_universe_ingest_failed latency_ms=%s",
            int((time.perf_counter() - started) * 1000),
        )
        raise HTTPException(
            status_code=502,
            detail="Security universe could not be ingested",
        ) from exc
    finally:
        _INGEST_LOCK.release()
    accepted = snapshot.status.value != "FAILED" and snapshot.record_count > 0
    _LOG.info(
        "security_universe_ingest ok=%s records=%s snapshot=%s latency_ms=%s",
        accepted,
        snapshot.record_count,
        snapshot.snapshot_id,
        int((time.perf_counter() - started) * 1000),
    )
    return SecurityIngestResponse(
        ok=accepted,
        available=accepted,
        message=snapshot.error or "",
        snapshot=snapshot.to_metadata_dict(),
    )
