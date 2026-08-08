"""Agent registry (EPIC-A005)."""

from __future__ import annotations

from typing import Callable

from dsp_platform.institutional_committee.agents import AGENT_SPECS, review_agent
from dsp_platform.institutional_committee.models import AGENT_IDS, AgentReview, CommitteeContext

__all__ = [
    "AgentRegistry",
    "get_agent_registry",
]


class AgentRegistry:
    """Deterministic registry of committee agents."""

    def __init__(self) -> None:
        self._agents: dict[str, Callable[[CommitteeContext], AgentReview]] = {
            aid: fn for aid, _name, fn in AGENT_SPECS
        }

    def agent_ids(self) -> tuple[str, ...]:
        return AGENT_IDS

    def list_agents(self) -> list[dict[str, str]]:
        return [
            {"agent_id": aid, "agent_name": name}
            for aid, name, _fn in AGENT_SPECS
        ]

    def review(self, agent_id: str, ctx: CommitteeContext) -> AgentReview:
        if agent_id not in self._agents:
            raise ValueError(f"unknown agent_id {agent_id!r}")
        return review_agent(agent_id, ctx)

    def review_all(self, ctx: CommitteeContext) -> tuple[AgentReview, ...]:
        return tuple(self.review(aid, ctx) for aid in AGENT_IDS)


_REG: AgentRegistry | None = None


def get_agent_registry() -> AgentRegistry:
    global _REG
    if _REG is None:
        _REG = AgentRegistry()
    return _REG
