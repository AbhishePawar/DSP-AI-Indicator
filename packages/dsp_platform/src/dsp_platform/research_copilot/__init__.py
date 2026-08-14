"""AI Research Copilot (EPIC-A001) — grounded on R001/R002/R004/R005 only."""

from __future__ import annotations

from dsp_platform.research_copilot.answer import build_grounded_answer
from dsp_platform.research_copilot.context import build_research_context
from dsp_platform.research_copilot.conversation import (
    ConversationStore,
    get_conversation_store,
    reset_conversation_store_for_tests,
)
from dsp_platform.research_copilot.models import (
    COPILOT_SCHEMA_VERSION,
    COPILOT_SERVICE_VERSION,
    UNAVAILABLE_MESSAGE,
    Citation,
    CopilotResponse,
    ProcessedQuestion,
    ResearchContextBundle,
    freeze_mapping,
    utc_now,
)
from dsp_platform.research_copilot.prompt import SYSTEM_RULES, build_prompt
from dsp_platform.research_copilot.question import process_question
from dsp_platform.research_copilot.serde import (
    copilot_response_from_dict,
    copilot_response_to_dict,
)
from dsp_platform.research_copilot.service import (
    ResearchCopilotService,
    ask_research_copilot,
)
from dsp_platform.research_copilot.validation import (
    ResearchCopilotValidationError,
    validate_copilot_response,
)

__all__ = [
    "COPILOT_SCHEMA_VERSION",
    "COPILOT_SERVICE_VERSION",
    "SYSTEM_RULES",
    "UNAVAILABLE_MESSAGE",
    "Citation",
    "ConversationStore",
    "CopilotResponse",
    "ProcessedQuestion",
    "ResearchContextBundle",
    "ResearchCopilotService",
    "ResearchCopilotValidationError",
    "ask_research_copilot",
    "build_grounded_answer",
    "build_prompt",
    "build_research_context",
    "copilot_response_from_dict",
    "copilot_response_to_dict",
    "freeze_mapping",
    "get_conversation_store",
    "process_question",
    "reset_conversation_store_for_tests",
    "utc_now",
    "validate_copilot_response",
]
