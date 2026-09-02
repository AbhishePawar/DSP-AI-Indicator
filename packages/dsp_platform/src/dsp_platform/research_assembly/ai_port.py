"""Provider-neutral canonical research AI execution port.

Business operation: interpret a private research prompt as
``CanonicalAIDraft``. This module does not select a vendor, load
credentials, open sockets, or assemble a public report.

Gate order (consulted here; production remains blocked):

    Gate A (canonical production activation)
        → if OFF: BLOCKED, do not consult evidence, do not interpret
        → if ON: consult injected evidence gate (Gate B seam)
        → if evidence is not READY: BLOCKED
        → ELIGIBLE only when both permit

STEP 5A does not invoke this port from production. Gate A stays OFF.
The live interpreter must not call ``invoke_canonical_research_ai_port``.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from dsp_platform.research_assembly.activation import CanonicalProductionAiDecision
from dsp_platform.research_validation.draft import (
    CanonicalAIDraft,
    CanonicalAIDraftError,
)

__all__ = [
    "BlockedCanonicalResearchAiPort",
    "CanonicalAiEvidenceGate",
    "CanonicalAiEvidenceState",
    "CanonicalAiPortBlockedError",
    "CanonicalAiPortResult",
    "CanonicalAiPortState",
    "CanonicalResearchAiPort",
    "invoke_canonical_research_ai_port",
    "resolve_canonical_ai_execution_access",
]


class CanonicalAiPortState(StrEnum):
    """Internal port outcome. Never a public HTTP enum."""

    BLOCKED = "blocked"
    ELIGIBLE = "eligible"
    EXECUTED = "executed"


class CanonicalAiEvidenceState(StrEnum):
    """Injected evidence-gate verdict. Ready means future execution may proceed."""

    BLOCKED = "blocked"
    READY = "ready"


class CanonicalAiPortBlockedError(RuntimeError):
    """Fail-closed port error. Message must not include prompt text."""


class CanonicalResearchAiPort(Protocol):
    """Vendor-neutral interpretation seam.

    Implementations belong outside DSP engines. They must return
    ``CanonicalAIDraft`` only — never a public report object.
    """

    def interpret(self, private_prompt: object) -> CanonicalAIDraft: ...


class CanonicalAiEvidenceGate(Protocol):
    """Vendor-neutral Gate B seam.

    A future adapter may wrap provider-layer evidence checks. This
    protocol must not import that layer into ``dsp_platform``.
    """

    def evaluate(self) -> CanonicalAiEvidenceState: ...


@dataclass(frozen=True, slots=True, repr=False)
class CanonicalAiPortResult:
    """Internal access/execution result. No prompt, vendor, or report."""

    state: CanonicalAiPortState
    draft: CanonicalAIDraft | None

    def __repr__(self) -> str:
        draft = "present" if self.draft is not None else "none"
        return f"CanonicalAiPortResult(state={self.state.value}, draft={draft})"


def resolve_canonical_ai_execution_access(
    *,
    gate_a: CanonicalProductionAiDecision,
    evidence_gate: CanonicalAiEvidenceGate | None = None,
) -> CanonicalAiPortResult:
    """Apply Gate A then the evidence seam. Never interprets a prompt.

    Gate A OFF → BLOCKED and the evidence gate is not consulted.
    Gate A ON without an evidence gate → BLOCKED (fail closed).
    """
    if not gate_a.activated:
        return CanonicalAiPortResult(
            state=CanonicalAiPortState.BLOCKED,
            draft=None,
        )
    if evidence_gate is None:
        return CanonicalAiPortResult(
            state=CanonicalAiPortState.BLOCKED,
            draft=None,
        )
    verdict = evidence_gate.evaluate()
    if verdict is not CanonicalAiEvidenceState.READY:
        return CanonicalAiPortResult(
            state=CanonicalAiPortState.BLOCKED,
            draft=None,
        )
    return CanonicalAiPortResult(
        state=CanonicalAiPortState.ELIGIBLE,
        draft=None,
    )


def invoke_canonical_research_ai_port(
    port: CanonicalResearchAiPort,
    private_prompt: object,
    access: CanonicalAiPortResult,
) -> CanonicalAiPortResult:
    """Call the port only when access is ELIGIBLE. Fail closed otherwise.

    Production 5A must not use this function. Invalid drafts do not become
    reports.
    """
    if access.state is not CanonicalAiPortState.ELIGIBLE:
        return CanonicalAiPortResult(
            state=CanonicalAiPortState.BLOCKED,
            draft=None,
        )
    try:
        draft = port.interpret(private_prompt)
    except (CanonicalAiPortBlockedError, CanonicalAIDraftError):
        return CanonicalAiPortResult(
            state=CanonicalAiPortState.BLOCKED,
            draft=None,
        )
    if not isinstance(draft, CanonicalAIDraft):
        return CanonicalAiPortResult(
            state=CanonicalAiPortState.BLOCKED,
            draft=None,
        )
    return CanonicalAiPortResult(
        state=CanonicalAiPortState.EXECUTED,
        draft=draft,
    )


class BlockedCanonicalResearchAiPort:
    """Default port. Cannot execute. Does not load credentials or network."""

    def interpret(self, private_prompt: object) -> CanonicalAIDraft:
        del private_prompt
        raise CanonicalAiPortBlockedError("canonical research AI port is blocked")
