"""Portfolio domain models — structure only (C4.1).

Immutable aggregate and value objects. No assembly, evaluation, or calculations.
"""

from __future__ import annotations

from dataclasses import dataclass

from core.exceptions import ValidationError
from industry import EvidenceBundleReference

from portfolio.enums import (
    PortfolioChangeType,
    PortfolioConstraintKind,
    PortfolioMonitoringStatus,
    PortfolioType,
)
from portfolio.exceptions import PortfolioError
from portfolio.refs import (
    ComparisonReportReference,
    DecisionPackReference,
    _normalize_id,
)

__all__ = [
    "CoverageSummary",
    "Portfolio",
    "PortfolioAllocation",
    "PortfolioChange",
    "PortfolioCitationSummary",
    "PortfolioConstraint",
    "PortfolioDescriptor",
    "PortfolioHolding",
    "PortfolioIdentity",
    "PortfolioMonitoringSummary",
    "PortfolioObservation",
    "PortfolioReport",
    "PortfolioSnapshot",
    "PortfolioSummary",
    "PortfolioTimeline",
]

_FORBIDDEN_CLAIM_WORDS = frozenset(
    {"better", "best", "winner", "score", "rank", "ranking", "league"}
)


def _reject_claim_language(text: str, *, field: str) -> str:
    cleaned = text.strip()
    if not cleaned:
        msg = f"{field} must not be empty"
        raise ValidationError(msg)
    lowered = cleaned.lower()
    for word in _FORBIDDEN_CLAIM_WORDS:
        if word in lowered.split() or f" {word} " in f" {lowered} ":
            msg = f"{field} must not use forbidden term {word!r}: {cleaned!r}"
            raise ValidationError(msg)
    return cleaned


def _require_weight(value: float | None, *, field: str) -> float | None:
    if value is None:
        return None
    if value < 0.0 or value > 1.0:
        msg = f"{field} must be between 0 and 1 inclusive"
        raise ValidationError(msg)
    return value


@dataclass(frozen=True, slots=True)
class PortfolioIdentity:
    """Immutable portfolio metadata — identity facet only."""

    portfolio_id: str
    portfolio_name: str
    portfolio_type: PortfolioType = PortfolioType.MODEL
    created_at: str | None = None
    base_currency: str = "USD"
    benchmark_reference: str | None = None
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        portfolio_id = _normalize_id(self.portfolio_id, field="portfolio_id")
        name = self.portfolio_name.strip()
        if not name:
            msg = "portfolio_name must not be empty"
            raise ValidationError(msg)
        created_at = (
            None if self.created_at is None else self.created_at.strip() or None
        )
        currency = self.base_currency.strip().upper()
        if len(currency) != 3 or not currency.isalpha():
            msg = "base_currency must be a 3-letter ISO currency code"
            raise ValidationError(msg)
        benchmark = (
            None
            if self.benchmark_reference is None
            else self.benchmark_reference.strip() or None
        )
        notes = tuple(n.strip() for n in self.notes if n.strip())
        object.__setattr__(self, "portfolio_id", portfolio_id)
        object.__setattr__(self, "portfolio_name", name)
        object.__setattr__(self, "created_at", created_at)
        object.__setattr__(self, "base_currency", currency)
        object.__setattr__(self, "benchmark_reference", benchmark)
        object.__setattr__(self, "notes", notes)


@dataclass(frozen=True, slots=True)
class PortfolioHolding:
    """One holding — cites DecisionPack; never embeds pack/bundle payloads."""

    instrument_symbol: str
    decision_pack_ref: DecisionPackReference
    weight: float | None = None
    units: float | None = None
    evidence_bundle_ref: EvidenceBundleReference | None = None
    comparison_report_ref: ComparisonReportReference | None = None
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        symbol = self.instrument_symbol.strip().upper()
        if not symbol:
            msg = "instrument_symbol must not be empty"
            raise ValidationError(msg)
        if self.decision_pack_ref is None:
            msg = "decision_pack_ref is required (DecisionPack citation)"
            raise ValidationError(msg)
        if self.decision_pack_ref.instrument_symbol != symbol:
            msg = (
                f"decision_pack_ref.instrument_symbol "
                f"{self.decision_pack_ref.instrument_symbol!r} must match "
                f"holding {symbol!r}"
            )
            raise ValidationError(msg)
        weight = _require_weight(self.weight, field="weight")
        if self.units is not None and self.units < 0.0:
            msg = "units must be >= 0"
            raise ValidationError(msg)
        if self.evidence_bundle_ref is not None:
            if self.evidence_bundle_ref.instrument_key != symbol:
                msg = (
                    f"evidence_bundle_ref.instrument_key "
                    f"{self.evidence_bundle_ref.instrument_key!r} must match "
                    f"holding {symbol!r}"
                )
                raise ValidationError(msg)
        if self.comparison_report_ref is not None:
            included = self.comparison_report_ref.included_symbols
            if included and symbol not in included:
                msg = (
                    f"comparison_report_ref.included_symbols must include "
                    f"holding {symbol!r} when provided"
                )
                raise ValidationError(msg)
        notes = tuple(n.strip() for n in self.notes if n.strip())
        object.__setattr__(self, "instrument_symbol", symbol)
        object.__setattr__(self, "weight", weight)
        object.__setattr__(self, "notes", notes)


@dataclass(frozen=True, slots=True)
class PortfolioConstraint:
    """Policy constraint descriptor — no evaluation logic."""

    id: str
    kind: PortfolioConstraintKind
    target: str
    limit: float
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        constraint_id = _normalize_id(self.id, field="id")
        target = self.target.strip().lower()
        if not target:
            msg = "constraint target must not be empty"
            raise ValidationError(msg)
        if self.kind is PortfolioConstraintKind.MAX_HOLDINGS:
            if self.limit < 0 or self.limit != int(self.limit):
                msg = "MAX_HOLDINGS limit must be a non-negative integer value"
                raise ValidationError(msg)
        else:
            if self.limit < 0.0 or self.limit > 1.0:
                msg = "constraint limit must be between 0 and 1 inclusive"
                raise ValidationError(msg)
        notes = tuple(n.strip() for n in self.notes if n.strip())
        object.__setattr__(self, "id", constraint_id)
        object.__setattr__(self, "target", target)
        object.__setattr__(self, "notes", notes)


@dataclass(frozen=True, slots=True)
class PortfolioAllocation:
    """Descriptive allocation information only — no optimization."""

    by_instrument: tuple[tuple[str, float], ...] = ()
    by_sector: tuple[tuple[str, float], ...] = ()
    cash_weight: float | None = None
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        instruments = _unique_weight_pairs(
            self.by_instrument, field="by_instrument"
        )
        sectors = _unique_weight_pairs(self.by_sector, field="by_sector")
        cash = _require_weight(self.cash_weight, field="cash_weight")
        notes = tuple(n.strip() for n in self.notes if n.strip())
        object.__setattr__(self, "by_instrument", instruments)
        object.__setattr__(self, "by_sector", sectors)
        object.__setattr__(self, "cash_weight", cash)
        object.__setattr__(self, "notes", notes)


@dataclass(frozen=True, slots=True)
class PortfolioSnapshot:
    """Immutable point-in-time portfolio state."""

    snapshot_id: str
    portfolio_id: str
    as_of: str
    holdings: tuple[PortfolioHolding, ...]
    cash_weight: float | None = None
    allocation: PortfolioAllocation | None = None
    comparison_report_ref: ComparisonReportReference | None = None
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        snapshot_id = _normalize_id(self.snapshot_id, field="snapshot_id")
        portfolio_id = _normalize_id(self.portfolio_id, field="portfolio_id")
        as_of = self.as_of.strip()
        if not as_of:
            msg = "as_of must not be empty"
            raise ValidationError(msg)
        holdings = _unique_holdings(self.holdings)
        cash = _require_weight(self.cash_weight, field="cash_weight")
        notes = tuple(n.strip() for n in self.notes if n.strip())
        object.__setattr__(self, "snapshot_id", snapshot_id)
        object.__setattr__(self, "portfolio_id", portfolio_id)
        object.__setattr__(self, "as_of", as_of)
        object.__setattr__(self, "holdings", holdings)
        object.__setattr__(self, "cash_weight", cash)
        object.__setattr__(self, "notes", notes)


@dataclass(frozen=True, slots=True)
class PortfolioObservation:
    """Qualitative portfolio observation — no scores or rankings."""

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
class PortfolioDescriptor:
    """Human-readable qualitative label — descriptive only; never a score."""

    dimension: str
    label: str
    code: str
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        dimension = self.dimension.strip().lower().replace(" ", "_")
        if not dimension:
            msg = "descriptor dimension must not be empty"
            raise ValidationError(msg)
        label = _reject_claim_language(self.label, field="label")
        code = self.code.strip().lower().replace(" ", "_")
        if not code:
            msg = "descriptor code must not be empty"
            raise ValidationError(msg)
        notes = tuple(
            _reject_claim_language(n, field="notes") for n in self.notes if n.strip()
        )
        object.__setattr__(self, "dimension", dimension)
        object.__setattr__(self, "label", label)
        object.__setattr__(self, "code", code)
        object.__setattr__(self, "notes", notes)


@dataclass(frozen=True, slots=True)
class PortfolioSummary:
    """High-level qualitative summary — descriptive only."""

    holding_count: int
    cash_weight: float | None = None
    coverage_notes: tuple[str, ...] = ()
    concentration_notes: tuple[str, ...] = ()
    limitation_notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.holding_count < 0:
            msg = "holding_count must be >= 0"
            raise ValidationError(msg)
        cash = _require_weight(self.cash_weight, field="cash_weight")
        coverage = tuple(
            _reject_claim_language(n, field="coverage_notes")
            for n in self.coverage_notes
            if n.strip()
        )
        concentration = tuple(
            _reject_claim_language(n, field="concentration_notes")
            for n in self.concentration_notes
            if n.strip()
        )
        limitations = tuple(
            _reject_claim_language(n, field="limitation_notes")
            for n in self.limitation_notes
            if n.strip()
        )
        object.__setattr__(self, "cash_weight", cash)
        object.__setattr__(self, "coverage_notes", coverage)
        object.__setattr__(self, "concentration_notes", concentration)
        object.__setattr__(self, "limitation_notes", limitations)


@dataclass(frozen=True, slots=True)
class CoverageSummary:
    """Citation coverage counts — descriptive completeness, not quality."""

    holding_count: int
    decision_pack_count: int
    evidence_bundle_count: int
    comparison_report_count: int
    holdings_with_evidence: int
    holdings_with_comparison: int
    missing_evidence_symbols: tuple[str, ...] = ()
    missing_comparison_symbols: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.holding_count < 0:
            msg = "holding_count must be >= 0"
            raise ValidationError(msg)
        object.__setattr__(
            self, "missing_evidence_symbols", tuple(self.missing_evidence_symbols)
        )
        object.__setattr__(
            self,
            "missing_comparison_symbols",
            tuple(self.missing_comparison_symbols),
        )
        object.__setattr__(self, "notes", tuple(n for n in self.notes if n.strip()))


@dataclass(frozen=True, slots=True)
class PortfolioCitationSummary:
    """Aggregated citation surface — references only, never payloads."""

    portfolio_id: str
    holding_count: int
    decision_citation_count: int
    evidence_citation_count: int
    comparison_citation_count: int
    bundle_versions: tuple[tuple[str, str, str], ...] = ()
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        portfolio_id = _normalize_id(self.portfolio_id, field="portfolio_id")
        if self.holding_count < 0:
            msg = "holding_count must be >= 0"
            raise ValidationError(msg)
        versions: list[tuple[str, str, str]] = []
        seen: set[tuple[str, str, str]] = set()
        for methodology_id, version, instrument in self.bundle_versions:
            mid = methodology_id.strip().lower()
            ver = version.strip()
            sym = instrument.strip().upper()
            if not mid or not ver or not sym:
                msg = "bundle_versions entries must be non-empty"
                raise ValidationError(msg)
            key = (mid, ver, sym)
            if key in seen:
                msg = f"duplicate citation id in bundle_versions: {key!r}"
                raise ValidationError(msg)
            seen.add(key)
            versions.append(key)
        notes = tuple(n.strip() for n in self.notes if n.strip())
        object.__setattr__(self, "portfolio_id", portfolio_id)
        object.__setattr__(self, "bundle_versions", tuple(versions))
        object.__setattr__(self, "notes", notes)


@dataclass(frozen=True, slots=True)
class PortfolioChange:
    """Descriptive record of a portfolio state difference — never a trade signal."""

    change_type: PortfolioChangeType
    description: str
    subjects: tuple[str, ...] = ()
    from_snapshot_id: str | None = None
    to_snapshot_id: str | None = None

    def __post_init__(self) -> None:
        description = _reject_claim_language(self.description, field="description")
        subjects = tuple(s.strip().upper() for s in self.subjects if s.strip())
        from_id = (
            None
            if self.from_snapshot_id is None
            else _normalize_id(self.from_snapshot_id, field="from_snapshot_id")
        )
        to_id = (
            None
            if self.to_snapshot_id is None
            else _normalize_id(self.to_snapshot_id, field="to_snapshot_id")
        )
        object.__setattr__(self, "description", description)
        object.__setattr__(self, "subjects", subjects)
        object.__setattr__(self, "from_snapshot_id", from_id)
        object.__setattr__(self, "to_snapshot_id", to_id)


@dataclass(frozen=True, slots=True)
class PortfolioTimeline:
    """Ordered snapshot history — descriptive chronology only."""

    portfolio_id: str
    entries: tuple[PortfolioSnapshot, ...] = ()
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        portfolio_id = _normalize_id(self.portfolio_id, field="portfolio_id")
        entries = tuple(self.entries)
        seen: set[str] = set()
        prior_as_of: str | None = None
        for snap in entries:
            if snap.portfolio_id != portfolio_id:
                msg = (
                    f"invalid ownership: timeline entry {snap.snapshot_id!r} "
                    f"belongs to {snap.portfolio_id!r}"
                )
                raise PortfolioError(msg)
            if snap.snapshot_id in seen:
                msg = f"duplicate snapshot ids: {snap.snapshot_id!r}"
                raise PortfolioError(msg)
            seen.add(snap.snapshot_id)
            if prior_as_of is not None and snap.as_of < prior_as_of:
                msg = (
                    f"non-sequential timeline: {snap.snapshot_id!r} as_of "
                    f"{snap.as_of!r} precedes prior {prior_as_of!r}"
                )
                raise PortfolioError(msg)
            prior_as_of = snap.as_of
        notes = tuple(n.strip() for n in self.notes if n.strip())
        object.__setattr__(self, "portfolio_id", portfolio_id)
        object.__setattr__(self, "entries", entries)
        object.__setattr__(self, "notes", notes)


@dataclass(frozen=True, slots=True)
class PortfolioMonitoringSummary:
    """Monitoring summary — historical counts only, not investment quality."""

    portfolio_id: str
    snapshot_count: int
    change_count: int
    status: PortfolioMonitoringStatus
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        portfolio_id = _normalize_id(self.portfolio_id, field="portfolio_id")
        if self.snapshot_count < 0 or self.change_count < 0:
            msg = "snapshot_count and change_count must be >= 0"
            raise ValidationError(msg)
        notes = tuple(n.strip() for n in self.notes if n.strip())
        object.__setattr__(self, "portfolio_id", portfolio_id)
        object.__setattr__(self, "notes", notes)


@dataclass(frozen=True, slots=True)
class PortfolioReport:
    """Presentation object — citations and qualitative content only."""

    portfolio_id: str
    summary: PortfolioSummary
    observations: tuple[PortfolioObservation, ...] = ()
    snapshot_id: str | None = None
    decision_pack_refs: tuple[DecisionPackReference, ...] = ()
    evidence_bundle_refs: tuple[EvidenceBundleReference, ...] = ()
    comparison_report_refs: tuple[ComparisonReportReference, ...] = ()
    limitations: tuple[str, ...] = ()
    citation_summary: PortfolioCitationSummary | None = None
    coverage_summary: CoverageSummary | None = None
    citation_gaps: tuple[str, ...] = ()
    monitoring_summary: PortfolioMonitoringSummary | None = None
    timeline: PortfolioTimeline | None = None
    recent_changes: tuple[PortfolioChange, ...] = ()
    monitoring_status: PortfolioMonitoringStatus | None = None

    def __post_init__(self) -> None:
        portfolio_id = _normalize_id(self.portfolio_id, field="portfolio_id")
        snapshot_id = (
            None
            if self.snapshot_id is None
            else _normalize_id(self.snapshot_id, field="snapshot_id")
        )
        pack_refs = tuple(self.decision_pack_refs)
        seen_syms: set[str] = set()
        for ref in pack_refs:
            if ref.instrument_symbol in seen_syms:
                msg = (
                    f"duplicate DecisionPack reference for "
                    f"{ref.instrument_symbol!r} in PortfolioReport"
                )
                raise ValidationError(msg)
            seen_syms.add(ref.instrument_symbol)
        evidence_refs = tuple(self.evidence_bundle_refs)
        seen_ev: set[tuple[str, str]] = set()
        for ref in evidence_refs:
            key = (ref.instrument_key, ref.digest)
            if key in seen_ev:
                msg = (
                    f"duplicate EvidenceBundle reference for "
                    f"{ref.instrument_key!r}"
                )
                raise ValidationError(msg)
            seen_ev.add(key)
        limitations = tuple(
            _reject_claim_language(n, field="limitations")
            for n in self.limitations
            if n.strip()
        )
        gaps = tuple(g.strip() for g in self.citation_gaps if g.strip())
        object.__setattr__(self, "portfolio_id", portfolio_id)
        object.__setattr__(self, "snapshot_id", snapshot_id)
        object.__setattr__(self, "decision_pack_refs", pack_refs)
        object.__setattr__(self, "evidence_bundle_refs", evidence_refs)
        object.__setattr__(
            self, "comparison_report_refs", tuple(self.comparison_report_refs)
        )
        object.__setattr__(self, "observations", tuple(self.observations))
        object.__setattr__(self, "limitations", limitations)
        object.__setattr__(self, "citation_gaps", gaps)
        object.__setattr__(self, "recent_changes", tuple(self.recent_changes))


@dataclass(frozen=True, slots=True)
class Portfolio:
    """Aggregate root — identity, holdings, constraints, snapshots only."""

    identity: PortfolioIdentity
    holdings: tuple[PortfolioHolding, ...] = ()
    constraints: tuple[PortfolioConstraint, ...] = ()
    snapshots: tuple[PortfolioSnapshot, ...] = ()
    cash_weight: float | None = None

    def __post_init__(self) -> None:
        holdings = _unique_holdings(self.holdings)
        constraints = _unique_constraints(self.constraints)
        snapshots = tuple(self.snapshots)
        seen_snap: set[str] = set()
        for snap in snapshots:
            if snap.snapshot_id in seen_snap:
                msg = f"duplicate snapshot id {snap.snapshot_id!r}"
                raise PortfolioError(msg)
            seen_snap.add(snap.snapshot_id)
            if snap.portfolio_id != self.identity.portfolio_id:
                msg = (
                    f"snapshot {snap.snapshot_id!r} portfolio_id "
                    f"{snap.portfolio_id!r} does not match aggregate "
                    f"{self.identity.portfolio_id!r} (cyclic/foreign ownership)"
                )
                raise PortfolioError(msg)
        cash = _require_weight(self.cash_weight, field="cash_weight")
        object.__setattr__(self, "holdings", holdings)
        object.__setattr__(self, "constraints", constraints)
        object.__setattr__(self, "snapshots", snapshots)
        object.__setattr__(self, "cash_weight", cash)

    @property
    def portfolio_id(self) -> str:
        return self.identity.portfolio_id


def _unique_holdings(
    holdings: tuple[PortfolioHolding, ...],
) -> tuple[PortfolioHolding, ...]:
    items = tuple(holdings)
    seen: set[str] = set()
    for holding in items:
        if holding.instrument_symbol in seen:
            msg = f"duplicate holding for {holding.instrument_symbol!r}"
            raise PortfolioError(msg)
        seen.add(holding.instrument_symbol)
    return items


def _unique_constraints(
    constraints: tuple[PortfolioConstraint, ...],
) -> tuple[PortfolioConstraint, ...]:
    items = tuple(constraints)
    seen: set[str] = set()
    for constraint in items:
        if constraint.id in seen:
            msg = f"duplicate constraint id {constraint.id!r}"
            raise PortfolioError(msg)
        seen.add(constraint.id)
    return items


def _unique_weight_pairs(
    pairs: tuple[tuple[str, float], ...], *, field: str
) -> tuple[tuple[str, float], ...]:
    cleaned: list[tuple[str, float]] = []
    seen: set[str] = set()
    for raw_key, weight in pairs:
        key = raw_key.strip().lower()
        if not key:
            msg = f"{field} keys must not be empty"
            raise ValidationError(msg)
        if key in seen:
            msg = f"duplicate {field} key {key!r}"
            raise ValidationError(msg)
        if weight < 0.0 or weight > 1.0:
            msg = f"{field} weights must be between 0 and 1 inclusive"
            raise ValidationError(msg)
        seen.add(key)
        cleaned.append((key, weight))
    return tuple(cleaned)
