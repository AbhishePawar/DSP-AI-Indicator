"""Portfolio Assembler tests (C4.2)."""

from __future__ import annotations

import pytest
from industry import EvidenceBundleReference, EvidenceBundleStatus

from portfolio import (
    ComparisonReportReference,
    DecisionPackReference,
    PortfolioAssembler,
    PortfolioAssemblyContext,
    PortfolioAssemblyStatus,
    PortfolioConstraint,
    PortfolioConstraintKind,
    PortfolioError,
    PortfolioHoldingInput,
    PortfolioIdentity,
    PortfolioSnapshot,
    PortfolioType,
)


def _identity() -> PortfolioIdentity:
    return PortfolioIdentity(
        portfolio_id="dsp.portfolio.demo",
        portfolio_name="Demo",
        portfolio_type=PortfolioType.MODEL,
        base_currency="INR",
    )


def _pack(symbol: str, digest: str = "abcdef0123456789") -> DecisionPackReference:
    return DecisionPackReference(instrument_symbol=symbol, digest=digest)


def _holding_input(symbol: str, *, weight: float = 0.1) -> PortfolioHoldingInput:
    return PortfolioHoldingInput(decision_pack_ref=_pack(symbol), weight=weight)


def _evidence(symbol: str) -> EvidenceBundleReference:
    return EvidenceBundleReference(
        bundle_id=f"dsp.evidence_bundle.{symbol.lower()}",
        instrument_key=symbol,
        methodology_id="dsp.methodology.commercial_banking",
        methodology_version="1.0.0",
        digest="abcdef0123456789deadbeef",
        status=EvidenceBundleStatus.INCOMPLETE,
    )


class TestSuccessfulAssembly:
    def test_assemble_with_optional_citations(self) -> None:
        assembler = PortfolioAssembler()
        ctx = PortfolioAssemblyContext(
            identity=_identity(),
            holdings=(
                _holding_input("HDFCBANK"),
                _holding_input("ICICIBANK"),
            ),
            evidence_bundle_refs=(_evidence("HDFCBANK"), _evidence("ICICIBANK")),
            comparison_report_refs=(
                ComparisonReportReference(
                    digest="compdigest01",
                    methodology_id="dsp.methodology.commercial_banking",
                    included_symbols=("HDFCBANK", "ICICIBANK"),
                ),
            ),
            constraints=(
                PortfolioConstraint(
                    id="dsp.constraint.max_pos",
                    kind=PortfolioConstraintKind.MAX_POSITION_WEIGHT,
                    target="position",
                    limit=0.2,
                ),
            ),
            cash_weight=0.05,
            as_of="2026-07-21",
        )
        result = assembler.assemble(ctx)
        assert result.status is PortfolioAssemblyStatus.COMPLETE
        assert len(result.portfolio.holdings) == 2
        assert result.portfolio.holdings[0].evidence_bundle_ref is not None
        assert result.portfolio.holdings[0].comparison_report_ref is not None
        assert len(result.portfolio.snapshots) == 1
        assert result.missing_evidence_symbols == ()

    def test_assemble_many_deterministic(self) -> None:
        assembler = PortfolioAssembler()
        ctx = PortfolioAssemblyContext(
            identity=_identity(),
            holdings=(_holding_input("AAA"),),
            evidence_bundle_refs=(_evidence("AAA"),),
        )
        a = assembler.assemble_many((ctx, ctx))
        b = assembler.assemble_many((ctx, ctx))
        assert a == b

    def test_partial_without_evidence(self) -> None:
        assembler = PortfolioAssembler()
        result = assembler.assemble(
            PortfolioAssemblyContext(
                identity=_identity(),
                holdings=(_holding_input("HDFCBANK"),),
            )
        )
        assert result.status is PortfolioAssemblyStatus.PARTIAL
        assert result.missing_evidence_symbols == ("HDFCBANK",)
        assert result.warnings


class TestValidation:
    def test_duplicate_holdings_rejected(self) -> None:
        assembler = PortfolioAssembler()
        with pytest.raises(PortfolioError, match="duplicate"):
            assembler.assemble(
                PortfolioAssemblyContext(
                    identity=_identity(),
                    holdings=(
                        _holding_input("HDFCBANK"),
                        _holding_input("HDFCBANK"),
                    ),
                )
            )

    def test_missing_decision_pack_inputs_rejected(self) -> None:
        with pytest.raises(Exception):
            PortfolioAssemblyContext(identity=_identity(), holdings=())

    def test_orphan_evidence_rejected(self) -> None:
        assembler = PortfolioAssembler()
        with pytest.raises(PortfolioError, match="orphan EvidenceBundle"):
            assembler.assemble(
                PortfolioAssemblyContext(
                    identity=_identity(),
                    holdings=(_holding_input("HDFCBANK"),),
                    evidence_bundle_refs=(_evidence("ICICIBANK"),),
                )
            )

    def test_orphan_comparison_rejected(self) -> None:
        assembler = PortfolioAssembler()
        with pytest.raises(PortfolioError, match="orphan ComparisonReport"):
            assembler.assemble(
                PortfolioAssemblyContext(
                    identity=_identity(),
                    holdings=(_holding_input("HDFCBANK"),),
                    comparison_report_refs=(
                        ComparisonReportReference(
                            digest="compdigest01",
                            included_symbols=("SBIN",),
                        ),
                    ),
                )
            )

    def test_foreign_snapshot_rejected(self) -> None:
        assembler = PortfolioAssembler()
        with pytest.raises(PortfolioError, match="foreign ownership"):
            assembler.assemble(
                PortfolioAssemblyContext(
                    identity=_identity(),
                    holdings=(_holding_input("HDFCBANK"),),
                    evidence_bundle_refs=(_evidence("HDFCBANK"),),
                    snapshots=(
                        PortfolioSnapshot(
                            snapshot_id="dsp.snapshot.x",
                            portfolio_id="dsp.portfolio.other",
                            as_of="2026-07-21",
                            holdings=(),
                        ),
                    ),
                )
            )

    def test_portfolio_metadata(self) -> None:
        assembler = PortfolioAssembler()
        ctx = PortfolioAssemblyContext(
            identity=_identity(),
            holdings=(_holding_input("HDFCBANK"),),
            evidence_bundle_refs=(_evidence("HDFCBANK"),),
        )
        assert assembler.portfolio_metadata(ctx).portfolio_id == "dsp.portfolio.demo"

    def test_optional_comparison_only(self) -> None:
        assembler = PortfolioAssembler()
        result = assembler.assemble(
            PortfolioAssemblyContext(
                identity=_identity(),
                holdings=(_holding_input("HDFCBANK"),),
                evidence_bundle_refs=(_evidence("HDFCBANK"),),
                comparison_report_refs=(
                    ComparisonReportReference(
                        digest="compdigest01",
                        included_symbols=("HDFCBANK",),
                    ),
                ),
            )
        )
        assert result.status is PortfolioAssemblyStatus.COMPLETE
        assert result.portfolio.holdings[0].comparison_report_ref is not None

    def test_validate_inputs_ok(self) -> None:
        assembler = PortfolioAssembler()
        ctx = PortfolioAssemblyContext(
            identity=_identity(),
            holdings=(_holding_input("HDFCBANK"),),
            evidence_bundle_refs=(_evidence("HDFCBANK"),),
        )
        assembler.validate_inputs(ctx)


class TestBackwardCompatibility:
    def test_platform_reexports_assembler(self) -> None:
        import dsp_platform as platform

        assert platform.PortfolioAssembler is PortfolioAssembler
        assert platform.PortfolioAssemblyStatus is PortfolioAssemblyStatus
        assert platform.Portfolio is not None
        assert platform.DecisionPackReference is DecisionPackReference
