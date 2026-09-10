"""Research-agent boundaries. Missing agents return UNAVAILABLE, never fabrications.

Gemini = FIND, ChatGPT = VERIFY, Deep Search = ATTACK, Claude = REVIEW, DSP = JUDGE.
Agents never execute code, change provider config, or write VERIFIED truth.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from data_engine.official_research.extraction import attack_corporate_actions
from data_engine.official_research.models import (
    FailureStatus,
    ResearchAgentRole,
    ResearchClaim,
)
from data_engine.official_research.prompt_guard import sanitize_document_text

__all__ = [
    "ChatGPTVerifyAgent",
    "ClaudeReviewAgent",
    "DeepSearchAttackAgent",
    "GeminiFindAgent",
    "ResearchAgent",
    "UnavailableAgent",
    "agent_outcome",
]


class ResearchAgent(Protocol):
    role: ResearchAgentRole

    def available(self) -> bool: ...

    def run(
        self, *, identity: str, field: str, document_text: str | None
    ) -> ResearchClaim: ...


def _unavailable_claim(role: str, field: str) -> ResearchClaim:
    return ResearchClaim(
        field=field,
        value=None,
        source_url=None,
        document_locator=None,
        agent=role,
        notes="agent unavailable — not fabricated",
    )


@dataclass(frozen=True, slots=True)
class UnavailableAgent:
    role: ResearchAgentRole

    def available(self) -> bool:
        return False

    def run(
        self, *, identity: str, field: str, document_text: str | None
    ) -> ResearchClaim:
        _ = sanitize_document_text(document_text or "")
        _ = identity
        return _unavailable_claim(self.role, field)


@dataclass(frozen=True, slots=True)
class GeminiFindAgent:
    """FIND candidate primary sources. Never a financial authority."""

    enabled: bool = False
    role: ResearchAgentRole = "gemini_find"

    def available(self) -> bool:
        return self.enabled

    def run(
        self, *, identity: str, field: str, document_text: str | None
    ) -> ResearchClaim:
        _ = identity
        if not self.available():
            return _unavailable_claim(self.role, field)
        sanitized = sanitize_document_text(document_text or "")
        return ResearchClaim(
            field=field,
            value=None,
            source_url=None,
            document_locator="find-only",
            agent=self.role,
            notes="FIND proposal only; not financial truth"
            + (f"; document_chars={len(sanitized)}" if sanitized else ""),
        )


@dataclass(frozen=True, slots=True)
class ChatGPTVerifyAgent:
    """VERIFY claims against supplied document text. Cannot write VERIFIED."""

    enabled: bool = False
    role: ResearchAgentRole = "chatgpt_verify"

    def available(self) -> bool:
        return self.enabled

    def run(
        self, *, identity: str, field: str, document_text: str | None
    ) -> ResearchClaim:
        _ = identity
        if not self.available():
            return _unavailable_claim(self.role, field)
        sanitized = sanitize_document_text(document_text or "")
        return ResearchClaim(
            field=field,
            value=None,
            source_url=None,
            document_locator="verify-only",
            agent=self.role,
            notes="VERIFY proposal only; DSP judge required"
            + (f"; document_chars={len(sanitized)}" if sanitized else ""),
        )


@dataclass(frozen=True, slots=True)
class DeepSearchAttackAgent:
    """ATTACK share/currentness assumptions. Reports CA hits as claims, not truth."""

    enabled: bool = False
    role: ResearchAgentRole = "deep_search_attack"

    def available(self) -> bool:
        return self.enabled

    def run(
        self, *, identity: str, field: str, document_text: str | None
    ) -> ResearchClaim:
        _ = identity
        if not self.available():
            return _unavailable_claim(self.role, field)
        sanitized = sanitize_document_text(document_text or "")
        events = attack_corporate_actions(sanitized)
        return ResearchClaim(
            field=field,
            value=(
                None if not events else ",".join(event.event_type for event in events)
            ),
            source_url=None,
            document_locator="attack-only",
            agent=self.role,
            notes="ATTACK proposal only; does not change evidence status",
        )


@dataclass(frozen=True, slots=True)
class ClaudeReviewAgent:
    """Optional independent review. Absence is UNAVAILABLE, never fabricated."""

    enabled: bool = False
    role: ResearchAgentRole = "claude_review"

    def available(self) -> bool:
        return self.enabled

    def run(
        self, *, identity: str, field: str, document_text: str | None
    ) -> ResearchClaim:
        _ = identity
        if not self.available():
            return _unavailable_claim(self.role, field)
        sanitize_document_text(document_text or "")
        return ResearchClaim(
            field=field,
            value=None,
            source_url=None,
            document_locator="review-only",
            agent=self.role,
            notes="INDEPENDENT REVIEW proposal only; DSP remains the judge",
        )


def agent_outcome(agent: ResearchAgent | None) -> FailureStatus:
    if agent is None or not agent.available():
        return "UNAVAILABLE"
    return "UNKNOWN"
