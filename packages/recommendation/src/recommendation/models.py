"""Recommendation Intelligence domain models — contracts only (G1.0).

Immutable value objects and aggregate. No synthesis, scoring algorithms, or engines.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from core.exceptions import ValidationError

from recommendation.enums import (
    ConfidenceLevel,
    ConflictSeverity,
    RecommendationType,
)
from recommendation.exceptions import RecommendationError
from recommendation.refs import (
    ComparisonReference,
    DecisionReference,
    PortfolioReference,
    QuantitativeRiskReference,
    ResearchReference,
    RiskReference,
    _normalize_id,
)

__all__ = [
    "RecommendationConflict",
    "RecommendationIdentity",
    "RecommendationOption",
    "RecommendationProfile",
    "RecommendationRationale",
    "RecommendationReport",
    "RecommendationScore",
    "RecommendationSummary",
]


def _require_decimal(value: Any, *, field: str) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, Decimal):
        msg = f"{field} must be decimal.Decimal, never float or other numeric types"
        raise ValidationError(msg)
    if not value.is_finite():
        msg = f"{field} must be a finite Decimal"
        raise ValidationError(msg)
    return value


def _non_empty(text: str, *, field: str) -> str:
    cleaned = text.strip()
    if not cleaned:
        msg = f"{field} must not be empty"
        raise ValidationError(msg)
    return cleaned


@dataclass(frozen=True, slots=True)
class RecommendationIdentity:
    """Canonical identity of a Recommendation profile / session."""

    recommendation_id: str
    recommendation_name: str
    created_at: str | None = None
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        rid = _normalize_id(self.recommendation_id, field="recommendation_id")
        name = _non_empty(self.recommendation_name, field="recommendation_name")
        created_at = (
            None if self.created_at is None else self.created_at.strip() or None
        )
        notes = tuple(n.strip() for n in self.notes if n.strip())
        object.__setattr__(self, "recommendation_id", rid)
        object.__setattr__(self, "recommendation_name", name)
        object.__setattr__(self, "created_at", created_at)
        object.__setattr__(self, "notes", notes)


@dataclass(frozen=True, slots=True)
class RecommendationScore:
    """Transparent confidence score — does not replace rationale."""

    score_id: str
    score_type: str
    value: Decimal
    unit: str
    method_id: str
    provenance: tuple[str, ...]
    calculation_timestamp: str
    confidence_level: ConfidenceLevel | None = None
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        score_id = _normalize_id(self.score_id, field="score_id")
        score_type = _non_empty(self.score_type, field="score_type").lower().replace(
            " ", "_"
        )
        value = _require_decimal(self.value, field="value")
        unit = _non_empty(self.unit, field="unit")
        method_id = _normalize_id(self.method_id, field="method_id")
        if not self.provenance:
            msg = "missing provenance: RecommendationScore requires provenance"
            raise RecommendationError(msg)
        provenance = tuple(_non_empty(p, field="provenance") for p in self.provenance)
        timestamp = _non_empty(
            self.calculation_timestamp, field="calculation_timestamp"
        )
        notes = tuple(n.strip() for n in self.notes if n.strip())
        object.__setattr__(self, "score_id", score_id)
        object.__setattr__(self, "score_type", score_type)
        object.__setattr__(self, "value", value)
        object.__setattr__(self, "unit", unit)
        object.__setattr__(self, "method_id", method_id)
        object.__setattr__(self, "provenance", provenance)
        object.__setattr__(self, "calculation_timestamp", timestamp)
        object.__setattr__(self, "notes", notes)


@dataclass(frozen=True, slots=True)
class RecommendationRationale:
    """Cite-backed explanation — never a trade order."""

    rationale_id: str
    title: str
    body: str
    supporting_report_refs: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        rationale_id = _normalize_id(self.rationale_id, field="rationale_id")
        title = _non_empty(self.title, field="title")
        body = _non_empty(self.body, field="body")
        refs = tuple(_non_empty(r, field="supporting_report_refs") for r in self.supporting_report_refs)
        notes = tuple(n.strip() for n in self.notes if n.strip())
        object.__setattr__(self, "rationale_id", rationale_id)
        object.__setattr__(self, "title", title)
        object.__setattr__(self, "body", body)
        object.__setattr__(self, "supporting_report_refs", refs)
        object.__setattr__(self, "notes", notes)


@dataclass(frozen=True, slots=True)
class RecommendationOption:
    """Candidate action posture — not an OMS / broker order."""

    option_id: str
    option_type: RecommendationType
    title: str
    description: str
    supporting_rationale_refs: tuple[str, ...]
    supporting_report_refs: tuple[str, ...]
    confidence_reference: str
    priority: int
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        option_id = _normalize_id(self.option_id, field="option_id")
        title = _non_empty(self.title, field="title")
        description = _non_empty(self.description, field="description")
        if not self.supporting_rationale_refs:
            msg = "broken rationale references: supporting_rationale_refs required"
            raise RecommendationError(msg)
        rationale_refs = tuple(
            _normalize_id(r, field="supporting_rationale_refs")
            for r in self.supporting_rationale_refs
        )
        report_refs = tuple(
            _non_empty(r, field="supporting_report_refs")
            for r in self.supporting_report_refs
        )
        confidence_reference = _normalize_id(
            self.confidence_reference, field="confidence_reference"
        )
        if self.priority < 0:
            msg = "priority must be >= 0"
            raise ValidationError(msg)
        notes = tuple(n.strip() for n in self.notes if n.strip())
        object.__setattr__(self, "option_id", option_id)
        object.__setattr__(self, "title", title)
        object.__setattr__(self, "description", description)
        object.__setattr__(self, "supporting_rationale_refs", rationale_refs)
        object.__setattr__(self, "supporting_report_refs", report_refs)
        object.__setattr__(self, "confidence_reference", confidence_reference)
        object.__setattr__(self, "notes", notes)


@dataclass(frozen=True, slots=True)
class RecommendationConflict:
    """Declared tension between options and/or upstream citations."""

    conflict_id: str
    title: str
    description: str
    severity: ConflictSeverity
    option_refs: tuple[str, ...] = ()
    report_refs: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        conflict_id = _normalize_id(self.conflict_id, field="conflict_id")
        title = _non_empty(self.title, field="title")
        description = _non_empty(self.description, field="description")
        option_refs = tuple(
            _normalize_id(r, field="option_refs") for r in self.option_refs
        )
        report_refs = tuple(
            _non_empty(r, field="report_refs") for r in self.report_refs
        )
        notes = tuple(n.strip() for n in self.notes if n.strip())
        object.__setattr__(self, "conflict_id", conflict_id)
        object.__setattr__(self, "title", title)
        object.__setattr__(self, "description", description)
        object.__setattr__(self, "option_refs", option_refs)
        object.__setattr__(self, "report_refs", report_refs)
        object.__setattr__(self, "notes", notes)


@dataclass(frozen=True, slots=True)
class RecommendationSummary:
    """High-level recommendation summary — descriptive counts only."""

    option_count: int
    conflict_count: int = 0
    rationale_count: int = 0
    score_count: int = 0
    limitation_notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for name in (
            "option_count",
            "conflict_count",
            "rationale_count",
            "score_count",
        ):
            if getattr(self, name) < 0:
                msg = "counts must be >= 0"
                raise ValidationError(msg)
        limitations = tuple(
            n.strip() for n in self.limitation_notes if n.strip()
        )
        object.__setattr__(self, "limitation_notes", limitations)


@dataclass(frozen=True, slots=True)
class RecommendationReport:
    """Canonical immutable Recommendation presentation snapshot."""

    recommendation_id: str
    summary: RecommendationSummary
    as_of: str
    options: tuple[RecommendationOption, ...] = ()
    scores: tuple[RecommendationScore, ...] = ()
    rationales: tuple[RecommendationRationale, ...] = ()
    conflicts: tuple[RecommendationConflict, ...] = ()
    decision_refs: tuple[DecisionReference, ...] = ()
    comparison_refs: tuple[ComparisonReference, ...] = ()
    portfolio_ref: PortfolioReference | None = None
    risk_refs: tuple[RiskReference, ...] = ()
    research_refs: tuple[ResearchReference, ...] = ()
    quantitative_risk_refs: tuple[QuantitativeRiskReference, ...] = ()
    preferred_option_id: str | None = None
    limitations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        rid = _normalize_id(self.recommendation_id, field="recommendation_id")
        as_of = _non_empty(self.as_of, field="as_of")
        options = _unique_options(self.options)
        scores = _unique_scores(self.scores)
        rationales = _unique_rationales(self.rationales)
        conflicts = _unique_conflicts(self.conflicts)
        _validate_option_links(options, scores, rationales)
        _validate_conflict_links(conflicts, options)
        known = _known_report_citations(
            decision_refs=self.decision_refs,
            comparison_refs=self.comparison_refs,
            portfolio_ref=self.portfolio_ref,
            risk_refs=self.risk_refs,
            research_refs=self.research_refs,
            quantitative_risk_refs=self.quantitative_risk_refs,
        )
        _validate_report_citations(options, rationales, conflicts, known)
        preferred = (
            None
            if self.preferred_option_id is None
            else _normalize_id(self.preferred_option_id, field="preferred_option_id")
        )
        if preferred is not None and preferred not in {o.option_id for o in options}:
            msg = f"broken references: preferred_option_id {preferred!r} missing"
            raise RecommendationError(msg)
        limitations = tuple(n.strip() for n in self.limitations if n.strip())
        object.__setattr__(self, "recommendation_id", rid)
        object.__setattr__(self, "as_of", as_of)
        object.__setattr__(self, "options", options)
        object.__setattr__(self, "scores", scores)
        object.__setattr__(self, "rationales", rationales)
        object.__setattr__(self, "conflicts", conflicts)
        object.__setattr__(self, "decision_refs", tuple(self.decision_refs))
        object.__setattr__(self, "comparison_refs", tuple(self.comparison_refs))
        object.__setattr__(self, "risk_refs", tuple(self.risk_refs))
        object.__setattr__(self, "research_refs", tuple(self.research_refs))
        object.__setattr__(
            self, "quantitative_risk_refs", tuple(self.quantitative_risk_refs)
        )
        object.__setattr__(self, "preferred_option_id", preferred)
        object.__setattr__(self, "limitations", limitations)


@dataclass(frozen=True, slots=True)
class RecommendationProfile:
    """Aggregate root — cites upstream reports; owns recommendation artifacts only."""

    identity: RecommendationIdentity
    decision_refs: tuple[DecisionReference, ...] = ()
    comparison_refs: tuple[ComparisonReference, ...] = ()
    portfolio_ref: PortfolioReference | None = None
    risk_refs: tuple[RiskReference, ...] = ()
    research_refs: tuple[ResearchReference, ...] = ()
    quantitative_risk_refs: tuple[QuantitativeRiskReference, ...] = ()
    options: tuple[RecommendationOption, ...] = ()
    scores: tuple[RecommendationScore, ...] = ()
    rationales: tuple[RecommendationRationale, ...] = ()
    conflicts: tuple[RecommendationConflict, ...] = ()
    summary: RecommendationSummary | None = None
    preferred_option_id: str | None = None
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.identity is None:
            msg = "missing identity: RecommendationIdentity is required"
            raise RecommendationError(msg)

        options = _unique_options(self.options)
        scores = _unique_scores(self.scores)
        rationales = _unique_rationales(self.rationales)
        conflicts = _unique_conflicts(self.conflicts)
        _validate_option_links(options, scores, rationales)
        _validate_conflict_links(conflicts, options)
        known = _known_report_citations(
            decision_refs=self.decision_refs,
            comparison_refs=self.comparison_refs,
            portfolio_ref=self.portfolio_ref,
            risk_refs=self.risk_refs,
            research_refs=self.research_refs,
            quantitative_risk_refs=self.quantitative_risk_refs,
        )
        _validate_report_citations(options, rationales, conflicts, known)
        preferred = (
            None
            if self.preferred_option_id is None
            else _normalize_id(self.preferred_option_id, field="preferred_option_id")
        )
        if preferred is not None and preferred not in {o.option_id for o in options}:
            msg = f"broken references: preferred_option_id {preferred!r} missing"
            raise RecommendationError(msg)
        notes = tuple(n.strip() for n in self.notes if n.strip())
        object.__setattr__(self, "options", options)
        object.__setattr__(self, "scores", scores)
        object.__setattr__(self, "rationales", rationales)
        object.__setattr__(self, "conflicts", conflicts)
        object.__setattr__(self, "decision_refs", tuple(self.decision_refs))
        object.__setattr__(self, "comparison_refs", tuple(self.comparison_refs))
        object.__setattr__(self, "risk_refs", tuple(self.risk_refs))
        object.__setattr__(self, "research_refs", tuple(self.research_refs))
        object.__setattr__(
            self, "quantitative_risk_refs", tuple(self.quantitative_risk_refs)
        )
        object.__setattr__(self, "preferred_option_id", preferred)
        object.__setattr__(self, "notes", notes)

    @property
    def recommendation_id(self) -> str:
        return self.identity.recommendation_id


def _unique_options(
    items: tuple[RecommendationOption, ...],
) -> tuple[RecommendationOption, ...]:
    seen: set[str] = set()
    for item in items:
        if item.option_id in seen:
            msg = f"duplicate options: id {item.option_id!r}"
            raise RecommendationError(msg)
        seen.add(item.option_id)
    return tuple(items)


def _unique_scores(
    items: tuple[RecommendationScore, ...],
) -> tuple[RecommendationScore, ...]:
    seen: set[str] = set()
    for item in items:
        if item.score_id in seen:
            msg = f"duplicate scores: id {item.score_id!r}"
            raise RecommendationError(msg)
        seen.add(item.score_id)
    return tuple(items)


def _unique_rationales(
    items: tuple[RecommendationRationale, ...],
) -> tuple[RecommendationRationale, ...]:
    seen: set[str] = set()
    for item in items:
        if item.rationale_id in seen:
            msg = f"duplicate rationales: id {item.rationale_id!r}"
            raise RecommendationError(msg)
        seen.add(item.rationale_id)
    return tuple(items)


def _unique_conflicts(
    items: tuple[RecommendationConflict, ...],
) -> tuple[RecommendationConflict, ...]:
    seen: set[str] = set()
    for item in items:
        if item.conflict_id in seen:
            msg = f"duplicate conflicts: id {item.conflict_id!r}"
            raise RecommendationError(msg)
        seen.add(item.conflict_id)
    return tuple(items)


def _validate_option_links(
    options: tuple[RecommendationOption, ...],
    scores: tuple[RecommendationScore, ...],
    rationales: tuple[RecommendationRationale, ...],
) -> None:
    score_ids = {s.score_id for s in scores}
    rationale_ids = {r.rationale_id for r in rationales}
    for option in options:
        if option.confidence_reference not in score_ids:
            msg = (
                f"broken references: option {option.option_id!r} confidence_reference "
                f"{option.confidence_reference!r} missing"
            )
            raise RecommendationError(msg)
        for rid in option.supporting_rationale_refs:
            if rid not in rationale_ids:
                msg = (
                    f"broken rationale references: option {option.option_id!r} "
                    f"references missing rationale {rid!r}"
                )
                raise RecommendationError(msg)


def _validate_conflict_links(
    conflicts: tuple[RecommendationConflict, ...],
    options: tuple[RecommendationOption, ...],
) -> None:
    option_ids = {o.option_id for o in options}
    for conflict in conflicts:
        for oid in conflict.option_refs:
            if oid not in option_ids:
                msg = (
                    f"broken conflict references: conflict {conflict.conflict_id!r} "
                    f"references missing option {oid!r}"
                )
                raise RecommendationError(msg)


def _known_report_citations(
    *,
    decision_refs: tuple[DecisionReference, ...],
    comparison_refs: tuple[ComparisonReference, ...],
    portfolio_ref: PortfolioReference | None,
    risk_refs: tuple[RiskReference, ...],
    research_refs: tuple[ResearchReference, ...],
    quantitative_risk_refs: tuple[QuantitativeRiskReference, ...],
) -> frozenset[str]:
    keys: set[str] = set()
    for ref in decision_refs:
        keys.add(ref.citation)
    for ref in comparison_refs:
        keys.add(ref.citation)
    if portfolio_ref is not None:
        keys.add(portfolio_ref.citation)
    for ref in risk_refs:
        keys.add(ref.citation)
    for ref in research_refs:
        keys.add(ref.citation)
    for ref in quantitative_risk_refs:
        keys.add(ref.citation)
    return frozenset(keys)


def _validate_report_citations(
    options: tuple[RecommendationOption, ...],
    rationales: tuple[RecommendationRationale, ...],
    conflicts: tuple[RecommendationConflict, ...],
    known: frozenset[str],
) -> None:
    for option in options:
        for key in option.supporting_report_refs:
            if key not in known:
                msg = (
                    f"broken report references: option {option.option_id!r} "
                    f"references unknown citation {key!r}"
                )
                raise RecommendationError(msg)
    for rationale in rationales:
        for key in rationale.supporting_report_refs:
            if key not in known:
                msg = (
                    f"broken report references: rationale {rationale.rationale_id!r} "
                    f"references unknown citation {key!r}"
                )
                raise RecommendationError(msg)
    for conflict in conflicts:
        for key in conflict.report_refs:
            if key not in known:
                msg = (
                    f"broken report references: conflict {conflict.conflict_id!r} "
                    f"references unknown citation {key!r}"
                )
                raise RecommendationError(msg)
