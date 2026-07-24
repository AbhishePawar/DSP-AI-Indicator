"""Portfolio qualitative analyzer tests (C4.3)."""

from __future__ import annotations

import pytest
from industry import EvidenceBundleReference, EvidenceBundleStatus

from portfolio import (
    ComparisonReportReference,
    DecisionPackReference,
    Portfolio,
    PortfolioAllocation,
    PortfolioAnalysisContext,
    PortfolioAnalysisStatus,
    PortfolioAnalyzer,
    PortfolioConstraint,
    PortfolioConstraintKind,
    PortfolioError,
    PortfolioHolding,
    PortfolioIdentity,
    PortfolioObservation,
    PortfolioSnapshot,
    PortfolioType,
)


def _pack(symbol: str) -> DecisionPackReference:
    return DecisionPackReference(
        instrument_symbol=symbol,
        digest="abcdef0123456789",
    )


def _evidence(symbol: str) -> EvidenceBundleReference:
    return EvidenceBundleReference(
        bundle_id=f"dsp.evidence_bundle.{symbol.lower()}",
        instrument_key=symbol,
        methodology_id="dsp.methodology.commercial_banking",
        methodology_version="1.0.0",
        digest="abcdef0123456789deadbeef",
        status=EvidenceBundleStatus.INCOMPLETE,
    )


def _identity() -> PortfolioIdentity:
    return PortfolioIdentity(
        portfolio_id="dsp.portfolio.demo",
        portfolio_name="Demo",
        portfolio_type=PortfolioType.MODEL,
        base_currency="INR",
    )


def _holding(
    symbol: str,
    *,
    weight: float | None = 0.1,
    evidence: bool = False,
    comparison: bool = False,
) -> PortfolioHolding:
    return PortfolioHolding(
        instrument_symbol=symbol,
        decision_pack_ref=_pack(symbol),
        weight=weight,
        evidence_bundle_ref=_evidence(symbol) if evidence else None,
        comparison_report_ref=(
            ComparisonReportReference(
                digest="compdigest01",
                included_symbols=(symbol,),
            )
            if comparison
            else None
        ),
    )


class TestEmptyAndSingle:
    def test_empty_portfolio(self) -> None:
        analyzer = PortfolioAnalyzer()
        result = analyzer.analyze(
            Portfolio(identity=_identity(), holdings=())
        )
        assert result.status is PortfolioAnalysisStatus.EMPTY
        assert result.summary.holding_count == 0
        assert any(d.code == "broadly_diversified" for d in result.descriptors)

    def test_single_holding_concentrated(self) -> None:
        analyzer = PortfolioAnalyzer()
        result = analyzer.analyze(
            Portfolio(
                identity=_identity(),
                holdings=(_holding("HDFCBANK", weight=0.95, evidence=True, comparison=True),),
                cash_weight=0.05,
            )
        )
        assert result.status is PortfolioAnalysisStatus.COMPLETE
        conc = next(d for d in result.descriptors if d.dimension == "concentration")
        assert conc.label == "Highly concentrated"


class TestMultipleHoldings:
    def test_concentrated_portfolio(self) -> None:
        analyzer = PortfolioAnalyzer()
        result = analyzer.analyze(
            Portfolio(
                identity=_identity(),
                holdings=(
                    _holding("AAA", weight=0.55, evidence=True, comparison=True),
                    _holding("BBB", weight=0.45, evidence=True, comparison=True),
                ),
            )
        )
        conc = next(d for d in result.descriptors if d.dimension == "concentration")
        assert conc.code == "highly_concentrated"

    def test_diversified_portfolio(self) -> None:
        analyzer = PortfolioAnalyzer()
        symbols = [f"S{i:02d}" for i in range(8)]
        holdings = tuple(
            _holding(s, weight=0.1, evidence=True, comparison=True) for s in symbols
        )
        snap = PortfolioSnapshot(
            snapshot_id="dsp.snapshot.1",
            portfolio_id="dsp.portfolio.demo",
            as_of="2026-07-21",
            holdings=holdings,
            allocation=PortfolioAllocation(
                by_sector=(
                    ("financials", 0.2),
                    ("technology", 0.2),
                    ("healthcare", 0.2),
                    ("energy", 0.2),
                    ("utilities", 0.2),
                )
            ),
        )
        result = analyzer.analyze(
            Portfolio(
                identity=_identity(),
                holdings=holdings,
                snapshots=(snap,),
                cash_weight=0.02,
            )
        )
        conc = next(d for d in result.descriptors if d.dimension == "concentration")
        div = next(d for d in result.descriptors if d.dimension == "diversification")
        assert conc.code == "broadly_diversified"
        assert div.code == "broad_sector_exposure"


class TestCashAndCoverage:
    def test_cash_position_descriptors(self) -> None:
        analyzer = PortfolioAnalyzer()
        low = analyzer.describe(
            Portfolio(
                identity=_identity(),
                holdings=(_holding("AAA", evidence=True, comparison=True),),
                cash_weight=0.01,
            )
        )
        mid = analyzer.describe(
            Portfolio(
                identity=_identity(),
                holdings=(_holding("AAA", evidence=True, comparison=True),),
                cash_weight=0.10,
            )
        )
        high = analyzer.describe(
            Portfolio(
                identity=_identity(),
                holdings=(_holding("AAA", evidence=True, comparison=True),),
                cash_weight=0.30,
            )
        )
        assert next(d for d in low if d.dimension == "cash_position").code == (
            "fully_invested"
        )
        assert next(d for d in mid if d.dimension == "cash_position").code == (
            "moderate_cash_reserve"
        )
        assert next(d for d in high if d.dimension == "cash_position").code == (
            "high_cash_reserve"
        )

    def test_missing_evidence(self) -> None:
        analyzer = PortfolioAnalyzer()
        result = analyzer.analyze(
            Portfolio(
                identity=_identity(),
                holdings=(_holding("HDFCBANK", comparison=True),),
            )
        )
        assert result.status is PortfolioAnalysisStatus.PARTIAL
        assert "HDFCBANK" in result.coverage.missing_evidence_symbols
        ev = next(d for d in result.descriptors if d.dimension == "evidence_coverage")
        assert ev.code == "evidence_gaps_exist"

    def test_missing_comparison(self) -> None:
        analyzer = PortfolioAnalyzer()
        result = analyzer.analyze(
            Portfolio(
                identity=_identity(),
                holdings=(_holding("HDFCBANK", evidence=True),),
            )
        )
        assert result.status is PortfolioAnalysisStatus.PARTIAL
        assert "HDFCBANK" in result.coverage.missing_comparison_symbols


class TestValidationAndImmutability:
    def test_foreign_evidence_citation_rejected(self) -> None:
        analyzer = PortfolioAnalyzer()
        with pytest.raises(PortfolioError, match="foreign"):
            analyzer.analyze(
                PortfolioAnalysisContext(
                    portfolio=Portfolio(
                        identity=_identity(),
                        holdings=(_holding("HDFCBANK"),),
                    ),
                    evidence_bundle_refs=(_evidence("ICICIBANK"),),
                )
            )

    def test_duplicate_observations_rejected(self) -> None:
        analyzer = PortfolioAnalyzer()
        with pytest.raises(PortfolioError, match="duplicate observations"):
            analyzer._reject_duplicate_observations(
                (
                    PortfolioObservation(code="same", text="One note."),
                    PortfolioObservation(code="same", text="Two note."),
                )
            )

    def test_immutability(self) -> None:
        analyzer = PortfolioAnalyzer()
        result = analyzer.analyze(
            Portfolio(
                identity=_identity(),
                holdings=(_holding("AAA", evidence=True, comparison=True),),
            )
        )
        with pytest.raises(AttributeError):
            result.summary = result.summary  # type: ignore[misc]
        with pytest.raises(AttributeError):
            result.descriptors = ()  # type: ignore[misc]

    def test_summarize_and_describe_and_many(self) -> None:
        analyzer = PortfolioAnalyzer()
        portfolio = Portfolio(
            identity=_identity(),
            holdings=(_holding("AAA", evidence=True, comparison=True),),
            constraints=(
                PortfolioConstraint(
                    id="dsp.constraint.max_pos",
                    kind=PortfolioConstraintKind.MAX_POSITION_WEIGHT,
                    target="position",
                    limit=0.2,
                ),
            ),
        )
        summary = analyzer.summarize(portfolio)
        descriptors = analyzer.describe(portfolio)
        many = analyzer.analyze_many((portfolio, portfolio))
        assert summary.holding_count == 1
        assert descriptors
        assert len(many) == 2
        assert any("not evaluated" in n.lower() for n in many[0].constraint_gap_notes)

    def test_platform_backward_compatible(self) -> None:
        import dsp_platform as platform

        assert platform.PortfolioAnalyzer is PortfolioAnalyzer
        assert platform.PortfolioAnalysisStatus.PARTIAL.value == "partial"
        assert platform.PortfolioDescriptor is not None
