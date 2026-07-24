"""Industry Evidence Applicability — methodology-owned policy (C3.2).

Connects IndustryMethodology to IndustryEvidenceDefinition.
No providers, interpreters, snapshots, or evaluation.
"""

from __future__ import annotations

from dataclasses import dataclass

from core.exceptions import ValidationError

from industry.enums import (
    ApplicabilityLevel,
    EvidenceLifecycle,
    MissingEvidencePolicy,
)
from industry.models import _normalize_id
from industry.semver import require_semver

__all__ = [
    "ApplicabilityGroup",
    "EvidenceApplicabilityRule",
    "IndustryEvidenceApplicability",
    "RequiredEvidenceSet",
]


@dataclass(frozen=True, slots=True)
class ApplicabilityGroup:
    """Optional thematic grouping of applicability rules."""

    id: str
    name: str
    description: str | None = None

    def __post_init__(self) -> None:
        group_id = _normalize_id(self.id, field="id")
        name = self.name.strip()
        if not name:
            msg = "group name must not be empty"
            raise ValidationError(msg)
        description = (
            None if self.description is None else self.description.strip() or None
        )
        object.__setattr__(self, "id", group_id)
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "description", description)


@dataclass(frozen=True, slots=True)
class EvidenceApplicabilityRule:
    """Single evidence_id → applicability level under a methodology."""

    evidence_id: str
    level: ApplicabilityLevel
    group_id: str | None = None
    condition_notes: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        evidence_id = _normalize_id(self.evidence_id, field="evidence_id")
        group_id = (
            None
            if self.group_id is None
            else _normalize_id(self.group_id, field="group_id")
        )
        conditions = tuple(c.strip() for c in self.condition_notes if c.strip())
        notes = tuple(n.strip() for n in self.notes if n.strip())
        if self.level is ApplicabilityLevel.CONDITIONAL and not conditions:
            msg = (
                f"CONDITIONAL rule for {evidence_id!r} requires condition_notes"
            )
            raise ValidationError(msg)
        object.__setattr__(self, "evidence_id", evidence_id)
        object.__setattr__(self, "group_id", group_id)
        object.__setattr__(self, "condition_notes", conditions)
        object.__setattr__(self, "notes", notes)


@dataclass(frozen=True, slots=True)
class RequiredEvidenceSet:
    """Named minimum evidence set for a methodology (policy metadata)."""

    id: str
    name: str
    evidence_ids: tuple[str, ...]
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        set_id = _normalize_id(self.id, field="id")
        name = self.name.strip()
        if not name:
            msg = "required set name must not be empty"
            raise ValidationError(msg)
        ids = _unique_ids(self.evidence_ids, field="evidence_ids")
        if not ids:
            msg = "required evidence set must include at least one evidence_id"
            raise ValidationError(msg)
        notes = tuple(n.strip() for n in self.notes if n.strip())
        object.__setattr__(self, "id", set_id)
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "evidence_ids", ids)
        object.__setattr__(self, "notes", notes)


@dataclass(frozen=True, slots=True)
class IndustryEvidenceApplicability:
    """Versioned evidence-policy binding for one IndustryMethodology.

    Owned as methodology policy — not by the Evidence definition registry.
    """

    id: str
    methodology_id: str
    version: str
    rules: tuple[EvidenceApplicabilityRule, ...]
    status: EvidenceLifecycle = EvidenceLifecycle.ACTIVE
    groups: tuple[ApplicabilityGroup, ...] = ()
    required_sets: tuple[RequiredEvidenceSet, ...] = ()
    missing_evidence_policy: MissingEvidencePolicy = MissingEvidencePolicy.RECORD_GAP
    methodology_version_pin: str | None = None
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        applicability_id = _normalize_id(self.id, field="id")
        methodology_id = _normalize_id(self.methodology_id, field="methodology_id")
        version = require_semver(self.version, field="version")
        pin = (
            None
            if self.methodology_version_pin is None
            else require_semver(
                self.methodology_version_pin, field="methodology_version_pin"
            )
        )
        rules = tuple(self.rules)
        if not rules:
            msg = "applicability must include at least one rule"
            raise ValidationError(msg)

        seen_evidence: dict[str, ApplicabilityLevel] = {}
        for rule in rules:
            prior = seen_evidence.get(rule.evidence_id)
            if prior is not None:
                if prior is rule.level:
                    msg = (
                        f"duplicate applicability rule for evidence "
                        f"{rule.evidence_id!r}"
                    )
                    raise ValidationError(msg)
                msg = (
                    f"conflicting applicability for evidence "
                    f"{rule.evidence_id!r}: {prior.value} vs {rule.level.value}"
                )
                raise ValidationError(msg)
            seen_evidence[rule.evidence_id] = rule.level

        groups = tuple(self.groups)
        group_ids = {g.id for g in groups}
        if len(group_ids) != len(groups):
            msg = "duplicate applicability group ids"
            raise ValidationError(msg)
        for rule in rules:
            if rule.group_id is not None and rule.group_id not in group_ids:
                msg = (
                    f"unknown applicability group {rule.group_id!r} on "
                    f"evidence {rule.evidence_id!r}"
                )
                raise ValidationError(msg)

        required_sets = tuple(self.required_sets)
        set_ids = {s.id for s in required_sets}
        if len(set_ids) != len(required_sets):
            msg = "duplicate required evidence set ids"
            raise ValidationError(msg)
        for req in required_sets:
            for eid in req.evidence_ids:
                level = seen_evidence.get(eid)
                if level is None:
                    msg = (
                        f"required set {req.id!r} references evidence {eid!r} "
                        f"with no applicability rule"
                    )
                    raise ValidationError(msg)
                if level is ApplicabilityLevel.UNSUPPORTED:
                    msg = (
                        f"required set {req.id!r} cannot include UNSUPPORTED "
                        f"evidence {eid!r}"
                    )
                    raise ValidationError(msg)
                if level is ApplicabilityLevel.UNKNOWN:
                    msg = (
                        f"required set {req.id!r} cannot include UNKNOWN "
                        f"evidence {eid!r}"
                    )
                    raise ValidationError(msg)

        notes = tuple(n.strip() for n in self.notes if n.strip())
        object.__setattr__(self, "id", applicability_id)
        object.__setattr__(self, "methodology_id", methodology_id)
        object.__setattr__(self, "version", version)
        object.__setattr__(self, "rules", rules)
        object.__setattr__(self, "groups", groups)
        object.__setattr__(self, "required_sets", required_sets)
        object.__setattr__(self, "methodology_version_pin", pin)
        object.__setattr__(self, "notes", notes)

    @property
    def registry_key(self) -> tuple[str, str]:
        return (self.id, self.version)

    def rules_by_level(
        self, level: ApplicabilityLevel
    ) -> tuple[EvidenceApplicabilityRule, ...]:
        return tuple(r for r in self.rules if r.level is level)

    def required_evidence_ids(self) -> tuple[str, ...]:
        return tuple(
            r.evidence_id
            for r in self.rules
            if r.level is ApplicabilityLevel.REQUIRED
        )

    def unsupported_evidence_ids(self) -> tuple[str, ...]:
        return tuple(
            r.evidence_id
            for r in self.rules
            if r.level is ApplicabilityLevel.UNSUPPORTED
        )


def _unique_ids(values: tuple[str, ...], *, field: str) -> tuple[str, ...]:
    seen: set[str] = set()
    out: list[str] = []
    for raw in values:
        cleaned = _normalize_id(raw, field=field)
        if cleaned not in seen:
            seen.add(cleaned)
            out.append(cleaned)
    return tuple(out)
