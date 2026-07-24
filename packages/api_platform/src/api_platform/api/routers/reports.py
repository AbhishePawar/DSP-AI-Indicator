"""Report retrieval routes — ephemeral API registry only."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from api_platform.api.dependencies import ApiState, get_api_state
from api_platform.api.schemas import ReportResponse

router = APIRouter(tags=["reports"])


@router.get("/report/{report_id}", response_model=ReportResponse)
def get_report(
    report_id: str,
    state: ApiState = Depends(get_api_state),
) -> ReportResponse:
    """Fetch a report from the process-local ephemeral registry.

    Not durable persistence — entries exist only for the API process lifetime
    (typically populated by ``POST /analyze/company``).
    """
    stored = state.reports.get(report_id)
    exported = state.platform.export_report(stored, format_name="native")
    payload = exported.payload or {}
    return ReportResponse(
        report_id=report_id,
        format=str(payload.get("format", "native")),
        report=payload.get("report", stored),
        api_version=state.api_version,
        limitations=list(exported.limitations),
    )
