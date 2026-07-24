"""Portfolio monitoring tests (C4.6)."""

from __future__ import annotations

import pytest

from portfolio import (
    DecisionPackReference,
    Portfolio,
    PortfolioChangeType,
    PortfolioError,
    PortfolioHolding,
    PortfolioIdentity,
    PortfolioMonitor,
    PortfolioMonitoringContext,
    PortfolioMonitoringStatus,
    PortfolioSnapshot,
    PortfolioType,
)


def _pack(symbol: str, digest: str = "abcdef0123456789") -> DecisionPackReference:
    return DecisionPackReference(instrument_symbol=symbol, digest=digest)


def _holding(symbol: str, *, weight: float | None = 0.1) -> PortfolioHolding:
    return PortfolioHolding(
        instrument_symbol=symbol,
        decision_pack_ref=_pack(symbol),
        weight=weight,
    )


def _identity() -> PortfolioIdentity:
    return PortfolioIdentity(
        portfolio_id="dsp.portfolio.demo",
        portfolio_name="Demo",
        portfolio_type=PortfolioType.WATCHLIST,
        base_currency="INR",
    )


def _snap(
    snap_id: str,
    as_of: str,
    holdings: tuple[PortfolioHolding, ...],
    *,
    cash: float | None = 0.05,
) -> PortfolioSnapshot:
    return PortfolioSnapshot(
        snapshot_id=snap_id,
        portfolio_id="dsp.portfolio.demo",
        as_of=as_of,
        holdings=holdings,
        cash_weight=cash,
    )


class TestMonitoringFlow:
    def test_initial_snapshot(self) -> None:
        monitor = PortfolioMonitor()
        snap = _snap("dsp.snapshot.1", "2026-07-01", (_holding("AAA"),))
        result = monitor.monitor(
            Portfolio(identity=_identity(), snapshots=(snap,))
        )
        assert result.status is PortfolioMonitoringStatus.INITIAL
        assert result.current_snapshot is not None
        assert result.previous_snapshot is None
        assert result.timeline.entries[0].snapshot_id == "dsp.snapshot.1"
        assert result.report.monitoring_status is PortfolioMonitoringStatus.INITIAL

    def test_second_snapshot_unchanged(self) -> None:
        monitor = PortfolioMonitor()
        h = (_holding("AAA"),)
        s1 = _snap("dsp.snapshot.1", "2026-07-01", h)
        s2 = _snap("dsp.snapshot.2", "2026-07-02", h)
        result = monitor.monitor(
            Portfolio(identity=_identity(), snapshots=(s1, s2))
        )
        assert result.status is PortfolioMonitoringStatus.UNCHANGED

    def test_holding_added_and_removed(self) -> None:
        monitor = PortfolioMonitor()
        s1 = _snap("dsp.snapshot.1", "2026-07-01", (_holding("AAA"),))
        s2 = _snap(
            "dsp.snapshot.2",
            "2026-07-02",
            (_holding("BBB"),),
        )
        changes = monitor.compare_snapshots(s1, s2)
        types = {c.change_type for c in changes}
        assert PortfolioChangeType.HOLDING_ADDED in types
        assert PortfolioChangeType.HOLDING_REMOVED in types

    def test_weight_changed(self) -> None:
        monitor = PortfolioMonitor()
        s1 = _snap("dsp.snapshot.1", "2026-07-01", (_holding("AAA", weight=0.1),))
        s2 = _snap("dsp.snapshot.2", "2026-07-02", (_holding("AAA", weight=0.2),))
        changes = monitor.compare_snapshots(s1, s2)
        assert any(c.change_type is PortfolioChangeType.WEIGHT_CHANGED for c in changes)

    def test_cash_changed(self) -> None:
        monitor = PortfolioMonitor()
        h = (_holding("AAA"),)
        s1 = _snap("dsp.snapshot.1", "2026-07-01", h, cash=0.05)
        s2 = _snap("dsp.snapshot.2", "2026-07-02", h, cash=0.15)
        changes = monitor.compare_snapshots(s1, s2)
        assert any(c.change_type is PortfolioChangeType.CASH_CHANGED for c in changes)

    def test_timeline_ordering(self) -> None:
        monitor = PortfolioMonitor()
        s1 = _snap("dsp.snapshot.b", "2026-07-02", (_holding("AAA"),))
        s2 = _snap("dsp.snapshot.a", "2026-07-01", (_holding("AAA"),))
        timeline = monitor.timeline(
            Portfolio(identity=_identity(), snapshots=(s1, s2))
        )
        assert [e.as_of for e in timeline.entries] == ["2026-07-01", "2026-07-02"]


class TestValidationAndImmutability:
    def test_duplicate_snapshot_pair_rejected(self) -> None:
        monitor = PortfolioMonitor()
        snap = _snap("dsp.snapshot.1", "2026-07-01", (_holding("AAA"),))
        with pytest.raises(PortfolioError, match="duplicate"):
            monitor.monitor(
                PortfolioMonitoringContext(
                    portfolio=Portfolio(identity=_identity(), snapshots=(snap,)),
                    current_snapshot=snap,
                    previous_snapshot=snap,
                )
            )

    def test_foreign_snapshot_rejected(self) -> None:
        monitor = PortfolioMonitor()
        foreign = PortfolioSnapshot(
            snapshot_id="dsp.snapshot.x",
            portfolio_id="dsp.portfolio.other",
            as_of="2026-07-01",
            holdings=(),
        )
        with pytest.raises(PortfolioError, match="foreign"):
            monitor.monitor(
                PortfolioMonitoringContext(
                    portfolio=Portfolio(identity=_identity()),
                    current_snapshot=foreign,
                )
            )

    def test_non_sequential_rejected(self) -> None:
        monitor = PortfolioMonitor()
        s1 = _snap("dsp.snapshot.1", "2026-07-02", (_holding("AAA"),))
        s2 = _snap("dsp.snapshot.2", "2026-07-01", (_holding("AAA"),))
        with pytest.raises(PortfolioError, match="non-sequential"):
            monitor.compare_snapshots(s1, s2)

    def test_immutability(self) -> None:
        monitor = PortfolioMonitor()
        result = monitor.monitor(
            Portfolio(
                identity=_identity(),
                snapshots=(_snap("dsp.snapshot.1", "2026-07-01", (_holding("AAA"),)),),
            )
        )
        with pytest.raises(AttributeError):
            result.changes = ()  # type: ignore[misc]
        with pytest.raises(AttributeError):
            result.timeline = result.timeline  # type: ignore[misc]

    def test_platform_exports(self) -> None:
        import dsp_platform as platform

        assert platform.PortfolioMonitor is PortfolioMonitor
        assert platform.PortfolioMonitoringStatus.CHANGED.value == "changed"
        assert platform.PortfolioTimeline is not None
        assert platform.PortfolioChangeType.HOLDING_ADDED.value == "holding_added"
