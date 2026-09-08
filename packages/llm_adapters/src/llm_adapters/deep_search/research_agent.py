"""Deep Search research agent.

Deep Search is a named research role, not a synonym for Gemini, ChatGPT,
or generic web search. This runtime has no callable Deep Search API.
"""

from __future__ import annotations

from data_engine.multi_agent_research.agents import (
    AgentCapabilityState,
    AgentFailureClass,
    AgentRole,
    AgentRunResult,
)
from data_engine.multi_agent_research.contracts import ResearchRequest
from llm_adapters.research.qualification import (
    AgentQualification,
    LiveQualificationStatus,
)


class DeepSearchLiveResearchAgent:
    """ATTACK/INVESTIGATE port. Not Gemini. Not ChatGPT. Not web-search-as-proxy."""

    role = AgentRole.DEEP_SEARCH
    capability_state = AgentCapabilityState.UNKNOWN
    timeout_seconds = 0.0
    model_label = ""

    def is_configured(self) -> bool:
        return False

    def probe(self) -> AgentQualification:
        return AgentQualification(
            agent=self.role,
            status=LiveQualificationStatus.CAPABILITY_UNAVAILABLE,
            configured=False,
            model="",
            http_status=None,
            failure=AgentFailureClass.AGENT_UNAVAILABLE,
            detail=(
                "No callable Deep Search API, tool integration, or "
                "authenticated connector exists in this repository or GCP "
                "project. Gemini deep-research-* models are Gemini, not "
                "this agent."
            ),
        )

    def research(self, request: ResearchRequest) -> AgentRunResult:
        del request
        return AgentRunResult(
            agent=self.role,
            capability_state=AgentCapabilityState.UNKNOWN,
            failure=AgentFailureClass.AGENT_UNAVAILABLE,
            claims=(),
            detail="CAPABILITY_UNAVAILABLE: Deep Search is not a configured provider",
        )
