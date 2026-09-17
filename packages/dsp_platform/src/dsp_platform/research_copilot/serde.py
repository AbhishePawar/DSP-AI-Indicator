"""Serialize / deserialize copilot responses (EPIC-A001)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from dsp_platform.research_copilot.models import (
    COPILOT_SCHEMA_VERSION,
    COPILOT_SERVICE_VERSION,
    Citation,
    CopilotResponse,
    freeze_mapping_or_empty,
)
from dsp_platform.research_copilot.validation import (
    ResearchCopilotValidationError,
    validate_copilot_response,
)

__all__ = [
    "copilot_response_from_dict",
    "copilot_response_to_dict",
]


def copilot_response_to_dict(response: CopilotResponse) -> dict[str, Any]:
    validate_copilot_response(response)
    return response.to_dict()


def copilot_response_from_dict(data: Mapping[str, Any]) -> CopilotResponse:
    if not isinstance(data, Mapping):
        raise ResearchCopilotValidationError("response must be a mapping")
    citations_raw = data.get("citations") or []
    citations: list[Citation] = []
    if isinstance(citations_raw, list):
        for row in citations_raw:
            if not isinstance(row, Mapping):
                continue
            citations.append(
                Citation(
                    source_kind=str(row.get("source_kind") or ""),
                    section=str(row.get("section") or ""),
                    path=str(row.get("path") or ""),
                    available=bool(row.get("available")),
                    label=str(row.get("label") or ""),
                    research_object_id=row.get("research_object_id"),
                    report_id=row.get("report_id"),
                    snapshot_id=row.get("snapshot_id"),
                    diff_id=row.get("diff_id"),
                )
            )
    limitations = data.get("limitations") or ()

    def mapping_field(name: str) -> Mapping[str, Any]:
        value = data.get(name)
        return value if isinstance(value, Mapping) else {}

    response = CopilotResponse(
        response_id=str(data.get("response_id") or ""),
        schema_version=str(data.get("schema_version") or COPILOT_SCHEMA_VERSION),
        service_version=str(data.get("service_version") or COPILOT_SERVICE_VERSION),
        created_at=str(data.get("created_at") or ""),
        conversation_id=data.get("conversation_id"),
        question=freeze_mapping_or_empty(mapping_field("question")),
        answer=str(data.get("answer") or ""),
        citations=tuple(citations),
        unavailable=bool(data.get("unavailable")),
        prompt=freeze_mapping_or_empty(mapping_field("prompt")),
        context_refs=freeze_mapping_or_empty(mapping_field("context_refs")),
        provenance=freeze_mapping_or_empty(mapping_field("provenance")),
        audit=freeze_mapping_or_empty(mapping_field("audit")),
        limitations=(
            tuple(limitations) if isinstance(limitations, (list, tuple)) else ()
        ),
    )
    validate_copilot_response(response)
    return response
