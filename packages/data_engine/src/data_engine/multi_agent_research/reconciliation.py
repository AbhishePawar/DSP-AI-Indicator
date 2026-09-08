"""Deterministic reconciliation for multi-agent research claims."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from data_engine.data_states import DataState
from data_engine.multi_agent_research.contracts import (
    AUTHORITATIVE_FINANCIAL_FIELDS,
    CurrentnessStatus,
    EvidenceRecord,
)
from data_engine.source_policy import SourceTier, classify_source

__all__ = [
    "AgreementReport",
    "ReconciliationResult",
    "ReconciliationStatus",
    "compare_agents",
    "reconcile_field",
]


class ReconciliationStatus(StrEnum):
    ACCEPT = "ACCEPT"
    REJECT = "REJECT"
    CONFLICT = "CONFLICT"
    UNKNOWN = "UNKNOWN"
    REFRESH_REQUIRED = "REFRESH_REQUIRED"


@dataclass(frozen=True, slots=True)
class ReconciliationResult:
    field: str
    identity_key: str
    status: ReconciliationStatus
    data_state: DataState
    currentness: CurrentnessStatus
    values: tuple[str, ...]
    sources: tuple[str, ...]
    agents: tuple[str, ...]
    detail: str

    def to_dict(self) -> dict[str, str]:
        return {
            "field": self.field,
            "status": self.status.value,
            "data_state": self.data_state.value,
            "currentness": self.currentness.value,
            "detail": self.detail,
        }


@dataclass(frozen=True, slots=True)
class AgreementReport:
    agent_agreement: bool
    source_agreement: bool
    dsp_validation: str
    detail: str


def _norm(value: str) -> str:
    return " ".join(str(value or "").strip().split()).upper()


def _identity_key(row: EvidenceRecord) -> str:
    if row.isin and row.mic:
        return f"{row.isin}|{row.mic}"
    return f"{row.ticker}|{row.field}"


def reconcile_field(
    evidence: tuple[EvidenceRecord, ...],
    *,
    field: str,
    requested_as_of: str,
) -> ReconciliationResult:
    rows = tuple(e for e in evidence if e.field == field)
    identity = rows[0] if rows else None
    identity_key = _identity_key(identity) if identity else ""
    if not rows:
        return ReconciliationResult(
            field=field,
            identity_key=identity_key,
            status=ReconciliationStatus.UNKNOWN,
            data_state=DataState.RAW_PROVIDER_DATA,
            currentness=CurrentnessStatus.UNKNOWN,
            values=(),
            sources=(),
            agents=(),
            detail="no evidence",
        )

    identities = {_identity_key(r) for r in rows}
    if len(identities) > 1:
        return ReconciliationResult(
            field=field,
            identity_key=identity_key,
            status=ReconciliationStatus.CONFLICT,
            data_state=DataState.RAW_PROVIDER_DATA,
            currentness=CurrentnessStatus.CONFLICT,
            values=tuple(r.value for r in rows),
            sources=tuple(r.source for r in rows),
            agents=tuple(r.agent for r in rows),
            detail="identity mismatch across evidence",
        )

    authoritative = field in AUTHORITATIVE_FINANCIAL_FIELDS
    rejected = []
    eligible = []
    for row in rows:
        tier, _dec = classify_source(row.source)
        if tier in {SourceTier.AI_AGENT, SourceTier.FORBIDDEN}:
            rejected.append(row)
            continue
        if authoritative and tier is not SourceTier.PRIMARY:
            rejected.append(row)
            continue
        if not row.source_url or not row.document_date or not row.evidence_locator:
            rejected.append(row)
            continue
        eligible.append(row)

    if not eligible:
        return ReconciliationResult(
            field=field,
            identity_key=identity_key,
            status=ReconciliationStatus.REJECT,
            data_state=DataState.RAW_PROVIDER_DATA,
            currentness=CurrentnessStatus.UNKNOWN,
            values=tuple(r.value for r in rows),
            sources=tuple(r.source for r in rows),
            agents=tuple(r.agent for r in rows),
            detail="no eligible primary evidence",
        )

    values = {_norm(r.value) for r in eligible}
    dates = {r.document_date for r in eligible}
    if len(values) > 1:
        return ReconciliationResult(
            field=field,
            identity_key=identity_key,
            status=ReconciliationStatus.CONFLICT,
            data_state=DataState.RECONCILED_DATA,
            currentness=CurrentnessStatus.CONFLICT,
            values=tuple(r.value for r in eligible),
            sources=tuple(r.source for r in eligible),
            agents=tuple(r.agent for r in eligible),
            detail="contradictory eligible values",
        )

    as_of = str(requested_as_of or "").strip()
    currentness = CurrentnessStatus.CURRENT
    status = ReconciliationStatus.ACCEPT
    if as_of and any(d and d < as_of for d in dates if d):
        currentness = CurrentnessStatus.REFRESH_REQUIRED
        status = ReconciliationStatus.REFRESH_REQUIRED
    if any(r.freshness_status in {"STALE", "REFRESH_REQUIRED"} for r in eligible):
        currentness = CurrentnessStatus.STALE
        status = ReconciliationStatus.REFRESH_REQUIRED

    return ReconciliationResult(
        field=field,
        identity_key=identity_key,
        status=status,
        data_state=DataState.RECONCILED_DATA,
        currentness=currentness,
        values=tuple(r.value for r in eligible),
        sources=tuple(r.source for r in eligible),
        agents=tuple(r.agent for r in eligible),
        detail="eligible primary evidence reconciled",
    )


def compare_agents(evidence: tuple[EvidenceRecord, ...]) -> AgreementReport:
    values = {_norm(e.value) for e in evidence if e.value}
    sources = {_norm(e.source) for e in evidence if e.source}
    agents = {e.agent for e in evidence}
    agent_agreement = len(values) == 1 and len(agents) > 1
    source_agreement = len(sources) == 1 and len(sources) > 0
    dsp_validation = "NOT_VALIDATED"
    detail = (
        "AI consensus is not proof"
        if agent_agreement
        else "agents disagree or insufficient overlap"
    )
    return AgreementReport(
        agent_agreement=agent_agreement,
        source_agreement=source_agreement,
        dsp_validation=dsp_validation,
        detail=detail,
    )
