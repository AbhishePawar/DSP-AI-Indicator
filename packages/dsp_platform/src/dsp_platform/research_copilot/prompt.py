"""Prompt builder (EPIC-A001) — deterministic prompt document for audit / optional LM."""

from __future__ import annotations

from typing import Any, Mapping

from dsp_platform.research_copilot.models import (
    COPILOT_SERVICE_VERSION,
    ProcessedQuestion,
    ResearchContextBundle,
    UNAVAILABLE_MESSAGE,
)

__all__ = ["SYSTEM_RULES", "build_prompt"]

SYSTEM_RULES = (
    "You are the DSP AI Research Copilot.",
    "Explain existing Institutional Research Platform outputs only.",
    "Never calculate, value, score, or invent numbers.",
    "Never recommend beyond statements already present in the report.",
    "Never call market or fundamental data providers.",
    "Never modify research objects, reports, archives, or diffs.",
    f"If a requested field is missing, answer exactly: {UNAVAILABLE_MESSAGE}",
    "Every factual statement must cite a source section path.",
)


def build_prompt(
    question: ProcessedQuestion,
    context: ResearchContextBundle,
) -> dict[str, Any]:
    """Assemble a deterministic prompt descriptor (not sent to providers by default)."""
    available_sources: list[str] = []
    if context.research_object is not None:
        available_sources.append("research_object")
    if context.report is not None:
        available_sources.append("institutional_report")
    if context.archive_snapshot is not None:
        available_sources.append("archive_snapshot")
    if context.research_diff is not None:
        available_sources.append("research_diff")

    return {
        "schema": "research_copilot_prompt_v1",
        "service_version": COPILOT_SERVICE_VERSION,
        "system_rules": list(SYSTEM_RULES),
        "question": question.to_dict(),
        "available_sources": available_sources,
        "source_refs": dict(context.source_refs),
        "assembled_at": context.assembled_at,
        "instruction": (
            "Answer using only the attached platform context. "
            "Cite section paths. Do not invent missing data."
        ),
        # Context is referenced, not duplicated into a free-form narrative
        "context_attached": bool(available_sources),
    }
