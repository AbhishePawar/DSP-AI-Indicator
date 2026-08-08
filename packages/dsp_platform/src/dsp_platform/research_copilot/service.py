"""AI Research Copilot service (EPIC-A001).

Explains R001/R002/R004/R005 outputs only — never calculates or fabricates.
"""

from __future__ import annotations

import uuid
from typing import Any, Mapping

from dsp_platform.research_copilot.answer import build_grounded_answer
from dsp_platform.research_copilot.context import build_research_context
from dsp_platform.research_copilot.conversation import get_conversation_store
from dsp_platform.research_copilot.models import (
    COPILOT_SCHEMA_VERSION,
    COPILOT_SERVICE_VERSION,
    CopilotResponse,
    freeze_mapping,
    utc_now,
)
from dsp_platform.research_copilot.prompt import build_prompt
from dsp_platform.research_copilot.question import process_question
from dsp_platform.research_copilot.serde import copilot_response_to_dict
from dsp_platform.research_copilot.validation import validate_copilot_response

__all__ = [
    "COPILOT_SERVICE_VERSION",
    "ResearchCopilotService",
    "ask_research_copilot",
]


class ResearchCopilotService:
    """Read-only grounded Q&A over institutional research artifacts."""

    def ask(
        self,
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
        assembled_at: str | None = None,
    ) -> CopilotResponse:
        processed = process_question(question)
        context = build_research_context(
            research_object=research_object,
            report=report,
            archive_snapshot=archive_snapshot,
            research_diff=research_diff,
            snapshot_id=snapshot_id,
            assembled_at=assembled_at or created_at,
        )
        prompt = build_prompt(processed, context)
        answer, citations, unavailable = build_grounded_answer(processed, context)

        created = created_at or utc_now().isoformat()
        rid = response_id or str(uuid.uuid4())
        store = get_conversation_store()
        cid = store.ensure(conversation_id)

        provenance = {
            "source": "research_copilot",
            "service_version": COPILOT_SERVICE_VERSION,
            "mode": "extractive_grounded",
            "providers_called": False,
            "engines_called": False,
            "source_refs": dict(context.source_refs),
        }
        audit = {
            "response_id": rid,
            "conversation_id": cid,
            "created_at": created,
            "intent": processed.intent,
            "topics": list(processed.topics),
            "citation_count": len(citations),
            "unavailable": unavailable,
            "prompt_schema": prompt.get("schema"),
            "history_turns": len(store.history(cid)),
        }
        limitations = (
            "Extractive grounded mode — explains existing platform outputs only.",
            "No external data providers consulted.",
            "No calculations, valuation, or scoring performed.",
        )

        response = CopilotResponse(
            response_id=rid,
            schema_version=COPILOT_SCHEMA_VERSION,
            service_version=COPILOT_SERVICE_VERSION,
            created_at=created,
            conversation_id=cid,
            question=freeze_mapping(processed.to_dict()) or freeze_mapping({}),
            answer=answer,
            citations=citations,
            unavailable=unavailable,
            prompt=freeze_mapping(prompt) or freeze_mapping({}),
            context_refs=freeze_mapping(dict(context.source_refs))
            or freeze_mapping({}),
            provenance=freeze_mapping(provenance) or freeze_mapping({}),
            audit=freeze_mapping(audit) or freeze_mapping({}),
            limitations=limitations,
        )
        validate_copilot_response(response)
        store.append(
            cid,
            {
                "response_id": rid,
                "created_at": created,
                "intent": processed.intent,
                "unavailable": unavailable,
            },
        )
        return response


def ask_research_copilot(
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
    assembled_at: str | None = None,
) -> dict[str, Any]:
    response = ResearchCopilotService().ask(
        question,
        research_object=research_object,
        report=report,
        archive_snapshot=archive_snapshot,
        research_diff=research_diff,
        snapshot_id=snapshot_id,
        conversation_id=conversation_id,
        response_id=response_id,
        created_at=created_at,
        assembled_at=assembled_at,
    )
    return copilot_response_to_dict(response)
