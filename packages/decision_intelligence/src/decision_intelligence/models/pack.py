"""Decision Pack — primary investor-facing artifact."""

from __future__ import annotations

from dataclasses import dataclass

from contracts.domain.recommendation import Recommendation
from core.exceptions import ValidationError
from industry import EvidenceBundleReference, EvidenceBundleStatus

from decision_intelligence.models.assurance import AssuranceAssessment
from decision_intelligence.models.brief import DecisionBrief

__all__ = ["DecisionPack", "DecisionPackEvidenceSummary"]


@dataclass(frozen=True, slots=True)
class DecisionPackEvidenceSummary:
    """Reference-only evidence projection for DecisionPack consumers.

    Never includes observations, scores, or embedded bundles.
    """

    attached: bool
    status: EvidenceBundleStatus | None
    availability: str
    bundle_version: str | None
    methodology_id: str | None
    methodology_version: str | None
    bundle_id: str | None
    digest: str | None
    instrument_key: str | None
    reference: str | None

    @classmethod
    def from_pack(cls, pack: DecisionPack) -> DecisionPackEvidenceSummary:
        ref = pack.evidence_bundle_ref
        if ref is None:
            return cls(
                attached=False,
                status=None,
                availability="not_attached",
                bundle_version=None,
                methodology_id=None,
                methodology_version=None,
                bundle_id=None,
                digest=None,
                instrument_key=None,
                reference=None,
            )
        return cls(
            attached=True,
            status=ref.status,
            availability=ref.status.value,
            bundle_version=ref.methodology_version,
            methodology_id=ref.methodology_id,
            methodology_version=ref.methodology_version,
            bundle_id=ref.bundle_id,
            digest=ref.digest,
            instrument_key=ref.instrument_key,
            reference=f"{ref.bundle_id}@{ref.digest}",
        )


@dataclass(frozen=True, slots=True)
class DecisionPack:
    """Recommendation plus Decision Brief and Assurance Assessment.

    This is the preferred product artifact for UI / Dashboard consumers.
    ``Recommendation`` remains available for backward compatibility.

    Optional ``evidence_bundle_ref`` cites an Industry Evidence Bundle.
    DecisionPack never owns or embeds the bundle payload.

    Frozen architecture maps single-security citations to this reference
    field (EvidenceBundleReference fulfills the DecisionPack snapshot-ref role).
    """

    recommendation: Recommendation
    brief: DecisionBrief
    assurance: AssuranceAssessment
    evidence_bundle_ref: EvidenceBundleReference | None = None

    def __post_init__(self) -> None:
        if self.brief.instrument != self.recommendation.instrument:
            msg = "brief.instrument must match recommendation.instrument"
            raise ValidationError(msg)
        if self.assurance.instrument != self.recommendation.instrument:
            msg = "assurance.instrument must match recommendation.instrument"
            raise ValidationError(msg)
        if self.brief.action is not self.recommendation.action:
            msg = "brief.action must match recommendation.action"
            raise ValidationError(msg)
        if self.assurance.action is not self.recommendation.action:
            msg = "assurance.action must match recommendation.action"
            raise ValidationError(msg)
        if self.evidence_bundle_ref is not None:
            _validate_evidence_bundle_ref(
                self.evidence_bundle_ref,
                instrument_symbol=self.recommendation.instrument.symbol,
            )

    def evidence_summary(self) -> DecisionPackEvidenceSummary:
        """Reference-only evidence summary (status / version / availability)."""
        return DecisionPackEvidenceSummary.from_pack(self)


def _validate_evidence_bundle_ref(
    ref: EvidenceBundleReference,
    *,
    instrument_symbol: str,
) -> None:
    """Reject invalid / broken EvidenceBundle references.

    DecisionPack stores citations only — this validates reference integrity,
    not bundle contents.
    """
    expected = instrument_symbol.strip().upper()
    if ref.instrument_key != expected:
        msg = (
            f"evidence_bundle_ref.instrument_key {ref.instrument_key!r} "
            f"must match DecisionPack instrument {expected!r}"
        )
        raise ValidationError(msg)
    if not ref.bundle_id:
        msg = "evidence_bundle_ref.bundle_id must not be empty"
        raise ValidationError(msg)
    if not ref.digest:
        msg = "evidence_bundle_ref.digest must not be empty"
        raise ValidationError(msg)
    if not all(c in "0123456789abcdef" for c in ref.digest):
        msg = "evidence_bundle_ref.digest must be lowercase hex"
        raise ValidationError(msg)
    if len(ref.digest) < 16:
        msg = "evidence_bundle_ref.digest is too short to be a valid digest"
        raise ValidationError(msg)
    if not isinstance(ref.status, EvidenceBundleStatus):
        msg = "evidence_bundle_ref.status must be EvidenceBundleStatus"
        raise ValidationError(msg)
