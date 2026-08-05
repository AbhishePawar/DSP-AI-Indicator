"""Comparison routes — HTTP -> DSPPlatform.compare_companies only.

Business comparison logic lives entirely in ``comparison`` +
``industry``; this router only resolves ``report_ids`` into previously
computed ``DecisionPack`` reports and shapes the HTTP envelope.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from api_platform.api.dependencies import ApiState, get_api_state
from api_platform.api.exceptions import ApiValidationError
from api_platform.api.schemas import ApiResponse, CompareRequest
from dsp_platform import DecisionPack, EligibilityOptions, comparison_result_public_dict

router = APIRouter(tags=["comparison"])


@router.post("/compare", response_model=ApiResponse)
def compare(
    body: CompareRequest,
    state: ApiState = Depends(get_api_state),
) -> ApiResponse:
    """Compare Decision Pack reports via the platform's comparison engine.

    ``report_ids`` must reference reports previously created by
    ``POST /analyze/company`` with ``as_decision_pack=true``.
    """
    report_ids = [r.strip() for r in body.report_ids if r.strip()]
    if len(set(report_ids)) < 2:
        raise ApiValidationError(
            "compare requires at least two distinct report_ids "
            "(from POST /analyze/company with as_decision_pack=true)"
        )

    packs: list[DecisionPack] = []
    missing: list[str] = []
    invalid: list[str] = []
    for report_id in report_ids:
        if not state.reports.has(report_id):
            missing.append(report_id)
            continue
        record = state.reports.get(report_id)
        payload = record.get("payload") if isinstance(record, dict) else None
        if not isinstance(payload, DecisionPack):
            invalid.append(report_id)
            continue
        packs.append(payload)

    if missing:
        raise ApiValidationError(f"unknown report_ids: {missing}")
    if invalid:
        raise ApiValidationError(
            "report_ids must reference Decision Pack reports "
            f"(created with as_decision_pack=true): {invalid}"
        )

    result = state.platform.compare_companies(
        packs,
        eligibility_options=EligibilityOptions(
            allow_related=body.allow_related, allow_limited=body.allow_limited
        ),
    )

    payload = comparison_result_public_dict(result.payload) if result.ok else None
    limitations = list(result.limitations)
    if body.note:
        limitations.append(body.note)

    return ApiResponse(
        ok=result.ok,
        capability=result.capability,
        payload=payload,
        limitations=limitations,
        errors=list(result.errors),
        api_version=state.api_version,
        platform_version=result.metadata.version,
    )
