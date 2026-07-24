"""Portfolio citation enrichment tests (C4.4)."""

from __future__ import annotations

import pytest
from industry import EvidenceBundleReference, EvidenceBundleStatus

from portfolio import (
    ComparisonReportReference,
    DecisionPackReference,
    Portfolio,
    PortfolioCitationAssembler,
    PortfolioCitationContext,
    PortfolioCitationStatus,
    PortfolioError,
    PortfolioHolding,
    PortfolioIdentity,
    PortfolioType,
)


def _pack(symbol: str, digest: str = "abcdef0123456789") -> DecisionPackReference:
    return DecisionPackReference(instrument_symbol=symbol, digest=digest)


def _evidence(symbol: str) -> EvidenceBundleReference:
    return EvidenceBundleReference(
        bundle_id=f"dsp.evidence_bundle.{symbol.lower()}",
        instrument_key=symbol,
        methodology_id="dsp.methodology.commercial_banking",
        methodology_version="1.0.0",
        digest="abcdef0123456789deadbeef",
        status=EvidenceBundleStatus.INCOMPLETE,
    )


def _comparison(*symbols: str) -> ComparisonReportReference:
    return ComparisonReportReference(
        digest="compdigest01",
        methodology_id="dsp.methodology.commercial_banking",
        included_symbols=symbols,
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
    evidence: bool = False,
    comparison: bool = False,
) -> PortfolioHolding:
    return PortfolioHolding(
        instrument_symbol=symbol,
        decision_pack_ref=_pack(symbol),
        weight=0.1,
        evidence_bundle_ref=_evidence(symbol) if evidence else None,
        comparison_report_ref=(
            _comparison(symbol) if comparison else None
        ),
    )


class TestCitationAggregation:
    def test_portfolio_without_optional_citations(self) -> None:
        assembler = PortfolioCitationAssembler()
        result = assembler.assemble(
            Portfolio(
                identity=_identity(),
                holdings=(_holding("HDFCBANK"),),
            )
        )
        assert result.status is PortfolioCitationStatus.ABSENT
        assert result.decision_citations
        assert result.evidence_citations == ()
        assert result.comparison_citations == ()
        assert result.report.citation_summary is not None
        assert result.report.observations == ()

    def test_decision_pack_citations(self) -> None:
        assembler = PortfolioCitationAssembler()
        result = assembler.assemble(
            Portfolio(
                identity=_identity(),
                holdings=(_holding("AAA"), _holding("BBB")),
            )
        )
        assert len(result.decision_citations) == 2
        assert result.summary.decision_citation_count == 2

    def test_evidence_bundle_citations(self) -> None:
        assembler = PortfolioCitationAssembler()
        result = assembler.assemble(
            Portfolio(
                identity=_identity(),
                holdings=(_holding("HDFCBANK", evidence=True),),
            )
        )
        assert len(result.evidence_citations) == 1
        assert result.summary.bundle_versions
        assert result.report.evidence_bundle_refs

    def test_comparison_citations(self) -> None:
        assembler = PortfolioCitationAssembler()
        result = assembler.assemble(
            PortfolioCitationContext(
                portfolio=Portfolio(
                    identity=_identity(),
                    holdings=(_holding("HDFCBANK"), _holding("ICICIBANK")),
                ),
                comparison_report_refs=(_comparison("HDFCBANK", "ICICIBANK"),),
            )
        )
        assert len(result.comparison_citations) == 1
        assert result.report.comparison_report_refs

    def test_mixed_coverage(self) -> None:
        assembler = PortfolioCitationAssembler()
        result = assembler.assemble(
            Portfolio(
                identity=_identity(),
                holdings=(
                    _holding("AAA", evidence=True, comparison=True),
                    _holding("BBB", evidence=True),
                ),
            )
        )
        assert result.status is PortfolioCitationStatus.PARTIAL
        assert "BBB" in result.coverage.missing_comparison_symbols
        assert result.citation_gaps
        assert result.report.coverage_summary is not None
        assert result.report.citation_gaps


class TestValidationAndBoundaries:
    def test_duplicate_overlay_citations(self) -> None:
        assembler = PortfolioCitationAssembler()
        with pytest.raises(PortfolioError, match="duplicate"):
            assembler.assemble(
                PortfolioCitationContext(
                    portfolio=Portfolio(
                        identity=_identity(),
                        holdings=(_holding("HDFCBANK"),),
                    ),
                    evidence_bundle_refs=(
                        _evidence("HDFCBANK"),
                        _evidence("HDFCBANK"),
                    ),
                )
            )

    def test_foreign_citations(self) -> None:
        assembler = PortfolioCitationAssembler()
        with pytest.raises(PortfolioError, match="foreign"):
            assembler.assemble(
                PortfolioCitationContext(
                    portfolio=Portfolio(
                        identity=_identity(),
                        holdings=(_holding("HDFCBANK"),),
                    ),
                    evidence_bundle_refs=(_evidence("SBIN"),),
                )
            )

    def test_broken_comparison_symbols(self) -> None:
        assembler = PortfolioCitationAssembler()
        with pytest.raises(PortfolioError, match="foreign"):
            assembler.assemble(
                PortfolioCitationContext(
                    portfolio=Portfolio(
                        identity=_identity(),
                        holdings=(_holding("HDFCBANK"),),
                    ),
                    comparison_report_refs=(_comparison("SBIN"),),
                )
            )

    def test_immutability(self) -> None:
        assembler = PortfolioCitationAssembler()
        result = assembler.assemble(
            Portfolio(
                identity=_identity(),
                holdings=(_holding("AAA", evidence=True, comparison=True),),
            )
        )
        assert result.status is PortfolioCitationStatus.COMPLETE
        with pytest.raises(AttributeError):
            result.decision_citations = ()  # type: ignore[misc]
        with pytest.raises(AttributeError):
            result.report.citation_gaps = ()  # type: ignore[misc]

    def test_platform_exports(self) -> None:
        import dsp_platform as platform

        assert platform.PortfolioCitationAssembler is PortfolioCitationAssembler
        assert platform.PortfolioCitationStatus.ABSENT.value == "absent"
        assert platform.PortfolioCitationSummary is not None
