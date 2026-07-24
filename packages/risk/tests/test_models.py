"""Risk domain model tests (E1.0)."""

from __future__ import annotations

import json
from dataclasses import asdict

import pytest
from core.exceptions import ValidationError
from industry import EvidenceBundleReference, EvidenceBundleStatus
from portfolio import (
    ComparisonReportReference,
    DecisionPackReference,
    PortfolioMonitoringStatus,
)

from risk import (
    MonitoringReference,
    PortfolioReference,
    RiskAssessment,
    RiskConstraint,
    RiskConstraintKind,
    RiskCoverage,
    RiskCoverageKind,
    RiskCoverageStatus,
    RiskDescriptor,
    RiskError,
    RiskIdentity,
    RiskLevel,
    RiskObservation,
    RiskProfile,
    RiskReport,
    RiskSummary,
)


def _identity() -> RiskIdentity:
    return RiskIdentity(
        risk_id="dsp.risk.demo",
        risk_name="Demo Risk Profile",
        created_at="2026-07-21T00:00:00Z",
    )


def _portfolio_ref() -> PortfolioReference:
    return PortfolioReference(
        portfolio_id="dsp.portfolio.demo",
        snapshot_id="dsp.snapshot.1",
    )


class TestIdentityAndConstruction:
    def test_identity(self) -> None:
        identity = _identity()
        assert identity.risk_id == "dsp.risk.demo"
        assert identity.risk_name == "Demo Risk Profile"

    def test_empty_identity_name_rejected(self) -> None:
        with pytest.raises(ValidationError, match="risk_name"):
            RiskIdentity(risk_id="dsp.risk.x", risk_name="  ")

    def test_profile_aggregate(self) -> None:
        profile = RiskProfile(
            identity=_identity(),
            portfolio_ref=_portfolio_ref(),
            monitoring_ref=MonitoringReference(
                portfolio_id="dsp.portfolio.demo",
                status=PortfolioMonitoringStatus.INITIAL,
            ),
            decision_pack_refs=(
                DecisionPackReference(
                    instrument_symbol="HDFCBANK",
                    digest="abcdef0123456789",
                ),
            ),
            constraints=(
                RiskConstraint(
                    id="dsp.risk.constraint.conc",
                    kind=RiskConstraintKind.CONCENTRATION_POSTURE,
                    target="portfolio",
                    posture=RiskLevel.MODERATE,
                ),
            ),
            assessments=(
                RiskAssessment(
                    assessment_id="dsp.risk.assessment.1",
                    risk_id="dsp.risk.demo",
                    portfolio_id="dsp.portfolio.demo",
                    as_of="2026-07-21",
                    observations=(
                        RiskObservation(
                            code="concentration_elevated",
                            text="Concentration elevated.",
                        ),
                    ),
                    descriptors=(
                        RiskDescriptor(
                            dimension="concentration",
                            level=RiskLevel.ELEVATED,
                            label="Elevated concentration posture",
                        ),
                    ),
                    coverage=(
                        RiskCoverage(
                            kind=RiskCoverageKind.DECISION,
                            status=RiskCoverageStatus.COMPLETE,
                            label="Decision coverage complete",
                        ),
                    ),
                    summary=RiskSummary(
                        observation_count=1,
                        descriptor_count=1,
                        posture_notes=("Concentration elevated.",),
                        limitation_notes=(
                            "Qualitative Risk assessment only.",
                        ),
                    ),
                ),
            ),
        )
        assert profile.risk_id == "dsp.risk.demo"
        assert profile.portfolio_id == "dsp.portfolio.demo"
        assert len(profile.assessments) == 1

    def test_report_construction(self) -> None:
        report = RiskReport(
            risk_id="dsp.risk.demo",
            portfolio_id="dsp.portfolio.demo",
            summary=RiskSummary(
                observation_count=1,
                descriptor_count=1,
                limitation_notes=("No recommendations.",),
            ),
            observations=(
                RiskObservation(
                    code="coverage_incomplete",
                    text="Coverage incomplete.",
                ),
            ),
            descriptors=(
                RiskDescriptor(
                    dimension="evidence_coverage",
                    level=RiskLevel.HIGH,
                    label="Evidence coverage gaps",
                ),
            ),
            coverage=(
                RiskCoverage(
                    kind=RiskCoverageKind.EVIDENCE,
                    status=RiskCoverageStatus.PARTIAL,
                    label="Evidence coverage partial",
                ),
            ),
            limitations=("Qualitative only.",),
        )
        assert report.summary.observation_count == 1


class TestValidation:
    def test_duplicate_observations(self) -> None:
        obs = RiskObservation(code="same", text="Constraint satisfied.")
        with pytest.raises(RiskError, match="duplicate observations"):
            RiskAssessment(
                assessment_id="dsp.risk.assessment.1",
                risk_id="dsp.risk.demo",
                portfolio_id="dsp.portfolio.demo",
                as_of="2026-07-21",
                observations=(obs, obs),
            )

    def test_duplicate_descriptors(self) -> None:
        d = RiskDescriptor(
            dimension="liquidity",
            level=RiskLevel.LOW,
            label="Liquidity acceptable",
        )
        with pytest.raises(RiskError, match="duplicate descriptors"):
            RiskAssessment(
                assessment_id="dsp.risk.assessment.1",
                risk_id="dsp.risk.demo",
                portfolio_id="dsp.portfolio.demo",
                as_of="2026-07-21",
                descriptors=(d, d),
            )

    def test_duplicate_constraints(self) -> None:
        c = RiskConstraint(
            id="dsp.risk.constraint.x",
            kind=RiskConstraintKind.CUSTOM,
            target="portfolio",
            posture=RiskLevel.UNKNOWN,
        )
        with pytest.raises(RiskError, match="duplicate constraints"):
            RiskProfile(
                identity=_identity(),
                portfolio_ref=_portfolio_ref(),
                constraints=(c, c),
            )

    def test_foreign_monitoring_ownership(self) -> None:
        with pytest.raises(RiskError, match="foreign Monitoring"):
            RiskProfile(
                identity=_identity(),
                portfolio_ref=_portfolio_ref(),
                monitoring_ref=MonitoringReference(
                    portfolio_id="dsp.portfolio.other",
                ),
            )

    def test_foreign_portfolio_on_assessment(self) -> None:
        with pytest.raises(RiskError, match="foreign Portfolio"):
            RiskProfile(
                identity=_identity(),
                portfolio_ref=_portfolio_ref(),
                assessments=(
                    RiskAssessment(
                        assessment_id="dsp.risk.assessment.1",
                        risk_id="dsp.risk.demo",
                        portfolio_id="dsp.portfolio.other",
                        as_of="2026-07-21",
                    ),
                ),
            )

    def test_broken_decision_pack_digest(self) -> None:
        with pytest.raises(Exception):
            DecisionPackReference(instrument_symbol="AAA", digest="short")

    def test_observation_rejects_score_language(self) -> None:
        with pytest.raises(ValidationError, match="forbidden"):
            RiskObservation(code="x", text="This score is high")

    def test_observation_rejects_var_language(self) -> None:
        with pytest.raises(ValidationError, match="forbidden"):
            RiskObservation(code="x", text="Computed var exceeded limit")


class TestImmutabilityAndSerialization:
    def test_immutability(self) -> None:
        profile = RiskProfile(
            identity=_identity(),
            portfolio_ref=_portfolio_ref(),
        )
        with pytest.raises(AttributeError):
            profile.assessments = ()  # type: ignore[misc]
        with pytest.raises(AttributeError):
            profile.identity.risk_name = "x"  # type: ignore[misc]

    def test_serialization_roundtrip_dict(self) -> None:
        obs = RiskObservation(
            code="liquidity_acceptable",
            text="Liquidity acceptable.",
        )
        payload = asdict(obs)
        assert payload["code"] == "liquidity_acceptable"
        # JSON-serializable qualitative payload
        encoded = json.dumps(payload)
        decoded = json.loads(encoded)
        assert decoded["text"] == "Liquidity acceptable."

    def test_levels_are_categorical(self) -> None:
        assert {level.value for level in RiskLevel} == {
            "low",
            "moderate",
            "elevated",
            "high",
            "unknown",
        }


class TestBackwardCompatibility:
    def test_platform_exports(self) -> None:
        import dsp_platform as platform

        assert platform.RiskProfile is RiskProfile
        assert platform.RiskLevel.ELEVATED.value == "elevated"
        assert platform.PortfolioReference is PortfolioReference
        assert platform.RiskReport is not None
