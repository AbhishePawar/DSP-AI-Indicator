"""Portfolio Citation Enrichment — aggregation only (C4.4).

Aggregates DecisionPack, EvidenceBundle, and ComparisonReport citations.
Never interprets evidence, performs comparison, or generates observations.
"""

from __future__ import annotations

from dataclasses import dataclass

from industry import EvidenceBundleReference

from portfolio.enums import PortfolioCitationStatus
from portfolio.exceptions import PortfolioError
from portfolio.models import (
    CoverageSummary,
    Portfolio,
    PortfolioCitationSummary,
    PortfolioReport,
    PortfolioSummary,
)
from portfolio.refs import ComparisonReportReference, DecisionPackReference

__all__ = [
    "PortfolioCitationAssembler",
    "PortfolioCitationContext",
    "PortfolioCitationResult",
]


@dataclass(frozen=True, slots=True)
class PortfolioCitationContext:
    """Inputs for citation aggregation — references only."""

    portfolio: Portfolio
    decision_pack_refs: tuple[DecisionPackReference, ...] = ()
    evidence_bundle_refs: tuple[EvidenceBundleReference, ...] = ()
    comparison_report_refs: tuple[ComparisonReportReference, ...] = ()
    base_report: PortfolioReport | None = None

    def __post_init__(self) -> None:
        if self.portfolio is None:
            msg = "portfolio is required"
            raise PortfolioError(msg)
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
class PortfolioCitationResult:
    """Citation aggregation output — references and coverage only."""

    portfolio_id: str
    status: PortfolioCitationStatus
    summary: PortfolioCitationSummary
    coverage: CoverageSummary
    decision_citations: tuple[DecisionPackReference, ...]
    evidence_citations: tuple[EvidenceBundleReference, ...]
    comparison_citations: tuple[ComparisonReportReference, ...]
    citation_gaps: tuple[str, ...]
    report: PortfolioReport
    warnings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "decision_citations", tuple(self.decision_citations)
        )
        object.__setattr__(
            self, "evidence_citations", tuple(self.evidence_citations)
        )
        object.__setattr__(
            self, "comparison_citations", tuple(self.comparison_citations)
        )
        object.__setattr__(self, "citation_gaps", tuple(self.citation_gaps))
        object.__setattr__(self, "warnings", tuple(self.warnings))


class PortfolioCitationAssembler:
    """Canonical aggregation layer for portfolio citations.

    Pure consumer — aggregates and summarizes references only.
    """

    def validate_inputs(self, context: PortfolioCitationContext) -> None:
        """Reject foreign, duplicate, or broken citation references."""
        portfolio = context.portfolio
        if portfolio is None:
            msg = "invalid Portfolio: portfolio is required"
            raise PortfolioError(msg)
        if portfolio.identity is None or not portfolio.identity.portfolio_id:
            msg = "mismatched portfolio ownership: missing identity"
            raise PortfolioError(msg)

        holding_symbols = {h.instrument_symbol for h in portfolio.holdings}

        for snap in portfolio.snapshots:
            if snap.portfolio_id != portfolio.identity.portfolio_id:
                msg = (
                    f"mismatched portfolio ownership: snapshot "
                    f"{snap.snapshot_id!r}"
                )
                raise PortfolioError(msg)

        if context.base_report is not None:
            if context.base_report.portfolio_id != portfolio.identity.portfolio_id:
                msg = (
                    "mismatched portfolio ownership: base_report "
                    f"{context.base_report.portfolio_id!r}"
                )
                raise PortfolioError(msg)

        # Overlay DecisionPack refs
        seen_pack: set[str] = set()
        for ref in context.decision_pack_refs:
            self._reject_broken_decision(ref)
            if ref.instrument_symbol not in holding_symbols:
                msg = (
                    f"foreign citations: DecisionPack for "
                    f"{ref.instrument_symbol!r} not in portfolio holdings"
                )
                raise PortfolioError(msg)
            if ref.instrument_symbol in seen_pack:
                msg = (
                    f"duplicate citation ids: DecisionPack for "
                    f"{ref.instrument_symbol!r}"
                )
                raise PortfolioError(msg)
            seen_pack.add(ref.instrument_symbol)

        # Holding-level DecisionPack uniqueness (invariant already on Portfolio,
        # re-check for broken digests)
        for holding in portfolio.holdings:
            self._reject_broken_decision(holding.decision_pack_ref)

        # Evidence overlays + holding refs
        seen_evidence_ids: set[str] = set()
        seen_evidence_keys: set[tuple[str, str]] = set()
        for ref in context.evidence_bundle_refs:
            self._reject_broken_evidence(ref)
            if ref.instrument_key not in holding_symbols:
                msg = (
                    f"foreign citations: EvidenceBundle for "
                    f"{ref.instrument_key!r} not in portfolio holdings"
                )
                raise PortfolioError(msg)
            if ref.bundle_id in seen_evidence_ids:
                msg = f"duplicate citation ids: EvidenceBundle {ref.bundle_id!r}"
                raise PortfolioError(msg)
            key = (ref.instrument_key, ref.digest)
            if key in seen_evidence_keys:
                msg = (
                    f"duplicate citation ids: EvidenceBundle for "
                    f"{ref.instrument_key!r}"
                )
                raise PortfolioError(msg)
            seen_evidence_ids.add(ref.bundle_id)
            seen_evidence_keys.add(key)

        for holding in portfolio.holdings:
            ref = holding.evidence_bundle_ref
            if ref is None:
                continue
            self._reject_broken_evidence(ref)
            if ref.instrument_key != holding.instrument_symbol:
                msg = (
                    f"broken bundle references: EvidenceBundle "
                    f"{ref.bundle_id!r} instrument mismatch"
                )
                raise PortfolioError(msg)
            if ref.bundle_id in seen_evidence_ids:
                # Same bundle cited on holding and overlay is OK if identical;
                # conflict if different digest for same bundle_id.
                continue
            if (ref.instrument_key, ref.digest) in seen_evidence_keys:
                msg = (
                    f"duplicate citation ids: EvidenceBundle for "
                    f"{ref.instrument_key!r}"
                )
                raise PortfolioError(msg)

        # Comparison overlays
        seen_comp: set[str] = set()
        for ref in context.comparison_report_refs:
            self._reject_broken_comparison(ref)
            if ref.digest in seen_comp:
                msg = (
                    f"duplicate citation ids: ComparisonReport "
                    f"{ref.digest!r}"
                )
                raise PortfolioError(msg)
            seen_comp.add(ref.digest)
            if ref.included_symbols:
                orphans = tuple(
                    s for s in ref.included_symbols if s not in holding_symbols
                )
                if orphans:
                    msg = (
                        f"foreign citations: ComparisonReport symbols "
                        f"{list(orphans)!r}"
                    )
                    raise PortfolioError(msg)

        for holding in portfolio.holdings:
            ref = holding.comparison_report_ref
            if ref is None:
                continue
            self._reject_broken_comparison(ref)
            if ref.included_symbols and holding.instrument_symbol not in (
                ref.included_symbols
            ):
                msg = (
                    f"broken bundle references: ComparisonReport "
                    f"{ref.digest!r} does not include "
                    f"{holding.instrument_symbol!r}"
                )
                raise PortfolioError(msg)

    def assemble(
        self, context: PortfolioCitationContext | Portfolio
    ) -> PortfolioCitationResult:
        """Aggregate citations into an enriched PortfolioReport."""
        ctx = (
            PortfolioCitationContext(portfolio=context)
            if isinstance(context, Portfolio)
            else context
        )
        self.validate_inputs(ctx)

        decision = self._aggregate_decision(ctx)
        evidence = self._aggregate_evidence(ctx)
        comparison = self._aggregate_comparison(ctx)
        coverage = self._build_coverage(ctx, decision, evidence, comparison)
        gaps = self._build_gaps(coverage)
        summary = self._build_summary(ctx, decision, evidence, comparison, gaps)
        status = self._status(ctx, coverage, evidence, comparison)
        warnings = self._warnings(coverage, status)
        report = self._build_report(
            ctx, summary, coverage, gaps, decision, evidence, comparison
        )

        return PortfolioCitationResult(
            portfolio_id=ctx.portfolio.identity.portfolio_id,
            status=status,
            summary=summary,
            coverage=coverage,
            decision_citations=decision,
            evidence_citations=evidence,
            comparison_citations=comparison,
            citation_gaps=gaps,
            report=report,
            warnings=warnings,
        )

    def assemble_many(
        self, contexts: tuple[PortfolioCitationContext | Portfolio, ...]
    ) -> tuple[PortfolioCitationResult, ...]:
        return tuple(self.assemble(ctx) for ctx in contexts)

    def _reject_broken_decision(self, ref: DecisionPackReference) -> None:
        if ref is None or not ref.digest or len(ref.digest) < 8:
            msg = "invalid references: broken DecisionPack digest"
            raise PortfolioError(msg)
        if not ref.instrument_symbol:
            msg = "invalid references: DecisionPack missing instrument_symbol"
            raise PortfolioError(msg)

    def _reject_broken_evidence(self, ref: EvidenceBundleReference) -> None:
        if ref is None:
            msg = "broken bundle references: EvidenceBundle is None"
            raise PortfolioError(msg)
        if not ref.bundle_id or not ref.digest or len(ref.digest) < 8:
            msg = (
                f"broken bundle references: EvidenceBundle "
                f"{getattr(ref, 'bundle_id', None)!r}"
            )
            raise PortfolioError(msg)
        if not ref.methodology_id or not ref.methodology_version:
            msg = (
                f"broken bundle references: EvidenceBundle {ref.bundle_id!r} "
                f"missing methodology identity"
            )
            raise PortfolioError(msg)
        if not ref.instrument_key:
            msg = (
                f"broken bundle references: EvidenceBundle {ref.bundle_id!r} "
                f"missing instrument_key"
            )
            raise PortfolioError(msg)

    def _reject_broken_comparison(self, ref: ComparisonReportReference) -> None:
        if ref is None or not ref.digest or len(ref.digest) < 8:
            msg = "invalid references: broken ComparisonReport digest"
            raise PortfolioError(msg)

    def _aggregate_decision(
        self, context: PortfolioCitationContext
    ) -> tuple[DecisionPackReference, ...]:
        by_symbol: dict[str, DecisionPackReference] = {
            h.instrument_symbol: h.decision_pack_ref
            for h in context.portfolio.holdings
        }
        for ref in context.decision_pack_refs:
            existing = by_symbol.get(ref.instrument_symbol)
            if existing is not None and existing.digest != ref.digest:
                msg = (
                    f"duplicate citation ids: conflicting DecisionPack digests "
                    f"for {ref.instrument_symbol!r}"
                )
                raise PortfolioError(msg)
            by_symbol[ref.instrument_symbol] = ref
        return tuple(by_symbol[s] for s in sorted(by_symbol))

    def _aggregate_evidence(
        self, context: PortfolioCitationContext
    ) -> tuple[EvidenceBundleReference, ...]:
        by_symbol: dict[str, EvidenceBundleReference] = {}
        for holding in context.portfolio.holdings:
            if holding.evidence_bundle_ref is not None:
                by_symbol[holding.instrument_symbol] = holding.evidence_bundle_ref
        for ref in context.evidence_bundle_refs:
            existing = by_symbol.get(ref.instrument_key)
            if (
                existing is not None
                and (
                    existing.digest != ref.digest
                    or existing.bundle_id != ref.bundle_id
                )
            ):
                msg = (
                    f"duplicate citation ids: conflicting EvidenceBundle for "
                    f"{ref.instrument_key!r}"
                )
                raise PortfolioError(msg)
            by_symbol[ref.instrument_key] = ref
        return tuple(by_symbol[s] for s in sorted(by_symbol))

    def _aggregate_comparison(
        self, context: PortfolioCitationContext
    ) -> tuple[ComparisonReportReference, ...]:
        by_digest: dict[str, ComparisonReportReference] = {}
        for holding in context.portfolio.holdings:
            ref = holding.comparison_report_ref
            if ref is not None:
                by_digest[ref.digest] = ref
        for snap in context.portfolio.snapshots:
            ref = snap.comparison_report_ref
            if ref is not None:
                by_digest[ref.digest] = ref
        for ref in context.comparison_report_refs:
            existing = by_digest.get(ref.digest)
            if existing is not None and existing.included_symbols != (
                ref.included_symbols
            ):
                # Same digest must be identical citation; allow identical re-add
                if (
                    existing.methodology_id != ref.methodology_id
                    or existing.included_symbols != ref.included_symbols
                ):
                    msg = (
                        f"duplicate citation ids: conflicting ComparisonReport "
                        f"{ref.digest!r}"
                    )
                    raise PortfolioError(msg)
            by_digest[ref.digest] = ref
        return tuple(by_digest[d] for d in sorted(by_digest))

    def _build_coverage(
        self,
        context: PortfolioCitationContext,
        decision: tuple[DecisionPackReference, ...],
        evidence: tuple[EvidenceBundleReference, ...],
        comparison: tuple[ComparisonReportReference, ...],
    ) -> CoverageSummary:
        holdings = context.portfolio.holdings
        evidence_symbols = {ref.instrument_key for ref in evidence}
        comparison_symbols: set[str] = set()
        portfolio_level = False
        for ref in comparison:
            if ref.included_symbols:
                comparison_symbols.update(ref.included_symbols)
            else:
                portfolio_level = True
        if portfolio_level:
            comparison_symbols.update(h.instrument_symbol for h in holdings)

        missing_evidence = tuple(
            h.instrument_symbol
            for h in holdings
            if h.instrument_symbol not in evidence_symbols
        )
        missing_comparison = tuple(
            h.instrument_symbol
            for h in holdings
            if h.instrument_symbol not in comparison_symbols
        )
        notes: list[str] = []
        if missing_evidence:
            notes.append(
                f"Evidence citation gaps for {len(missing_evidence)} holding(s)."
            )
        if missing_comparison:
            notes.append(
                f"Comparison citation gaps for "
                f"{len(missing_comparison)} holding(s)."
            )
        return CoverageSummary(
            holding_count=len(holdings),
            decision_pack_count=len(decision),
            evidence_bundle_count=len(evidence),
            comparison_report_count=len(comparison),
            holdings_with_evidence=len(holdings) - len(missing_evidence),
            holdings_with_comparison=len(holdings) - len(missing_comparison),
            missing_evidence_symbols=missing_evidence,
            missing_comparison_symbols=missing_comparison,
            notes=tuple(notes),
        )

    def _build_gaps(self, coverage: CoverageSummary) -> tuple[str, ...]:
        gaps: list[str] = []
        for sym in coverage.missing_evidence_symbols:
            gaps.append(f"Missing EvidenceBundle citation for {sym}.")
        for sym in coverage.missing_comparison_symbols:
            gaps.append(f"Missing ComparisonReport citation for {sym}.")
        return tuple(gaps)

    def _build_summary(
        self,
        context: PortfolioCitationContext,
        decision: tuple[DecisionPackReference, ...],
        evidence: tuple[EvidenceBundleReference, ...],
        comparison: tuple[ComparisonReportReference, ...],
        gaps: tuple[str, ...],
    ) -> PortfolioCitationSummary:
        versions = tuple(
            sorted(
                {
                    (
                        ref.methodology_id,
                        ref.methodology_version,
                        ref.instrument_key,
                    )
                    for ref in evidence
                }
            )
        )
        notes: list[str] = [
            "Citation aggregation only — no interpretation or comparison.",
        ]
        if not evidence and not comparison:
            notes.append("No optional EvidenceBundle or ComparisonReport citations.")
        if gaps:
            notes.append(f"{len(gaps)} citation gap(s) recorded.")
        return PortfolioCitationSummary(
            portfolio_id=context.portfolio.identity.portfolio_id,
            holding_count=len(context.portfolio.holdings),
            decision_citation_count=len(decision),
            evidence_citation_count=len(evidence),
            comparison_citation_count=len(comparison),
            bundle_versions=versions,
            notes=tuple(notes),
        )

    def _status(
        self,
        context: PortfolioCitationContext,
        coverage: CoverageSummary,
        evidence: tuple[EvidenceBundleReference, ...],
        comparison: tuple[ComparisonReportReference, ...],
    ) -> PortfolioCitationStatus:
        if coverage.holding_count == 0:
            return PortfolioCitationStatus.EMPTY
        if not evidence and not comparison:
            return PortfolioCitationStatus.ABSENT
        if coverage.missing_evidence_symbols or coverage.missing_comparison_symbols:
            return PortfolioCitationStatus.PARTIAL
        return PortfolioCitationStatus.COMPLETE

    def _warnings(
        self,
        coverage: CoverageSummary,
        status: PortfolioCitationStatus,
    ) -> tuple[str, ...]:
        warnings: list[str] = []
        if status is PortfolioCitationStatus.ABSENT:
            warnings.append(
                "Optional EvidenceBundle and ComparisonReport citations absent."
            )
        warnings.extend(coverage.notes)
        return tuple(dict.fromkeys(warnings))

    def _build_report(
        self,
        context: PortfolioCitationContext,
        citation_summary: PortfolioCitationSummary,
        coverage: CoverageSummary,
        gaps: tuple[str, ...],
        decision: tuple[DecisionPackReference, ...],
        evidence: tuple[EvidenceBundleReference, ...],
        comparison: tuple[ComparisonReportReference, ...],
    ) -> PortfolioReport:
        base = context.base_report
        if base is not None:
            return PortfolioReport(
                portfolio_id=context.portfolio.identity.portfolio_id,
                summary=base.summary,
                observations=base.observations,
                snapshot_id=base.snapshot_id,
                decision_pack_refs=decision,
                evidence_bundle_refs=evidence,
                comparison_report_refs=comparison,
                limitations=base.limitations
                + (
                    "Citation enrichment applied — aggregation only.",
                ),
                citation_summary=citation_summary,
                coverage_summary=coverage,
                citation_gaps=gaps,
            )
        return PortfolioReport(
            portfolio_id=context.portfolio.identity.portfolio_id,
            summary=PortfolioSummary(
                holding_count=len(context.portfolio.holdings),
                cash_weight=context.portfolio.cash_weight,
                coverage_notes=coverage.notes,
                limitation_notes=(
                    "Citation aggregation only — no observations generated.",
                ),
            ),
            observations=(),
            decision_pack_refs=decision,
            evidence_bundle_refs=evidence,
            comparison_report_refs=comparison,
            limitations=(
                "Citation aggregation only — no interpretation, comparison, "
                "or recommendations.",
            ),
            citation_summary=citation_summary,
            coverage_summary=coverage,
            citation_gaps=gaps,
        )
