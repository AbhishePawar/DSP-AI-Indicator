"""Portfolio Monitoring — historical state evolution only (C4.6).

Records and summarizes PortfolioSnapshot changes over time.
Never analyzes quality, optimizes, computes risk, or recommends trades.
"""

from __future__ import annotations

from dataclasses import dataclass

from portfolio.enums import PortfolioChangeType, PortfolioMonitoringStatus
from portfolio.exceptions import PortfolioError
from portfolio.models import (
    Portfolio,
    PortfolioChange,
    PortfolioConstraint,
    PortfolioHolding,
    PortfolioMonitoringSummary,
    PortfolioReport,
    PortfolioSnapshot,
    PortfolioSummary,
    PortfolioTimeline,
)

__all__ = [
    "PortfolioMonitoringContext",
    "PortfolioMonitoringResult",
    "PortfolioMonitor",
]


@dataclass(frozen=True, slots=True)
class PortfolioMonitoringContext:
    """Inputs for portfolio history monitoring."""

    portfolio: Portfolio
    current_snapshot: PortfolioSnapshot | None = None
    previous_snapshot: PortfolioSnapshot | None = None
    previous_constraints: tuple[PortfolioConstraint, ...] | None = None
    base_report: PortfolioReport | None = None

    def __post_init__(self) -> None:
        if self.portfolio is None:
            msg = "portfolio is required"
            raise PortfolioError(msg)
        if self.previous_constraints is not None:
            object.__setattr__(
                self, "previous_constraints", tuple(self.previous_constraints)
            )


@dataclass(frozen=True, slots=True)
class PortfolioMonitoringResult:
    """Monitoring output — history and descriptive changes only."""

    portfolio_id: str
    status: PortfolioMonitoringStatus
    current_snapshot: PortfolioSnapshot | None
    previous_snapshot: PortfolioSnapshot | None
    changes: tuple[PortfolioChange, ...]
    timeline: PortfolioTimeline
    summary: PortfolioMonitoringSummary
    report: PortfolioReport
    warnings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "changes", tuple(self.changes))
        object.__setattr__(self, "warnings", tuple(self.warnings))


class PortfolioMonitor:
    """Canonical subsystem for Portfolio evolution tracking.

    Independent from Risk Intelligence — records history only.
    """

    def validate_inputs(self, context: PortfolioMonitoringContext) -> None:
        """Reject foreign ownership, duplicates, and non-sequential pairs."""
        portfolio = context.portfolio
        if portfolio is None or portfolio.identity is None:
            msg = "invalid ownership: portfolio identity required"
            raise PortfolioError(msg)
        pid = portfolio.identity.portfolio_id

        seen: set[str] = set()
        for snap in portfolio.snapshots:
            if snap.portfolio_id != pid:
                msg = f"foreign snapshots: {snap.snapshot_id!r}"
                raise PortfolioError(msg)
            if snap.snapshot_id in seen:
                msg = f"duplicate snapshot ids: {snap.snapshot_id!r}"
                raise PortfolioError(msg)
            seen.add(snap.snapshot_id)

        for label, snap in (
            ("current_snapshot", context.current_snapshot),
            ("previous_snapshot", context.previous_snapshot),
        ):
            if snap is None:
                continue
            if snap.portfolio_id != pid:
                msg = f"foreign snapshots: {label} {snap.snapshot_id!r}"
                raise PortfolioError(msg)

        if (
            context.current_snapshot is not None
            and context.previous_snapshot is not None
        ):
            if (
                context.current_snapshot.snapshot_id
                == context.previous_snapshot.snapshot_id
            ):
                msg = (
                    "duplicate snapshot ids: current and previous are "
                    f"{context.current_snapshot.snapshot_id!r}"
                )
                raise PortfolioError(msg)
            if context.previous_snapshot.as_of > context.current_snapshot.as_of:
                msg = (
                    "non-sequential timeline: previous as_of "
                    f"{context.previous_snapshot.as_of!r} is after current "
                    f"{context.current_snapshot.as_of!r}"
                )
                raise PortfolioError(msg)

        if context.base_report is not None and context.base_report.portfolio_id != pid:
            msg = (
                "invalid ownership: base_report "
                f"{context.base_report.portfolio_id!r}"
            )
            raise PortfolioError(msg)

    def timeline(
        self, context: PortfolioMonitoringContext | Portfolio
    ) -> PortfolioTimeline:
        """Build an ordered PortfolioTimeline from portfolio snapshots."""
        ctx = self._as_context(context)
        self.validate_inputs(ctx)
        return self._build_timeline(ctx)

    def compare_snapshots(
        self,
        previous: PortfolioSnapshot,
        current: PortfolioSnapshot,
        *,
        previous_constraints: tuple[PortfolioConstraint, ...] | None = None,
        current_constraints: tuple[PortfolioConstraint, ...] = (),
    ) -> tuple[PortfolioChange, ...]:
        """Detect descriptive changes between two snapshots."""
        if previous.portfolio_id != current.portfolio_id:
            msg = "foreign snapshots: portfolio_id mismatch in compare_snapshots"
            raise PortfolioError(msg)
        if previous.snapshot_id == current.snapshot_id:
            msg = f"duplicate snapshot ids: {previous.snapshot_id!r}"
            raise PortfolioError(msg)
        if previous.as_of > current.as_of:
            msg = "non-sequential timeline in compare_snapshots"
            raise PortfolioError(msg)
        return self._diff_snapshots(
            previous,
            current,
            previous_constraints=previous_constraints,
            current_constraints=current_constraints,
        )

    def changes(
        self, context: PortfolioMonitoringContext | Portfolio
    ) -> tuple[PortfolioChange, ...]:
        """Return detected changes for the monitoring context."""
        ctx = self._as_context(context)
        self.validate_inputs(ctx)
        current, previous = self._resolve_pair(ctx)
        if current is None:
            return ()
        if previous is None:
            return (
                PortfolioChange(
                    change_type=PortfolioChangeType.SNAPSHOT_RECORDED,
                    description=(
                        f"Initial snapshot {current.snapshot_id} recorded."
                    ),
                    to_snapshot_id=current.snapshot_id,
                ),
            )
        return self._diff_snapshots(
            previous,
            current,
            previous_constraints=ctx.previous_constraints,
            current_constraints=ctx.portfolio.constraints,
        )

    def monitor(
        self, context: PortfolioMonitoringContext | Portfolio
    ) -> PortfolioMonitoringResult:
        """Run full monitoring — history and change detection only."""
        ctx = self._as_context(context)
        self.validate_inputs(ctx)

        timeline = self._build_timeline(ctx)
        current, previous = self._resolve_pair(ctx)
        changes = self.changes(ctx)
        status = self._status(current, previous, changes)
        summary = PortfolioMonitoringSummary(
            portfolio_id=ctx.portfolio.identity.portfolio_id,
            snapshot_count=len(timeline.entries),
            change_count=len(changes),
            status=status,
            notes=(
                "Monitoring records history only — no risk, returns, or trades.",
            ),
        )
        warnings: list[str] = []
        if status is PortfolioMonitoringStatus.EMPTY:
            warnings.append("No snapshots available for monitoring.")
        elif status is PortfolioMonitoringStatus.INITIAL:
            warnings.append("Only an initial snapshot is available.")
        report = self._build_report(ctx, summary, timeline, changes, status, current)

        return PortfolioMonitoringResult(
            portfolio_id=ctx.portfolio.identity.portfolio_id,
            status=status,
            current_snapshot=current,
            previous_snapshot=previous,
            changes=changes,
            timeline=timeline,
            summary=summary,
            report=report,
            warnings=tuple(warnings),
        )

    def _as_context(
        self, context: PortfolioMonitoringContext | Portfolio
    ) -> PortfolioMonitoringContext:
        if isinstance(context, Portfolio):
            return PortfolioMonitoringContext(portfolio=context)
        return context

    def _ordered_snapshots(
        self, portfolio: Portfolio
    ) -> tuple[PortfolioSnapshot, ...]:
        return tuple(
            sorted(
                portfolio.snapshots,
                key=lambda s: (s.as_of, s.snapshot_id),
            )
        )

    def _build_timeline(
        self, context: PortfolioMonitoringContext
    ) -> PortfolioTimeline:
        entries = list(self._ordered_snapshots(context.portfolio))
        # Include explicit current/previous if not already on the aggregate.
        for snap in (context.previous_snapshot, context.current_snapshot):
            if snap is None:
                continue
            if all(s.snapshot_id != snap.snapshot_id for s in entries):
                entries.append(snap)
        entries = sorted(entries, key=lambda s: (s.as_of, s.snapshot_id))
        return PortfolioTimeline(
            portfolio_id=context.portfolio.identity.portfolio_id,
            entries=tuple(entries),
            notes=("Timeline ordered by as_of, then snapshot_id.",),
        )

    def _resolve_pair(
        self, context: PortfolioMonitoringContext
    ) -> tuple[PortfolioSnapshot | None, PortfolioSnapshot | None]:
        ordered = list(self._ordered_snapshots(context.portfolio))
        for snap in (context.previous_snapshot, context.current_snapshot):
            if snap is None:
                continue
            if all(s.snapshot_id != snap.snapshot_id for s in ordered):
                ordered.append(snap)
        ordered = sorted(ordered, key=lambda s: (s.as_of, s.snapshot_id))

        current = context.current_snapshot
        if current is None and ordered:
            current = ordered[-1]

        if context.previous_snapshot is not None:
            previous = context.previous_snapshot
        elif current is None:
            previous = None
        else:
            before = [
                s
                for s in ordered
                if (s.as_of, s.snapshot_id) < (current.as_of, current.snapshot_id)
            ]
            previous = before[-1] if before else None
        return current, previous

    def _status(
        self,
        current: PortfolioSnapshot | None,
        previous: PortfolioSnapshot | None,
        changes: tuple[PortfolioChange, ...],
    ) -> PortfolioMonitoringStatus:
        if current is None:
            return PortfolioMonitoringStatus.EMPTY
        if previous is None:
            return PortfolioMonitoringStatus.INITIAL
        material = tuple(
            c
            for c in changes
            if c.change_type is not PortfolioChangeType.SNAPSHOT_RECORDED
        )
        if not material:
            return PortfolioMonitoringStatus.UNCHANGED
        return PortfolioMonitoringStatus.CHANGED

    def _diff_snapshots(
        self,
        previous: PortfolioSnapshot,
        current: PortfolioSnapshot,
        *,
        previous_constraints: tuple[PortfolioConstraint, ...] | None,
        current_constraints: tuple[PortfolioConstraint, ...],
    ) -> tuple[PortfolioChange, ...]:
        changes: list[PortfolioChange] = []
        prev_map = {h.instrument_symbol: h for h in previous.holdings}
        curr_map = {h.instrument_symbol: h for h in current.holdings}
        from_id = previous.snapshot_id
        to_id = current.snapshot_id

        added = sorted(set(curr_map) - set(prev_map))
        removed = sorted(set(prev_map) - set(curr_map))
        for sym in added:
            changes.append(
                PortfolioChange(
                    change_type=PortfolioChangeType.HOLDING_ADDED,
                    description=f"Holding added: {sym}.",
                    subjects=(sym,),
                    from_snapshot_id=from_id,
                    to_snapshot_id=to_id,
                )
            )
        for sym in removed:
            changes.append(
                PortfolioChange(
                    change_type=PortfolioChangeType.HOLDING_REMOVED,
                    description=f"Holding removed: {sym}.",
                    subjects=(sym,),
                    from_snapshot_id=from_id,
                    to_snapshot_id=to_id,
                )
            )

        for sym in sorted(set(prev_map) & set(curr_map)):
            prev_h = prev_map[sym]
            curr_h = curr_map[sym]
            if prev_h.weight != curr_h.weight:
                changes.append(
                    PortfolioChange(
                        change_type=PortfolioChangeType.WEIGHT_CHANGED,
                        description=(
                            f"Weight changed for {sym}: "
                            f"{prev_h.weight} -> {curr_h.weight}."
                        ),
                        subjects=(sym,),
                        from_snapshot_id=from_id,
                        to_snapshot_id=to_id,
                    )
                )
            if self._decision_key(prev_h) != self._decision_key(curr_h):
                changes.append(
                    PortfolioChange(
                        change_type=PortfolioChangeType.DECISION_COVERAGE_CHANGED,
                        description=(
                            f"Decision coverage changed for {sym}."
                        ),
                        subjects=(sym,),
                        from_snapshot_id=from_id,
                        to_snapshot_id=to_id,
                    )
                )
            if self._evidence_key(prev_h) != self._evidence_key(curr_h):
                changes.append(
                    PortfolioChange(
                        change_type=PortfolioChangeType.EVIDENCE_COVERAGE_CHANGED,
                        description=(
                            f"Evidence coverage changed for {sym}."
                        ),
                        subjects=(sym,),
                        from_snapshot_id=from_id,
                        to_snapshot_id=to_id,
                    )
                )

        if previous.cash_weight != current.cash_weight:
            changes.append(
                PortfolioChange(
                    change_type=PortfolioChangeType.CASH_CHANGED,
                    description=(
                        f"Cash changed: {previous.cash_weight} -> "
                        f"{current.cash_weight}."
                    ),
                    from_snapshot_id=from_id,
                    to_snapshot_id=to_id,
                )
            )

        # Aggregate evidence coverage count shift (portfolio-level note).
        prev_ev = sum(1 for h in previous.holdings if h.evidence_bundle_ref)
        curr_ev = sum(1 for h in current.holdings if h.evidence_bundle_ref)
        if prev_ev != curr_ev and not any(
            c.change_type is PortfolioChangeType.EVIDENCE_COVERAGE_CHANGED
            for c in changes
        ):
            changes.append(
                PortfolioChange(
                    change_type=PortfolioChangeType.EVIDENCE_COVERAGE_CHANGED,
                    description=(
                        f"Evidence coverage count changed: {prev_ev} -> {curr_ev}."
                    ),
                    from_snapshot_id=from_id,
                    to_snapshot_id=to_id,
                )
            )

        if previous_constraints is not None:
            if self._constraints_key(previous_constraints) != self._constraints_key(
                current_constraints
            ):
                changes.append(
                    PortfolioChange(
                        change_type=PortfolioChangeType.CONSTRAINT_METADATA_CHANGED,
                        description="Constraint metadata changed.",
                        from_snapshot_id=from_id,
                        to_snapshot_id=to_id,
                    )
                )

        return tuple(changes)

    def _decision_key(self, holding: PortfolioHolding) -> tuple[str, str]:
        ref = holding.decision_pack_ref
        return (ref.instrument_symbol, ref.digest)

    def _evidence_key(
        self, holding: PortfolioHolding
    ) -> tuple[str, str, str] | None:
        ref = holding.evidence_bundle_ref
        if ref is None:
            return None
        return (ref.bundle_id, ref.digest, ref.instrument_key)

    def _constraints_key(
        self, constraints: tuple[PortfolioConstraint, ...]
    ) -> tuple[tuple[str, str, str, float], ...]:
        return tuple(
            sorted(
                (c.id, c.kind.value, c.target, float(c.limit)) for c in constraints
            )
        )

    def _build_report(
        self,
        context: PortfolioMonitoringContext,
        summary: PortfolioMonitoringSummary,
        timeline: PortfolioTimeline,
        changes: tuple[PortfolioChange, ...],
        status: PortfolioMonitoringStatus,
        current: PortfolioSnapshot | None,
    ) -> PortfolioReport:
        base = context.base_report
        recent = changes[-20:] if changes else ()
        if base is not None:
            return PortfolioReport(
                portfolio_id=context.portfolio.identity.portfolio_id,
                summary=base.summary,
                observations=base.observations,
                snapshot_id=(
                    base.snapshot_id
                    if current is None
                    else current.snapshot_id
                ),
                decision_pack_refs=base.decision_pack_refs,
                evidence_bundle_refs=base.evidence_bundle_refs,
                comparison_report_refs=base.comparison_report_refs,
                limitations=base.limitations
                + (
                    "Monitoring enrichment applied — history only.",
                ),
                citation_summary=base.citation_summary,
                coverage_summary=base.coverage_summary,
                citation_gaps=base.citation_gaps,
                monitoring_summary=summary,
                timeline=timeline,
                recent_changes=recent,
                monitoring_status=status,
            )
        holding_count = (
            len(current.holdings)
            if current is not None
            else len(context.portfolio.holdings)
        )
        return PortfolioReport(
            portfolio_id=context.portfolio.identity.portfolio_id,
            summary=PortfolioSummary(
                holding_count=holding_count,
                cash_weight=(
                    None if current is None else current.cash_weight
                ),
                limitation_notes=(
                    "Monitoring report — history only; no investment evaluation.",
                ),
            ),
            observations=(),
            snapshot_id=None if current is None else current.snapshot_id,
            limitations=(
                "Monitoring records history only — no risk, returns, "
                "optimization, or trade recommendations.",
            ),
            monitoring_summary=summary,
            timeline=timeline,
            recent_changes=recent,
            monitoring_status=status,
        )
