"""Map platform composition results / errors to stable API DTOs."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from api_platform.api.composition_schemas import (
    AnalyseResponse,
    CompositionErrorBody,
)
from api_platform.api.exceptions import ApiError

__all__ = [
    "CompositionApiError",
    "map_pipeline_payload",
    "map_platform_result",
]


class CompositionApiError(ApiError):
    """Structured composition failure (never exposes internal exceptions)."""

    def __init__(
        self,
        message: str,
        *,
        error_code: str = "COMPOSITION_ERROR",
        status_code: int = 422,
        pipeline_stage: str | None = None,
        validation_errors: list[str] | None = None,
        correlation_id: str | None = None,
        detail: str | None = None,
    ) -> None:
        super().__init__(message, status_code=status_code)
        self.error_code = error_code
        self.pipeline_stage = pipeline_stage
        self.validation_errors = list(validation_errors or [])
        self.correlation_id = correlation_id
        self.detail = detail


def map_platform_result(
    platform_result: Any,
    *,
    api_version: str,
    correlation_id: str | None,
    public_payload: dict[str, Any],
) -> AnalyseResponse:
    meta = getattr(platform_result, "metadata", None)
    pipeline_meta = None
    payload_obj = getattr(platform_result, "payload", None)
    if payload_obj is not None:
        pipeline_meta = getattr(payload_obj, "metadata", None)
    return AnalyseResponse(
        ok=bool(getattr(platform_result, "ok", False)),
        capability=str(
            getattr(platform_result, "capability", "compose_intelligence")
        ),
        payload=public_payload,
        limitations=list(getattr(platform_result, "limitations", ()) or ()),
        errors=list(getattr(platform_result, "errors", ()) or ()),
        api_version=api_version,
        platform_version=getattr(meta, "version", None),
        pipeline_version=getattr(pipeline_meta, "pipeline_version", None),
        correlation_id=correlation_id,
    )


def map_pipeline_payload(pipeline_result: Any) -> dict[str, Any]:
    from dsp_platform import pipeline_result_public_dict

    return pipeline_result_public_dict(pipeline_result)


def composition_error_body(
    exc: CompositionApiError,
    *,
    api_version: str = "v1",
) -> CompositionErrorBody:
    return CompositionErrorBody(
        error_code=exc.error_code,
        message=exc.message,
        detail=exc.detail,
        pipeline_stage=exc.pipeline_stage,
        validation_errors=exc.validation_errors,
        correlation_id=exc.correlation_id,
        timestamp=datetime.now(tz=UTC),
        api_version=api_version,
        status_code=exc.status_code,
    )
