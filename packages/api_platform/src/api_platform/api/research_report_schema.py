"""Public research report schema validation & privacy-boundary enforcement."""

from __future__ import annotations

import json
import math
import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

__all__ = [
    "ALLOWED_RECOMMENDATIONS",
    "FORBIDDEN_PRIVATE_KEYS",
    "PublicResearchReportDTO",
    "validate_public_research_report",
]

ALLOWED_RECOMMENDATIONS = frozenset({
    "BUY",
    "SELL",
    "HOLD",
    "UNAVAILABLE",
    "NEUTRAL",
    "AVOID",
    "WATCHLIST",
})

FORBIDDEN_PRIVATE_KEYS = frozenset({
    "provider",
    "model",
    "routing_tier",
    "routing_reasons",
    "confidence_requirement",
    "estimated_cost_usd",
    "input_tokens",
    "output_tokens",
    "latency_ms",
    "model_score",
    "routing_criteria",
    "internal_prompt",
    "tool_calls",
    "tool_results",
    "raw_ai_response",
    "internal_validation",
    "chain_of_thought",
    "scratchpad",
    "system_prompt",
    "api_key",
    "secret",
    "access_token",
    "authorization",
    "canary",
})

_CANARY_PATTERN = re.compile(
    r"(?:sk-[a-zA-Z0-9_-]{16,}|canary_[a-zA-Z0-9_-]{8,}|bearer\s+[a-zA-Z0-9_\.\-]{20,}|DSP_AI_SECRET_CANARY)",
    re.IGNORECASE,
)


class PublicResearchReportDTO(BaseModel):
    """Explicit public research report contract."""

    model_config = ConfigDict(extra="forbid")

    recommendation: str
    valuation: str | None = None
    analysis: str
    risks: list[str] = Field(default_factory=list)
    evidence_citations: list[str] = Field(default_factory=list)
    confidence: float
    limitations: list[str] = Field(default_factory=list)
    schema_version: Literal["public_decision_pack_v1"] = "public_decision_pack_v1"

    @field_validator("recommendation", mode="before")
    @classmethod
    def _validate_recommendation(cls, v: Any) -> str:
        if not isinstance(v, str):
            raise ValueError("recommendation must be a string")
        stripped = v.strip()
        if not stripped:
            raise ValueError("recommendation cannot be empty or blank")
        upper = stripped.upper()
        if upper not in ALLOWED_RECOMMENDATIONS:
            raise ValueError(
                f"unsupported recommendation: {upper!r}. Allowed values: {sorted(ALLOWED_RECOMMENDATIONS)}"
            )
        return upper

    @field_validator("analysis", mode="before")
    @classmethod
    def _validate_analysis(cls, v: Any) -> str:
        if not isinstance(v, str):
            raise ValueError("analysis must be a string")
        stripped = v.strip()
        if not stripped:
            raise ValueError("analysis cannot be empty or blank")
        return stripped

    @field_validator("valuation", mode="before")
    @classmethod
    def _validate_valuation(cls, v: Any) -> str | None:
        if v is None:
            return None
        if not isinstance(v, str):
            raise ValueError("valuation must be a string or null")
        stripped = v.strip()
        if not stripped:
            return None
        return stripped

    @field_validator("confidence", mode="before")
    @classmethod
    def _validate_confidence(cls, v: Any) -> float:
        if isinstance(v, bool):
            raise ValueError("confidence cannot be a boolean")
        if not isinstance(v, (int, float)):
            raise ValueError("confidence must be a number")
        fval = float(v)
        if not math.isfinite(fval):
            raise ValueError("confidence must be a finite number")
        if not (0.0 <= fval <= 1.0):
            raise ValueError("confidence must be between 0.0 and 1.0")
        return fval

    @field_validator("risks", "evidence_citations", "limitations", mode="before")
    @classmethod
    def _validate_string_lists(cls, v: Any, info: Any) -> list[str]:
        field_name = info.field_name
        if v is None:
            return []
        if not isinstance(v, (list, tuple)):
            raise ValueError(f"{field_name} must be a list or tuple of strings")
        cleaned: list[str] = []
        for idx, item in enumerate(v):
            if not isinstance(item, str):
                raise ValueError(f"{field_name}[{idx}] must be a string")
            stripped = item.strip()
            if not stripped:
                raise ValueError(f"{field_name}[{idx}] cannot be empty or blank")
            if any(ord(c) < 32 and c not in "\t\n\r" for c in stripped):
                raise ValueError(f"{field_name}[{idx}] contains invalid control characters")
            cleaned.append(stripped)
        return cleaned


def _scan_for_leakage(val: Any) -> str | None:
    """Recursively scan for private keys, secret patterns, and canaries."""
    if isinstance(val, dict):
        for k, v in val.items():
            if not isinstance(k, str):
                return f"non-string key: {k!r}"
            if k.strip().lower() in FORBIDDEN_PRIVATE_KEYS:
                return f"forbidden private key present: {k!r}"
            err = _scan_for_leakage(v)
            if err:
                return err
    elif isinstance(val, (list, tuple)):
        for item in val:
            err = _scan_for_leakage(item)
            if err:
                return err
    elif isinstance(val, str):
        if _CANARY_PATTERN.search(val):
            return "secret canary or credential pattern detected in text"
    return None


def validate_public_research_report(data: Any) -> tuple[dict[str, Any] | None, str | None]:
    """Validate research report dict against explicit schema and privacy boundary.

    Returns:
        (validated_dict, None) on success.
        (None, error_reason) on validation failure or privacy violation.
    """
    if not isinstance(data, dict):
        return None, f"expected dict, got {type(data).__name__}"

    leak = _scan_for_leakage(data)
    if leak:
        return None, f"privacy boundary violation: {leak}"

    try:
        dto = PublicResearchReportDTO.model_validate(data)
    except ValidationError as exc:
        details = []
        for err in exc.errors():
            loc = ".".join(str(p) for p in err.get("loc", ()))
            msg = err.get("msg", "invalid")
            details.append(f"{loc}: {msg}" if loc else msg)
        sanitized = "; ".join(details)
        if _CANARY_PATTERN.search(sanitized):
            return None, "schema validation failed: invalid input"
        return None, f"schema validation failed: {sanitized}"
    except Exception as exc:  # noqa: BLE001
        return None, f"unexpected validation error: {type(exc).__name__}"

    dumped = dto.model_dump()
    try:
        json.dumps(dumped, allow_nan=False)
    except (TypeError, ValueError) as exc:
        return None, f"report failed JSON serialization check: {type(exc).__name__}"

    return dumped, None
