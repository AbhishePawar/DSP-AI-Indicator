"""Risk Assembler tests (E1.1)."""

from __future__ import annotations

import json
from dataclasses import asdict

import pytest
from industry import EvidenceBundleReference, EvidenceBundleStatus
from portfolio import (
    ComparisonReportReference,
    DecisionPackReference,
    PortfolioMonitoringStatus,
)

from risk import (
    MonitoringReference,
    PortfolioReference,
    RiskAssembler,
    RiskAssemblyContext,
    RiskAssemblyStatus,
    RiskError,
    RiskIdentity,
)


def _identity(risk_id: str = "dsp.risk.demo") -> RiskIdentity:
    return RiskIdentity(risk_id=risk_id, risk_name="Demo Risk")


def _portfolio(portfolio_id: str = "dsp.portfolio.demo") -> PortfolioReference:
    return PortfolioReference(portfolio_id=portfolio_id)


def _ctx(
    *,
    with_monitoring: bool = False,
    risk_id: str = "dsp.risk.demo",
) -> RiskAssemblyContext:
    return RiskAssemblyContext(
        identity=_identity(risk_id),
        portfolio_ref=_portfolio(),
        monitoring_ref=(
            MonitoringReference(
                portfolio_id="dsp.portfolio.demo",
                status=PortfolioMonitoringStatus.INITIAL,
            )
            if with_monitoring
            else None
        ),
        decision_pack_refs=(
            DecisionPackReference(
                instrument_symbol="HDFCBANK",
                digest="abcdef0123456789",
            ),
        ),
        evidence_bundle_refs=(
            EvidenceBundleReference(
                bundle_id="dsp.evidence_bundle.hdfcbank",
                instrument_key="HDFCBANK",
                methodology_id="dsp.methodology.commercial_banking",
                methodology_version="1.0.0",
                digest="abcdef0123456789deadbeef",
                status=EvidenceBundleStatus.INCOMPLETE,
            ),
        ),
        comparison_report_refs=(
            ComparisonReportReference(digest="compdigest01"),
        ),
    )


class TestAssembly:
    def test_basic_assembly_without_monitoring(self) -> None:
        result = RiskAssembler().assemble(_ctx(with_monitoring=False))
        assert result.status is RiskAssemblyStatus.PARTIAL
        assert result.profile.monitoring_ref is None
        assert result.profile.assessments == ()
        assert result.report.observations == ()
        assert result.report.descriptors == ()
        assert result.report.summary.observation_count == 0
        assert result.warnings

    def test_assembly_with_monitoring(self) -> None:
        result = RiskAssembler().assemble(_ctx(with_monitoring=True))
        assert result.status is RiskAssemblyStatus.COMPLETE
        assert result.profile.monitoring_ref is not None
        assert len(result.profile.decision_pack_refs) == 1
        assert len(result.report.decision_pack_refs) == 1

    def test_assemble_many_deterministic(self) -> None:
        assembler = RiskAssembler()
        a = assembler.assemble_many((_ctx(risk_id="dsp.risk.a"), _ctx(risk_id="dsp.risk.b")))
        b = assembler.assemble_many((_ctx(risk_id="dsp.risk.a"), _ctx(risk_id="dsp.risk.b")))
        assert a == b


class TestValidation:
    def test_duplicate_decision_refs(self) -> None:
        pack = DecisionPackReference(
            instrument_symbol="AAA", digest="abcdef0123456789"
        )
        with pytest.raises(RiskError, match="duplicate"):
            RiskAssembler().assemble(
                RiskAssemblyContext(
                    identity=_identity(),
                    portfolio_ref=_portfolio(),
                    decision_pack_refs=(pack, pack),
                )
            )

    def test_foreign_monitoring(self) -> None:
        with pytest.raises(RiskError, match="foreign Monitoring"):
            RiskAssembler().assemble(
                RiskAssemblyContext(
                    identity=_identity(),
                    portfolio_ref=_portfolio(),
                    monitoring_ref=MonitoringReference(
                        portfolio_id="dsp.portfolio.other",
                    ),
                )
            )

    def test_broken_comparison_digest(self) -> None:
        with pytest.raises(Exception):
            ComparisonReportReference(digest="short")

    def test_duplicate_reports_in_assemble_many(self) -> None:
        with pytest.raises(RiskError, match="duplicate reports"):
            RiskAssembler().assemble_many(
                (_ctx(risk_id="dsp.risk.same"), _ctx(risk_id="dsp.risk.same"))
            )


class TestImmutabilityAndSerialization:
    def test_immutability(self) -> None:
        result = RiskAssembler().assemble(_ctx(with_monitoring=True))
        with pytest.raises(AttributeError):
            result.profile = result.profile  # type: ignore[misc]
        with pytest.raises(AttributeError):
            result.report.observations = ()  # type: ignore[misc]

    def test_serialization(self) -> None:
        result = RiskAssembler().assemble(_ctx())
        payload = asdict(result.report.summary)
        assert json.loads(json.dumps(payload))["observation_count"] == 0


class TestArchitectureAndCompatibility:
    def test_platform_exports(self) -> None:
        import dsp_platform as platform

        assert platform.RiskAssembler is RiskAssembler
        assert platform.RiskAssemblyStatus.COMPLETE.value == "complete"
        assert platform.RiskAssemblyContext is not None
