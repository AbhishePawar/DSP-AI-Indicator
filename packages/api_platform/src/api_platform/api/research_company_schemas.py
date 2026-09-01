"""Canonical research HTTP contract — STEP 4I blocked stub.

Typed request/response for POST /api/v1/research/company.
Does not execute AI, compose a ResearchPackage, or return a report.
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


class AiExecutionState(StrEnum):
    """Public AI execution state. STEP 4I emits only the blocked value."""

    AI_EXECUTION_BLOCKED = "ai_execution_blocked"


class ResearchCompanyOutcome(StrEnum):
    """Public research outcome. STEP 4I emits only the blocked value."""

    AI_EXECUTION_BLOCKED = "ai_execution_blocked"


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

    extra=forbid so unknown private keys cannot pass this contract.
    Nested public sections stay JSON objects. STEP 4I never populates this
    model — ``report`` is always null while AI execution is blocked.
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


# Keep the HTTP twin aligned with the canonical public report keys.
assert frozenset(PublicResearchReportHttp.model_fields) == PUBLIC_TOP_LEVEL_KEYS
# Semantic anchor — the HTTP report field is the public projection of this type.
assert PublicResearchReport.__name__ == "PublicResearchReport"


class ResearchCompanyResponse(BaseModel):
    """Typed blocked/success envelope. Not ``dict[str, Any]``."""

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
            name
            for name in payload
            if str(name) in PRIVATE_REPORT_FIELD_NAMES
        )
        if leaked:
            raise ValueError(f"private fields leaked into research HTTP: {leaked}")
        return self
