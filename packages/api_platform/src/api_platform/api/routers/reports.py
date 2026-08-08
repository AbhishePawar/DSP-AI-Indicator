"""Report retrieval routes — owner-scoped durable registry (P1-07)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from api_platform.api.dependencies import (
    ApiState,
    get_api_state,
    require_authenticated_actor,
)
from api_platform.api.schemas import ReportResponse
from api_platform.api.tenant_isolation import actor_owns_report

router = APIRouter(tags=["reports"])


@router.get("/report/{report_id}", response_model=ReportResponse)
def get_report(
    report_id: str,
    state: ApiState = Depends(get_api_state),
    auth: dict[str, Any] = Depends(require_authenticated_actor),
) -> ReportResponse:
    """Fetch a report owned by the authenticated principal only (P1-07)."""
    actor = str(auth.get("user_id") or "").strip()
    if not actor:
        raise HTTPException(status_code=401, detail="authentication required")

    if not state.reports.has(report_id):
        raise HTTPException(status_code=404, detail="report not found")
    stored = state.reports.get(report_id)
    if not actor_owns_report(stored, actor):
        # Fail closed without confirming foreign ownership (IDOR-safe).
        raise HTTPException(status_code=404, detail="report not found")

    exported = state.platform.export_report(stored, format_name="native")
    payload = exported.payload or {}
    return ReportResponse(
        report_id=report_id,
        format=str(payload.get("format", "native")),
        report=payload.get("report", stored),
        api_version=state.api_version,
        limitations=list(exported.limitations),
    )
