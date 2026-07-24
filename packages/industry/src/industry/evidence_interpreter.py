"""Industry Evidence Interpreter contracts — meaning only (C3.4).

Interpreters transform provider results into structured observations under
methodology context. They do not calculate metrics, compare companies, or score.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from core.exceptions import ValidationError

from industry.enums import (
    ApplicabilityLevel,
    EvidenceAvailability,
    EvidenceLifecycle,
    EvidenceObservationCategory,
    EvidenceObservationConfidence,
    EvidenceObservationSeverity,
)
from industry.evidence_models import IndustryEvidenceDefinition
from industry.evidence_provider import EvidenceProviderResult
from industry.models import _normalize_id
from industry.semver import require_semver

__all__ = [
    "EvidenceInterpretation",
    "EvidenceInterpretationContext",
    "EvidenceInterpreter",
    "EvidenceObservation",
    "IndustryEvidenceInterpreter",
]

_FORBIDDEN_CLAIM_WORDS = frozenset(
    {"better", "best", "winner", "score", "rank", "ranking", "league"}
)


def _reject_claim_language(text: str, *, field: str) -> str:
    cleaned = text.strip()
    if not cleaned:
        msg = f"{field} must not be empty"
        raise ValidationError(msg)
    lowered = cleaned.lower()
    for word in _FORBIDDEN_CLAIM_WORDS:
        if word in lowered.split() or f" {word} " in f" {lowered} ":
            msg = f"{field} must not use forbidden term {word!r}: {cleaned!r}"
            raise ValidationError(msg)
    return cleaned


@dataclass(frozen=True, slots=True)
class EvidenceInterpretation:
    """Rules-as-data: interpreter may interpret this evidence_id."""

    evidence_id: str
    category: EvidenceObservationCategory = EvidenceObservationCategory.OTHER
    default_severity: EvidenceObservationSeverity = EvidenceObservationSeverity.INFO
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        evidence_id = _normalize_id(self.evidence_id, field="evidence_id")
        notes = tuple(n.strip() for n in self.notes if n.strip())
        object.__setattr__(self, "evidence_id", evidence_id)
        object.__setattr__(self, "notes", notes)


@dataclass(frozen=True, slots=True)
class IndustryEvidenceInterpreter:
    """Registered interpreter metadata (interpretation contract identity)."""

    id: str
    name: str
    version: str
    interpretations: tuple[EvidenceInterpretation, ...]
    status: EvidenceLifecycle = EvidenceLifecycle.ACTIVE
    description: str | None = None
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        interpreter_id = _normalize_id(self.id, field="id")
        name = self.name.strip()
        if not name:
            msg = "interpreter name must not be empty"
            raise ValidationError(msg)
        version = require_semver(self.version, field="version")
        interpretations = tuple(self.interpretations)
        if not interpretations:
            msg = "interpreter must declare at least one interpretation"
            raise ValidationError(msg)
        seen: set[str] = set()
        for item in interpretations:
            if item.evidence_id in seen:
                msg = (
                    f"duplicate interpreter capability for evidence "
                    f"{item.evidence_id!r} on interpreter {interpreter_id!r}"
                )
                raise ValidationError(msg)
            seen.add(item.evidence_id)
        description = (
            None if self.description is None else self.description.strip() or None
        )
        notes = tuple(n.strip() for n in self.notes if n.strip())
        object.__setattr__(self, "id", interpreter_id)
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "version", version)
        object.__setattr__(self, "interpretations", interpretations)
        object.__setattr__(self, "description", description)
        object.__setattr__(self, "notes", notes)

    @property
    def registry_key(self) -> tuple[str, str]:
        return (self.id, self.version)

    @property
    def evidence_ids(self) -> tuple[str, ...]:
        return tuple(item.evidence_id for item in self.interpretations)


@dataclass(frozen=True, slots=True)
class EvidenceInterpretationContext:
    """Inputs for deterministic interpretation (no calculation / comparison)."""

    instrument_key: str
    methodology_id: str
    methodology_version: str
    provider_result: EvidenceProviderResult
    evidence_definition: IndustryEvidenceDefinition | None = None
    applicability_level: ApplicabilityLevel = ApplicabilityLevel.UNKNOWN
    as_of: str | None = None
    extras: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        key = self.instrument_key.strip().upper()
        if not key:
            msg = "instrument_key must not be empty"
            raise ValidationError(msg)
        methodology_id = _normalize_id(self.methodology_id, field="methodology_id")
        methodology_version = require_semver(
            self.methodology_version, field="methodology_version"
        )
        if self.evidence_definition is not None:
            if self.evidence_definition.id != self.provider_result.evidence_id:
                msg = (
                    "evidence_definition.id must match "
                    "provider_result.evidence_id"
                )
                raise ValidationError(msg)
        as_of = None if self.as_of is None else self.as_of.strip() or None
        extras = tuple(
            (k.strip().lower(), v.strip())
            for k, v in self.extras
            if k.strip() and v.strip()
        )
        object.__setattr__(self, "instrument_key", key)
        object.__setattr__(self, "methodology_id", methodology_id)
        object.__setattr__(self, "methodology_version", methodology_version)
        object.__setattr__(self, "as_of", as_of)
        object.__setattr__(self, "extras", extras)

    @property
    def evidence_id(self) -> str:
        return self.provider_result.evidence_id


@dataclass(frozen=True, slots=True)
class EvidenceObservation:
    """Interpreted, citable claim — no scores, rankings, or comparisons."""

    id: str
    title: str
    summary: str
    explanation: str
    evidence_refs: tuple[str, ...]
    confidence: EvidenceObservationConfidence
    severity: EvidenceObservationSeverity
    category: EvidenceObservationCategory
    interpreter_id: str
    instrument_key: str
    methodology_id: str
    methodology_version: str
    provider_id: str | None = None
    availability: EvidenceAvailability | None = None
    is_placeholder: bool = False
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        observation_id = _normalize_id(self.id, field="id")
        title = _reject_claim_language(self.title, field="title")
        summary = _reject_claim_language(self.summary, field="summary")
        explanation = _reject_claim_language(self.explanation, field="explanation")
        refs = tuple(_normalize_id(r, field="evidence_refs") for r in self.evidence_refs)
        if not refs:
            msg = "evidence_refs must not be empty"
            raise ValidationError(msg)
        interpreter_id = _normalize_id(self.interpreter_id, field="interpreter_id")
        instrument_key = self.instrument_key.strip().upper()
        if not instrument_key:
            msg = "instrument_key must not be empty"
            raise ValidationError(msg)
        methodology_id = _normalize_id(self.methodology_id, field="methodology_id")
        methodology_version = require_semver(
            self.methodology_version, field="methodology_version"
        )
        provider_id = (
            None
            if self.provider_id is None
            else _normalize_id(self.provider_id, field="provider_id")
        )
        notes = tuple(n.strip() for n in self.notes if n.strip())
        object.__setattr__(self, "id", observation_id)
        object.__setattr__(self, "title", title)
        object.__setattr__(self, "summary", summary)
        object.__setattr__(self, "explanation", explanation)
        object.__setattr__(self, "evidence_refs", refs)
        object.__setattr__(self, "interpreter_id", interpreter_id)
        object.__setattr__(self, "instrument_key", instrument_key)
        object.__setattr__(self, "methodology_id", methodology_id)
        object.__setattr__(self, "methodology_version", methodology_version)
        object.__setattr__(self, "provider_id", provider_id)
        object.__setattr__(self, "notes", notes)


@runtime_checkable
class EvidenceInterpreter(Protocol):
    """Deterministic contract for provider results → observations."""

    def interpreter_metadata(self) -> IndustryEvidenceInterpreter:
        """Return immutable interpreter identity and interpretation rules."""

    def supports(
        self, evidence_id: str, context: EvidenceInterpretationContext
    ) -> bool:
        """Return whether this interpreter may interpret the evidence."""

    def interpret(
        self, context: EvidenceInterpretationContext
    ) -> EvidenceObservation:
        """Interpret one provider result. Never calculate or compare."""

    def interpret_many(
        self, contexts: tuple[EvidenceInterpretationContext, ...]
    ) -> tuple[EvidenceObservation, ...]:
        """Interpret many contexts deterministically (stable order)."""
