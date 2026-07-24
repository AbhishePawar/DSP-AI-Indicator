"""Comparison routes — schema validation + platform orchestration envelope."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from api_platform.api.dependencies import ApiState, get_api_state
from api_platform.api.exceptions import ApiValidationError
from api_platform.api.schemas import ApiResponse, CompareRequest

router = APIRouter(tags=["comparison"])


@router.post("/compare", response_model=ApiResponse)
def compare(
    body: CompareRequest,
    state: ApiState = Depends(get_api_state),
) -> ApiResponse:
    """Validate comparison request; require Decision Pack payloads.

    Full ``QualitativeComparisonEngine`` wiring remains a composition concern.
    Without packs the API returns a validation error. When packs are present,
    the API returns an orchestration envelope noting that engine injection is
    required (no business comparison is performed in the API layer).
    """
    if not body.packs:
        raise ApiValidationError(
            "compare requires at least one Decision Pack payload in packs"
        )

    limitations = [
        "API layer performs no qualitative comparison math.",
        "Provide a wired QualitativeComparisonEngine via platform composition "
        "to execute DSPPlatform.compare_companies.",
    ]
    if body.note:
        limitations.append(body.note)

    return ApiResponse(
        ok=False,
        capability="compare_companies",
        payload={
            "pack_count": len(body.packs),
            "status": "accepted_for_orchestration",
        },
        limitations=limitations,
        errors=[
            "comparison engine not injected in default API composition; "
            "packs validated only"
        ],
        api_version=state.api_version,
        platform_version=state.platform.get_platform_info().version,
    )
