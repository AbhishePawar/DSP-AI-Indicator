"""HTTP contract for Security Master search and universe metadata.

Does not change POST /analyse.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SecuritySearchResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ok: bool
    api_version: str = "v1"
    query: str
    resolution: str
    available: bool
    message: str
    snapshot_id: str | None = None
    source_date: str | None = None
    retrieved_at: str | None = None
    candidates: list[dict[str, Any]] = Field(default_factory=list)


class SecurityUniverseResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ok: bool
    api_version: str = "v1"
    available: bool
    message: str
    snapshot: dict[str, Any] | None = None
    history: list[dict[str, Any]] = Field(default_factory=list)


class SecurityIngestResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ok: bool
    api_version: str = "v1"
    available: bool
    message: str
    snapshot: dict[str, Any] | None = None
