"""Copilot HTTP schemas — transport only (EPIC-012)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

__all__ = [
    "CopilotCompleteRequest",
    "CopilotCompleteResponse",
    "CopilotProviderInfo",
    "CopilotStreamChunk",
]


class CopilotCompleteRequest(BaseModel):
    """Inline copilot request with frozen analyse payloads."""

    model_config = ConfigDict(extra="forbid")

    question_id: str = Field(default="freeform", max_length=64)
    freeform: str | None = Field(default=None, max_length=8000)
    request: dict[str, Any] | None = None
    response: dict[str, Any] | None = None
    secondary_request: dict[str, Any] | None = None
    secondary_response: dict[str, Any] | None = None
    last_intent: str | None = Field(default=None, max_length=64)
    market_context: dict[str, Any] | None = None


class CopilotCompleteResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: str
    citations: list[str] = Field(default_factory=list)
    intent: str
    unavailable: bool = False
    provider_id: str
    limitations: list[str] = Field(default_factory=list)


class CopilotStreamChunk(BaseModel):
    model_config = ConfigDict(extra="forbid")

    delta: str
    done: bool = False
    provider_id: str | None = None


class CopilotProviderInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    providers: list[dict[str, Any]] = Field(default_factory=list)
    active_provider: str
