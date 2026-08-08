"""RC1 Milestone 7 — AI Research Copilot 2.0 (orchestration / explanation only)."""

from __future__ import annotations

from dsp_platform.copilot_v2.orchestrator import (
    COPILOT_V2_SCHEMA_VERSION,
    COPILOT_V2_SERVICE_VERSION,
    UNAVAILABLE_MESSAGE,
    copilot_v2_schema,
    run_copilot_v2,
)
from dsp_platform.copilot_v2.memory import (
    CopilotMemoryStore,
    get_copilot_memory_store,
    reset_copilot_memory_store_for_tests,
)

__all__ = [
    "COPILOT_V2_SCHEMA_VERSION",
    "COPILOT_V2_SERVICE_VERSION",
    "UNAVAILABLE_MESSAGE",
    "CopilotMemoryStore",
    "copilot_v2_schema",
    "get_copilot_memory_store",
    "reset_copilot_memory_store_for_tests",
    "run_copilot_v2",
]
