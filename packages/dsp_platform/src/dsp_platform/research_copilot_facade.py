"""Platform façade helpers for AI Research Copilot (EPIC-A001)."""

from __future__ import annotations

from typing import Any, Mapping

from dsp_platform.research_copilot import (
    COPILOT_SCHEMA_VERSION,
    COPILOT_SERVICE_VERSION,
    ask_research_copilot,
)

__all__ = [
    "ask_canonical_research_copilot",
    "research_copilot_schema",
]


def research_copilot_schema() -> dict[str, Any]:
    return {
        "schema_version": COPILOT_SCHEMA_VERSION,
        "service_version": COPILOT_SERVICE_VERSION,
        "read_only": True,
        "mode": "extractive_grounded",
        "sources": [
            "research_object",
            "institutional_report",
            "archive_snapshot",
            "research_diff",
        ],
        "rules": [
            "platform_outputs_only",
            "no_provider_calls",
            "no_calculations",
            "no_valuation",
            "no_scoring",
            "cite_sections",
            "missing_is_data_unavailable",
        ],
    }


def ask_canonical_research_copilot(
    question: str,
    *,
    research_object: Mapping[str, Any] | None = None,
    report: Mapping[str, Any] | None = None,
    archive_snapshot: Mapping[str, Any] | None = None,
    research_diff: Mapping[str, Any] | None = None,
    snapshot_id: str | None = None,
    conversation_id: str | None = None,
    response_id: str | None = None,
    created_at: str | None = None,
) -> dict[str, Any]:
    return ask_research_copilot(
        question,
        research_object=research_object,
        report=report,
        archive_snapshot=archive_snapshot,
        research_diff=research_diff,
        snapshot_id=snapshot_id,
        conversation_id=conversation_id,
        response_id=response_id,
        created_at=created_at,
    )
