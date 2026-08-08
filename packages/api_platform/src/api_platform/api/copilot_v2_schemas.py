"""RC1 Milestone 7 — Copilot 2.0 request schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CopilotV2Request(BaseModel):
    """Shared body for Copilot 2.0 specialist routes and enhanced chat."""

    model_config = ConfigDict(extra="forbid")

    message: str | None = Field(None, max_length=8000)
    user_text: str | None = Field(None, max_length=8000)
    mode: str | None = Field(None, max_length=32)
    conversation_id: str | None = Field(None, max_length=128)
    symbol: str | None = Field(None, max_length=32)
    symbols: list[str] | None = None
    portfolio_id: str | None = Field(None, max_length=128)
    analyse_response: dict[str, Any] | None = None
    secondary_analyse_response: dict[str, Any] | None = None
    research_object: dict[str, Any] | None = None
    report: dict[str, Any] | None = None
    portfolio: dict[str, Any] | None = None
    portfolio_intelligence: dict[str, Any] | None = None
    committee_result: dict[str, Any] | None = None
    comparison_result: dict[str, Any] | None = None
    document_kind: str | None = Field(None, max_length=64)
    workspace: str | None = Field(None, max_length=128)
    buffett_mode: bool = False
    # Legacy J1 chat fields (optional)
    context_ref: str | None = Field(None, max_length=128)
    note: str | None = Field(None, max_length=1000)

    def resolved_message(self) -> str:
        return (self.message or self.user_text or "").strip()
