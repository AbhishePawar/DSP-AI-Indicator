"""Independent research-agent composition. No silent substitution."""

from __future__ import annotations

from data_engine.multi_agent_research.agents import (
    AgentFailureClass,
    AgentRole,
    ResearchAgentPort,
)
from llm_adapters.research.qualification import (
    AgentQualification,
    LiveQualificationStatus,
)

__all__ = [
    "build_research_agents",
    "qualify_agents",
]


def build_research_agents() -> dict[AgentRole, ResearchAgentPort]:
    from llm_adapters.anthropic.research_agent import ClaudeLiveResearchAgent
    from llm_adapters.deep_search.research_agent import DeepSearchLiveResearchAgent
    from llm_adapters.gemini.research_agent import GeminiLiveResearchAgent
    from llm_adapters.openai.research_agent import ChatGptLiveResearchAgent

    return {
        AgentRole.GEMINI: GeminiLiveResearchAgent(),
        AgentRole.CHATGPT: ChatGptLiveResearchAgent(),
        AgentRole.DEEP_SEARCH: DeepSearchLiveResearchAgent(),
        AgentRole.CLAUDE: ClaudeLiveResearchAgent(),
    }


def _missing(role: AgentRole, detail: str) -> AgentQualification:
    return AgentQualification(
        agent=role,
        status=LiveQualificationStatus.UNKNOWN,
        configured=False,
        model="",
        http_status=None,
        failure=AgentFailureClass.AGENT_UNAVAILABLE,
        detail=detail,
    )


def qualify_agents(
    agents: dict[AgentRole, ResearchAgentPort] | None = None,
) -> dict[AgentRole, AgentQualification]:
    from llm_adapters.anthropic.research_agent import ClaudeLiveResearchAgent
    from llm_adapters.deep_search.research_agent import DeepSearchLiveResearchAgent
    from llm_adapters.gemini.research_agent import GeminiLiveResearchAgent
    from llm_adapters.openai.research_agent import ChatGptLiveResearchAgent

    bundle = agents or build_research_agents()
    gemini = bundle.get(AgentRole.GEMINI)
    chatgpt = bundle.get(AgentRole.CHATGPT)
    deep = bundle.get(AgentRole.DEEP_SEARCH)
    claude = bundle.get(AgentRole.CLAUDE)
    return {
        AgentRole.GEMINI: (
            gemini.probe_list_models()
            if isinstance(gemini, GeminiLiveResearchAgent)
            else _missing(
                AgentRole.GEMINI, "Gemini port is not GeminiLiveResearchAgent"
            )
        ),
        AgentRole.CHATGPT: (
            chatgpt.probe()
            if isinstance(chatgpt, ChatGptLiveResearchAgent)
            else _missing(
                AgentRole.CHATGPT, "ChatGPT port is not ChatGptLiveResearchAgent"
            )
        ),
        AgentRole.DEEP_SEARCH: (
            deep.probe()
            if isinstance(deep, DeepSearchLiveResearchAgent)
            else _missing(
                AgentRole.DEEP_SEARCH,
                "Deep Search port is not DeepSearchLiveResearchAgent",
            )
        ),
        AgentRole.CLAUDE: (
            claude.probe()
            if isinstance(claude, ClaudeLiveResearchAgent)
            else _missing(
                AgentRole.CLAUDE, "Claude port is not ClaudeLiveResearchAgent"
            )
        ),
    }
