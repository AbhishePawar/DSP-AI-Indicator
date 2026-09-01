"""AI Research Orchestrator — isolated service (STEP 3I)."""

from __future__ import annotations

from llm_adapters.orchestrator.loop import (
    DEFAULT_TOOL_LOOP_LIMITS,
    ToolLoopLimits,
    ToolLoopRun,
)
from llm_adapters.orchestrator.orchestrator import (
    OrchestratorResult,
    OrchestratorStatus,
    ResearchOrchestrator,
)
from llm_adapters.orchestrator.provider import (
    AdapterBackedAIProvider,
    AICompletion,
    AIProvider,
)
from llm_adapters.orchestrator.research_prompt import (
    PRIVATE_PROMPT_CANARY,
    build_research_prompt,
)
from llm_adapters.orchestrator.schema import AIResearchOutput
from llm_adapters.orchestrator.specification import (
    COMPLEX_TOOLS,
    SIMPLE_TOOLS,
    SPEC_VERSION,
    ResearchSpecification,
    UserResearchRequest,
)
from llm_adapters.orchestrator.validation import (
    ValidationFailure,
    ValidationSuccess,
    failed_closed_pack,
    validate_research_output,
)

__all__ = [
    "AICompletion",
    "AIProvider",
    "AIResearchOutput",
    "AdapterBackedAIProvider",
    "COMPLEX_TOOLS",
    "DEFAULT_TOOL_LOOP_LIMITS",
    "OrchestratorResult",
    "OrchestratorStatus",
    "PRIVATE_PROMPT_CANARY",
    "ResearchOrchestrator",
    "ResearchSpecification",
    "SIMPLE_TOOLS",
    "SPEC_VERSION",
    "ToolLoopLimits",
    "ToolLoopRun",
    "UserResearchRequest",
    "ValidationFailure",
    "ValidationSuccess",
    "build_research_prompt",
    "failed_closed_pack",
    "validate_research_output",
]
