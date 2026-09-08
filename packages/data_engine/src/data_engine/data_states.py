"""Three data states and the quality gate (SIMPLE-14G).

Only VERIFIED_DATA may feed authoritative DSP calculations.
AI candidate claims cannot skip RAW → RECONCILED → VERIFIED.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from data_engine.source_policy import (
    SourceDecision,
    classify_source,
    is_ai_agent_source,
)

__all__ = [
    "DataState",
    "QualityDecision",
    "QualityGateResult",
    "apply_quality_gate",
]


class DataState(StrEnum):
    RAW_PROVIDER_DATA = "RAW_PROVIDER_DATA"
    RECONCILED_DATA = "RECONCILED_DATA"
    VERIFIED_DATA = "VERIFIED_DATA"


class QualityDecision(StrEnum):
    ACCEPT = "ACCEPT"
    REJECT = "REJECT"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class QualityGateResult:
    decision: QualityDecision
    state: DataState
    detail: str

    def to_dict(self) -> dict[str, str]:
        return {
            "decision": self.decision.value,
            "state": self.state.value,
            "detail": self.detail,
        }


def apply_quality_gate(
    *,
    source: str,
    has_evidence: bool,
    identity_ok: bool,
    agent: str | None = None,
) -> QualityGateResult:
    """Promote a candidate only when source + evidence + identity pass.

    AI agents never produce VERIFIED_DATA directly.
    """
    if is_ai_agent_source(agent or "") or is_ai_agent_source(source):
        return QualityGateResult(
            decision=QualityDecision.REJECT,
            state=DataState.RAW_PROVIDER_DATA,
            detail="AI output cannot become verified DSP data",
        )
    if not identity_ok:
        return QualityGateResult(
            decision=QualityDecision.UNKNOWN,
            state=DataState.RAW_PROVIDER_DATA,
            detail="identity not verified",
        )
    if not has_evidence:
        return QualityGateResult(
            decision=QualityDecision.UNKNOWN,
            state=DataState.RAW_PROVIDER_DATA,
            detail="no evidence",
        )
    _tier, decision = classify_source(source)
    if decision is SourceDecision.REJECT:
        return QualityGateResult(
            decision=QualityDecision.REJECT,
            state=DataState.RAW_PROVIDER_DATA,
            detail="source not approved as financial truth",
        )
    if decision is SourceDecision.ACCEPT:
        return QualityGateResult(
            decision=QualityDecision.ACCEPT,
            state=DataState.VERIFIED_DATA,
            detail="primary source with evidence",
        )
    return QualityGateResult(
        decision=QualityDecision.UNKNOWN,
        state=DataState.RECONCILED_DATA,
        detail="secondary or unclassified source; not verified",
    )
