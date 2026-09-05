"""Generic Option-B share-count refresh — candidate only, never silent promote.

Runtime analyse still consumes signed promoted_share_counts/*.json.
This module does not call Gemini, vendors, or write production files.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from typing import Any

from dsp_platform.current_outstanding_protocol.currentness import (
    CorporateActionCurrentnessEvidence,
    ShareChangingCorporateAction,
    evaluate_option_b_currentness,
)
from dsp_platform.promoted_share_count import canonical_promoted_snapshot_digest
from dsp_platform.share_count_source_authorization import (
    SourceAuthorizationError,
    SourceAuthorizationStatus,
    SourceRole,
    assert_source_authorized,
)

__all__ = [
    "CoverageState",
    "InstrumentIdentity",
    "ShareCountObservation",
    "ShareCountRefreshRequest",
    "ShareCountRefreshResult",
    "refresh_share_count",
]

_ADMISSIBLE_TIERS = frozenset({"TIER_1_PRIMARY", "TIER_2_SECONDARY"})


class CoverageState(StrEnum):
    """Derived coverage. Catalogue searchability is a different axis.

    UNKNOWN → DISCOVERED → CANDIDATE → VALIDATED → (human) PROMOTED
    → CURRENT → STALE → REFRESH_PENDING
    """

    UNKNOWN = "UNKNOWN"
    DISCOVERED = "DISCOVERED"
    CANDIDATE = "CANDIDATE"
    VALIDATED = "VALIDATED"
    PROMOTED = "PROMOTED"
    CURRENT = "CURRENT"
    STALE = "STALE"
    REFRESH_PENDING = "REFRESH_PENDING"
    UNAVAILABLE = "UNAVAILABLE"
    INVALID = "INVALID"


@dataclass(frozen=True, slots=True)
class InstrumentIdentity:
    symbol: str
    exchange: str
    mic: str
    isin: str
    issuer: str = ""
    security_type: str = "common_equity"

    def normalized(self) -> InstrumentIdentity:
        return InstrumentIdentity(
            symbol=str(self.symbol or "").strip().upper(),
            exchange=str(self.exchange or "").strip().upper(),
            mic=str(self.mic or "").strip().upper(),
            isin=str(self.isin or "").strip().upper(),
            issuer=str(self.issuer or "").strip(),
            security_type=str(self.security_type or "common_equity").strip().lower()
            or "common_equity",
        )


@dataclass(frozen=True, slots=True)
class ShareCountObservation:
    """Authoritative outstanding observation. retrieved_at is never as_of."""

    shares_outstanding: Decimal
    as_of: date
    effective_date: date
    retrieved_at: datetime
    source_id: str
    source_url: str
    evidence_reference: str
    source_tier: str
    publication_at: date | None = None
    basis: str = "current_outstanding"
    unit: str = "shares"


@dataclass(frozen=True, slots=True)
class ShareCountRefreshRequest:
    identity: InstrumentIdentity
    lookup_horizon: datetime
    current_snapshot: Mapping[str, Any] | None = None
    corporate_action_evidence: CorporateActionCurrentnessEvidence | None = None
    observation: ShareCountObservation | None = None
    observation_source_id: str = "promoted_snapshot_artifact"
    ca_source_id: str = "t1_corporate_action_completeness"


@dataclass(frozen=True, slots=True)
class ShareCountRefreshResult:
    state: CoverageState
    reason: str
    candidate: dict[str, Any] | None = None
    shares_outstanding: Decimal | None = None
    as_of: date | None = None
    complete_through: date | None = None
    source_status: SourceAuthorizationStatus | None = None


def refresh_share_count(request: ShareCountRefreshRequest) -> ShareCountRefreshResult:
    """Evaluate currentness and optionally emit a VALIDATED candidate.

    Does not sign, package, or write production snapshots.
    """
    identity = request.identity.normalized()
    if not identity.isin or not identity.mic or not identity.symbol:
        return ShareCountRefreshResult(
            state=CoverageState.UNKNOWN,
            reason="canonical identity requires symbol, MIC, and ISIN",
        )
    horizon_dt = request.lookup_horizon
    if not isinstance(horizon_dt, datetime) or horizon_dt.tzinfo is None:
        return ShareCountRefreshResult(
            state=CoverageState.UNAVAILABLE,
            reason="lookup_horizon must be timezone-aware and is not as_of",
        )
    horizon = horizon_dt.date()

    try:
        assert_source_authorized(request.ca_source_id, SourceRole.CORPORATE_ACTION_COMPLETENESS)
        assert_source_authorized(
            request.observation_source_id, SourceRole.SHARE_COUNT_OBSERVATION
        )
    except SourceAuthorizationError as exc:
        state = (
            CoverageState.REFRESH_PENDING
            if exc.status is SourceAuthorizationStatus.PENDING
            else CoverageState.UNAVAILABLE
        )
        return ShareCountRefreshResult(
            state=state,
            reason=str(exc),
            source_status=exc.status,
        )

    snapshot = dict(request.current_snapshot) if request.current_snapshot else None
    if snapshot is not None:
        integrity_error = _snapshot_integrity_error(snapshot)
        if integrity_error is not None:
            return ShareCountRefreshResult(
                state=CoverageState.INVALID, reason=integrity_error
            )
        mismatch = _identity_mismatch(identity, snapshot)
        if mismatch is not None:
            return ShareCountRefreshResult(
                state=CoverageState.INVALID, reason=mismatch
            )

    observation = request.observation
    if observation is None and snapshot is not None:
        observation = _observation_from_snapshot(snapshot, request.observation_source_id)
        if observation is None:
            return ShareCountRefreshResult(
                state=CoverageState.UNAVAILABLE,
                reason="promoted snapshot is not a usable outstanding observation",
            )
    if observation is None:
        return ShareCountRefreshResult(
            state=CoverageState.DISCOVERED,
            reason="canonical identity known; no promoted snapshot and no authoritative observation",
        )
    obs_error = _validate_observation(observation, horizon=horizon)
    if obs_error is not None:
        return ShareCountRefreshResult(state=CoverageState.UNAVAILABLE, reason=obs_error)

    conflict = _observation_conflicts_snapshot(snapshot, observation)
    if conflict is not None:
        return ShareCountRefreshResult(state=CoverageState.INVALID, reason=conflict)

    evidence = request.corporate_action_evidence
    if evidence is None and snapshot is not None:
        evidence = _evidence_from_snapshot(snapshot)
    if evidence is None:
        return ShareCountRefreshResult(
            state=CoverageState.CANDIDATE,
            reason="observation present; corporate-action completeness evidence is missing",
            shares_outstanding=observation.shares_outstanding,
            as_of=observation.as_of,
        )
    if evidence.share_count_as_of != observation.as_of:
        return ShareCountRefreshResult(
            state=CoverageState.INVALID,
            reason="corporate-action evidence as_of does not match observation as_of",
            shares_outstanding=observation.shares_outstanding,
            as_of=observation.as_of,
        )

    verdict = evaluate_option_b_currentness(
        share_count_as_of=observation.as_of,
        retrieved_at=horizon_dt,
        evidence=evidence,
    )
    if not verdict.proven:
        return ShareCountRefreshResult(
            state=_unproven_coverage_state(verdict.reason),
            reason=verdict.reason,
            shares_outstanding=observation.shares_outstanding,
            as_of=observation.as_of,
            complete_through=evidence.complete_through,
        )

    candidate = _candidate_payload(
        identity=identity,
        observation=observation,
        evidence=evidence,
        snapshot=snapshot,
    )
    snapshot_through = _snapshot_complete_through(snapshot)
    if (
        snapshot is not None
        and snapshot_through == evidence.complete_through
        and Decimal(str(snapshot.get("shares_outstanding")))
        == observation.shares_outstanding
        and _parse_date(snapshot.get("as_of")) == observation.as_of
    ):
        return ShareCountRefreshResult(
            state=CoverageState.CURRENT,
            reason="existing promoted snapshot remains Option-B proven at horizon",
            candidate=None,
            shares_outstanding=observation.shares_outstanding,
            as_of=observation.as_of,
            complete_through=evidence.complete_through,
            source_status=SourceAuthorizationStatus.APPROVED,
        )
    return ShareCountRefreshResult(
        state=CoverageState.VALIDATED,
        reason=(
            "Option B proven; candidate ready for human promotion "
            "(refresh does not write production files)"
        ),
        candidate=candidate,
        shares_outstanding=observation.shares_outstanding,
        as_of=observation.as_of,
        complete_through=evidence.complete_through,
        source_status=SourceAuthorizationStatus.APPROVED,
    )


def _unproven_coverage_state(reason: str) -> CoverageState:
    text = str(reason or "")
    if "does not reach retrieved_at" in text:
        return CoverageState.STALE
    if "complete_through is before" in text or "future observations" in text:
        return CoverageState.UNAVAILABLE
    return CoverageState.REFRESH_PENDING


def _snapshot_integrity_error(snapshot: Mapping[str, Any]) -> str | None:
    integrity = snapshot.get("integrity")
    if integrity is None:
        return None
    if not isinstance(integrity, Mapping):
        return "promoted snapshot integrity envelope is invalid"
    expected = str(integrity.get("sha256") or "").strip().lower()
    digest = canonical_promoted_snapshot_digest(snapshot)
    if not expected or digest != expected:
        return "promoted snapshot integrity digest mismatch"
    return None


def _observation_conflicts_snapshot(
    snapshot: Mapping[str, Any] | None, observation: ShareCountObservation
) -> str | None:
    if snapshot is None:
        return None
    snap_as_of = _parse_date(snapshot.get("as_of"))
    if snap_as_of != observation.as_of:
        return None
    try:
        snap_shares = Decimal(str(snapshot.get("shares_outstanding")))
    except (InvalidOperation, TypeError, ValueError):
        return "promoted snapshot shares_outstanding is not numeric"
    if snap_shares != observation.shares_outstanding:
        return "conflicting outstanding counts for the same as_of"
    return None


def _validate_observation(observation: ShareCountObservation, *, horizon: date) -> str | None:
    if observation.basis != "current_outstanding":
        return "observation basis must be current_outstanding"
    if observation.unit != "shares":
        return "observation unit must be shares"
    if observation.source_tier not in _ADMISSIBLE_TIERS:
        return "observation source_tier is not admissible"
    if not observation.source_url.strip() or not observation.evidence_reference.strip():
        return "observation source_url and evidence_reference are required"
    if "outstanding" not in observation.evidence_reference.lower():
        return "evidence_reference does not explicitly support outstanding shares"
    if not isinstance(observation.retrieved_at, datetime) or observation.retrieved_at.tzinfo is None:
        return "observation retrieved_at must be timezone-aware"
    if observation.as_of == observation.retrieved_at.date() and observation.publication_at is None:
        # Equality is allowed only when the source independently proves it.
        # A missing publication_at is not that proof.
        return "retrieved_at must not be used as as_of without an independent publication date"
    if observation.as_of > horizon:
        return "observation as_of is after lookup horizon"
    if observation.effective_date > horizon:
        return "observation effective_date is after lookup horizon"
    if observation.shares_outstanding <= 0 or not observation.shares_outstanding.is_finite():
        return "shares_outstanding must be > 0"
    return None


def _identity_mismatch(identity: InstrumentIdentity, snapshot: Mapping[str, Any]) -> str | None:
    raw = snapshot.get("identity")
    if not isinstance(raw, Mapping):
        return "snapshot identity is required"
    snap_isin = str(raw.get("isin") or "").strip().upper()
    snap_mic = str(raw.get("mic") or "").strip().upper()
    snap_symbol = str(raw.get("symbol") or "").strip().upper()
    if snap_isin != identity.isin:
        return "snapshot ISIN does not match requested identity"
    if snap_symbol != identity.symbol:
        return "snapshot symbol does not match requested identity"
    if snap_mic != identity.mic and not (
        {snap_mic, identity.mic} <= {"XNSE", "XBOM"}
    ):
        return "snapshot MIC does not match requested identity"
    return None


def _observation_from_snapshot(
    snapshot: Mapping[str, Any], source_id: str
) -> ShareCountObservation | None:
    try:
        shares = Decimal(str(snapshot.get("shares_outstanding")))
        as_of = _parse_date(snapshot.get("as_of"))
        effective = _parse_date(snapshot.get("effective_date") or snapshot.get("as_of"))
    except (InvalidOperation, TypeError, ValueError):
        return None
    if as_of is None or effective is None:
        return None
    source = snapshot.get("source") if isinstance(snapshot.get("source"), Mapping) else {}
    complete = _parse_date(snapshot.get("complete_through"))
    retrieved_day = complete if complete is not None else as_of
    return ShareCountObservation(
        shares_outstanding=shares,
        as_of=as_of,
        effective_date=effective,
        retrieved_at=datetime.combine(retrieved_day, time(12, 0), tzinfo=UTC),
        publication_at=as_of,
        source_id=source_id,
        source_url=str(source.get("source_url") or ""),
        evidence_reference=str(source.get("evidence_reference") or ""),
        source_tier=str(snapshot.get("source_tier") or ""),
        basis=str(snapshot.get("basis") or "current_outstanding"),
        unit=str(snapshot.get("unit") or "shares"),
    )


def _evidence_from_snapshot(
    snapshot: Mapping[str, Any],
) -> CorporateActionCurrentnessEvidence | None:
    as_of = _parse_date(snapshot.get("as_of"))
    complete = _parse_date(snapshot.get("complete_through"))
    source = snapshot.get("source") if isinstance(snapshot.get("source"), Mapping) else {}
    if as_of is None or complete is None:
        return None
    events = []
    raw_events = snapshot.get("corporate_action_events") or []
    if not isinstance(raw_events, list):
        return None
    for item in raw_events:
        if not isinstance(item, Mapping):
            return None
        effective = item.get("effective_date")
        events.append(
            ShareChangingCorporateAction(
                action_type=str(item.get("action_type") or "").strip().lower(),
                effective_date=_parse_date(effective) if effective not in (None, "") else None,
                changes_outstanding_shares=item.get("changes_outstanding_shares"),
                already_reflected_in_share_count=item.get(
                    "already_reflected_in_share_count"
                ),
                description=(
                    str(item["description"]) if item.get("description") else None
                ),
            )
        )
    return CorporateActionCurrentnessEvidence(
        events=tuple(events),
        complete_through=complete,
        share_count_as_of=as_of,
        source_tier=str(snapshot.get("source_tier") or ""),
        source_url=str(source.get("source_url") or ""),
        evidence_reference=str(source.get("evidence_reference") or ""),
    )


def _snapshot_complete_through(snapshot: Mapping[str, Any] | None) -> date | None:
    if snapshot is None:
        return None
    return _parse_date(snapshot.get("complete_through"))


def _parse_date(raw: object) -> date | None:
    if isinstance(raw, datetime):
        return None
    if isinstance(raw, date):
        return raw
    text = str(raw or "").strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def _candidate_payload(
    *,
    identity: InstrumentIdentity,
    observation: ShareCountObservation,
    evidence: CorporateActionCurrentnessEvidence,
    snapshot: Mapping[str, Any] | None,
) -> dict[str, Any]:
    events = [event.to_dict() for event in evidence.events]
    snap_identity = (
        dict(snapshot["identity"])
        if snapshot is not None and isinstance(snapshot.get("identity"), Mapping)
        else {}
    )
    return {
        "schema_version": "dsp.promoted_share_count.v1",
        "identity": {
            "symbol": identity.symbol,
            "exchange": identity.exchange or snap_identity.get("exchange"),
            "mic": identity.mic,
            "isin": identity.isin,
            "company_name": snap_identity.get("company_name"),
        },
        "shares_outstanding": str(observation.shares_outstanding),
        "basis": "current_outstanding",
        "unit": "shares",
        "as_of": observation.as_of.isoformat(),
        "effective_date": observation.effective_date.isoformat(),
        "complete_through": evidence.complete_through.isoformat()
        if evidence.complete_through is not None
        else None,
        "source_tier": observation.source_tier,
        "corporate_action_adjusted": True,
        "source": {
            "provider_id": "promoted_t1_share_count",
            "provider_name": "Validated refresh candidate (not production until signed)",
            "source_type": "primary_filing",
            "source_url": observation.source_url,
            "evidence_reference": observation.evidence_reference,
        },
        "corporate_action_events": events,
        "refresh": {
            "status": "VALIDATED_CANDIDATE",
            "human_promotion_required": True,
        },
    }
