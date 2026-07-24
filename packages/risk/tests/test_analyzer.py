"""Risk Analyzer tests (E1.2)."""

from __future__ import annotations

import pytest
from industry import EvidenceBundleReference, EvidenceBundleStatus
from portfolio import (
    DecisionPackReference,
    Portfolio,
    PortfolioHolding,
    PortfolioIdentity,
    PortfolioType,
)

from risk import (
    PortfolioReference,
    RiskAnalysisContext,
    RiskAnalysisStatus,
    RiskAnalyzer,
    RiskAssembler,
    RiskAssemblyContext,
    RiskConstraint,
    RiskConstraintKind,
    RiskError,
    RiskIdentity,
    RiskLevel,
    RiskObservation,
    RiskProfile,
)


def _pack(symbol: str) -> DecisionPackReference:
    return DecisionPackReference(instrument_symbol=symbol, digest="abcdef0123456789")


def _assembled_profile(*, with_evidence: bool = True) -> RiskProfile:
    evidence = ()
    if with_evidence:
        evidence = (
            EvidenceBundleReference(
                bundle_id="dsp.evidence_bundle.aaa",
                instrument_key="AAA",
                methodology_id="dsp.methodology.commercial_banking",
                methodology_version="1.0.0",
                digest="abcdef0123456789deadbeef",
                status=EvidenceBundleStatus.INCOMPLETE,
            ),
        )
    result = RiskAssembler().assemble(
        RiskAssemblyContext(
            identity=RiskIdentity(risk_id="dsp.risk.demo", risk_name="Demo"),
            portfolio_ref=PortfolioReference(portfolio_id="dsp.portfolio.demo"),
            decision_pack_refs=(_pack("AAA"), _pack("BBB")),
            evidence_bundle_refs=evidence,
            constraints=(
                RiskConstraint(
                    id="dsp.risk.constraint.conc",
                    kind=RiskConstraintKind.CONCENTRATION_POSTURE,
                    target="portfolio",
                    posture=RiskLevel.LOW,
                ),
            ),
        )
    )
    return result.profile


def _portfolio(*, concentrated: bool = False) -> Portfolio:
    if concentrated:
        holdings = (
            PortfolioHolding(
                instrument_symbol="AAA",
                decision_pack_ref=_pack("AAA"),
                weight=0.9,
            ),
        )
        cash = 0.1
    else:
        holdings = tuple(
            PortfolioHolding(
                instrument_symbol=f"S{i}",
                decision_pack_ref=_pack(f"S{i}"),
                weight=0.08,
            )
            for i in range(10)
        )
        cash = 0.02
    return Portfolio(
        identity=PortfolioIdentity(
            portfolio_id="dsp.portfolio.demo",
            portfolio_name="Demo",
            portfolio_type=PortfolioType.MODEL,
            base_currency="INR",
        ),
        holdings=holdings,
        cash_weight=cash,
    )


class TestAnalysis:
    def test_basic_analysis(self) -> None:
        result = RiskAnalyzer().analyze(_assembled_profile())
        assert result.assessment is not None
        assert result.report.observations
        assert result.report.descriptors
        assert result.report.coverage
        assert result.summary.observation_count == len(result.observations)

    def test_concentration_posture(self) -> None:
        result = RiskAnalyzer().analyze(
            RiskAnalysisContext(
                profile=_assembled_profile(),
                portfolio=_portfolio(concentrated=True),
            )
        )
        conc = next(d for d in result.descriptors if d.dimension == "concentration")
        assert conc.level in {RiskLevel.HIGH, RiskLevel.ELEVATED}
        assert any("concentrated" in o.text.lower() for o in result.observations)

    def test_diversification_posture(self) -> None:
        result = RiskAnalyzer().analyze(
            RiskAnalysisContext(
                profile=_assembled_profile(),
                portfolio=_portfolio(concentrated=False),
            )
        )
        div = next(d for d in result.descriptors if d.dimension == "diversification")
        assert div.level is RiskLevel.LOW

    def test_cash_posture(self) -> None:
        result = RiskAnalyzer().analyze(
            RiskAnalysisContext(
                profile=_assembled_profile(),
                portfolio=_portfolio(concentrated=False),
            )
        )
        cash = next(d for d in result.descriptors if d.dimension == "cash")
        assert cash.level is RiskLevel.LOW

    def test_coverage_posture(self) -> None:
        missing = RiskAnalyzer().analyze(_assembled_profile(with_evidence=False))
        assert missing.status is RiskAnalysisStatus.PARTIAL
        assert any("evidence" in o.code for o in missing.observations)

    def test_constraint_and_liquidity_posture(self) -> None:
        result = RiskAnalyzer().analyze(
            RiskAnalysisContext(
                profile=_assembled_profile(),
                portfolio=_portfolio(concentrated=False),
            )
        )
        assert any(d.dimension == "constraint" for d in result.descriptors)
        assert any(d.dimension == "liquidity" for d in result.descriptors)
        assert any(o.code == "constraint_posture" for o in result.observations)
        assert any(o.code == "liquidity_posture" for o in result.observations)


class TestValidationAndBoundaries:
    def test_foreign_portfolio_rejected(self) -> None:
        profile = _assembled_profile()
        foreign = Portfolio(
            identity=PortfolioIdentity(
                portfolio_id="dsp.portfolio.other",
                portfolio_name="Other",
                base_currency="USD",
            ),
            holdings=(),
        )
        with pytest.raises(RiskError, match="foreign"):
            RiskAnalyzer().analyze(
                RiskAnalysisContext(profile=profile, portfolio=foreign)
            )

    def test_duplicate_observations_rejected(self) -> None:
        analyzer = RiskAnalyzer()
        with pytest.raises(RiskError, match="duplicate observations"):
            analyzer._reject_duplicates(
                (
                    RiskObservation(code="same", text="Constraint posture is acceptable."),
                    RiskObservation(code="same", text="Liquidity posture is acceptable."),
                ),
                (),
            )

    def test_immutability(self) -> None:
        result = RiskAnalyzer().analyze(_assembled_profile())
        with pytest.raises(AttributeError):
            result.observations = ()  # type: ignore[misc]
        with pytest.raises(AttributeError):
            result.report.descriptors = ()  # type: ignore[misc]

    def test_platform_exports(self) -> None:
        import dsp_platform as platform

        assert platform.RiskAnalyzer is RiskAnalyzer
        assert platform.RiskAnalysisStatus.PARTIAL.value == "partial"
