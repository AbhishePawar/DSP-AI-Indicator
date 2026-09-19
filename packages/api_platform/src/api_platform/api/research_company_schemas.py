"""Canonical research HTTP contract.

Typed request/response for POST /api/v1/research/company.
AI execution happens outside the HTTP contract; only the validated public
research report may cross this boundary.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from dsp_platform.research_report.models import (
    PRIVATE_REPORT_FIELD_NAMES,
    PUBLIC_TOP_LEVEL_KEYS,
    PublicResearchReport,
    assert_public_report_privacy,
)

__all__ = [
    "AI_EXECUTION_BLOCKED_MESSAGE",
    "AI_EXECUTION_UNAVAILABLE_MESSAGE",
    "AI_VALIDATION_FAILED_MESSAGE",
    "AiExecutionState",
    "PublicResearchReportHttp",
    "ResearchCompanyOutcome",
    "ResearchCompanyRequest",
    "ResearchCompanyResponse",
]

# Matches composition ticker / exchange conventions (AnalyseRequest + validation.py).
_TICKER_PATTERN = r"^[A-Za-z0-9.\-]{1,32}$"
_EXCHANGE_PATTERN = r"^[A-Za-z0-9_\-]{1,32}$"

AI_EXECUTION_BLOCKED_MESSAGE = (
    "Research is unavailable because production AI execution is blocked."
)
AI_EXECUTION_UNAVAILABLE_MESSAGE = (
    "Research AI is unavailable because the configured AI provider is unavailable."
)
AI_VALIDATION_FAILED_MESSAGE = (
    "Research AI output failed DSP validation and was rejected."
)


class AiExecutionState(StrEnum):
    """Public AI execution state."""

    AI_EXECUTION_BLOCKED = "ai_execution_blocked"
    AI_EXECUTED = "ai_executed"
    AI_UNAVAILABLE = "ai_unavailable"
    AI_VALIDATION_FAILED = "ai_validation_failed"


class ResearchCompanyOutcome(StrEnum):
    """Public research outcome."""

    AI_EXECUTION_BLOCKED = "ai_execution_blocked"
    SUCCESS = "success"
    AI_UNAVAILABLE = "ai_unavailable"
    AI_VALIDATION_FAILED = "ai_validation_failed"


class ResearchCompanyRequest(BaseModel):
    """POST /research/company — client asks to research a company only."""

    model_config = ConfigDict(extra="forbid")

    ticker: str = Field(min_length=1, max_length=32, pattern=_TICKER_PATTERN)
    exchange: str | None = Field(default=None, max_length=32, pattern=_EXCHANGE_PATTERN)
    company: str | None = Field(default=None, max_length=256)

    @field_validator("ticker", "exchange", "company", mode="before")
    @classmethod
    def _strip_optional_text(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value


class PublicResearchReportHttp(BaseModel):
    """Strict HTTP twin of ``PublicResearchReport.to_public_dict()``.

    Extra fields are forbidden so private DSP/AI internals cannot pass this
    contract. The report is populated only after DSP validation succeeds.
    """

    model_config = ConfigDict(extra="forbid")

    schema_version: str
    methodology_version: str
    source_pipeline: str
    research_status: str
    identity: dict[str, object]
    executive_summary: dict[str, object]
    business_quality: dict[str, object]
    economic_moat: dict[str, object]
    management_quality: dict[str, object]
    financial_strength: dict[str, object]
    earnings_quality: dict[str, object]
    growth_quality: dict[str, object]
    factor_scorecard: list[dict[str, object]]
    buffett_analysis: dict[str, object]
    financials: dict[str, object]
    valuation: dict[str, object]
    recommendation: dict[str, object]
    risk: dict[str, object]
    entry_exit: dict[str, object]
    scenarios: dict[str, object]
    expected_returns: dict[str, object]
    industry: dict[str, object]
    evidence: list[dict[str, object]]
    limitations: list[str]


assert frozenset(PublicResearchReportHttp.model_fields) == PUBLIC_TOP_LEVEL_KEYS
assert PublicResearchReport.__name__ == "PublicResearchReport"


class ResearchCompanyResponse(BaseModel):
    """Typed research envelope; never exposes raw AI/provider internals."""

    model_config = ConfigDict(extra="forbid")

    ok: bool
    api_version: Literal["v1"] = "v1"
    correlation_id: str | None = None
    analysis_id: str | None = None
    ai_execution_state: AiExecutionState
    outcome: ResearchCompanyOutcome
    report: PublicResearchReportHttp | None = None
    limitations: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _privacy_fail_closed(self) -> ResearchCompanyResponse:
        payload = self.model_dump(mode="python")
        assert_public_report_privacy(payload)
        leaked = sorted(
            name for name in payload if str(name) in PRIVATE_REPORT_FIELD_NAMES
        )
        if leaked:
            raise ValueError(f"private fields leaked into research HTTP: {leaked}")
        return self
