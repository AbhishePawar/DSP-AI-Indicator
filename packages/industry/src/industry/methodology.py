"""Industry Methodology domain models — policy ownership only.

No comparison, ranking, scoring, or metric calculations.
"""

from __future__ import annotations

from dataclasses import dataclass

from core.exceptions import ValidationError

from industry.characteristics import (
    CharacteristicDefaults,
    InvestmentCharacteristics,
)
from industry.enums import (
    ComparisonDimension,
    ComparisonDimensionHint,
    MergeSource,
    MetricImportance,
    MethodologyLifecycle,
    PeerUse,
    ValuationPhilosophyHint,
)
from industry.models import _normalize_id
from industry.semver import require_semver

__all__ = [
    "AssembledMethodology",
    "IndustryMethodology",
    "MetricApplicability",
    "PeerEligibilityPolicyRef",
    "SYSTEM_DEFAULT_DIMENSIONS",
    "SYSTEM_DEFAULT_VALUATION",
    "ValuationProfile",
    "assemble_methodology",
    "dimension_from_hint",
    "valuation_from_characteristic_defaults",
]

_HINT_TO_DIMENSION: dict[ComparisonDimensionHint, ComparisonDimension] = {
    ComparisonDimensionHint.QUALITY: ComparisonDimension.QUALITY,
    ComparisonDimensionHint.GROWTH: ComparisonDimension.GROWTH,
    ComparisonDimensionHint.VALUATION: ComparisonDimension.VALUATION,
    ComparisonDimensionHint.PREDICTABILITY: ComparisonDimension.PREDICTABILITY,
    ComparisonDimensionHint.CAPITAL_ALLOCATION: ComparisonDimension.CAPITAL_ALLOCATION,
    ComparisonDimensionHint.FINANCIAL_STRENGTH: ComparisonDimension.FINANCIAL_STRENGTH,
    ComparisonDimensionHint.EFFICIENCY: ComparisonDimension.EFFICIENCY,
    ComparisonDimensionHint.RISK: ComparisonDimension.RISK,
}


def _normalize_method_refs(methods: tuple[str, ...]) -> tuple[str, ...]:
    cleaned: list[str] = []
    seen: set[str] = set()
    for method in methods:
        ref = method.strip().lower()
        if not ref or ref in seen:
            continue
        seen.add(ref)
        cleaned.append(ref)
    return tuple(cleaned)


@dataclass(frozen=True, slots=True)
class ValuationProfile:
    """Valuation method policy — does not execute or modify Valuation Engine."""

    preferred: tuple[str, ...] = ()
    acceptable: tuple[str, ...] = ()
    unsupported: tuple[str, ...] = ()
    interpretation_notes: tuple[str, ...] = ()
    requires_engine_extension: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        preferred = _normalize_method_refs(self.preferred)
        acceptable = _normalize_method_refs(self.acceptable)
        unsupported = _normalize_method_refs(self.unsupported)
        extensions = _normalize_method_refs(self.requires_engine_extension)
        notes = tuple(n.strip() for n in self.interpretation_notes if n.strip())
        overlap = set(preferred) & set(unsupported)
        if overlap:
            msg = (
                f"valuation methods cannot be both preferred and unsupported: "
                f"{sorted(overlap)}"
            )
            raise ValidationError(msg)
        overlap_acc = set(acceptable) & set(unsupported)
        if overlap_acc:
            msg = (
                f"valuation methods cannot be both acceptable and unsupported: "
                f"{sorted(overlap_acc)}"
            )
            raise ValidationError(msg)
        object.__setattr__(self, "preferred", preferred)
        object.__setattr__(self, "acceptable", acceptable)
        object.__setattr__(self, "unsupported", unsupported)
        object.__setattr__(self, "requires_engine_extension", extensions)
        object.__setattr__(self, "interpretation_notes", notes)


SYSTEM_DEFAULT_VALUATION = ValuationProfile(
    preferred=(),
    acceptable=("dcf", "owner_earnings", "earnings_multiple"),
    unsupported=(),
    interpretation_notes=(
        "System default valuation policy — no industry-specific guidance.",
    ),
)

SYSTEM_DEFAULT_DIMENSIONS: tuple[ComparisonDimension, ...] = (
    ComparisonDimension.QUALITY,
    ComparisonDimension.VALUATION,
    ComparisonDimension.FINANCIAL_STRENGTH,
    ComparisonDimension.DECISION_ROBUSTNESS,
)


@dataclass(frozen=True, slots=True)
class MetricApplicability:
    """Contract placeholder for future industry metric ownership.

    Does not define calculations, formulas, or metric registries.
    """

    metric_id: str
    importance: MetricImportance = MetricImportance.CONTEXTUAL
    peer_use: PeerUse = PeerUse.CAUTION
    interpretation_notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        metric_id = _normalize_id(self.metric_id, field="metric_id")
        notes = tuple(n.strip() for n in self.interpretation_notes if n.strip())
        object.__setattr__(self, "metric_id", metric_id)
        object.__setattr__(self, "interpretation_notes", notes)


@dataclass(frozen=True, slots=True)
class PeerEligibilityPolicyRef:
    """Reference to a future PeerEligibility policy — not the policy itself."""

    policy_id: str
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        policy_id = _normalize_id(self.policy_id, field="policy_id")
        notes = tuple(n.strip() for n in self.notes if n.strip())
        object.__setattr__(self, "policy_id", policy_id)
        object.__setattr__(self, "notes", notes)


@dataclass(frozen=True, slots=True)
class IndustryMethodology:
    """Versioned investment policy bound to one IndustryIdentity.

    Authoritative for valuation policy, dimensions, metric applicability
    placeholders, and peer-policy references. Characteristics supply defaults
    only via assemble_methodology().
    """

    id: str
    industry_id: str
    version: str
    status: MethodologyLifecycle = MethodologyLifecycle.ACTIVE
    name: str | None = None
    description: str | None = None
    characteristic_ids: tuple[str, ...] = ()
    valuation: ValuationProfile | None = None
    dimensions: tuple[ComparisonDimension, ...] | None = None
    metrics: tuple[MetricApplicability, ...] = ()
    peer_policy: PeerEligibilityPolicyRef | None = None
    interpretation_notes: tuple[str, ...] = ()
    changelog: str | None = None

    def __post_init__(self) -> None:
        methodology_id = _normalize_id(self.id, field="id")
        industry_id = _normalize_id(self.industry_id, field="industry_id")
        version = require_semver(self.version, field="version")
        name = None if self.name is None else self.name.strip() or None
        description = (
            None if self.description is None else self.description.strip() or None
        )
        char_ids = tuple(
            _normalize_id(c, field="characteristic_ids")
            for c in self.characteristic_ids
        )
        seen: set[str] = set()
        unique_chars: list[str] = []
        for cid in char_ids:
            if cid not in seen:
                seen.add(cid)
                unique_chars.append(cid)
        notes = tuple(n.strip() for n in self.interpretation_notes if n.strip())
        changelog = (
            None if self.changelog is None else self.changelog.strip() or None
        )
        dimensions = (
            None if self.dimensions is None else tuple(self.dimensions)
        )
        object.__setattr__(self, "id", methodology_id)
        object.__setattr__(self, "industry_id", industry_id)
        object.__setattr__(self, "version", version)
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "description", description)
        object.__setattr__(self, "characteristic_ids", tuple(unique_chars))
        object.__setattr__(self, "dimensions", dimensions)
        object.__setattr__(self, "metrics", tuple(self.metrics))
        object.__setattr__(self, "interpretation_notes", notes)
        object.__setattr__(self, "changelog", changelog)

    @property
    def registry_key(self) -> tuple[str, str]:
        return (self.id, self.version)


@dataclass(frozen=True, slots=True)
class AssembledMethodology:
    """Resolved policy with explicit field provenance (never silent)."""

    methodology_id: str
    industry_id: str
    version: str
    valuation: ValuationProfile
    valuation_source: MergeSource
    dimensions: tuple[ComparisonDimension, ...]
    dimensions_source: MergeSource
    metrics: tuple[MetricApplicability, ...]
    peer_policy: PeerEligibilityPolicyRef | None
    characteristic_ids: tuple[str, ...]
    interpretation_notes: tuple[str, ...]
    merge_trace: tuple[str, ...]


def dimension_from_hint(hint: ComparisonDimensionHint) -> ComparisonDimension:
    try:
        return _HINT_TO_DIMENSION[hint]
    except KeyError as exc:
        msg = f"unmapped comparison dimension hint: {hint!r}"
        raise ValidationError(msg) from exc


def valuation_from_characteristic_defaults(
    defaults: CharacteristicDefaults,
) -> ValuationProfile:
    notes: list[str] = list(defaults.investment_philosophy_notes)
    if defaults.valuation_philosophy is not None:
        notes.insert(
            0,
            _philosophy_note(defaults.valuation_philosophy),
        )
    return ValuationProfile(
        preferred=defaults.preferred_method_hints,
        acceptable=(),
        unsupported=(),
        interpretation_notes=tuple(notes),
    )


def assemble_methodology(
    methodology: IndustryMethodology,
    characteristics: tuple[InvestmentCharacteristics, ...] = (),
) -> AssembledMethodology:
    """Deterministic merge: methodology > characteristics > system.

    Provenance is recorded per resolved field. Metrics and peer_policy never
    come from characteristics.
    """
    expected = set(methodology.characteristic_ids)
    provided = {c.id for c in characteristics}
    if expected - provided:
        missing = sorted(expected - provided)
        msg = (
            f"missing characteristics for methodology {methodology.id!r}: "
            f"{missing}"
        )
        raise ValidationError(msg)
    # Apply characteristics in methodology declaration order
    ordered = tuple(
        next(c for c in characteristics if c.id == cid)
        for cid in methodology.characteristic_ids
    )

    valuation, valuation_source, val_trace = _resolve_valuation(
        methodology, ordered
    )
    dimensions, dimensions_source, dim_trace = _resolve_dimensions(
        methodology, ordered
    )

    notes = list(methodology.interpretation_notes)
    for char in ordered:
        notes.extend(char.defaults.investment_philosophy_notes)

    trace = (
        f"assemble {methodology.id}@{methodology.version}",
        *val_trace,
        *dim_trace,
        "metrics: methodology-owned (never characteristics)",
        "peer_policy: methodology-owned (never characteristics)",
    )
    return AssembledMethodology(
        methodology_id=methodology.id,
        industry_id=methodology.industry_id,
        version=methodology.version,
        valuation=valuation,
        valuation_source=valuation_source,
        dimensions=dimensions,
        dimensions_source=dimensions_source,
        metrics=methodology.metrics,
        peer_policy=methodology.peer_policy,
        characteristic_ids=methodology.characteristic_ids,
        interpretation_notes=tuple(dict.fromkeys(n for n in notes if n)),
        merge_trace=trace,
    )


def _resolve_valuation(
    methodology: IndustryMethodology,
    characteristics: tuple[InvestmentCharacteristics, ...],
) -> tuple[ValuationProfile, MergeSource, tuple[str, ...]]:
    if methodology.valuation is not None:
        return (
            methodology.valuation,
            MergeSource.METHODOLOGY,
            ("valuation: methodology override",),
        )
    # Later characteristics override earlier characteristic defaults
    profile: ValuationProfile | None = None
    source_id: str | None = None
    for char in characteristics:
        if (
            char.defaults.preferred_method_hints
            or char.defaults.investment_philosophy_notes
            or char.defaults.valuation_philosophy is not None
        ):
            profile = valuation_from_characteristic_defaults(char.defaults)
            source_id = char.id
    if profile is not None:
        return (
            profile,
            MergeSource.CHARACTERISTICS,
            (f"valuation: characteristics default from {source_id}",),
        )
    return (
        SYSTEM_DEFAULT_VALUATION,
        MergeSource.SYSTEM,
        ("valuation: system default",),
    )


def _resolve_dimensions(
    methodology: IndustryMethodology,
    characteristics: tuple[InvestmentCharacteristics, ...],
) -> tuple[tuple[ComparisonDimension, ...], MergeSource, tuple[str, ...]]:
    if methodology.dimensions is not None:
        return (
            methodology.dimensions,
            MergeSource.METHODOLOGY,
            ("dimensions: methodology override",),
        )
    dims: tuple[ComparisonDimension, ...] | None = None
    source_id: str | None = None
    for char in characteristics:
        if char.defaults.dimension_emphasis:
            dims = tuple(
                dimension_from_hint(h) for h in char.defaults.dimension_emphasis
            )
            source_id = char.id
    if dims is not None:
        return (
            dims,
            MergeSource.CHARACTERISTICS,
            (f"dimensions: characteristics default from {source_id}",),
        )
    return (
        SYSTEM_DEFAULT_DIMENSIONS,
        MergeSource.SYSTEM,
        ("dimensions: system default",),
    )


def _philosophy_note(philosophy: ValuationPhilosophyHint) -> str:
    return f"Characteristic valuation philosophy hint: {philosophy.value}."
