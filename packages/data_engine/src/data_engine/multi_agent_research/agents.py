"""Typed multi-agent research ports (SIMPLE-14H).

Agents are researchers, not sources of truth. Live HTTP stays outside
data_engine. Missing agents return typed unavailability — never fabricate.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from data_engine.multi_agent_research.contracts import ResearchClaim, ResearchRequest

__all__ = [
    "AgentCapabilityState",
    "AgentFailureClass",
    "AgentRole",
    "AgentRunResult",
    "ResearchAgentPort",
    "ScriptedResearchAgent",
    "UnavailableResearchAgent",
    "classify_http_agent_failure",
]


class AgentRole(StrEnum):
    GEMINI = "GEMINI"
    CHATGPT = "CHATGPT"
    DEEP_SEARCH = "DEEP_SEARCH"
    CLAUDE = "CLAUDE"


class AgentCapabilityState(StrEnum):
    LIVE = "LIVE"
    MOCK = "MOCK"
    STUB = "STUB"
    DOCUMENTED = "DOCUMENTED"
    UNKNOWN = "UNKNOWN"
    EXTERNAL_BLOCKER = "EXTERNAL_BLOCKER"


class AgentFailureClass(StrEnum):
    NONE = "NONE"
    AGENT_UNAVAILABLE = "AGENT_UNAVAILABLE"
    AUTH_FAILURE = "AUTH_FAILURE"
    RATE_LIMITED = "RATE_LIMITED"
    TIMEOUT = "TIMEOUT"
    TRANSPORT_FAILURE = "TRANSPORT_FAILURE"
    INVALID_RESPONSE = "INVALID_RESPONSE"
    MALFORMED_RESPONSE = "MALFORMED_RESPONSE"
    EMPTY_RESPONSE = "EMPTY_RESPONSE"
    TOOL_ONLY_RESPONSE = "TOOL_ONLY_RESPONSE"
    SOURCE_POLICY_REJECTED = "SOURCE_POLICY_REJECTED"
    EVIDENCE_INSUFFICIENT = "EVIDENCE_INSUFFICIENT"
    HTTP_4XX = "HTTP_4XX"
    HTTP_5XX = "HTTP_5XX"
    MODEL_NOT_FOUND = "MODEL_NOT_FOUND"
    POLICY_REJECTED = "POLICY_REJECTED"


@dataclass(frozen=True, slots=True)
class AgentRunResult:
    agent: AgentRole
    capability_state: AgentCapabilityState
    failure: AgentFailureClass
    claims: tuple[ResearchClaim, ...]
    detail: str

    @property
    def ok(self) -> bool:
        return self.failure is AgentFailureClass.NONE


class ResearchAgentPort(Protocol):
    role: AgentRole
    capability_state: AgentCapabilityState

    def research(self, request: ResearchRequest) -> AgentRunResult: ...


def classify_http_agent_failure(
    status_code: int | None,
    *,
    timed_out: bool = False,
    body_text: str = "",
    tool_only: bool = False,
) -> AgentFailureClass:
    """SIMPLE-11: never collapse provider failures into MALFORMED."""
    if timed_out:
        return AgentFailureClass.TIMEOUT
    if status_code is None:
        return AgentFailureClass.TRANSPORT_FAILURE
    lowered = (body_text or "").lower()
    if status_code == 401 or status_code == 403:
        return AgentFailureClass.AUTH_FAILURE
    if status_code == 404 or "not_found" in lowered or "model_not_found" in lowered:
        return AgentFailureClass.MODEL_NOT_FOUND
    if status_code == 429 or "resource_exhausted" in lowered:
        return AgentFailureClass.RATE_LIMITED
    if 400 <= status_code < 500:
        return AgentFailureClass.HTTP_4XX
    if 500 <= status_code < 600:
        return AgentFailureClass.HTTP_5XX
    if tool_only:
        return AgentFailureClass.TOOL_ONLY_RESPONSE
    if not (body_text or "").strip():
        return AgentFailureClass.EMPTY_RESPONSE
    return AgentFailureClass.NONE


class UnavailableResearchAgent:
    """Honest stub: agent is not live. Does not invent claims."""

    def __init__(
        self,
        role: AgentRole,
        *,
        capability_state: AgentCapabilityState = AgentCapabilityState.STUB,
        failure: AgentFailureClass = AgentFailureClass.AGENT_UNAVAILABLE,
        detail: str = "",
    ) -> None:
        self.role = role
        self.capability_state = capability_state
        self._failure = failure
        self._detail = detail or f"{role.value} unavailable"

    def research(self, request: ResearchRequest) -> AgentRunResult:
        del request
        return AgentRunResult(
            agent=self.role,
            capability_state=self.capability_state,
            failure=self._failure,
            claims=(),
            detail=self._detail,
        )


class ScriptedResearchAgent:
    """Test double. Never used as a production source of truth."""

    def __init__(
        self,
        role: AgentRole,
        claims: tuple[ResearchClaim, ...] = (),
        *,
        failure: AgentFailureClass = AgentFailureClass.NONE,
        capability_state: AgentCapabilityState = AgentCapabilityState.MOCK,
        detail: str = "scripted",
    ) -> None:
        self.role = role
        self.capability_state = capability_state
        self._claims = claims
        self._failure = failure
        self._detail = detail

    def research(self, request: ResearchRequest) -> AgentRunResult:
        scoped = tuple(
            c
            for c in self._claims
            if c.research_request_id in {"", request.research_request_id}
            or c.ticker == request.ticker
        )
        return AgentRunResult(
            agent=self.role,
            capability_state=self.capability_state,
            failure=self._failure,
            claims=scoped if self._failure is AgentFailureClass.NONE else (),
            detail=self._detail,
        )
