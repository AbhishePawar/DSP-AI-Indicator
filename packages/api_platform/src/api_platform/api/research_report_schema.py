"""Public research report schema validation & privacy-boundary enforcement."""

from __future__ import annotations

import json
import math
import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

__all__ = [
    "FORBIDDEN_PRIVATE_KEYS",
    "PublicResearchReportDTO",
    "validate_public_research_report",
]

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

    recommendation: str = Field(min_length=1)
    valuation: str | None = None
    analysis: str = Field(min_length=1)
    risks: list[str] = Field(default_factory=list)
    evidence_citations: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    limitations: list[str] = Field(default_factory=list)
    schema_version: Literal["public_decision_pack_v1"] = "public_decision_pack_v1"


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
        return None, f"schema validation failed: {exc}"
    except Exception as exc:  # noqa: BLE001
        return None, f"unexpected validation error: {exc}"

    if not math.isfinite(dto.confidence):
        return None, "confidence must be a finite number"

    for idx, citation in enumerate(dto.evidence_citations):
        if not isinstance(citation, str) or not citation.strip():
            return None, f"citation at index {idx} must be a non-empty string"
        if any(ord(c) < 32 and c not in "\t\n\r" for c in citation):
            return None, f"citation at index {idx} contains invalid control characters"

    # Verify JSON serializability
    dumped = dto.model_dump()
    try:
        json.dumps(dumped)
    except (TypeError, ValueError) as exc:
        return None, f"report failed JSON serialization check: {exc}"

    return dumped, None
