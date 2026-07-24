"""Portfolio domain model tests (C4.1)."""

from __future__ import annotations

import pytest
from core.exceptions import ValidationError
from industry import EvidenceBundleReference, EvidenceBundleStatus

from portfolio import (
    DecisionPackReference,
    Portfolio,
    PortfolioAllocation,
    PortfolioConstraint,
    PortfolioConstraintKind,
    PortfolioError,
    PortfolioHolding,
    PortfolioIdentity,
    PortfolioObservation,
    PortfolioReport,
    PortfolioSnapshot,
    PortfolioSummary,
    PortfolioType,
)


def _pack_ref(symbol: str = "HDFCBANK") -> DecisionPackReference:
    return DecisionPackReference(
        instrument_symbol=symbol,
        digest="abcdef0123456789",
    )


def _holding(symbol: str = "HDFCBANK", *, weight: float = 0.1) -> PortfolioHolding:
    return PortfolioHolding(
        instrument_symbol=symbol,
        decision_pack_ref=_pack_ref(symbol),
        weight=weight,
    )


def _identity(portfolio_id: str = "dsp.portfolio.demo") -> PortfolioIdentity:
    return PortfolioIdentity(
        portfolio_id=portfolio_id,
        portfolio_name="Demo Portfolio",
        portfolio_type=PortfolioType.MODEL,
        created_at="2026-07-21T00:00:00Z",
        base_currency="INR",
    )


class TestConstruction:
    def test_aggregate_root(self) -> None:
        holding = _holding()
        constraint = PortfolioConstraint(
            id="dsp.constraint.max_pos",
            kind=PortfolioConstraintKind.MAX_POSITION_WEIGHT,
            target="position",
            limit=0.1,
        )
        snap = PortfolioSnapshot(
            snapshot_id="dsp.snapshot.1",
            portfolio_id="dsp.portfolio.demo",
            as_of="2026-07-21",
            holdings=(holding,),
            cash_weight=0.05,
            allocation=PortfolioAllocation(
                by_instrument=(("hdfcbank", 0.1),),
                cash_weight=0.05,
            ),
        )
        portfolio = Portfolio(
            identity=_identity(),
            holdings=(holding,),
            constraints=(constraint,),
            snapshots=(snap,),
            cash_weight=0.05,
        )
        assert portfolio.portfolio_id == "dsp.portfolio.demo"
        assert len(portfolio.holdings) == 1
        assert len(portfolio.snapshots) == 1

    def test_report_presentation(self) -> None:
        report = PortfolioReport(
            portfolio_id="dsp.portfolio.demo",
            summary=PortfolioSummary(
                holding_count=1,
                coverage_notes=("One DecisionPack citation attached.",),
            ),
            observations=(
                PortfolioObservation(
                    code="cash_posture",
                    text="Cash weight is recorded descriptively.",
                ),
            ),
            decision_pack_refs=(_pack_ref(),),
        )
        assert report.summary.holding_count == 1


class TestValidation:
    def test_duplicate_holdings_rejected(self) -> None:
        with pytest.raises(PortfolioError, match="duplicate holding"):
            Portfolio(
                identity=_identity(),
                holdings=(_holding("AAA"), _holding("AAA")),
            )

    def test_missing_decision_pack_rejected(self) -> None:
        with pytest.raises(TypeError):
            PortfolioHolding(instrument_symbol="AAA")  # type: ignore[call-arg]

    def test_pack_symbol_mismatch_rejected(self) -> None:
        with pytest.raises(ValidationError, match="must match"):
            PortfolioHolding(
                instrument_symbol="HDFCBANK",
                decision_pack_ref=_pack_ref("ICICIBANK"),
            )

    def test_foreign_snapshot_rejected(self) -> None:
        with pytest.raises(PortfolioError, match="does not match"):
            Portfolio(
                identity=_identity("dsp.portfolio.a"),
                snapshots=(
                    PortfolioSnapshot(
                        snapshot_id="dsp.snapshot.1",
                        portfolio_id="dsp.portfolio.other",
                        as_of="2026-07-21",
                        holdings=(),
                    ),
                ),
            )

    def test_evidence_ref_instrument_mismatch(self) -> None:
        with pytest.raises(ValidationError, match="evidence_bundle_ref"):
            PortfolioHolding(
                instrument_symbol="HDFCBANK",
                decision_pack_ref=_pack_ref("HDFCBANK"),
                evidence_bundle_ref=EvidenceBundleReference(
                    bundle_id="dsp.evidence_bundle.x",
                    instrument_key="ICICIBANK",
                    methodology_id="dsp.methodology.commercial_banking",
                    methodology_version="1.0.0",
                    digest="abcdef0123456789deadbeef",
                    status=EvidenceBundleStatus.INCOMPLETE,
                ),
            )

    def test_observation_rejects_ranking_language(self) -> None:
        with pytest.raises(ValidationError, match="forbidden"):
            PortfolioObservation(code="x", text="This is the best portfolio")

    def test_duplicate_constraint_ids(self) -> None:
        c = PortfolioConstraint(
            id="dsp.constraint.x",
            kind=PortfolioConstraintKind.MIN_CASH_WEIGHT,
            target="cash",
            limit=0.05,
        )
        with pytest.raises(PortfolioError, match="duplicate constraint"):
            Portfolio(identity=_identity(), constraints=(c, c))


class TestImmutability:
    def test_frozen(self) -> None:
        portfolio = Portfolio(identity=_identity(), holdings=(_holding(),))
        with pytest.raises(AttributeError):
            portfolio.holdings = ()  # type: ignore[misc]
        with pytest.raises(AttributeError):
            portfolio.identity.portfolio_name = "x"  # type: ignore[misc]
