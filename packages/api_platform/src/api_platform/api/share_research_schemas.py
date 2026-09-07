"""HTTP contract for POST /api/v1/share-research."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

_TICKER_PATTERN = r"^[A-Za-z0-9.\-]{1,32}$"
_EXCHANGE_PATTERN = r"^[A-Za-z0-9_\-]{1,32}$"


class ShareResearchHttpRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ticker: str = Field(min_length=1, max_length=32, pattern=_TICKER_PATTERN)
    exchange: str | None = Field(default=None, max_length=32, pattern=_EXCHANGE_PATTERN)
    company: str | None = Field(default=None, max_length=256)
    isin: str | None = Field(default=None, max_length=16)
    force_refresh: bool = False

    @field_validator("ticker", "exchange", "company", "isin", mode="before")
    @classmethod
    def _strip(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value


class ShareResearchHttpResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ok: bool
    api_version: str = "v1"
    result: dict[str, Any]
    limitations: list[str] = Field(default_factory=list)
