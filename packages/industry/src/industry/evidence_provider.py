"""Industry Evidence Provider contracts — resolution only (C3.3).

Providers retrieve/expose evidence values. They do not interpret, calculate
financial statements, or compare companies.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from core.exceptions import ValidationError

from industry.enums import EvidenceAvailability, EvidenceLifecycle
from industry.models import _normalize_id
from industry.semver import require_semver

__all__ = [
    "EvidenceProvider",
    "EvidenceProviderCapability",
    "EvidenceProviderResult",
    "EvidenceResolutionContext",
    "IndustryEvidenceProvider",
]


@dataclass(frozen=True, slots=True)
class EvidenceProviderCapability:
    """Declares that a provider can attempt resolution for an evidence_id."""

    evidence_id: str
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        evidence_id = _normalize_id(self.evidence_id, field="evidence_id")
        notes = tuple(n.strip() for n in self.notes if n.strip())
        object.__setattr__(self, "evidence_id", evidence_id)
        object.__setattr__(self, "notes", notes)


@dataclass(frozen=True, slots=True)
class IndustryEvidenceProvider:
    """Registered provider metadata (execution contract identity)."""

    id: str
    name: str
    version: str
    capabilities: tuple[EvidenceProviderCapability, ...]
    status: EvidenceLifecycle = EvidenceLifecycle.ACTIVE
    description: str | None = None
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        provider_id = _normalize_id(self.id, field="id")
        name = self.name.strip()
        if not name:
            msg = "provider name must not be empty"
            raise ValidationError(msg)
        version = require_semver(self.version, field="version")
        capabilities = tuple(self.capabilities)
        if not capabilities:
            msg = "provider must declare at least one capability"
            raise ValidationError(msg)
        seen: set[str] = set()
        for cap in capabilities:
            if cap.evidence_id in seen:
                msg = (
                    f"duplicate provider capability for evidence "
                    f"{cap.evidence_id!r} on provider {provider_id!r}"
                )
                raise ValidationError(msg)
            seen.add(cap.evidence_id)
        description = (
            None if self.description is None else self.description.strip() or None
        )
        notes = tuple(n.strip() for n in self.notes if n.strip())
        object.__setattr__(self, "id", provider_id)
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "version", version)
        object.__setattr__(self, "capabilities", capabilities)
        object.__setattr__(self, "description", description)
        object.__setattr__(self, "notes", notes)

    @property
    def registry_key(self) -> tuple[str, str]:
        return (self.id, self.version)

    @property
    def evidence_ids(self) -> tuple[str, ...]:
        return tuple(c.evidence_id for c in self.capabilities)


@dataclass(frozen=True, slots=True)
class EvidenceResolutionContext:
    """Inputs for deterministic evidence resolution (no interpretation)."""

    instrument_key: str
    methodology_id: str | None = None
    methodology_version: str | None = None
    as_of: str | None = None
    extras: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        key = self.instrument_key.strip().upper()
        if not key:
            msg = "instrument_key must not be empty"
            raise ValidationError(msg)
        methodology_id = (
            None
            if self.methodology_id is None
            else _normalize_id(self.methodology_id, field="methodology_id")
        )
        methodology_version = (
            None
            if self.methodology_version is None
            else require_semver(
                self.methodology_version, field="methodology_version"
            )
        )
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


@dataclass(frozen=True, slots=True)
class EvidenceProviderResult:
    """Outcome of resolving one evidence definition via a provider."""

    evidence_id: str
    provider_id: str
    availability: EvidenceAvailability
    value: float | str | None = None
    unit: str | None = None
    as_of: str | None = None
    is_placeholder: bool = False
    notes: tuple[str, ...] = ()
    error_message: str | None = None

    def __post_init__(self) -> None:
        evidence_id = _normalize_id(self.evidence_id, field="evidence_id")
        provider_id = _normalize_id(self.provider_id, field="provider_id")
        notes = tuple(n.strip() for n in self.notes if n.strip())
        error_message = (
            None
            if self.error_message is None
            else self.error_message.strip() or None
        )
        unit = None if self.unit is None else self.unit.strip() or None
        as_of = None if self.as_of is None else self.as_of.strip() or None

        if self.availability is EvidenceAvailability.AVAILABLE:
            if self.value is None:
                msg = "AVAILABLE result must include a value"
                raise ValidationError(msg)
        else:
            if self.value is not None and not self.is_placeholder:
                msg = (
                    f"{self.availability.value} result must not include a "
                    f"non-placeholder value"
                )
                raise ValidationError(msg)
        if self.availability is EvidenceAvailability.ERROR and not error_message:
            msg = "ERROR result must include error_message"
            raise ValidationError(msg)

        object.__setattr__(self, "evidence_id", evidence_id)
        object.__setattr__(self, "provider_id", provider_id)
        object.__setattr__(self, "notes", notes)
        object.__setattr__(self, "error_message", error_message)
        object.__setattr__(self, "unit", unit)
        object.__setattr__(self, "as_of", as_of)


@runtime_checkable
class EvidenceProvider(Protocol):
    """Deterministic contract for resolving evidence definitions to values."""

    def provider_metadata(self) -> IndustryEvidenceProvider:
        """Return immutable provider identity and capabilities."""

    def supports(
        self, evidence_id: str, context: EvidenceResolutionContext
    ) -> bool:
        """Return whether this provider may attempt resolution."""

    def availability(
        self, evidence_id: str, context: EvidenceResolutionContext
    ) -> EvidenceAvailability:
        """Return availability without fabricating evidence."""

    def resolve(
        self, evidence_id: str, context: EvidenceResolutionContext
    ) -> EvidenceProviderResult:
        """Resolve one evidence definition. Never invent financial meaning."""

    def resolve_many(
        self,
        evidence_ids: tuple[str, ...],
        context: EvidenceResolutionContext,
    ) -> tuple[EvidenceProviderResult, ...]:
        """Resolve many evidence ids deterministically (stable order)."""
