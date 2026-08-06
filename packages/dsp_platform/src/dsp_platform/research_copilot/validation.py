"""Validate copilot responses (EPIC-A001)."""

from __future__ import annotations

from dsp_platform.research_copilot.models import (
    COPILOT_SCHEMA_VERSION,
    CopilotResponse,
    UNAVAILABLE_MESSAGE,
)

__all__ = [
    "ResearchCopilotValidationError",
    "validate_copilot_response",
]


class ResearchCopilotValidationError(ValueError):
    """Copilot response failed structural / grounding validation."""


def validate_copilot_response(response: CopilotResponse) -> None:
    if response.schema_version != COPILOT_SCHEMA_VERSION:
        raise ResearchCopilotValidationError(
            f"unsupported schema_version {response.schema_version!r}"
        )
    if not response.response_id.strip():
        raise ResearchCopilotValidationError("missing response_id")
    if not response.created_at:
        raise ResearchCopilotValidationError("missing created_at")
    if not response.answer:
        raise ResearchCopilotValidationError("missing answer")
    if response.unavailable and UNAVAILABLE_MESSAGE not in response.answer:
        raise ResearchCopilotValidationError(
            "unavailable responses must include Data unavailable."
        )
    if not response.unavailable and not response.citations:
        raise ResearchCopilotValidationError(
            "grounded answers require at least one citation"
        )
    for citation in response.citations:
        if not citation.section or not citation.path:
            raise ResearchCopilotValidationError("citation missing section/path")
    if response.provenance is None or response.audit is None:
        raise ResearchCopilotValidationError("missing provenance/audit")
