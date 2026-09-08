"""SIMPLE-14I forensic facade.

Product imports must use ``llm_adapters.gemini`` / ``openai`` /
``anthropic`` / ``deep_search`` and ``llm_adapters.research``.

This module only re-exports those packages so 14I qualification artifacts
keep a stable name. It is not the permanent architecture.
"""

from __future__ import annotations

from llm_adapters.anthropic import ClaudeLiveResearchAgent
from llm_adapters.deep_search import DeepSearchLiveResearchAgent
from llm_adapters.gemini import (
    SIMPLE11_BLOCKED_GEMINI_MODELS,
    GeminiLiveResearchAgent,
)
from llm_adapters.openai import ChatGptLiveResearchAgent
from llm_adapters.research import (
    AgentQualification,
    LiveQualificationStatus,
    build_research_agents,
    claims_from_model_output,
    qualification_security_master,
    qualify_agents,
)

build_simple14i_agents = build_research_agents

__all__ = [
    "AgentQualification",
    "ChatGptLiveResearchAgent",
    "ClaudeLiveResearchAgent",
    "DeepSearchLiveResearchAgent",
    "GeminiLiveResearchAgent",
    "LiveQualificationStatus",
    "SIMPLE11_BLOCKED_GEMINI_MODELS",
    "build_research_agents",
    "build_simple14i_agents",
    "claims_from_model_output",
    "qualification_security_master",
    "qualify_agents",
]
