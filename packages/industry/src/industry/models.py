"""Industry Identity and classification mapping domain models."""

from __future__ import annotations

from dataclasses import dataclass

from core.exceptions import ValidationError

from industry.enums import IdentityLifecycle, MappingStatus, TaxonomySource

__all__ = [
    "ClassificationReference",
    "IndustryIdentity",
    "IndustryMapping",
]


def _normalize_id(value: str, *, field: str) -> str:
    cleaned = value.strip().lower()
    if not cleaned:
        msg = f"{field} must not be empty"
        raise ValidationError(msg)
    if any(ch.isspace() for ch in cleaned):
        msg = f"{field} must not contain whitespace"
        raise ValidationError(msg)
    return cleaned


@dataclass(frozen=True, slots=True)
class IndustryIdentity:
    """Canonical, vendor-independent DSP industry identity.

    Owns stable identity only — not methodology, metrics, or valuation.
    """

    id: str
    name: str
    status: IdentityLifecycle = IdentityLifecycle.ACTIVE
    description: str | None = None
    parent_id: str | None = None
    display_name: str | None = None

    def __post_init__(self) -> None:
        identity_id = _normalize_id(self.id, field="id")
        name = self.name.strip()
        if not name:
            msg = "name must not be empty"
            raise ValidationError(msg)
        parent = (
            None
            if self.parent_id is None
            else _normalize_id(self.parent_id, field="parent_id")
        )
        if parent == identity_id:
            msg = "parent_id must not equal identity id"
            raise ValidationError(msg)
        description = (
            None if self.description is None else self.description.strip() or None
        )
        display = (
            None
            if self.display_name is None
            else self.display_name.strip() or None
        )
        object.__setattr__(self, "id", identity_id)
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "parent_id", parent)
        object.__setattr__(self, "description", description)
        object.__setattr__(self, "display_name", display)


@dataclass(frozen=True, slots=True)
class ClassificationReference:
    """Reference to an external taxonomy node (never DSP identity)."""

    source: TaxonomySource
    code: str
    label: str | None = None
    taxonomy_version: str | None = None

    def __post_init__(self) -> None:
        code = self.code.strip()
        if not code:
            msg = "code must not be empty"
            raise ValidationError(msg)
        label = None if self.label is None else self.label.strip() or None
        version = (
            None
            if self.taxonomy_version is None
            else self.taxonomy_version.strip() or None
        )
        object.__setattr__(self, "code", code)
        object.__setattr__(self, "label", label)
        object.__setattr__(self, "taxonomy_version", version)

    @property
    def key(self) -> tuple[str, str, str]:
        """Lookup key: source + code + taxonomy_version (empty if unset)."""
        return (
            self.source.value,
            self.code.lower(),
            (self.taxonomy_version or "").lower(),
        )


@dataclass(frozen=True, slots=True)
class IndustryMapping:
    """Versioned mapping from an external classification to a DSP identity.

    Mappings never mutate IndustryIdentity instances.
    """

    classification: ClassificationReference
    industry_id: str
    mapping_version: str
    status: MappingStatus = MappingStatus.ACTIVE
    notes: str | None = None

    def __post_init__(self) -> None:
        industry_id = _normalize_id(self.industry_id, field="industry_id")
        version = self.mapping_version.strip()
        if not version:
            msg = "mapping_version must not be empty"
            raise ValidationError(msg)
        notes = None if self.notes is None else self.notes.strip() or None
        object.__setattr__(self, "industry_id", industry_id)
        object.__setattr__(self, "mapping_version", version)
        object.__setattr__(self, "notes", notes)

    @property
    def registry_key(self) -> tuple[str, str, str, str]:
        """Unique key: classification key + mapping_version."""
        return (*self.classification.key, self.mapping_version.lower())
