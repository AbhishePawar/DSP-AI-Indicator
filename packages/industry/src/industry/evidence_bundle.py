"""Industry Evidence Bundle models — assembly artifacts only (C3.5).

Bundles orchestrate existing provider results and observations.
They never calculate metrics, interpret evidence, or compare companies.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from core.exceptions import ValidationError

from industry.enums import (
    ApplicabilityLevel,
    EvidenceAvailability,
    EvidenceBundleStatus,
    MissingEvidencePolicy,
)
from industry.evidence_interpreter import EvidenceObservation
from industry.evidence_provider import EvidenceProviderResult
from industry.models import _normalize_id
from industry.semver import require_semver

__all__ = [
    "EvidenceBundle",
    "EvidenceBundleAssemblyContext",
    "EvidenceBundleEntry",
    "EvidenceBundleMetadata",
    "EvidenceBundleReference",
    "EvidenceBundleSummary",
]

_FORBIDDEN_CLAIM_WORDS = frozenset(
    {"better", "best", "winner", "score", "rank", "ranking", "league"}
)


def _reject_claim_language(text: str, *, field: str) -> str:
    cleaned = text.strip()
    if not cleaned:
        return cleaned
    lowered = cleaned.lower()
    for word in _FORBIDDEN_CLAIM_WORDS:
        if word in lowered.split() or f" {word} " in f" {lowered} ":
            msg = f"{field} must not use forbidden term {word!r}: {cleaned!r}"
            raise ValidationError(msg)
    return cleaned


@dataclass(frozen=True, slots=True)
class EvidenceBundleAssemblyContext:
    """Inputs for deterministic bundle assembly (orchestration only)."""

    instrument_key: str
    methodology_id: str
    methodology_version: str
    as_of: str | None = None
    extras: tuple[tuple[str, str], ...] = ()
    provider_by_evidence: tuple[tuple[str, str], ...] = ()
    interpreter_by_evidence: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        key = self.instrument_key.strip().upper()
        if not key:
            msg = "instrument_key must not be empty"
            raise ValidationError(msg)
        methodology_id = _normalize_id(self.methodology_id, field="methodology_id")
        methodology_version = require_semver(
            self.methodology_version, field="methodology_version"
        )
        as_of = None if self.as_of is None else self.as_of.strip() or None
        extras = tuple(
            (k.strip().lower(), v.strip())
            for k, v in self.extras
            if k.strip() and v.strip()
        )
        provider_by_evidence = tuple(
            (
                _normalize_id(eid, field="provider_by_evidence"),
                _normalize_id(pid, field="provider_by_evidence"),
            )
            for eid, pid in self.provider_by_evidence
        )
        interpreter_by_evidence = tuple(
            (
                _normalize_id(eid, field="interpreter_by_evidence"),
                _normalize_id(iid, field="interpreter_by_evidence"),
            )
            for eid, iid in self.interpreter_by_evidence
        )
        object.__setattr__(self, "instrument_key", key)
        object.__setattr__(self, "methodology_id", methodology_id)
        object.__setattr__(self, "methodology_version", methodology_version)
        object.__setattr__(self, "as_of", as_of)
        object.__setattr__(self, "extras", extras)
        object.__setattr__(self, "provider_by_evidence", provider_by_evidence)
        object.__setattr__(self, "interpreter_by_evidence", interpreter_by_evidence)


@dataclass(frozen=True, slots=True)
class EvidenceBundleEntry:
    """One evidence_id slot inside a bundle — assembled, not calculated."""

    evidence_id: str
    applicability_level: ApplicabilityLevel
    provider_result: EvidenceProviderResult | None = None
    observation: EvidenceObservation | None = None
    provider_id: str | None = None
    interpreter_id: str | None = None
    limitations: tuple[str, ...] = ()
    is_gap: bool = False

    def __post_init__(self) -> None:
        evidence_id = _normalize_id(self.evidence_id, field="evidence_id")
        provider_id = (
            None
            if self.provider_id is None
            else _normalize_id(self.provider_id, field="provider_id")
        )
        interpreter_id = (
            None
            if self.interpreter_id is None
            else _normalize_id(self.interpreter_id, field="interpreter_id")
        )
        limitations = tuple(
            _reject_claim_language(n, field="limitations")
            for n in self.limitations
            if n.strip()
        )
        if self.provider_result is not None:
            if self.provider_result.evidence_id != evidence_id:
                msg = "provider_result.evidence_id must match entry evidence_id"
                raise ValidationError(msg)
        if self.observation is not None:
            if evidence_id not in self.observation.evidence_refs:
                msg = "observation.evidence_refs must include entry evidence_id"
                raise ValidationError(msg)
        if self.is_gap and self.provider_result is not None:
            if self.provider_result.availability is EvidenceAvailability.AVAILABLE:
                msg = "gap entry cannot have AVAILABLE provider_result"
                raise ValidationError(msg)
        object.__setattr__(self, "evidence_id", evidence_id)
        object.__setattr__(self, "provider_id", provider_id)
        object.__setattr__(self, "interpreter_id", interpreter_id)
        object.__setattr__(self, "limitations", limitations)


@dataclass(frozen=True, slots=True)
class EvidenceBundleMetadata:
    """Identity and methodology lineage for an assembled bundle."""

    bundle_id: str
    instrument_key: str
    methodology_id: str
    methodology_version: str
    applicability_id: str
    applicability_version: str
    missing_evidence_policy: MissingEvidencePolicy
    as_of: str | None = None
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        bundle_id = _normalize_id(self.bundle_id, field="bundle_id")
        instrument_key = self.instrument_key.strip().upper()
        if not instrument_key:
            msg = "instrument_key must not be empty"
            raise ValidationError(msg)
        methodology_id = _normalize_id(self.methodology_id, field="methodology_id")
        methodology_version = require_semver(
            self.methodology_version, field="methodology_version"
        )
        applicability_id = _normalize_id(
            self.applicability_id, field="applicability_id"
        )
        applicability_version = require_semver(
            self.applicability_version, field="applicability_version"
        )
        as_of = None if self.as_of is None else self.as_of.strip() or None
        notes = tuple(n.strip() for n in self.notes if n.strip())
        object.__setattr__(self, "bundle_id", bundle_id)
        object.__setattr__(self, "instrument_key", instrument_key)
        object.__setattr__(self, "methodology_id", methodology_id)
        object.__setattr__(self, "methodology_version", methodology_version)
        object.__setattr__(self, "applicability_id", applicability_id)
        object.__setattr__(self, "applicability_version", applicability_version)
        object.__setattr__(self, "as_of", as_of)
        object.__setattr__(self, "notes", notes)


@dataclass(frozen=True, slots=True)
class EvidenceBundleSummary:
    """Counts and gap notes — descriptive only, never a score."""

    entry_count: int
    required_count: int
    required_available_count: int
    required_missing_count: int
    gap_count: int
    observation_count: int
    limitation_notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for field in (
            "entry_count",
            "required_count",
            "required_available_count",
            "required_missing_count",
            "gap_count",
            "observation_count",
        ):
            value = getattr(self, field)
            if value < 0:
                msg = f"{field} must be >= 0"
                raise ValidationError(msg)
        if self.required_available_count + self.required_missing_count > self.required_count:
            msg = "required available/missing counts exceed required_count"
            raise ValidationError(msg)
        notes = tuple(
            _reject_claim_language(n, field="limitation_notes")
            for n in self.limitation_notes
            if n.strip()
        )
        object.__setattr__(self, "limitation_notes", notes)


@dataclass(frozen=True, slots=True)
class EvidenceBundleReference:
    """Lightweight citation for future DecisionPack / Comparison consumers."""

    bundle_id: str
    instrument_key: str
    methodology_id: str
    methodology_version: str
    digest: str
    status: EvidenceBundleStatus

    def __post_init__(self) -> None:
        bundle_id = _normalize_id(self.bundle_id, field="bundle_id")
        instrument_key = self.instrument_key.strip().upper()
        if not instrument_key:
            msg = "instrument_key must not be empty"
            raise ValidationError(msg)
        methodology_id = _normalize_id(self.methodology_id, field="methodology_id")
        methodology_version = require_semver(
            self.methodology_version, field="methodology_version"
        )
        digest = self.digest.strip().lower()
        if not digest:
            msg = "digest must not be empty"
            raise ValidationError(msg)
        object.__setattr__(self, "bundle_id", bundle_id)
        object.__setattr__(self, "instrument_key", instrument_key)
        object.__setattr__(self, "methodology_id", methodology_id)
        object.__setattr__(self, "methodology_version", methodology_version)
        object.__setattr__(self, "digest", digest)


@dataclass(frozen=True, slots=True)
class EvidenceBundle:
    """Canonical assembled evidence artifact for one instrument + methodology."""

    metadata: EvidenceBundleMetadata
    status: EvidenceBundleStatus
    entries: tuple[EvidenceBundleEntry, ...]
    summary: EvidenceBundleSummary
    limitations: tuple[str, ...] = ()
    digest: str = ""

    def __post_init__(self) -> None:
        entries = tuple(self.entries)
        seen: set[str] = set()
        for entry in entries:
            if entry.evidence_id in seen:
                msg = f"duplicate evidence in bundle: {entry.evidence_id!r}"
                raise ValidationError(msg)
            seen.add(entry.evidence_id)
        limitations = tuple(
            _reject_claim_language(n, field="limitations")
            for n in self.limitations
            if n.strip()
        )
        digest = self.digest.strip().lower()
        if not digest:
            digest = _compute_bundle_digest(
                metadata=self.metadata,
                status=self.status,
                entries=entries,
            )
        if self.summary.entry_count != len(entries):
            msg = "summary.entry_count must match entries length"
            raise ValidationError(msg)
        if not entries and self.status is not EvidenceBundleStatus.EMPTY:
            msg = "empty entries require EMPTY status"
            raise ValidationError(msg)
        if entries and self.status is EvidenceBundleStatus.EMPTY:
            msg = "non-empty bundle cannot have EMPTY status"
            raise ValidationError(msg)
        object.__setattr__(self, "entries", entries)
        object.__setattr__(self, "limitations", limitations)
        object.__setattr__(self, "digest", digest)

    def reference(self) -> EvidenceBundleReference:
        return EvidenceBundleReference(
            bundle_id=self.metadata.bundle_id,
            instrument_key=self.metadata.instrument_key,
            methodology_id=self.metadata.methodology_id,
            methodology_version=self.metadata.methodology_version,
            digest=self.digest,
            status=self.status,
        )

    def entry_for(self, evidence_id: str) -> EvidenceBundleEntry | None:
        eid = evidence_id.strip().lower()
        for entry in self.entries:
            if entry.evidence_id == eid:
                return entry
        return None


def _compute_bundle_digest(
    *,
    metadata: EvidenceBundleMetadata,
    status: EvidenceBundleStatus,
    entries: tuple[EvidenceBundleEntry, ...],
) -> str:
    parts = [
        metadata.bundle_id,
        metadata.instrument_key,
        metadata.methodology_id,
        metadata.methodology_version,
        metadata.applicability_id,
        metadata.applicability_version,
        status.value,
        metadata.as_of or "",
    ]
    for entry in sorted(entries, key=lambda e: e.evidence_id):
        avail = (
            ""
            if entry.provider_result is None
            else entry.provider_result.availability.value
        )
        obs = "" if entry.observation is None else entry.observation.id
        parts.append(
            f"{entry.evidence_id}|{entry.applicability_level.value}|"
            f"{avail}|{obs}|{int(entry.is_gap)}"
        )
    raw = "\n".join(parts).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()
