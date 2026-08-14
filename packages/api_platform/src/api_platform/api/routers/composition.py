"""Composition routes — HTTP → DSPPlatform.compose_intelligence only."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from api_platform.api.composition_schemas import (
    AnalyseRequest,
    AnalyseResponse,
    ValidateResponse,
)
from api_platform.api.dependencies import ApiState, get_api_state
from api_platform.api.mappers import (
    CompositionApiError,
    map_pipeline_payload,
    map_platform_result,
)
from api_platform.api.validation import validate_analyse_request
from dsp_platform import CompositionInputError, build_composition_request

router = APIRouter(tags=["composition"])


@router.post("/analyse", response_model=AnalyseResponse)
def analyse(
    body: AnalyseRequest,
    request: Request,
    state: ApiState = Depends(get_api_state),
) -> AnalyseResponse:
    """Run the platform composition pipeline; return public PipelineResult DTO."""
    correlation_id = getattr(request.state, "request_id", None)
    errors = validate_analyse_request(body)
    if errors:
        raise CompositionApiError(
            "request validation failed",
            error_code="VALIDATION_ERROR",
            status_code=422,
            validation_errors=errors,
            correlation_id=correlation_id,
        )

    try:
        composition_request = build_composition_request(
            ticker=body.ticker,
            company=body.company,
            current_market_price=body.current_market_price,
            financial_statements=body.financial_statements.model_dump(),
            valuation_signals=(
                body.valuation_signals.model_dump()
                if body.valuation_signals is not None
                else None
            ),
            stop_on_stage_failure=body.stop_on_stage_failure,
        )
    except CompositionInputError as exc:
        raise CompositionApiError(
            "invalid composition input",
            error_code="COMPOSITION_INPUT_ERROR",
            status_code=422,
            validation_errors=[str(exc)],
            correlation_id=correlation_id,
            detail=str(exc),
        ) from None

    platform_result = state.platform.compose_intelligence(composition_request)
    pipeline = platform_result.payload
    if pipeline is None:
        raise CompositionApiError(
            "composition returned no payload",
            error_code="COMPOSITION_EMPTY",
            status_code=502,
            correlation_id=correlation_id,
        )

    public_payload = map_pipeline_payload(pipeline)
    response = map_platform_result(
        platform_result,
        api_version=state.api_version,
        correlation_id=correlation_id,
        public_payload=public_payload,
    )

    if not platform_result.ok:
        failed = getattr(getattr(pipeline, "metadata", None), "failed_stage", None)
        # Still return 200 with ok=False for graceful degradation payloads;
        # structured errors remain in payload.errors / metadata.
        response.errors = list(response.errors) + [
            f"pipeline degraded; failed_stage={failed}"
        ]

    # EPIC-011B — best-effort immutable snapshot capture AFTER pipeline completes.
    # Never alters engines, recommendation logic, or the analyse response contract.
    try:
        import os

        if os.getenv("DSP_RI_AUTO_CAPTURE", "1").lower() in {
            "1",
            "true",
            "yes",
            "on",
        }:
            capture_payload = (
                public_payload if isinstance(public_payload, dict) else {}
            )
            state.platform.capture_research_intelligence_snapshot(
                capture_payload,
                ticker=body.ticker,
                company=body.company or None,
                exchange=body.exchange,
                allow_duplicate=True,
            )
    except Exception:  # noqa: BLE001
        pass

    return response


@router.post("/validate", response_model=ValidateResponse)
def validate_payload(
    body: AnalyseRequest,
    state: ApiState = Depends(get_api_state),
) -> ValidateResponse:
    """Validate analyse request shape only — no pipeline execution."""
    errors = validate_analyse_request(body)
    warnings: list[str] = []
    if body.exchange is None:
        warnings.append("exchange not provided")
    if body.valuation_signals is None and body.current_market_price is not None:
        warnings.append(
            "price-only valuation path may run degraded valuation stage"
        )
    return ValidateResponse(
        ok=len(errors) == 0,
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        api_version=state.api_version,
    )
