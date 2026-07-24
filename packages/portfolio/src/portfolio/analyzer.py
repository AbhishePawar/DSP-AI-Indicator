"""Portfolio Qualitative Analyzer — descriptive consumer only (C4.3).

Reads Portfolio + citations. Emits summaries, descriptors, and observations.
Never optimizes, scores, ranks, evaluates constraints mathematically,
computes risk, or recommends trades.
"""

from __future__ import annotations

from dataclasses import dataclass

from industry import EvidenceBundleReference

from portfolio.enums import PortfolioAnalysisStatus
from portfolio.exceptions import PortfolioError
from portfolio.models import (
    CoverageSummary,
    Portfolio,
    PortfolioDescriptor,
    PortfolioHolding,
    PortfolioObservation,
    PortfolioReport,
    PortfolioSnapshot,
    PortfolioSummary,
)
from portfolio.refs import ComparisonReportReference, DecisionPackReference

__all__ = [
    "PortfolioAnalysisContext",
    "PortfolioAnalysisResult",
    "PortfolioAnalyzer",
]

# Qualitative concentration heuristics (descriptive labels only — not risk metrics).
_HIGH_CONCENTRATION_WEIGHT = 0.40
_MODERATE_CONCENTRATION_WEIGHT = 0.25
_HIGH_CASH = 0.20
_MODERATE_CASH = 0.05


@dataclass(frozen=True, slots=True)
class PortfolioAnalysisContext:
    """Inputs for qualitative portfolio analysis."""

    portfolio: Portfolio
    decision_pack_refs: tuple[DecisionPackReference, ...] = ()
    evidence_bundle_refs: tuple[EvidenceBundleReference, ...] = ()
    comparison_report_refs: tuple[ComparisonReportReference, ...] = ()
    snapshot_id: str | None = None

    def __post_init__(self) -> None:
        if self.portfolio is None:
            msg = "portfolio is required"
            raise PortfolioError(msg)
        snap = (
            None
            if self.snapshot_id is None
            else self.snapshot_id.strip() or None
        )
        object.__setattr__(self, "snapshot_id", snap)
        object.__setattr__(
            self, "decision_pack_refs", tuple(self.decision_pack_refs)
        )
        object.__setattr__(
            self, "evidence_bundle_refs", tuple(self.evidence_bundle_refs)
        )
        object.__setattr__(
            self, "comparison_report_refs", tuple(self.comparison_report_refs)
        )


@dataclass(frozen=True, slots=True)
class PortfolioAnalysisResult:
    """Qualitative analysis output — descriptive only."""

    portfolio_id: str
    status: PortfolioAnalysisStatus
    summary: PortfolioSummary
    observations: tuple[PortfolioObservation, ...]
    descriptors: tuple[PortfolioDescriptor, ...]
    constraint_gap_notes: tuple[str, ...]
    coverage: CoverageSummary
    report: PortfolioReport
    warnings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "observations", tuple(self.observations))
        object.__setattr__(self, "descriptors", tuple(self.descriptors))
        object.__setattr__(
            self, "constraint_gap_notes", tuple(self.constraint_gap_notes)
        )
        object.__setattr__(self, "warnings", tuple(self.warnings))


class PortfolioAnalyzer:
    """Canonical qualitative consumer for descriptive portfolio insights.

    Produces observations and descriptors only — never recommendations.
    """

    def validate_inputs(self, context: PortfolioAnalysisContext) -> None:
        """Reject invalid analysis inputs."""
        portfolio = context.portfolio
        if portfolio is None:
            msg = "invalid Portfolio: portfolio is required"
            raise PortfolioError(msg)
        if portfolio.identity is None:
            msg = "missing PortfolioIdentity"
            raise PortfolioError(msg)
        if not portfolio.identity.portfolio_id:
            msg = "missing PortfolioIdentity: empty portfolio_id"
            raise PortfolioError(msg)

        holding_symbols = {h.instrument_symbol for h in portfolio.holdings}

        for ref in context.decision_pack_refs:
            if ref.instrument_symbol not in holding_symbols:
                msg = (
                    f"foreign holdings / invalid citation: DecisionPack for "
                    f"{ref.instrument_symbol!r} is not in portfolio holdings"
                )
                raise PortfolioError(msg)

        for ref in context.evidence_bundle_refs:
            if ref.instrument_key not in holding_symbols:
                msg = (
                    f"foreign holdings / invalid citation: EvidenceBundle for "
                    f"{ref.instrument_key!r} is not in portfolio holdings"
                )
                raise PortfolioError(msg)

        for ref in context.comparison_report_refs:
            if ref.included_symbols:
                orphans = tuple(
                    s for s in ref.included_symbols if s not in holding_symbols
                )
                if orphans:
                    msg = (
                        f"foreign holdings / invalid citation: ComparisonReport "
                        f"symbols {list(orphans)!r} are not in portfolio holdings"
                    )
                    raise PortfolioError(msg)

        if context.snapshot_id is not None:
            ids = {s.snapshot_id for s in portfolio.snapshots}
            if context.snapshot_id not in ids:
                msg = (
                    f"invalid citation: snapshot_id {context.snapshot_id!r} "
                    f"not found on portfolio"
                )
                raise PortfolioError(msg)

        for snap in portfolio.snapshots:
            if snap.portfolio_id != portfolio.identity.portfolio_id:
                msg = (
                    f"foreign holdings: snapshot {snap.snapshot_id!r} ownership "
                    f"mismatch"
                )
                raise PortfolioError(msg)

    def summarize(
        self, context: PortfolioAnalysisContext | Portfolio
    ) -> PortfolioSummary:
        """Build a qualitative PortfolioSummary."""
        ctx = self._as_context(context)
        self.validate_inputs(ctx)
        return self._build_summary(ctx)

    def describe(
        self, context: PortfolioAnalysisContext | Portfolio
    ) -> tuple[PortfolioDescriptor, ...]:
        """Build qualitative PortfolioDescriptors."""
        ctx = self._as_context(context)
        self.validate_inputs(ctx)
        return self._build_descriptors(ctx)

    def analyze(
        self, context: PortfolioAnalysisContext | Portfolio
    ) -> PortfolioAnalysisResult:
        """Run full qualitative analysis — descriptive only."""
        ctx = self._as_context(context)
        self.validate_inputs(ctx)

        coverage = self._build_coverage(ctx)
        descriptors = self._build_descriptors(ctx)
        observations = self._build_observations(ctx, coverage)
        constraint_notes = self._build_constraint_gap_notes(ctx)
        summary = self._build_summary(ctx, coverage)
        status = self._status(ctx, coverage)
        warnings = self._warnings(ctx, coverage)
        report = self._build_report(ctx, summary, observations, coverage)

        self._reject_duplicate_observations(observations)

        return PortfolioAnalysisResult(
            portfolio_id=ctx.portfolio.identity.portfolio_id,
            status=status,
            summary=summary,
            observations=observations,
            descriptors=descriptors,
            constraint_gap_notes=constraint_notes,
            coverage=coverage,
            report=report,
            warnings=warnings,
        )

    def analyze_many(
        self, contexts: tuple[PortfolioAnalysisContext | Portfolio, ...]
    ) -> tuple[PortfolioAnalysisResult, ...]:
        return tuple(self.analyze(ctx) for ctx in contexts)

    def _as_context(
        self, context: PortfolioAnalysisContext | Portfolio
    ) -> PortfolioAnalysisContext:
        if isinstance(context, Portfolio):
            return PortfolioAnalysisContext(portfolio=context)
        return context

    def _resolve_snapshot(
        self, context: PortfolioAnalysisContext
    ) -> PortfolioSnapshot | None:
        snaps = context.portfolio.snapshots
        if not snaps:
            return None
        if context.snapshot_id is not None:
            for snap in snaps:
                if snap.snapshot_id == context.snapshot_id:
                    return snap
            return None
        return snaps[-1]

    def _merged_evidence_map(
        self, context: PortfolioAnalysisContext
    ) -> dict[str, EvidenceBundleReference]:
        mapping: dict[str, EvidenceBundleReference] = {}
        for holding in context.portfolio.holdings:
            if holding.evidence_bundle_ref is not None:
                mapping[holding.instrument_symbol] = holding.evidence_bundle_ref
        for ref in context.evidence_bundle_refs:
            mapping[ref.instrument_key] = ref
        return mapping

    def _merged_comparison_symbols(
        self, context: PortfolioAnalysisContext
    ) -> set[str]:
        covered: set[str] = set()
        portfolio_level = False
        for holding in context.portfolio.holdings:
            if holding.comparison_report_ref is not None:
                covered.add(holding.instrument_symbol)
        for snap in context.portfolio.snapshots:
            if snap.comparison_report_ref is not None:
                if snap.comparison_report_ref.included_symbols:
                    covered.update(snap.comparison_report_ref.included_symbols)
                else:
                    portfolio_level = True
        for ref in context.comparison_report_refs:
            if ref.included_symbols:
                covered.update(ref.included_symbols)
            else:
                portfolio_level = True
        if portfolio_level:
            covered.update(h.instrument_symbol for h in context.portfolio.holdings)
        return covered

    def _build_coverage(self, context: PortfolioAnalysisContext) -> CoverageSummary:
        holdings = context.portfolio.holdings
        evidence_map = self._merged_evidence_map(context)
        comparison_covered = self._merged_comparison_symbols(context)

        missing_evidence = tuple(
            h.instrument_symbol
            for h in holdings
            if h.instrument_symbol not in evidence_map
        )
        missing_comparison = tuple(
            h.instrument_symbol
            for h in holdings
            if h.instrument_symbol not in comparison_covered
        )

        pack_refs = {h.instrument_symbol: h.decision_pack_ref for h in holdings}
        for ref in context.decision_pack_refs:
            pack_refs[ref.instrument_symbol] = ref

        comparison_refs: set[str] = set()
        for h in holdings:
            if h.comparison_report_ref is not None:
                comparison_refs.add(h.comparison_report_ref.digest)
        for snap in context.portfolio.snapshots:
            if snap.comparison_report_ref is not None:
                comparison_refs.add(snap.comparison_report_ref.digest)
        for ref in context.comparison_report_refs:
            comparison_refs.add(ref.digest)

        notes: list[str] = []
        if missing_evidence:
            notes.append(
                f"Evidence gaps for {len(missing_evidence)} holding(s)."
            )
        if missing_comparison:
            notes.append(
                f"Comparison citation gaps for "
                f"{len(missing_comparison)} holding(s)."
            )

        return CoverageSummary(
            holding_count=len(holdings),
            decision_pack_count=len(pack_refs),
            evidence_bundle_count=len(evidence_map),
            comparison_report_count=len(comparison_refs),
            holdings_with_evidence=len(holdings) - len(missing_evidence),
            holdings_with_comparison=len(holdings) - len(missing_comparison),
            missing_evidence_symbols=missing_evidence,
            missing_comparison_symbols=missing_comparison,
            notes=tuple(notes),
        )

    def _cash_weight(self, context: PortfolioAnalysisContext) -> float | None:
        if context.portfolio.cash_weight is not None:
            return context.portfolio.cash_weight
        snap = self._resolve_snapshot(context)
        if snap is not None and snap.cash_weight is not None:
            return snap.cash_weight
        if snap is not None and snap.allocation is not None:
            return snap.allocation.cash_weight
        return None

    def _build_descriptors(
        self, context: PortfolioAnalysisContext
    ) -> tuple[PortfolioDescriptor, ...]:
        holdings = context.portfolio.holdings
        coverage = self._build_coverage(context)
        descriptors: list[PortfolioDescriptor] = [
            self._concentration_descriptor(holdings),
            self._cash_descriptor(self._cash_weight(context)),
            self._diversification_descriptor(context),
            self._evidence_coverage_descriptor(coverage),
            self._decision_coverage_descriptor(holdings),
        ]
        descriptors.extend(self._constraint_descriptors(context))
        return tuple(descriptors)

    def _concentration_descriptor(
        self, holdings: tuple[PortfolioHolding, ...]
    ) -> PortfolioDescriptor:
        n = len(holdings)
        if n == 0:
            return PortfolioDescriptor(
                dimension="concentration",
                label="Broadly diversified",
                code="broadly_diversified",
                notes=("Empty portfolio — no concentrated holdings present.",),
            )
        weights = [h.weight for h in holdings if h.weight is not None]
        max_w = max(weights) if weights else None
        if n == 1 or (max_w is not None and max_w >= _HIGH_CONCENTRATION_WEIGHT):
            return PortfolioDescriptor(
                dimension="concentration",
                label="Highly concentrated",
                code="highly_concentrated",
                notes=(
                    "Descriptive label from holding count / declared weights only.",
                ),
            )
        if n <= 5 or (
            max_w is not None and max_w >= _MODERATE_CONCENTRATION_WEIGHT
        ):
            return PortfolioDescriptor(
                dimension="concentration",
                label="Moderately concentrated",
                code="moderately_concentrated",
                notes=(
                    "Descriptive label from holding count / declared weights only.",
                ),
            )
        return PortfolioDescriptor(
            dimension="concentration",
            label="Broadly diversified",
            code="broadly_diversified",
            notes=(
                "Descriptive label from holding count / declared weights only.",
            ),
        )

    def _cash_descriptor(self, cash_weight: float | None) -> PortfolioDescriptor:
        if cash_weight is None or cash_weight < _MODERATE_CASH:
            return PortfolioDescriptor(
                dimension="cash_position",
                label="Fully invested",
                code="fully_invested",
                notes=(
                    "Cash weight absent or below moderate-reserve threshold.",
                ),
            )
        if cash_weight < _HIGH_CASH:
            return PortfolioDescriptor(
                dimension="cash_position",
                label="Moderate cash reserve",
                code="moderate_cash_reserve",
            )
        return PortfolioDescriptor(
            dimension="cash_position",
            label="High cash reserve",
            code="high_cash_reserve",
        )

    def _diversification_descriptor(
        self, context: PortfolioAnalysisContext
    ) -> PortfolioDescriptor:
        snap = self._resolve_snapshot(context)
        sectors: tuple[tuple[str, float], ...] = ()
        if snap is not None and snap.allocation is not None:
            sectors = snap.allocation.by_sector
        n_holdings = len(context.portfolio.holdings)
        if not sectors:
            if n_holdings <= 1:
                return PortfolioDescriptor(
                    dimension="diversification",
                    label="Single-sector exposure",
                    code="single_sector_exposure",
                    notes=(
                        "Sector allocation not declared; "
                        "inferred from holding count.",
                    ),
                )
            if n_holdings <= 4:
                return PortfolioDescriptor(
                    dimension="diversification",
                    label="Limited sector exposure",
                    code="limited_sector_exposure",
                    notes=(
                        "Sector allocation not declared; "
                        "inferred from holding count.",
                    ),
                )
            return PortfolioDescriptor(
                dimension="diversification",
                label="Broad sector exposure",
                code="broad_sector_exposure",
                notes=(
                    "Sector allocation not declared; "
                    "inferred from holding count.",
                ),
            )
        if len(sectors) == 1:
            return PortfolioDescriptor(
                dimension="diversification",
                label="Single-sector exposure",
                code="single_sector_exposure",
            )
        if len(sectors) <= 3:
            return PortfolioDescriptor(
                dimension="diversification",
                label="Limited sector exposure",
                code="limited_sector_exposure",
            )
        return PortfolioDescriptor(
            dimension="diversification",
            label="Broad sector exposure",
            code="broad_sector_exposure",
        )

    def _evidence_coverage_descriptor(
        self, coverage: CoverageSummary
    ) -> PortfolioDescriptor:
        if coverage.holding_count == 0:
            return PortfolioDescriptor(
                dimension="evidence_coverage",
                label="Complete evidence coverage",
                code="complete_evidence_coverage",
                notes=("Empty portfolio — no evidence gaps.",),
            )
        if not coverage.missing_evidence_symbols:
            return PortfolioDescriptor(
                dimension="evidence_coverage",
                label="Complete evidence coverage",
                code="complete_evidence_coverage",
            )
        if coverage.holdings_with_evidence == 0:
            return PortfolioDescriptor(
                dimension="evidence_coverage",
                label="Evidence gaps exist",
                code="evidence_gaps_exist",
            )
        return PortfolioDescriptor(
            dimension="evidence_coverage",
            label="Partial evidence coverage",
            code="partial_evidence_coverage",
        )

    def _decision_coverage_descriptor(
        self, holdings: tuple[PortfolioHolding, ...]
    ) -> PortfolioDescriptor:
        # Valid PortfolioHolding always requires DecisionPackReference.
        if not holdings or all(h.decision_pack_ref is not None for h in holdings):
            return PortfolioDescriptor(
                dimension="decision_coverage",
                label="All holdings contain DecisionPacks",
                code="all_holdings_contain_decision_packs",
                notes=(
                    ()
                    if holdings
                    else ("Empty portfolio — no missing DecisionPacks.",)
                ),
            )
        return PortfolioDescriptor(
            dimension="decision_coverage",
            label="Missing DecisionPacks detected",
            code="missing_decision_packs_detected",
        )

    def _constraint_descriptors(
        self, context: PortfolioAnalysisContext
    ) -> tuple[PortfolioDescriptor, ...]:
        constraints = context.portfolio.constraints
        if not constraints:
            return (
                PortfolioDescriptor(
                    dimension="constraint_notes",
                    label="Constraint not evaluated",
                    code="constraint_not_evaluated",
                    notes=("No portfolio constraints declared.",),
                ),
            )
        out: list[PortfolioDescriptor] = []
        for constraint in constraints:
            needs_weights = constraint.kind.value in {
                "max_position_weight",
                "min_cash_weight",
            }
            needs_sectors = constraint.kind.value in {
                "max_sector_weight",
                "max_industry_weight",
            }
            holdings = context.portfolio.holdings
            missing_weights = False
            if needs_weights:
                if constraint.kind.value == "min_cash_weight":
                    missing_weights = context.portfolio.cash_weight is None
                else:
                    missing_weights = any(h.weight is None for h in holdings)
            snap = self._resolve_snapshot(context)
            missing_sectors = needs_sectors and (
                snap is None
                or snap.allocation is None
                or not snap.allocation.by_sector
            )
            if missing_weights or missing_sectors:
                out.append(
                    PortfolioDescriptor(
                        dimension="constraint_notes",
                        label="Constraint requires attention",
                        code=f"constraint_requires_attention_{constraint.id}",
                        notes=(
                            f"Constraint {constraint.id} declared; inputs "
                            f"needed for descriptive review are incomplete. "
                            f"Not evaluated mathematically.",
                        ),
                    )
                )
            else:
                out.append(
                    PortfolioDescriptor(
                        dimension="constraint_notes",
                        label="Constraint not evaluated",
                        code=f"constraint_not_evaluated_{constraint.id}",
                        notes=(
                            f"Constraint {constraint.id} is declared and stored. "
                            f"C4.3 does not evaluate constraints mathematically.",
                        ),
                    )
                )
        return tuple(out)

    def _build_constraint_gap_notes(
        self, context: PortfolioAnalysisContext
    ) -> tuple[str, ...]:
        notes: list[str] = []
        if not context.portfolio.constraints:
            notes.append(
                "No portfolio constraints declared — "
                "constraint gaps not applicable."
            )
            return tuple(notes)
        for constraint in context.portfolio.constraints:
            notes.append(
                f"Constraint {constraint.id} ({constraint.kind.value}) "
                f"target={constraint.target!r} limit={constraint.limit} — "
                f"Constraint not evaluated."
            )
            holdings = context.portfolio.holdings
            if constraint.kind.value == "max_position_weight" and any(
                h.weight is None for h in holdings
            ):
                notes.append(
                    f"Constraint {constraint.id} requires attention: "
                    f"one or more holdings lack declared weights."
                )
            if constraint.kind.value == "min_cash_weight" and (
                context.portfolio.cash_weight is None
            ):
                notes.append(
                    f"Constraint {constraint.id} requires attention: "
                    f"cash_weight is not declared."
                )
        return tuple(notes)

    def _build_observations(
        self,
        context: PortfolioAnalysisContext,
        coverage: CoverageSummary,
    ) -> tuple[PortfolioObservation, ...]:
        holdings = context.portfolio.holdings
        observations: list[PortfolioObservation] = []

        concentration = self._concentration_descriptor(holdings)
        observations.append(
            PortfolioObservation(
                code=f"concentration_{concentration.code}",
                text=f"Concentration posture: {concentration.label}.",
                subjects=tuple(h.instrument_symbol for h in holdings),
            )
        )

        cash = self._cash_descriptor(self._cash_weight(context))
        observations.append(
            PortfolioObservation(
                code=f"cash_{cash.code}",
                text=f"Cash position: {cash.label}.",
            )
        )

        diversification = self._diversification_descriptor(context)
        observations.append(
            PortfolioObservation(
                code=f"diversification_{diversification.code}",
                text=f"Diversification posture: {diversification.label}.",
                subjects=tuple(h.instrument_symbol for h in holdings),
            )
        )

        evidence = self._evidence_coverage_descriptor(coverage)
        evidence_map = self._merged_evidence_map(context)
        evidence_refs = tuple(
            f"{sym}:{evidence_map[sym].digest}" for sym in sorted(evidence_map)
        )
        observations.append(
            PortfolioObservation(
                code=f"evidence_{evidence.code}",
                text=f"Evidence coverage: {evidence.label}.",
                subjects=coverage.missing_evidence_symbols,
                evidence_refs=evidence_refs,
            )
        )

        if coverage.missing_comparison_symbols:
            observations.append(
                PortfolioObservation(
                    code="comparison_citation_gaps",
                    text=(
                        "Optional ComparisonReport citations are missing for "
                        f"{len(coverage.missing_comparison_symbols)} holding(s)."
                    ),
                    subjects=coverage.missing_comparison_symbols,
                )
            )
        else:
            observations.append(
                PortfolioObservation(
                    code="comparison_citations_present_or_unused",
                    text=(
                        "Comparison citations are present for all holdings, "
                        "or no holdings exist."
                    ),
                    subjects=tuple(h.instrument_symbol for h in holdings),
                )
            )

        for idx, note in enumerate(self._build_constraint_gap_notes(context)):
            observations.append(
                PortfolioObservation(
                    code=f"constraint_gap_{idx + 1}",
                    text=note,
                )
            )

        return tuple(observations)

    def _build_summary(
        self,
        context: PortfolioAnalysisContext,
        coverage: CoverageSummary | None = None,
    ) -> PortfolioSummary:
        if coverage is None:
            coverage = self._build_coverage(context)
        concentration = self._concentration_descriptor(context.portfolio.holdings)
        cash = self._cash_descriptor(self._cash_weight(context))
        diversification = self._diversification_descriptor(context)
        evidence = self._evidence_coverage_descriptor(coverage)
        decision = self._decision_coverage_descriptor(context.portfolio.holdings)
        coverage_notes = list(coverage.notes)
        coverage_notes.append(f"Evidence coverage: {evidence.label}.")
        coverage_notes.append(f"Decision coverage: {decision.label}.")
        return PortfolioSummary(
            holding_count=len(context.portfolio.holdings),
            cash_weight=self._cash_weight(context),
            coverage_notes=tuple(coverage_notes),
            concentration_notes=(
                f"Concentration: {concentration.label}.",
                f"Diversification: {diversification.label}.",
                f"Cash position: {cash.label}.",
            ),
            limitation_notes=(
                "Qualitative analysis only — no scoring, ranking, optimization, "
                "risk metrics, or trade recommendations.",
                "Constraints are not evaluated mathematically in C4.3.",
            ),
        )

    def _build_report(
        self,
        context: PortfolioAnalysisContext,
        summary: PortfolioSummary,
        observations: tuple[PortfolioObservation, ...],
        coverage: CoverageSummary,
    ) -> PortfolioReport:
        holdings = context.portfolio.holdings
        pack_refs = tuple(h.decision_pack_ref for h in holdings)
        evidence_map = self._merged_evidence_map(context)
        evidence_refs = tuple(evidence_map[sym] for sym in sorted(evidence_map))

        comparison_by_digest: dict[str, ComparisonReportReference] = {}
        for h in holdings:
            if h.comparison_report_ref is not None:
                comparison_by_digest[h.comparison_report_ref.digest] = (
                    h.comparison_report_ref
                )
        for snap in context.portfolio.snapshots:
            if snap.comparison_report_ref is not None:
                comparison_by_digest[snap.comparison_report_ref.digest] = (
                    snap.comparison_report_ref
                )
        for ref in context.comparison_report_refs:
            comparison_by_digest[ref.digest] = ref

        snap = self._resolve_snapshot(context)
        limitations = list(summary.limitation_notes)
        if coverage.missing_evidence_symbols:
            limitations.append("Evidence citation gaps remain.")
        if coverage.missing_comparison_symbols:
            limitations.append("Comparison citation gaps remain.")

        return PortfolioReport(
            portfolio_id=context.portfolio.identity.portfolio_id,
            summary=summary,
            observations=observations,
            snapshot_id=None if snap is None else snap.snapshot_id,
            decision_pack_refs=pack_refs,
            evidence_bundle_refs=evidence_refs,
            comparison_report_refs=tuple(comparison_by_digest.values()),
            limitations=tuple(limitations),
            coverage_summary=coverage,
        )

    def _status(
        self, context: PortfolioAnalysisContext, coverage: CoverageSummary
    ) -> PortfolioAnalysisStatus:
        del context
        if coverage.holding_count == 0:
            return PortfolioAnalysisStatus.EMPTY
        if coverage.missing_evidence_symbols or coverage.missing_comparison_symbols:
            return PortfolioAnalysisStatus.PARTIAL
        return PortfolioAnalysisStatus.COMPLETE

    def _warnings(
        self, context: PortfolioAnalysisContext, coverage: CoverageSummary
    ) -> tuple[str, ...]:
        warnings: list[str] = []
        if coverage.missing_evidence_symbols:
            warnings.append(
                "Missing optional EvidenceBundle citations for: "
                + ", ".join(coverage.missing_evidence_symbols)
            )
        if coverage.missing_comparison_symbols:
            warnings.append(
                "Missing optional ComparisonReport citations for: "
                + ", ".join(coverage.missing_comparison_symbols)
            )
        if context.portfolio.constraints:
            warnings.append(
                "Declared constraints were not evaluated mathematically."
            )
        return tuple(warnings)

    def _reject_duplicate_observations(
        self, observations: tuple[PortfolioObservation, ...]
    ) -> None:
        seen: set[str] = set()
        for obs in observations:
            if obs.code in seen:
                msg = f"duplicate observations: code {obs.code!r}"
                raise PortfolioError(msg)
            seen.add(obs.code)
