"""Composition / analyse request & response DTOs — stable HTTP contracts only."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

__all__ = [
    "AnalyseRequest",
    "AnalyseResponse",
    "CapabilitiesResponse",
    "CompositionErrorBody",
    "FinancialPeriodDTO",
    "FinancialStatementsDTO",
    "StatementBlockDTO",
    "ValidateResponse",
    "ValuationSignalsDTO",
    "VersionResponse",
]


class StatementBlockDTO(BaseModel):
    """Opaque numeric line-item map (income / balance / cash-flow)."""

    model_config = ConfigDict(extra="allow")

    # Common fields documented for OpenAPI; extras allowed for full statements.
    revenue: float | None = None
    net_income: float | None = None
    total_assets: float | None = None
    total_equity: float | None = None
    operating_cash_flow: float | None = None
    free_cash_flow: float | None = None


class FinancialPeriodDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    period_type: str = Field(description="annual | quarterly | ttm | half_year | custom")
    period_end: str = Field(description="ISO date YYYY-MM-DD")
    fiscal_year: int | None = None
    fiscal_quarter: int | None = None
    currency: str | dict[str, Any] = "USD"


class FinancialStatementsDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    period: FinancialPeriodDTO
    income_statement: dict[str, Any] = Field(default_factory=dict)
    balance_sheet: dict[str, Any] = Field(default_factory=dict)
    cash_flow: dict[str, Any] = Field(default_factory=dict)
    statement_metadata: dict[str, Any] = Field(default_factory=dict)


class ValuationSignalsDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intrinsic_value_per_share: float | None = None
    current_market_price: float | None = None
    margin_of_safety: float | None = None
    premium_discount: float | None = None
    confidence: float = Field(default=0.55, ge=0.0, le=1.0)


class AnalyseRequest(BaseModel):
    """POST /analyse — composition input (presentation boundary only)."""

    model_config = ConfigDict(extra="forbid")

    ticker: str = Field(min_length=1, max_length=32)
    exchange: str | None = Field(default=None, max_length=32)
    company: str = Field(default="", max_length=256)
    # Optional: production ticker/exchange path loads authenticated Upstox
    # statements server-side (P1-01). Client FS remains accepted for tests /
    # Research Mode but is never authoritative over the auth bundle.
    financial_statements: FinancialStatementsDTO | None = None
    valuation_signals: ValuationSignalsDTO | None = None
    current_market_price: float | None = None
    stop_on_stage_failure: bool = False


class AnalyseResponse(BaseModel):
    """Typed envelope over platform PipelineResult public dict."""

    model_config = ConfigDict(extra="forbid")

    ok: bool
    capability: str = "compose_intelligence"
    payload: dict[str, Any]
    limitations: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    api_version: str = "v1"
    platform_version: str | None = None
    pipeline_version: str | None = None
    correlation_id: str | None = None
    # P1-06 — durable investment provenance reference (server-assigned only).
    analysis_id: str | None = None
    audit_reference: str | None = None
    provenance_persisted: bool = False


class ValidateResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ok: bool
    valid: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    api_version: str = "v1"


class VersionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    api_version: str
    api_package_version: str
    platform_version: str
    pipeline_version: str
    docs_version: str
    package_versions: dict[str, str] = Field(default_factory=dict)


class CapabilitiesResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    analytical_modules: list[str]
    supported_reports: list[str]
    pipeline_stages: list[str]
    pipeline_version: str
    platform_version: str
    api_version: str = "v1"
    package_versions: dict[str, str] = Field(default_factory=dict)
    platform_capabilities: list[str] = Field(default_factory=list)


class CompositionErrorBody(BaseModel):
    """Deterministic composition / validation error contract."""

    model_config = ConfigDict(extra="forbid")

    ok: bool = False
    error_code: str
    message: str
    detail: str | None = None
    pipeline_stage: str | None = None
    validation_errors: list[str] = Field(default_factory=list)
    correlation_id: str | None = None
    timestamp: datetime
    api_version: str = "v1"
    status_code: int
