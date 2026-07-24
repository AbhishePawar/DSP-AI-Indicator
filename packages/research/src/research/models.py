"""Research domain models — synthesis structure only (F1.0).

Immutable value objects and aggregate. No analysis, scoring, or calculations.
"""

from __future__ import annotations

from dataclasses import dataclass

from core.exceptions import ValidationError

from research.enums import (
    ResearchConflictSeverity,
    ResearchCoverageStatus,
    ResearchGapStatus,
    ResearchPriorityLevel,
)
from research.exceptions import ResearchError
from research.refs import (
    ComparisonReference,
    DecisionReference,
    EvidenceReference,
    IntegratedRiskReference,
    MonitoringReference,
    PortfolioReference,
    RiskReference,
    _normalize_id,
)

__all__ = [
    "ResearchAgenda",
    "ResearchConflict",
    "ResearchCoverage",
    "ResearchGap",
    "ResearchIdentity",
    "ResearchInsight",
    "ResearchObservation",
    "ResearchPriority",
    "ResearchProfile",
    "ResearchReport",
    "ResearchSummary",
]

# Align with Portfolio / Risk + F0.0B claim-language policy.
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
        "hold",
        "optimize",
        "optimise",
        "proves",
        "guaranteed",
        "certain",
        "definitely",
        "impossible",
        "risk-free",
        "riskfree",
    }
)


def _reject_claim_language(text: str, *, field: str) -> str:
    cleaned = text.strip()
    if not cleaned:
        msg = f"{field} must not be empty"
        raise ValidationError(msg)
    lowered = cleaned.lower().replace("-", " ")
    tokens = set(lowered.replace(",", " ").replace(".", " ").split())
    for word in _FORBIDDEN_CLAIM_WORDS:
        needle = word.replace("-", " ")
        if needle in tokens or f" {needle} " in f" {lowered} ":
            msg = f"{field} must not use forbidden term {word!r}: {cleaned!r}"
            raise ValidationError(msg)
    return cleaned


@dataclass(frozen=True, slots=True)
class ResearchIdentity:
    """Canonical identity of a Research profile / session."""

    research_id: str
    research_name: str
    created_at: str | None = None
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        research_id = _normalize_id(self.research_id, field="research_id")
        name = self.research_name.strip()
        if not name:
            msg = "invalid identity: research_name must not be empty"
            raise ValidationError(msg)
        created_at = (
            None if self.created_at is None else self.created_at.strip() or None
        )
        notes = tuple(n.strip() for n in self.notes if n.strip())
        object.__setattr__(self, "research_id", research_id)
        object.__setattr__(self, "research_name", name)
        object.__setattr__(self, "created_at", created_at)
        object.__setattr__(self, "notes", notes)


@dataclass(frozen=True, slots=True)
class ResearchObservation:
    """Immutable knowledge-state observation — never a trade signal."""

    observation_id: str
    code: str
    text: str
    evidence_refs: tuple[EvidenceReference, ...] = ()
    subjects: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        observation_id = _normalize_id(self.observation_id, field="observation_id")
        code = self.code.strip().lower().replace(" ", "_")
        if not code:
            msg = "observation code must not be empty"
            raise ValidationError(msg)
        text = _reject_claim_language(self.text, field="text")
        evidence_refs = tuple(self.evidence_refs)
        subjects = tuple(s.strip().upper() for s in self.subjects if s.strip())
        object.__setattr__(self, "observation_id", observation_id)
        object.__setattr__(self, "code", code)
        object.__setattr__(self, "text", text)
        object.__setattr__(self, "evidence_refs", evidence_refs)
        object.__setattr__(self, "subjects", subjects)


@dataclass(frozen=True, slots=True)
class ResearchInsight:
    """Cite-backed synthesis statement — requires Evidence provenance (F0.0B)."""

    insight_id: str
    text: str
    observation_ids: tuple[str, ...]
    evidence_refs: tuple[EvidenceReference, ...]
    decision_refs: tuple[DecisionReference, ...] = ()
    comparison_refs: tuple[ComparisonReference, ...] = ()
    risk_refs: tuple[RiskReference, ...] = ()

    def __post_init__(self) -> None:
        insight_id = _normalize_id(self.insight_id, field="insight_id")
        text = _reject_claim_language(self.text, field="text")
        observation_ids = tuple(
            _normalize_id(i, field="observation_id") for i in self.observation_ids
        )
        if not observation_ids:
            msg = "broken references: insight requires observation_ids"
            raise ResearchError(msg)
        evidence_refs = tuple(self.evidence_refs)
        if not evidence_refs:
            msg = (
                "broken references: insight requires one or more EvidenceReference"
            )
            raise ResearchError(msg)
        seen_obs: set[str] = set()
        for oid in observation_ids:
            if oid in seen_obs:
                msg = f"duplicate observation ids on insight: {oid!r}"
                raise ResearchError(msg)
            seen_obs.add(oid)
        seen_ev: set[tuple[str, str]] = set()
        for ref in evidence_refs:
            key = (ref.bundle_id, ref.digest)
            if key in seen_ev:
                msg = f"duplicate evidence refs on insight: {ref.bundle_id!r}"
                raise ResearchError(msg)
            seen_ev.add(key)
        object.__setattr__(self, "insight_id", insight_id)
        object.__setattr__(self, "text", text)
        object.__setattr__(self, "observation_ids", observation_ids)
        object.__setattr__(self, "evidence_refs", evidence_refs)
        object.__setattr__(self, "decision_refs", tuple(self.decision_refs))
        object.__setattr__(self, "comparison_refs", tuple(self.comparison_refs))
        object.__setattr__(self, "risk_refs", tuple(self.risk_refs))


@dataclass(frozen=True, slots=True)
class ResearchConflict:
    """Descriptive conflict record — Research never resolves conflicts."""

    conflict_id: str
    summary: str
    severity: ResearchConflictSeverity
    left_citations: tuple[str, ...]
    right_citations: tuple[str, ...]
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        conflict_id = _normalize_id(self.conflict_id, field="conflict_id")
        summary = _reject_claim_language(self.summary, field="summary")
        left = tuple(c.strip() for c in self.left_citations if c.strip())
        right = tuple(c.strip() for c in self.right_citations if c.strip())
        if not left or not right:
            msg = "broken references: conflict requires left and right citations"
            raise ResearchError(msg)
        notes = tuple(
            _reject_claim_language(n, field="notes") for n in self.notes if n.strip()
        )
        object.__setattr__(self, "conflict_id", conflict_id)
        object.__setattr__(self, "summary", summary)
        object.__setattr__(self, "left_citations", left)
        object.__setattr__(self, "right_citations", right)
        object.__setattr__(self, "notes", notes)


@dataclass(frozen=True, slots=True)
class ResearchGap:
    """Knowledge gap — descriptive; resolution is outside Research domain."""

    gap_id: str
    dimension: str
    status: ResearchGapStatus
    description: str
    missing_refs: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        gap_id = _normalize_id(self.gap_id, field="gap_id")
        dimension = self.dimension.strip().lower().replace(" ", "_")
        if not dimension:
            msg = "gap dimension must not be empty"
            raise ValidationError(msg)
        description = _reject_claim_language(self.description, field="description")
        missing = tuple(m.strip() for m in self.missing_refs if m.strip())
        notes = tuple(n.strip() for n in self.notes if n.strip())
        object.__setattr__(self, "gap_id", gap_id)
        object.__setattr__(self, "dimension", dimension)
        object.__setattr__(self, "description", description)
        object.__setattr__(self, "missing_refs", missing)
        object.__setattr__(self, "notes", notes)


@dataclass(frozen=True, slots=True)
class ResearchPriority:
    """Investigative agenda priority — never a trade or sizing recommendation."""

    priority_id: str
    level: ResearchPriorityLevel
    text: str
    gap_ids: tuple[str, ...] = ()
    conflict_ids: tuple[str, ...] = ()
    insight_ids: tuple[str, ...] = ()
    observation_ids: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        priority_id = _normalize_id(self.priority_id, field="priority_id")
        text = _reject_claim_language(self.text, field="text")
        gap_ids = tuple(_normalize_id(i, field="gap_id") for i in self.gap_ids)
        conflict_ids = tuple(
            _normalize_id(i, field="conflict_id") for i in self.conflict_ids
        )
        insight_ids = tuple(
            _normalize_id(i, field="insight_id") for i in self.insight_ids
        )
        observation_ids = tuple(
            _normalize_id(i, field="observation_id") for i in self.observation_ids
        )
        if not (gap_ids or conflict_ids or insight_ids or observation_ids):
            msg = (
                "broken references: priority requires gap, conflict, "
                "insight, or observation provenance"
            )
            raise ResearchError(msg)
        notes = tuple(n.strip() for n in self.notes if n.strip())
        object.__setattr__(self, "priority_id", priority_id)
        object.__setattr__(self, "text", text)
        object.__setattr__(self, "gap_ids", gap_ids)
        object.__setattr__(self, "conflict_ids", conflict_ids)
        object.__setattr__(self, "insight_ids", insight_ids)
        object.__setattr__(self, "observation_ids", observation_ids)
        object.__setattr__(self, "notes", notes)


@dataclass(frozen=True, slots=True)
class ResearchAgenda:
    """Ordered investigative plan — never portfolio or trading actions."""

    agenda_id: str
    priorities: tuple[ResearchPriority, ...] = ()
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        agenda_id = _normalize_id(self.agenda_id, field="agenda_id")
        priorities = _unique_priorities(tuple(self.priorities))
        notes = tuple(
            _reject_claim_language(n, field="notes") for n in self.notes if n.strip()
        )
        object.__setattr__(self, "agenda_id", agenda_id)
        object.__setattr__(self, "priorities", priorities)
        object.__setattr__(self, "notes", notes)


@dataclass(frozen=True, slots=True)
class ResearchCoverage:
    """Knowledge-coverage posture across a citation dimension."""

    dimension: str
    status: ResearchCoverageStatus
    label: str
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        dimension = self.dimension.strip().lower().replace(" ", "_")
        if not dimension:
            msg = "coverage dimension must not be empty"
            raise ValidationError(msg)
        label = _reject_claim_language(self.label, field="label")
        notes = tuple(n.strip() for n in self.notes if n.strip())
        object.__setattr__(self, "dimension", dimension)
        object.__setattr__(self, "label", label)
        object.__setattr__(self, "notes", notes)


@dataclass(frozen=True, slots=True)
class ResearchSummary:
    """High-level qualitative research summary — descriptive only."""

    observation_count: int
    insight_count: int
    conflict_count: int = 0
    gap_count: int = 0
    agenda_item_count: int = 0
    coverage_notes: tuple[str, ...] = ()
    limitation_notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for name in (
            "observation_count",
            "insight_count",
            "conflict_count",
            "gap_count",
            "agenda_item_count",
        ):
            if getattr(self, name) < 0:
                msg = "counts must be >= 0"
                raise ValidationError(msg)
        coverage = tuple(
            _reject_claim_language(n, field="coverage_notes")
            for n in self.coverage_notes
            if n.strip()
        )
        limitations = tuple(
            _reject_claim_language(n, field="limitation_notes")
            for n in self.limitation_notes
            if n.strip()
        )
        object.__setattr__(self, "coverage_notes", coverage)
        object.__setattr__(self, "limitation_notes", limitations)


@dataclass(frozen=True, slots=True)
class ResearchReport:
    """Canonical immutable Research presentation snapshot — no recommendations."""

    research_id: str
    summary: ResearchSummary
    as_of: str
    observations: tuple[ResearchObservation, ...] = ()
    insights: tuple[ResearchInsight, ...] = ()
    conflicts: tuple[ResearchConflict, ...] = ()
    gaps: tuple[ResearchGap, ...] = ()
    agenda: ResearchAgenda | None = None
    coverage: tuple[ResearchCoverage, ...] = ()
    decision_refs: tuple[DecisionReference, ...] = ()
    evidence_refs: tuple[EvidenceReference, ...] = ()
    comparison_refs: tuple[ComparisonReference, ...] = ()
    portfolio_ref: PortfolioReference | None = None
    monitoring_ref: MonitoringReference | None = None
    risk_refs: tuple[RiskReference, ...] = ()
    integrated_risk_refs: tuple[IntegratedRiskReference, ...] = ()
    limitations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        research_id = _normalize_id(self.research_id, field="research_id")
        as_of = self.as_of.strip()
        if not as_of:
            msg = "as_of must not be empty"
            raise ValidationError(msg)
        observations = _unique_observations(self.observations)
        insights = _unique_insights(self.insights)
        conflicts = _unique_conflicts(self.conflicts)
        gaps = _unique_gaps(self.gaps)
        coverage = _unique_coverage(self.coverage)
        _validate_insight_traceability(insights, observations)
        limitations = tuple(
            _reject_claim_language(n, field="limitations")
            for n in self.limitations
            if n.strip()
        )
        object.__setattr__(self, "research_id", research_id)
        object.__setattr__(self, "as_of", as_of)
        object.__setattr__(self, "observations", observations)
        object.__setattr__(self, "insights", insights)
        object.__setattr__(self, "conflicts", conflicts)
        object.__setattr__(self, "gaps", gaps)
        object.__setattr__(self, "coverage", coverage)
        object.__setattr__(self, "decision_refs", tuple(self.decision_refs))
        object.__setattr__(self, "evidence_refs", tuple(self.evidence_refs))
        object.__setattr__(self, "comparison_refs", tuple(self.comparison_refs))
        object.__setattr__(self, "risk_refs", tuple(self.risk_refs))
        object.__setattr__(
            self, "integrated_risk_refs", tuple(self.integrated_risk_refs)
        )
        object.__setattr__(self, "limitations", limitations)


@dataclass(frozen=True, slots=True)
class ResearchProfile:
    """Aggregate root — cites upstream; owns only Research artifacts."""

    identity: ResearchIdentity
    portfolio_ref: PortfolioReference | None = None
    monitoring_ref: MonitoringReference | None = None
    decision_refs: tuple[DecisionReference, ...] = ()
    evidence_refs: tuple[EvidenceReference, ...] = ()
    comparison_refs: tuple[ComparisonReference, ...] = ()
    risk_refs: tuple[RiskReference, ...] = ()
    integrated_risk_refs: tuple[IntegratedRiskReference, ...] = ()
    observations: tuple[ResearchObservation, ...] = ()
    insights: tuple[ResearchInsight, ...] = ()
    conflicts: tuple[ResearchConflict, ...] = ()
    gaps: tuple[ResearchGap, ...] = ()
    agenda: ResearchAgenda | None = None
    coverage: tuple[ResearchCoverage, ...] = ()
    summary: ResearchSummary | None = None
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.identity is None:
            msg = "missing identity: ResearchIdentity is required"
            raise ResearchError(msg)

        if self.monitoring_ref is not None and self.portfolio_ref is not None:
            if self.monitoring_ref.portfolio_id != self.portfolio_ref.portfolio_id:
                msg = (
                    "foreign ownership: monitoring portfolio_id "
                    f"{self.monitoring_ref.portfolio_id!r} does not match "
                    f"{self.portfolio_ref.portfolio_id!r}"
                )
                raise ResearchError(msg)

        decision_refs = _unique_decision_refs(self.decision_refs)
        evidence_refs = _unique_evidence_refs(self.evidence_refs)
        comparison_refs = _unique_comparison_refs(self.comparison_refs)
        risk_refs = _unique_risk_refs(self.risk_refs)
        integrated = _unique_integrated_risk_refs(self.integrated_risk_refs)

        observations = _unique_observations(self.observations)
        insights = _unique_insights(self.insights)
        conflicts = _unique_conflicts(self.conflicts)
        gaps = _unique_gaps(self.gaps)
        coverage = _unique_coverage(self.coverage)
        _validate_insight_traceability(insights, observations)
        if self.agenda is not None:
            _validate_agenda_provenance(
                self.agenda, observations, insights, conflicts, gaps
            )

        has_citations = bool(
            decision_refs
            or evidence_refs
            or comparison_refs
            or risk_refs
            or integrated
            or self.portfolio_ref is not None
            or self.monitoring_ref is not None
        )
        if not has_citations:
            msg = "missing citations: ResearchProfile requires at least one reference"
            raise ResearchError(msg)

        notes = tuple(n.strip() for n in self.notes if n.strip())
        object.__setattr__(self, "decision_refs", decision_refs)
        object.__setattr__(self, "evidence_refs", evidence_refs)
        object.__setattr__(self, "comparison_refs", comparison_refs)
        object.__setattr__(self, "risk_refs", risk_refs)
        object.__setattr__(self, "integrated_risk_refs", integrated)
        object.__setattr__(self, "observations", observations)
        object.__setattr__(self, "insights", insights)
        object.__setattr__(self, "conflicts", conflicts)
        object.__setattr__(self, "gaps", gaps)
        object.__setattr__(self, "coverage", coverage)
        object.__setattr__(self, "notes", notes)

    @property
    def research_id(self) -> str:
        return self.identity.research_id


def _validate_insight_traceability(
    insights: tuple[ResearchInsight, ...],
    observations: tuple[ResearchObservation, ...],
) -> None:
    obs_ids = {o.observation_id for o in observations}
    for insight in insights:
        for oid in insight.observation_ids:
            if oid not in obs_ids:
                msg = (
                    f"broken references: insight {insight.insight_id!r} "
                    f"references missing observation {oid!r}"
                )
                raise ResearchError(msg)


def _validate_agenda_provenance(
    agenda: ResearchAgenda,
    observations: tuple[ResearchObservation, ...],
    insights: tuple[ResearchInsight, ...],
    conflicts: tuple[ResearchConflict, ...],
    gaps: tuple[ResearchGap, ...],
) -> None:
    obs_ids = {o.observation_id for o in observations}
    insight_ids = {i.insight_id for i in insights}
    conflict_ids = {c.conflict_id for c in conflicts}
    gap_ids = {g.gap_id for g in gaps}
    for priority in agenda.priorities:
        for oid in priority.observation_ids:
            if oid not in obs_ids:
                msg = (
                    f"broken references: priority {priority.priority_id!r} "
                    f"references missing observation {oid!r}"
                )
                raise ResearchError(msg)
        for iid in priority.insight_ids:
            if iid not in insight_ids:
                msg = (
                    f"broken references: priority {priority.priority_id!r} "
                    f"references missing insight {iid!r}"
                )
                raise ResearchError(msg)
        for cid in priority.conflict_ids:
            if cid not in conflict_ids:
                msg = (
                    f"broken references: priority {priority.priority_id!r} "
                    f"references missing conflict {cid!r}"
                )
                raise ResearchError(msg)
        for gid in priority.gap_ids:
            if gid not in gap_ids:
                msg = (
                    f"broken references: priority {priority.priority_id!r} "
                    f"references missing gap {gid!r}"
                )
                raise ResearchError(msg)


def _unique_observations(
    items: tuple[ResearchObservation, ...],
) -> tuple[ResearchObservation, ...]:
    seen_id: set[str] = set()
    seen_code: set[str] = set()
    for obs in items:
        if obs.observation_id in seen_id:
            msg = f"duplicate observations: id {obs.observation_id!r}"
            raise ResearchError(msg)
        if obs.code in seen_code:
            msg = f"duplicate observations: code {obs.code!r}"
            raise ResearchError(msg)
        seen_id.add(obs.observation_id)
        seen_code.add(obs.code)
    return tuple(items)


def _unique_insights(
    items: tuple[ResearchInsight, ...],
) -> tuple[ResearchInsight, ...]:
    seen: set[str] = set()
    for insight in items:
        if insight.insight_id in seen:
            msg = f"duplicate insights: id {insight.insight_id!r}"
            raise ResearchError(msg)
        seen.add(insight.insight_id)
    return tuple(items)


def _unique_conflicts(
    items: tuple[ResearchConflict, ...],
) -> tuple[ResearchConflict, ...]:
    seen: set[str] = set()
    for conflict in items:
        if conflict.conflict_id in seen:
            msg = f"duplicate conflicts: id {conflict.conflict_id!r}"
            raise ResearchError(msg)
        seen.add(conflict.conflict_id)
    return tuple(items)


def _unique_gaps(items: tuple[ResearchGap, ...]) -> tuple[ResearchGap, ...]:
    seen_id: set[str] = set()
    seen_dim: set[str] = set()
    for gap in items:
        if gap.gap_id in seen_id:
            msg = f"duplicate gaps: id {gap.gap_id!r}"
            raise ResearchError(msg)
        if gap.dimension in seen_dim:
            msg = f"duplicate gaps: dimension {gap.dimension!r}"
            raise ResearchError(msg)
        seen_id.add(gap.gap_id)
        seen_dim.add(gap.dimension)
    return tuple(items)


def _unique_priorities(
    items: tuple[ResearchPriority, ...],
) -> tuple[ResearchPriority, ...]:
    seen: set[str] = set()
    for priority in items:
        if priority.priority_id in seen:
            msg = f"duplicate priorities: id {priority.priority_id!r}"
            raise ResearchError(msg)
        seen.add(priority.priority_id)
    return tuple(items)


def _unique_coverage(
    items: tuple[ResearchCoverage, ...],
) -> tuple[ResearchCoverage, ...]:
    seen: set[str] = set()
    for cov in items:
        if cov.dimension in seen:
            msg = f"duplicate coverage: dimension {cov.dimension!r}"
            raise ResearchError(msg)
        seen.add(cov.dimension)
    return tuple(items)


def _unique_decision_refs(
    items: tuple[DecisionReference, ...],
) -> tuple[DecisionReference, ...]:
    seen: set[str] = set()
    for ref in items:
        if ref.instrument_symbol in seen:
            msg = (
                f"broken references: duplicate DecisionReference for "
                f"{ref.instrument_symbol!r}"
            )
            raise ResearchError(msg)
        seen.add(ref.instrument_symbol)
    return tuple(items)


def _unique_evidence_refs(
    items: tuple[EvidenceReference, ...],
) -> tuple[EvidenceReference, ...]:
    seen: set[tuple[str, str]] = set()
    for ref in items:
        key = (ref.bundle_id, ref.digest)
        if key in seen:
            msg = (
                f"broken references: duplicate EvidenceReference for "
                f"{ref.bundle_id!r}"
            )
            raise ResearchError(msg)
        seen.add(key)
    return tuple(items)


def _unique_comparison_refs(
    items: tuple[ComparisonReference, ...],
) -> tuple[ComparisonReference, ...]:
    seen: set[str] = set()
    for ref in items:
        if ref.digest in seen:
            msg = (
                f"broken references: duplicate ComparisonReference "
                f"{ref.digest!r}"
            )
            raise ResearchError(msg)
        seen.add(ref.digest)
    return tuple(items)


def _unique_risk_refs(
    items: tuple[RiskReference, ...],
) -> tuple[RiskReference, ...]:
    seen: set[str] = set()
    for ref in items:
        key = ref.risk_id
        if key in seen:
            msg = f"broken references: duplicate RiskReference {key!r}"
            raise ResearchError(msg)
        seen.add(key)
    return tuple(items)


def _unique_integrated_risk_refs(
    items: tuple[IntegratedRiskReference, ...],
) -> tuple[IntegratedRiskReference, ...]:
    seen: set[str] = set()
    for ref in items:
        if ref.risk_id in seen:
            msg = (
                f"broken references: duplicate IntegratedRiskReference "
                f"{ref.risk_id!r}"
            )
            raise ResearchError(msg)
        seen.add(ref.risk_id)
    return tuple(items)
