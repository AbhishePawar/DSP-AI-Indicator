"""Immutable domain models for qualitative comparison."""

from __future__ import annotations

from dataclasses import dataclass

from core.exceptions import ValidationError
from decision_intelligence import DecisionPack
from industry import (
    ComparisonDimension,
    EligibilityOptions,
    EvidenceBundle,
    GroupEligibilityStatus,
)

from comparison.enums import ComparisonStatus

__all__ = [
    "ComparisonDimensionResult",
    "ComparisonEvidenceSummary",
    "ComparisonExplanation",
    "ComparisonLimitation",
    "ComparisonObservation",
    "ComparisonReport",
    "ComparisonRequest",
    "ComparisonResult",
]

_FORBIDDEN_WORDS = frozenset(
    {"better", "best", "winner", "score", "rank", "ranking", "league"}
)


@dataclass(frozen=True, slots=True)
class ComparisonObservation:
    """Qualitative note — explains differences; never declares a winner."""

    code: str
    text: str
    dimension: ComparisonDimension | None = None
    subjects: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        code = self.code.strip().lower().replace(" ", "_")
        text = self.text.strip()
        if not code:
            msg = "observation code must not be empty"
            raise ValidationError(msg)
        if not text:
            msg = "observation text must not be empty"
            raise ValidationError(msg)
        lowered = text.lower()
        for word in _FORBIDDEN_WORDS:
            if word in lowered.split() or f" {word} " in f" {lowered} ":
                msg = f"observation text must not use forbidden term {word!r}: {text!r}"
                raise ValidationError(msg)
        subjects = tuple(s.strip().upper() for s in self.subjects if s.strip())
        refs = tuple(r.strip() for r in self.evidence_refs if r.strip())
        object.__setattr__(self, "code", code)
        object.__setattr__(self, "text", text)
        object.__setattr__(self, "subjects", subjects)
        object.__setattr__(self, "evidence_refs", refs)


@dataclass(frozen=True, slots=True)
class ComparisonLimitation:
    """Explicit uncertainty or gap — comparison never implies certainty."""

    code: str
    message: str
    subjects: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        code = self.code.strip().lower().replace(" ", "_")
        message = self.message.strip()
        if not code or not message:
            msg = "limitation code and message must not be empty"
            raise ValidationError(msg)
        subjects = tuple(s.strip().upper() for s in self.subjects if s.strip())
        object.__setattr__(self, "code", code)
        object.__setattr__(self, "message", message)
        object.__setattr__(self, "subjects", subjects)


@dataclass(frozen=True, slots=True)
class ComparisonDimensionResult:
    """Observations for one methodology-declared dimension (unweighted)."""

    dimension: ComparisonDimension
    observations: tuple[ComparisonObservation, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "observations", tuple(self.observations))


@dataclass(frozen=True, slots=True)
class ComparisonExplanation:
    """Short narrative of what the comparison did and did not conclude."""

    summary: str
    detail: str | None = None

    def __post_init__(self) -> None:
        summary = self.summary.strip()
        if not summary:
            msg = "explanation summary must not be empty"
            raise ValidationError(msg)
        detail = None if self.detail is None else self.detail.strip() or None
        object.__setattr__(self, "summary", summary)
        object.__setattr__(self, "detail", detail)


@dataclass(frozen=True, slots=True)
class ComparisonEvidenceSummary:
    """Reference-level evidence coverage — never embeds bundle internals."""

    attached: bool
    availability: str
    bundle_count: int = 0
    covered_symbols: tuple[str, ...] = ()
    missing_symbols: tuple[str, ...] = ()
    methodology_id: str | None = None
    bundle_versions: tuple[str, ...] = ()
    bundle_statuses: tuple[str, ...] = ()
    digests: tuple[str, ...] = ()

    @classmethod
    def not_supplied(cls) -> ComparisonEvidenceSummary:
        return cls(attached=False, availability="not_supplied")


@dataclass(frozen=True, slots=True)
class ComparisonRequest:
    """Input for a qualitative comparison run."""

    packs: tuple[DecisionPack, ...]
    eligibility_options: EligibilityOptions = EligibilityOptions()
    evidence_bundles: tuple[EvidenceBundle, ...] = ()

    def __post_init__(self) -> None:
        packs = tuple(self.packs)
        if len(packs) < 2:
            msg = "comparison requires at least two DecisionPacks"
            raise ValidationError(msg)
        symbols = [p.recommendation.instrument.symbol for p in packs]
        if len(set(symbols)) != len(symbols):
            msg = "comparison packs must have distinct instrument symbols"
            raise ValidationError(msg)
        object.__setattr__(self, "packs", packs)
        object.__setattr__(self, "evidence_bundles", tuple(self.evidence_bundles))


@dataclass(frozen=True, slots=True)
class ComparisonReport:
    """Investor-facing qualitative comparison report — no overall score."""

    status: ComparisonStatus
    scope_notes: tuple[str, ...]
    methodology_id: str | None
    methodology_version: str | None
    industry_id: str | None
    included_symbols: tuple[str, ...]
    excluded_symbols: tuple[str, ...]
    exclusion_reasons: tuple[str, ...]
    eligibility_group_status: GroupEligibilityStatus | None
    dimension_results: tuple[ComparisonDimensionResult, ...]
    shared_observations: tuple[ComparisonObservation, ...]
    pair_observations: tuple[ComparisonObservation, ...]
    decision_context: tuple[ComparisonObservation, ...]
    valuation_context: tuple[ComparisonObservation, ...]
    robustness_context: tuple[ComparisonObservation, ...]
    limitations: tuple[ComparisonLimitation, ...]
    research_priorities: tuple[str, ...]
    explanation: ComparisonExplanation
    # C3.7 — evidence citation surface (defaults preserve C2.5 constructors)
    evidence_summary: ComparisonEvidenceSummary | None = None
    evidence_observations: tuple[ComparisonObservation, ...] = ()
    evidence_limitations: tuple[ComparisonLimitation, ...] = ()


@dataclass(frozen=True, slots=True)
class ComparisonResult:
    """Engine output: status + report (report always present, including refusals)."""

    status: ComparisonStatus
    report: ComparisonReport

    @property
    def refused(self) -> bool:
        return self.status is ComparisonStatus.REFUSED
