"""Portfolio Assembler — construction / orchestration only (C4.2).

Builds immutable Portfolio aggregates from citations.
Never analyzes, evaluates constraints, scores, or recommends.
"""

from __future__ import annotations

from dataclasses import dataclass

from core.exceptions import ValidationError
from industry import EvidenceBundleReference

from portfolio.enums import PortfolioAssemblyStatus
from portfolio.exceptions import PortfolioError
from portfolio.models import (
    Portfolio,
    PortfolioConstraint,
    PortfolioHolding,
    PortfolioIdentity,
    PortfolioSnapshot,
)
from portfolio.refs import ComparisonReportReference, DecisionPackReference

__all__ = [
    "PortfolioAssembler",
    "PortfolioAssemblyContext",
    "PortfolioAssemblyResult",
    "PortfolioHoldingInput",
]


@dataclass(frozen=True, slots=True)
class PortfolioHoldingInput:
    """Holding construction input — DecisionPack citation required."""

    decision_pack_ref: DecisionPackReference
    weight: float | None = None
    units: float | None = None
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.decision_pack_ref is None:
            msg = "decision_pack_ref is required"
            raise ValidationError(msg)
        notes = tuple(n.strip() for n in self.notes if n.strip())
        object.__setattr__(self, "notes", notes)


@dataclass(frozen=True, slots=True)
class PortfolioAssemblyContext:
    """Inputs for deterministic Portfolio construction."""

    identity: PortfolioIdentity
    holdings: tuple[PortfolioHoldingInput, ...]
    evidence_bundle_refs: tuple[EvidenceBundleReference, ...] = ()
    comparison_report_refs: tuple[ComparisonReportReference, ...] = ()
    constraints: tuple[PortfolioConstraint, ...] = ()
    snapshots: tuple[PortfolioSnapshot, ...] = ()
    cash_weight: float | None = None
    as_of: str | None = None

    def __post_init__(self) -> None:
        if self.identity is None:
            msg = "identity is required"
            raise ValidationError(msg)
        holdings = tuple(self.holdings)
        if not holdings:
            msg = "assembly requires at least one DecisionPack holding input"
            raise ValidationError(msg)
        as_of = None if self.as_of is None else self.as_of.strip() or None
        object.__setattr__(self, "holdings", holdings)
        object.__setattr__(self, "evidence_bundle_refs", tuple(self.evidence_bundle_refs))
        object.__setattr__(
            self, "comparison_report_refs", tuple(self.comparison_report_refs)
        )
        object.__setattr__(self, "constraints", tuple(self.constraints))
        object.__setattr__(self, "snapshots", tuple(self.snapshots))
        object.__setattr__(self, "as_of", as_of)


@dataclass(frozen=True, slots=True)
class PortfolioAssemblyResult:
    """Assembler output — Portfolio plus non-analytic warnings."""

    portfolio: Portfolio
    status: PortfolioAssemblyStatus
    warnings: tuple[str, ...] = ()
    missing_evidence_symbols: tuple[str, ...] = ()
    missing_comparison_citations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "warnings", tuple(self.warnings))
        object.__setattr__(
            self, "missing_evidence_symbols", tuple(self.missing_evidence_symbols)
        )
        object.__setattr__(
            self,
            "missing_comparison_citations",
            tuple(self.missing_comparison_citations),
        )


class PortfolioAssembler:
    """Canonical constructor for immutable Portfolio objects.

    Orchestration only — no investment analysis.
    """

    def validate_inputs(self, context: PortfolioAssemblyContext) -> None:
        """Reject invalid assembly inputs before construction."""
        if context.identity is None:
            msg = "missing identity"
            raise PortfolioError(msg)
        if not context.identity.portfolio_id:
            msg = "invalid metadata: empty portfolio_id"
            raise PortfolioError(msg)
        if not context.identity.portfolio_name:
            msg = "invalid metadata: empty portfolio_name"
            raise PortfolioError(msg)

        pack_symbols: list[str] = []
        pack_digests: set[tuple[str, str]] = set()
        for item in context.holdings:
            ref = item.decision_pack_ref
            sym = ref.instrument_symbol
            key = (sym, ref.digest)
            if sym in pack_symbols:
                msg = f"duplicate holdings / DecisionPacks for {sym!r}"
                raise PortfolioError(msg)
            if key in pack_digests:
                msg = f"duplicate DecisionPack reference for {sym!r}"
                raise PortfolioError(msg)
            pack_symbols.append(sym)
            pack_digests.add(key)

        holding_set = set(pack_symbols)

        seen_evidence: set[str] = set()
        for ref in context.evidence_bundle_refs:
            sym = ref.instrument_key
            if sym in seen_evidence:
                msg = f"duplicate EvidenceBundle reference for {sym!r}"
                raise PortfolioError(msg)
            seen_evidence.add(sym)
            if sym not in holding_set:
                msg = (
                    f"orphan EvidenceBundle reference for {sym!r}: "
                    f"no matching DecisionPack holding"
                )
                raise PortfolioError(msg)

        for ref in context.comparison_report_refs:
            included = ref.included_symbols
            if included:
                orphans = tuple(s for s in included if s not in holding_set)
                if orphans:
                    msg = (
                        f"orphan ComparisonReport reference symbols "
                        f"{list(orphans)!r}: not present in holdings"
                    )
                    raise PortfolioError(msg)
            # empty included_symbols => portfolio-level citation (allowed)

        for snap in context.snapshots:
            if snap.portfolio_id != context.identity.portfolio_id:
                msg = (
                    f"foreign ownership: snapshot {snap.snapshot_id!r} "
                    f"belongs to {snap.portfolio_id!r}, not "
                    f"{context.identity.portfolio_id!r}"
                )
                raise PortfolioError(msg)

        seen_constraints: set[str] = set()
        for constraint in context.constraints:
            if constraint.id in seen_constraints:
                msg = f"duplicate constraint id {constraint.id!r}"
                raise PortfolioError(msg)
            seen_constraints.add(constraint.id)

        if context.cash_weight is not None:
            if context.cash_weight < 0.0 or context.cash_weight > 1.0:
                msg = "invalid metadata: cash_weight must be between 0 and 1"
                raise PortfolioError(msg)

    def portfolio_metadata(
        self, context: PortfolioAssemblyContext
    ) -> PortfolioIdentity:
        """Return validated identity metadata (no analysis)."""
        self.validate_inputs(context)
        return context.identity

    def assemble(self, context: PortfolioAssemblyContext) -> PortfolioAssemblyResult:
        """Construct an immutable Portfolio from citations."""
        self.validate_inputs(context)

        evidence_by_symbol = {
            ref.instrument_key: ref for ref in context.evidence_bundle_refs
        }
        # Per-holding comparison: refs whose included_symbols mention the symbol
        comparison_for_symbol: dict[str, ComparisonReportReference] = {}
        portfolio_level_comparisons: list[ComparisonReportReference] = []
        for ref in context.comparison_report_refs:
            if not ref.included_symbols:
                portfolio_level_comparisons.append(ref)
                continue
            for sym in ref.included_symbols:
                # First matching citation wins (deterministic order)
                if sym not in comparison_for_symbol:
                    comparison_for_symbol[sym] = ref

        holdings: list[PortfolioHolding] = []
        missing_evidence: list[str] = []
        missing_comparison: list[str] = []
        warnings: list[str] = []

        for item in context.holdings:
            sym = item.decision_pack_ref.instrument_symbol
            evidence = evidence_by_symbol.get(sym)
            if evidence is None:
                missing_evidence.append(sym)
                warnings.append(
                    f"Optional EvidenceBundle reference missing for {sym}."
                )
            comparison = comparison_for_symbol.get(sym)
            if (
                context.comparison_report_refs
                and comparison is None
                and not portfolio_level_comparisons
            ):
                missing_comparison.append(sym)
                warnings.append(
                    f"Optional ComparisonReport citation missing for {sym}."
                )
            holdings.append(
                PortfolioHolding(
                    instrument_symbol=sym,
                    decision_pack_ref=item.decision_pack_ref,
                    weight=item.weight,
                    units=item.units,
                    evidence_bundle_ref=evidence,
                    comparison_report_ref=comparison,
                    notes=item.notes,
                )
            )

        snapshots = list(context.snapshots)
        if context.as_of is not None:
            snap_comparison = (
                portfolio_level_comparisons[0]
                if portfolio_level_comparisons
                else None
            )
            snapshots.append(
                PortfolioSnapshot(
                    snapshot_id=(
                        f"dsp.snapshot.{context.identity.portfolio_id}."
                        f"{context.as_of.lower().replace(':', '').replace('-', '')}"
                    ),
                    portfolio_id=context.identity.portfolio_id,
                    as_of=context.as_of,
                    holdings=tuple(holdings),
                    cash_weight=context.cash_weight,
                    comparison_report_ref=snap_comparison,
                    notes=(
                        "C4.2 assembler snapshot — construction only.",
                    ),
                )
            )
        elif portfolio_level_comparisons:
            warnings.append(
                "Portfolio-level ComparisonReport reference(s) supplied "
                "without as_of; not attached to a snapshot."
            )

        portfolio = Portfolio(
            identity=context.identity,
            holdings=tuple(holdings),
            constraints=context.constraints,
            snapshots=tuple(snapshots),
            cash_weight=context.cash_weight,
        )

        # Optional-citation completeness only (never a quality score).
        evidence_complete = bool(context.evidence_bundle_refs) and not missing_evidence
        comparison_complete = (
            not context.comparison_report_refs
            or bool(portfolio_level_comparisons)
            or not missing_comparison
        )
        if evidence_complete and comparison_complete:
            status = PortfolioAssemblyStatus.COMPLETE
        else:
            status = PortfolioAssemblyStatus.PARTIAL
            if not context.evidence_bundle_refs:
                warnings.insert(0, "No EvidenceBundle references were supplied.")

        return PortfolioAssemblyResult(
            portfolio=portfolio,
            status=status,
            warnings=tuple(dict.fromkeys(warnings)),
            missing_evidence_symbols=tuple(missing_evidence),
            missing_comparison_citations=tuple(missing_comparison),
        )

    def assemble_many(
        self, contexts: tuple[PortfolioAssemblyContext, ...]
    ) -> tuple[PortfolioAssemblyResult, ...]:
        return tuple(self.assemble(ctx) for ctx in contexts)
