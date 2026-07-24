"""Industry Evidence Framework — definition models only (C3.1).

No providers, interpreters, snapshots assembly, applicability, or evaluation.
"""

from __future__ import annotations

from dataclasses import dataclass

from core.exceptions import ValidationError

from industry.enums import (
    ComparisonDimension,
    EvidenceCategory,
    EvidenceLifecycle,
    MetricAvailability,
    MetricUnit,
)
from industry.models import _normalize_id
from industry.semver import require_semver

__all__ = [
    "EvidenceProviderRef",
    "EvidenceSnapshotRef",
    "EvidenceVersion",
    "IndustryEvidenceDefinition",
    "IndustryMetricDefinition",
]

_FORBIDDEN_CLAIM_WORDS = frozenset(
    {"better", "best", "winner", "score", "rank", "ranking", "league"}
)


@dataclass(frozen=True, slots=True)
class EvidenceVersion:
    """Semantic version wrapper for IEF definitions (MAJOR.MINOR.PATCH)."""

    value: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", require_semver(self.value, field="value"))

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class EvidenceProviderRef:
    """Reference to a future EvidenceProvider — not an implementation."""

    provider_id: str
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        provider_id = _normalize_id(self.provider_id, field="provider_id")
        notes = tuple(n.strip() for n in self.notes if n.strip())
        object.__setattr__(self, "provider_id", provider_id)
        object.__setattr__(self, "notes", notes)


@dataclass(frozen=True, slots=True)
class EvidenceSnapshotRef:
    """Definition-only reference shape for future DecisionPack attachment.

    Does not assemble or store snapshot payloads in C3.1.
    """

    snapshot_id: str
    methodology_id: str
    methodology_version: str
    digest: str

    def __post_init__(self) -> None:
        snapshot_id = _normalize_id(self.snapshot_id, field="snapshot_id")
        methodology_id = _normalize_id(self.methodology_id, field="methodology_id")
        methodology_version = require_semver(
            self.methodology_version, field="methodology_version"
        )
        digest = self.digest.strip().lower()
        if not digest:
            msg = "digest must not be empty"
            raise ValidationError(msg)
        object.__setattr__(self, "snapshot_id", snapshot_id)
        object.__setattr__(self, "methodology_id", methodology_id)
        object.__setattr__(self, "methodology_version", methodology_version)
        object.__setattr__(self, "digest", digest)


@dataclass(frozen=True, slots=True)
class IndustryMetricDefinition:
    """Metadata for an industry metric — no formulas or calculations."""

    id: str
    name: str
    version: str
    category: EvidenceCategory
    unit: MetricUnit = MetricUnit.RATIO
    status: EvidenceLifecycle = EvidenceLifecycle.ACTIVE
    description: str | None = None
    availability: MetricAvailability = MetricAvailability.REQUIRES_NEW_DATA
    provider: EvidenceProviderRef | None = None
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        metric_id = _normalize_id(self.id, field="id")
        name = self.name.strip()
        if not name:
            msg = "name must not be empty"
            raise ValidationError(msg)
        version = require_semver(self.version, field="version")
        description = (
            None if self.description is None else self.description.strip() or None
        )
        notes = tuple(n.strip() for n in self.notes if n.strip())
        object.__setattr__(self, "id", metric_id)
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "version", version)
        object.__setattr__(self, "description", description)
        object.__setattr__(self, "notes", notes)

    @property
    def registry_key(self) -> tuple[str, str]:
        return (self.id, self.version)

    @property
    def evidence_version(self) -> EvidenceVersion:
        return EvidenceVersion(self.version)


@dataclass(frozen=True, slots=True)
class IndustryEvidenceDefinition:
    """Canonical industry evidence type — definition only, no evaluation."""

    id: str
    name: str
    version: str
    category: EvidenceCategory
    purpose: str
    status: EvidenceLifecycle = EvidenceLifecycle.ACTIVE
    description: str | None = None
    related_metric_ids: tuple[str, ...] = ()
    supported_industry_ids: tuple[str, ...] = ()
    interpretation_guidance: tuple[str, ...] = ()
    provider_requirements: tuple[EvidenceProviderRef, ...] = ()
    dimension_hints: tuple[ComparisonDimension, ...] = ()
    snapshot_compatible: bool = True
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        evidence_id = _normalize_id(self.id, field="id")
        name = self.name.strip()
        if not name:
            msg = "name must not be empty"
            raise ValidationError(msg)
        version = require_semver(self.version, field="version")
        purpose = self.purpose.strip()
        if not purpose:
            msg = "purpose must not be empty"
            raise ValidationError(msg)
        _assert_no_forbidden_language(purpose, field="purpose")
        description = (
            None if self.description is None else self.description.strip() or None
        )
        related = _unique_ids(self.related_metric_ids, field="related_metric_ids")
        industries = _unique_ids(
            self.supported_industry_ids, field="supported_industry_ids"
        )
        guidance = tuple(
            g.strip() for g in self.interpretation_guidance if g.strip()
        )
        for g in guidance:
            _assert_no_forbidden_language(g, field="interpretation_guidance")
        providers = tuple(self.provider_requirements)
        dimensions = tuple(self.dimension_hints)
        notes = tuple(n.strip() for n in self.notes if n.strip())
        object.__setattr__(self, "id", evidence_id)
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "version", version)
        object.__setattr__(self, "purpose", purpose)
        object.__setattr__(self, "description", description)
        object.__setattr__(self, "related_metric_ids", related)
        object.__setattr__(self, "supported_industry_ids", industries)
        object.__setattr__(self, "interpretation_guidance", guidance)
        object.__setattr__(self, "provider_requirements", providers)
        object.__setattr__(self, "dimension_hints", dimensions)
        object.__setattr__(self, "notes", notes)

    @property
    def registry_key(self) -> tuple[str, str]:
        return (self.id, self.version)

    @property
    def evidence_version(self) -> EvidenceVersion:
        return EvidenceVersion(self.version)


def _unique_ids(values: tuple[str, ...], *, field: str) -> tuple[str, ...]:
    seen: set[str] = set()
    out: list[str] = []
    for raw in values:
        cleaned = _normalize_id(raw, field=field)
        if cleaned not in seen:
            seen.add(cleaned)
            out.append(cleaned)
    return tuple(out)


def _assert_no_forbidden_language(text: str, *, field: str) -> None:
    tokens = text.lower().replace(",", " ").replace(".", " ").split()
    for word in _FORBIDDEN_CLAIM_WORDS:
        if word in tokens:
            msg = f"{field} must not use forbidden term {word!r}: {text!r}"
            raise ValidationError(msg)
