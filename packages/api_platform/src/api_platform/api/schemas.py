"""Pydantic request/response schemas — transport only (K1.1)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

__all__ = [
    "AnalyzeCompanyRequest",
    "ApiErrorBody",
    "ApiResponse",
    "CompareRequest",
    "CopilotChatRequest",
    "HealthResponse",
    "PlatformInfoResponse",
    "ReportResponse",
    "WorkflowRunRequest",
]


class ApiResponse(BaseModel):
    """Stable envelope for platform orchestration results."""

    model_config = ConfigDict(extra="forbid")

    ok: bool
    capability: str
    payload: Any = None
    limitations: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    api_version: str = "v1"
    platform_version: str | None = None


class ApiErrorBody(BaseModel):
    """Global exception response body."""

    model_config = ConfigDict(extra="forbid")

    ok: bool = False
    error: str
    detail: str | None = None
    message: str | None = None
    error_code: str | None = None
    pipeline_stage: str | None = None
    validation_errors: list[str] = Field(default_factory=list)
    correlation_id: str | None = None
    timestamp: datetime | None = None
    api_version: str = "v1"
    status_code: int


class HealthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str
    ready: bool
    api_version: str = "v1"
    platform_version: str | None = None
    pipeline_version: str | None = None
    repository_version: str | None = None
    checks: list[dict[str, Any]] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class PlatformInfoResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    version: str
    status: str
    environment: str
    capabilities: list[str]
    registered_services: list[str]
    generated_at: datetime
    notes: list[str] = Field(default_factory=list)
    api_version: str = "v1"


class AnalyzeCompanyRequest(BaseModel):
    """HTTP input for single-company analysis — mapped to platform request."""

    model_config = ConfigDict(extra="forbid")

    symbol: str = Field(min_length=1, max_length=32)
    asset_class: str = "equity"
    currency: str = "USD"
    start: date
    end: date
    as_decision_pack: bool = False
    include_fundamentals: bool | None = None
    include_economic: bool | None = None
    include_valuation: bool | None = None
    allow_partial: bool | None = None


class CompareRequest(BaseModel):
    """Comparison request — packs are opaque cite payloads for the platform.

    The API does not construct business conclusions. Callers supply already
    produced Decision Pack payloads (as JSON-compatible dicts) for
    orchestration. When packs are empty, the API returns a validation error.
    """

    model_config = ConfigDict(extra="forbid")

    packs: list[dict[str, Any]] = Field(default_factory=list)
    note: str | None = None


class WorkflowRunRequest(BaseModel):
    """Workflow run request — opaque engine context payload.

    Persistence and workflow implementation are out of scope. The API
    validates presence of a context object and delegates to
    ``DSPPlatform.run_workflow`` when a live context handle is provided via
    the optional ``context_ref`` registry key.
    """

    model_config = ConfigDict(extra="forbid")

    context_ref: str | None = None
    context: dict[str, Any] | None = None
    note: str | None = None


class CopilotChatRequest(BaseModel):
    """Copilot chat request — opaque conversation context reference."""

    model_config = ConfigDict(extra="forbid")

    context_ref: str | None = None
    user_text: str | None = Field(default=None, max_length=8000)
    note: str | None = None


class ReportResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    report_id: str
    format: str
    report: Any
    api_version: str = "v1"
    limitations: list[str] = Field(default_factory=list)
