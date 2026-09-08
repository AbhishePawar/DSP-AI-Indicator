"""Three data states and the quality gate (SIMPLE-14G).

Only VERIFIED_DATA may feed authoritative DSP calculations.
AI candidate claims cannot skip RAW → RECONCILED → VERIFIED.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from data_engine.source_policy import (
    SourceDecision,
    SourceTier,
    classify_source,
    is_ai_agent_source,
)

__all__ = [
    "DataState",
    "QualityDecision",
    "QualityDimension",
    "QualityDimensionResult",
    "QualityGateResult",
    "apply_quality_gate",
    "evaluate_quality_dimensions",
]


class DataState(StrEnum):
    RAW_PROVIDER_DATA = "RAW_PROVIDER_DATA"
    RECONCILED_DATA = "RECONCILED_DATA"
    VERIFIED_DATA = "VERIFIED_DATA"


class QualityDecision(StrEnum):
    ACCEPT = "ACCEPT"
    REJECT = "REJECT"
    UNKNOWN = "UNKNOWN"


class QualityDimension(StrEnum):
    IDENTITY = "IDENTITY"
    SOURCE_AUTHORITY = "SOURCE_AUTHORITY"
    FRESHNESS = "FRESHNESS"
    SEMANTICS = "SEMANTICS"
    PERIOD = "PERIOD"
    CURRENCY = "CURRENCY"
    UNIT = "UNIT"
    CROSS_CHECK = "CROSS_CHECK"
    CORPORATE_ACTION = "CORPORATE_ACTION"
    CONSISTENCY = "CONSISTENCY"


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


@dataclass(frozen=True, slots=True)
class QualityDimensionResult:
    name: QualityDimension
    passed: bool
    detail: str

    def to_dict(self) -> dict[str, str]:
        return {
            "name": self.name.value,
            "passed": "true" if self.passed else "false",
            "detail": self.detail,
        }


def evaluate_quality_dimensions(
    *,
    identity_ok: bool,
    source: str,
    freshness_ok: bool,
    semantics_ok: bool,
    period_ok: bool,
    currency_ok: bool,
    unit_ok: bool,
    cross_check_ok: bool,
    corporate_action_ok: bool,
    consistency_ok: bool,
) -> tuple[QualityDimensionResult, ...]:
    """Ten independent gates. Not collapsed into an AI confidence score."""
    tier, _decision = classify_source(source)
    authority_ok = tier is SourceTier.PRIMARY
    checks = (
        (QualityDimension.IDENTITY, identity_ok, "identity"),
        (QualityDimension.SOURCE_AUTHORITY, authority_ok, f"tier={tier.value}"),
        (QualityDimension.FRESHNESS, freshness_ok, "freshness"),
        (QualityDimension.SEMANTICS, semantics_ok, "semantics"),
        (QualityDimension.PERIOD, period_ok, "period"),
        (QualityDimension.CURRENCY, currency_ok, "currency"),
        (QualityDimension.UNIT, unit_ok, "unit"),
        (QualityDimension.CROSS_CHECK, cross_check_ok, "cross_check"),
        (QualityDimension.CORPORATE_ACTION, corporate_action_ok, "corporate_action"),
        (QualityDimension.CONSISTENCY, consistency_ok, "consistency"),
    )
    return tuple(
        QualityDimensionResult(name=name, passed=ok, detail=detail)
        for name, ok, detail in checks
    )


def apply_quality_gate(
    *,
    source: str,
    has_evidence: bool,
    identity_ok: bool,
    agent: str | None = None,
    authoritative_financial: bool = False,
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
    if authoritative_financial and _tier is not SourceTier.PRIMARY:
        return QualityGateResult(
            decision=QualityDecision.REJECT,
            state=DataState.RAW_PROVIDER_DATA,
            detail="secondary/unknown source is not authoritative financial truth",
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
