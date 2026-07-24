"""Risk domain models — qualitative structure only (E1.0).

Immutable value objects and aggregate. No analysis, scoring, or calculations.
"""

from __future__ import annotations

from dataclasses import dataclass

from core.exceptions import ValidationError
from industry import EvidenceBundleReference
from portfolio import ComparisonReportReference, DecisionPackReference

from risk.enums import (
    RiskConstraintKind,
    RiskCoverageKind,
    RiskCoverageStatus,
    RiskLevel,
)
from risk.exceptions import RiskError
from risk.refs import MonitoringReference, PortfolioReference, _normalize_id

__all__ = [
    "RiskAssessment",
    "RiskConstraint",
    "RiskCoverage",
    "RiskDescriptor",
    "RiskIdentity",
    "RiskObservation",
    "RiskProfile",
    "RiskReport",
    "RiskSummary",
]

_FORBIDDEN_CLAIM_WORDS = frozenset(
    {
        "better",
        "best",
        "winner",
        "score",
        "rank",
        "ranking",
        "league",
        "sharpe",
        "sortino",
        "var",
        "beta",
        "alpha",
        "probability",
        "percent",
        "percentage",
        "buy",
        "sell",
        "optimize",
        "optimise",
    }
)


def _reject_claim_language(text: str, *, field: str) -> str:
    cleaned = text.strip()
    if not cleaned:
        msg = f"{field} must not be empty"
        raise ValidationError(msg)
    lowered = cleaned.lower()
    tokens = set(lowered.replace(",", " ").replace(".", " ").split())
    for word in _FORBIDDEN_CLAIM_WORDS:
        if word in tokens or f" {word} " in f" {lowered} ":
            msg = f"{field} must not use forbidden term {word!r}: {cleaned!r}"
            raise ValidationError(msg)
    return cleaned


@dataclass(frozen=True, slots=True)
class RiskIdentity:
    """Canonical identity of a Risk assessment / profile facet."""

    risk_id: str
    risk_name: str
    created_at: str | None = None
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        risk_id = _normalize_id(self.risk_id, field="risk_id")
        name = self.risk_name.strip()
        if not name:
            msg = "invalid identity: risk_name must not be empty"
            raise ValidationError(msg)
        created_at = (
            None if self.created_at is None else self.created_at.strip() or None
        )
        notes = tuple(n.strip() for n in self.notes if n.strip())
        object.__setattr__(self, "risk_id", risk_id)
        object.__setattr__(self, "risk_name", name)
        object.__setattr__(self, "created_at", created_at)
        object.__setattr__(self, "notes", notes)


@dataclass(frozen=True, slots=True)
class RiskObservation:
    """Immutable qualitative risk observation — never a score or trade signal."""

    code: str
    text: str
    subjects: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        code = self.code.strip().lower().replace(" ", "_")
        if not code:
            msg = "observation code must not be empty"
            raise ValidationError(msg)
        text = _reject_claim_language(self.text, field="text")
        subjects = tuple(s.strip().upper() for s in self.subjects if s.strip())
        refs = tuple(r.strip() for r in self.evidence_refs if r.strip())
        object.__setattr__(self, "code", code)
        object.__setattr__(self, "text", text)
        object.__setattr__(self, "subjects", subjects)
        object.__setattr__(self, "evidence_refs", refs)


@dataclass(frozen=True, slots=True)
class RiskDescriptor:
    """Categorical risk descriptor — LOW/MODERATE/ELEVATED/HIGH/UNKNOWN only."""

    dimension: str
    level: RiskLevel
    label: str
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        dimension = self.dimension.strip().lower().replace(" ", "_")
        if not dimension:
            msg = "descriptor dimension must not be empty"
            raise ValidationError(msg)
        label = _reject_claim_language(self.label, field="label")
        notes = tuple(
            _reject_claim_language(n, field="notes") for n in self.notes if n.strip()
        )
        object.__setattr__(self, "dimension", dimension)
        object.__setattr__(self, "label", label)
        object.__setattr__(self, "notes", notes)


@dataclass(frozen=True, slots=True)
class RiskCoverage:
    """Qualitative citation-coverage posture — no percentages."""

    kind: RiskCoverageKind
    status: RiskCoverageStatus
    label: str
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        label = _reject_claim_language(self.label, field="label")
        notes = tuple(n.strip() for n in self.notes if n.strip())
        object.__setattr__(self, "label", label)
        object.__setattr__(self, "notes", notes)


@dataclass(frozen=True, slots=True)
class RiskConstraint:
    """Risk-specific qualitative constraint descriptor — not PortfolioConstraint."""

    id: str
    kind: RiskConstraintKind
    target: str
    posture: RiskLevel
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        constraint_id = _normalize_id(self.id, field="id")
        target = self.target.strip().lower()
        if not target:
            msg = "constraint target must not be empty"
            raise ValidationError(msg)
        notes = tuple(n.strip() for n in self.notes if n.strip())
        object.__setattr__(self, "id", constraint_id)
        object.__setattr__(self, "target", target)
        object.__setattr__(self, "notes", notes)


@dataclass(frozen=True, slots=True)
class RiskSummary:
    """High-level qualitative summary — descriptive only."""

    observation_count: int
    descriptor_count: int
    coverage_notes: tuple[str, ...] = ()
    posture_notes: tuple[str, ...] = ()
    limitation_notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.observation_count < 0 or self.descriptor_count < 0:
            msg = "counts must be >= 0"
            raise ValidationError(msg)
        coverage = tuple(
            _reject_claim_language(n, field="coverage_notes")
            for n in self.coverage_notes
            if n.strip()
        )
        posture = tuple(
            _reject_claim_language(n, field="posture_notes")
            for n in self.posture_notes
            if n.strip()
        )
        limitations = tuple(
            _reject_claim_language(n, field="limitation_notes")
            for n in self.limitation_notes
            if n.strip()
        )
        object.__setattr__(self, "coverage_notes", coverage)
        object.__setattr__(self, "posture_notes", posture)
        object.__setattr__(self, "limitation_notes", limitations)


@dataclass(frozen=True, slots=True)
class RiskAssessment:
    """One qualitative assessment container for a portfolio as-of."""

    assessment_id: str
    risk_id: str
    portfolio_id: str
    as_of: str
    observations: tuple[RiskObservation, ...] = ()
    descriptors: tuple[RiskDescriptor, ...] = ()
    coverage: tuple[RiskCoverage, ...] = ()
    summary: RiskSummary | None = None
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        assessment_id = _normalize_id(self.assessment_id, field="assessment_id")
        risk_id = _normalize_id(self.risk_id, field="risk_id")
        portfolio_id = _normalize_id(self.portfolio_id, field="portfolio_id")
        as_of = self.as_of.strip()
        if not as_of:
            msg = "as_of must not be empty"
            raise ValidationError(msg)
        observations = _unique_observations(self.observations)
        descriptors = _unique_descriptors(self.descriptors)
        coverage = _unique_coverage(self.coverage)
        notes = tuple(n.strip() for n in self.notes if n.strip())
        object.__setattr__(self, "assessment_id", assessment_id)
        object.__setattr__(self, "risk_id", risk_id)
        object.__setattr__(self, "portfolio_id", portfolio_id)
        object.__setattr__(self, "as_of", as_of)
        object.__setattr__(self, "observations", observations)
        object.__setattr__(self, "descriptors", descriptors)
        object.__setattr__(self, "coverage", coverage)
        object.__setattr__(self, "notes", notes)


@dataclass(frozen=True, slots=True)
class RiskReport:
    """Canonical qualitative Risk presentation artifact — no recommendations."""

    risk_id: str
    portfolio_id: str
    summary: RiskSummary
    observations: tuple[RiskObservation, ...] = ()
    descriptors: tuple[RiskDescriptor, ...] = ()
    coverage: tuple[RiskCoverage, ...] = ()
    assessment_id: str | None = None
    decision_pack_refs: tuple[DecisionPackReference, ...] = ()
    evidence_bundle_refs: tuple[EvidenceBundleReference, ...] = ()
    comparison_report_refs: tuple[ComparisonReportReference, ...] = ()
    limitations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        risk_id = _normalize_id(self.risk_id, field="risk_id")
        portfolio_id = _normalize_id(self.portfolio_id, field="portfolio_id")
        assessment_id = (
            None
            if self.assessment_id is None
            else _normalize_id(self.assessment_id, field="assessment_id")
        )
        observations = _unique_observations(self.observations)
        descriptors = _unique_descriptors(self.descriptors)
        coverage = _unique_coverage(self.coverage)
        pack_refs = tuple(self.decision_pack_refs)
        seen_syms: set[str] = set()
        for ref in pack_refs:
            if ref.instrument_symbol in seen_syms:
                msg = (
                    f"duplicate DecisionPack reference for "
                    f"{ref.instrument_symbol!r}"
                )
                raise ValidationError(msg)
            seen_syms.add(ref.instrument_symbol)
        evidence_refs = tuple(self.evidence_bundle_refs)
        seen_ev: set[tuple[str, str]] = set()
        for ref in evidence_refs:
            key = (ref.instrument_key, ref.digest)
            if key in seen_ev:
                msg = (
                    f"broken references: duplicate EvidenceBundle for "
                    f"{ref.instrument_key!r}"
                )
                raise ValidationError(msg)
            seen_ev.add(key)
        limitations = tuple(
            _reject_claim_language(n, field="limitations")
            for n in self.limitations
            if n.strip()
        )
        object.__setattr__(self, "risk_id", risk_id)
        object.__setattr__(self, "portfolio_id", portfolio_id)
        object.__setattr__(self, "assessment_id", assessment_id)
        object.__setattr__(self, "observations", observations)
        object.__setattr__(self, "descriptors", descriptors)
        object.__setattr__(self, "coverage", coverage)
        object.__setattr__(self, "decision_pack_refs", pack_refs)
        object.__setattr__(self, "evidence_bundle_refs", evidence_refs)
        object.__setattr__(
            self, "comparison_report_refs", tuple(self.comparison_report_refs)
        )
        object.__setattr__(self, "limitations", limitations)


@dataclass(frozen=True, slots=True)
class RiskProfile:
    """Aggregate root — cites Portfolio / Monitoring; owns only Risk artifacts."""

    identity: RiskIdentity
    portfolio_ref: PortfolioReference
    monitoring_ref: MonitoringReference | None = None
    decision_pack_refs: tuple[DecisionPackReference, ...] = ()
    evidence_bundle_refs: tuple[EvidenceBundleReference, ...] = ()
    comparison_report_refs: tuple[ComparisonReportReference, ...] = ()
    constraints: tuple[RiskConstraint, ...] = ()
    assessments: tuple[RiskAssessment, ...] = ()
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.identity is None:
            msg = "invalid identity: RiskIdentity is required"
            raise RiskError(msg)
        if self.portfolio_ref is None:
            msg = "broken references: portfolio_ref is required"
            raise RiskError(msg)

        if self.monitoring_ref is not None:
            if self.monitoring_ref.portfolio_id != self.portfolio_ref.portfolio_id:
                msg = (
                    "foreign Monitoring ownership: monitoring portfolio_id "
                    f"{self.monitoring_ref.portfolio_id!r} does not match "
                    f"{self.portfolio_ref.portfolio_id!r}"
                )
                raise RiskError(msg)

        constraints = _unique_constraints(self.constraints)
        assessments = tuple(self.assessments)
        seen_assess: set[str] = set()
        for assessment in assessments:
            if assessment.assessment_id in seen_assess:
                msg = f"duplicate assessment id {assessment.assessment_id!r}"
                raise RiskError(msg)
            seen_assess.add(assessment.assessment_id)
            if assessment.risk_id != self.identity.risk_id:
                msg = (
                    f"foreign ownership: assessment {assessment.assessment_id!r} "
                    f"risk_id {assessment.risk_id!r} does not match "
                    f"{self.identity.risk_id!r}"
                )
                raise RiskError(msg)
            if assessment.portfolio_id != self.portfolio_ref.portfolio_id:
                msg = (
                    f"foreign Portfolio ownership: assessment "
                    f"{assessment.assessment_id!r} portfolio_id "
                    f"{assessment.portfolio_id!r} does not match "
                    f"{self.portfolio_ref.portfolio_id!r}"
                )
                raise RiskError(msg)

        pack_refs = tuple(self.decision_pack_refs)
        seen_syms: set[str] = set()
        for ref in pack_refs:
            if not ref.digest or len(ref.digest) < 8:
                msg = "broken references: DecisionPack digest invalid"
                raise RiskError(msg)
            if ref.instrument_symbol in seen_syms:
                msg = (
                    f"broken references: duplicate DecisionPack for "
                    f"{ref.instrument_symbol!r}"
                )
                raise RiskError(msg)
            seen_syms.add(ref.instrument_symbol)

        evidence_refs = tuple(self.evidence_bundle_refs)
        seen_ev: set[tuple[str, str]] = set()
        for ref in evidence_refs:
            if not ref.digest or not ref.bundle_id:
                msg = "broken references: EvidenceBundle citation invalid"
                raise RiskError(msg)
            key = (ref.instrument_key, ref.digest)
            if key in seen_ev:
                msg = (
                    f"broken references: duplicate EvidenceBundle for "
                    f"{ref.instrument_key!r}"
                )
                raise RiskError(msg)
            seen_ev.add(key)

        comparison_refs = tuple(self.comparison_report_refs)
        seen_comp: set[str] = set()
        for ref in comparison_refs:
            if not ref.digest or len(ref.digest) < 8:
                msg = "broken references: ComparisonReport digest invalid"
                raise RiskError(msg)
            if ref.digest in seen_comp:
                msg = (
                    f"broken references: duplicate ComparisonReport "
                    f"{ref.digest!r}"
                )
                raise RiskError(msg)
            seen_comp.add(ref.digest)

        notes = tuple(n.strip() for n in self.notes if n.strip())
        object.__setattr__(self, "constraints", constraints)
        object.__setattr__(self, "assessments", assessments)
        object.__setattr__(self, "decision_pack_refs", pack_refs)
        object.__setattr__(self, "evidence_bundle_refs", evidence_refs)
        object.__setattr__(self, "comparison_report_refs", comparison_refs)
        object.__setattr__(self, "notes", notes)

    @property
    def risk_id(self) -> str:
        return self.identity.risk_id

    @property
    def portfolio_id(self) -> str:
        return self.portfolio_ref.portfolio_id


def _unique_observations(
    items: tuple[RiskObservation, ...],
) -> tuple[RiskObservation, ...]:
    out = tuple(items)
    seen: set[str] = set()
    for obs in out:
        if obs.code in seen:
            msg = f"duplicate observations: code {obs.code!r}"
            raise RiskError(msg)
        seen.add(obs.code)
    return out


def _unique_descriptors(
    items: tuple[RiskDescriptor, ...],
) -> tuple[RiskDescriptor, ...]:
    out = tuple(items)
    seen: set[str] = set()
    for desc in out:
        if desc.dimension in seen:
            msg = f"duplicate descriptors: dimension {desc.dimension!r}"
            raise RiskError(msg)
        seen.add(desc.dimension)
    return out


def _unique_coverage(
    items: tuple[RiskCoverage, ...],
) -> tuple[RiskCoverage, ...]:
    out = tuple(items)
    seen: set[RiskCoverageKind] = set()
    for cov in out:
        if cov.kind in seen:
            msg = f"duplicate coverage: kind {cov.kind.value!r}"
            raise RiskError(msg)
        seen.add(cov.kind)
    return out


def _unique_constraints(
    items: tuple[RiskConstraint, ...],
) -> tuple[RiskConstraint, ...]:
    out = tuple(items)
    seen: set[str] = set()
    for constraint in out:
        if constraint.id in seen:
            msg = f"duplicate constraints: id {constraint.id!r}"
            raise RiskError(msg)
        seen.add(constraint.id)
    return out
