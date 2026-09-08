"""Live research capability statuses.

These are capability/forensic outcomes, not DSP truth and not AI consensus.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from data_engine.multi_agent_research.agents import AgentFailureClass, AgentRole

__all__ = [
    "AgentQualification",
    "LiveQualificationStatus",
]


class LiveQualificationStatus(StrEnum):
    LIVE_QUALIFIED = "LIVE_QUALIFIED"
    LIVE_AVAILABLE_BUT_UNQUALIFIED = "LIVE_AVAILABLE_BUT_UNQUALIFIED"
    AUTH_FAILURE = "AUTH_FAILURE"
    RATE_LIMITED = "RATE_LIMITED"
    MODEL_NOT_FOUND = "MODEL_NOT_FOUND"
    TIMEOUT = "TIMEOUT"
    TRANSPORT_FAILURE = "TRANSPORT_FAILURE"
    INVALID_RESPONSE = "INVALID_RESPONSE"
    EMPTY_RESPONSE = "EMPTY_RESPONSE"
    TOOL_ONLY_RESPONSE = "TOOL_ONLY_RESPONSE"
    SOURCE_POLICY_REJECTED = "SOURCE_POLICY_REJECTED"
    EVIDENCE_INSUFFICIENT = "EVIDENCE_INSUFFICIENT"
    CAPABILITY_UNAVAILABLE = "CAPABILITY_UNAVAILABLE"
    NOT_CONFIGURED = "NOT_CONFIGURED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class AgentQualification:
    agent: AgentRole
    status: LiveQualificationStatus
    configured: bool
    model: str
    http_status: int | None
    failure: AgentFailureClass
    detail: str
    evidence: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, str]:
        return {
            "agent": self.agent.value,
            "status": self.status.value,
            "configured": "true" if self.configured else "false",
            "model": self.model,
            "http_status": "" if self.http_status is None else str(self.http_status),
            "failure": self.failure.value,
            "detail": self.detail,
        }
