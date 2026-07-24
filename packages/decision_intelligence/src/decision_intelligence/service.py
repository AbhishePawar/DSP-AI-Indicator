"""Decision Intelligence service — Decision Pack synthesis."""

from __future__ import annotations

from ai_committee import CommitteeReport
from contracts import Recommendation
from industry import EvidenceBundleReference

from decision_intelligence.assurance import build_assurance_assessment
from decision_intelligence.brief import build_decision_brief
from decision_intelligence.exceptions import DecisionIntelligenceError
from decision_intelligence.models.assurance import AssuranceAssessment
from decision_intelligence.models.brief import DecisionBrief
from decision_intelligence.models.pack import DecisionPack

__all__ = ["DecisionIntelligenceService", "attach_evidence_bundle_ref"]


def attach_evidence_bundle_ref(
    pack: DecisionPack,
    evidence_bundle_ref: EvidenceBundleReference | None,
    *,
    expected_methodology_id: str | None = None,
    expected_methodology_version: str | None = None,
) -> DecisionPack:
    """Return a new DecisionPack citing an Evidence Bundle (optional).

    Does not embed the bundle. Pass ``None`` to clear a prior reference.
    """
    if evidence_bundle_ref is not None:
        if (
            expected_methodology_id is not None
            and evidence_bundle_ref.methodology_id
            != expected_methodology_id.strip().lower()
        ):
            msg = (
                f"evidence methodology_id mismatch: "
                f"expected {expected_methodology_id!r}, "
                f"got {evidence_bundle_ref.methodology_id!r}"
            )
            raise DecisionIntelligenceError(msg)
        if (
            expected_methodology_version is not None
            and evidence_bundle_ref.methodology_version
            != expected_methodology_version.strip()
        ):
            msg = (
                f"evidence methodology_version mismatch: "
                f"expected {expected_methodology_version!r}, "
                f"got {evidence_bundle_ref.methodology_version!r}"
            )
            raise DecisionIntelligenceError(msg)
    return DecisionPack(
        recommendation=pack.recommendation,
        brief=pack.brief,
        assurance=pack.assurance,
        evidence_bundle_ref=evidence_bundle_ref,
    )


class DecisionIntelligenceService:
    """Synthesize Decision Brief, Assurance, and Decision Pack.

    Consumes only ``CommitteeReport`` and ``Recommendation``. Never
    imports engines, recalculates MoS, or modifies the recommendation.
    """

    def build_brief(
        self,
        report: CommitteeReport,
        recommendation: Recommendation,
    ) -> DecisionBrief:
        """Build the investor-facing Decision Brief."""
        self._validate_pair(report, recommendation)
        try:
            return build_decision_brief(report, recommendation)
        except DecisionIntelligenceError:
            raise
        except Exception as exc:
            msg = f"failed to build Decision Brief: {exc}"
            raise DecisionIntelligenceError(msg) from exc

    def build_assurance(
        self,
        report: CommitteeReport,
        recommendation: Recommendation,
    ) -> AssuranceAssessment:
        """Build the Decision Assurance assessment."""
        self._validate_pair(report, recommendation)
        try:
            return build_assurance_assessment(report, recommendation)
        except DecisionIntelligenceError:
            raise
        except Exception as exc:
            msg = f"failed to build Assurance Assessment: {exc}"
            raise DecisionIntelligenceError(msg) from exc

    def build_pack(
        self,
        report: CommitteeReport,
        recommendation: Recommendation,
        *,
        evidence_bundle_ref: EvidenceBundleReference | None = None,
    ) -> DecisionPack:
        """Build the primary investor-facing Decision Pack.

        ``evidence_bundle_ref`` is optional. Omitted packs remain fully valid
        (backward compatible). The pack never owns Evidence Bundle payloads.
        """
        self._validate_pair(report, recommendation)
        try:
            brief = build_decision_brief(report, recommendation)
            assurance = build_assurance_assessment(report, recommendation)
            return DecisionPack(
                recommendation=recommendation,
                brief=brief,
                assurance=assurance,
                evidence_bundle_ref=evidence_bundle_ref,
            )
        except DecisionIntelligenceError:
            raise
        except Exception as exc:
            msg = f"failed to build Decision Pack: {exc}"
            raise DecisionIntelligenceError(msg) from exc

    @staticmethod
    def _validate_pair(
        report: CommitteeReport,
        recommendation: Recommendation,
    ) -> None:
        if report.instrument != recommendation.instrument:
            msg = (
                "report.instrument must match recommendation.instrument "
                f"({recommendation.instrument.symbol})"
            )
            raise DecisionIntelligenceError(msg)
