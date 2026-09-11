"""Historical share-count snapshots. Newer candidates never silently overwrite."""

from __future__ import annotations

import hashlib
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from data_engine.official_research.currentness import (
    CapitalEvent,
    corporate_action_horizon_status,
    judge_currentness,
)
from data_engine.official_research.extraction import (
    VALUATION_SHARE_SEMANTIC,
    canonical_share_semantic_type,
    classify_share_count_impact,
)
from data_engine.official_research.models import EvidenceItem
from data_engine.official_research.semantics import cannot_derive_shares
from data_engine.official_research.source_policy import SourcePolicy, authority_tier_for
from data_engine.official_research.verified_dataset import ShareCountSnapshot

__all__ = [
    "SHARE_RECORD_OUTCOMES",
    "ShareRecordStore",
    "compare_share_records",
    "integrity_hash_for",
    "snapshot_from_evidence",
    "validate_outstanding_shares",
]

SHARE_RECORD_OUTCOMES: frozenset[str] = frozenset(
    {
        "MATCH",
        "NEWER_VALID_RECORD",
        "CONFLICT",
        "STALE_STORED",
        "STALE_NEW",
        "UNKNOWN",
    }
)
_MONEY_UNITS = frozenset(
    {
        "crore",
        "crores",
        "lakh",
        "lakhs",
        "million",
        "millions",
        "thousand",
        "inr",
        "rupee",
        "rupees",
    }
)


def integrity_hash_for(
    *,
    isin: str,
    mic: str,
    shares: Decimal,
    as_of: date,
    source: str,
    document_hash: str | None = None,
) -> str:
    payload = "|".join(
        (
            isin.strip().upper(),
            mic.strip().upper(),
            format(shares, "f"),
            as_of.isoformat(),
            source.strip(),
            (document_hash or "").strip(),
        )
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def snapshot_from_evidence(
    item: EvidenceItem,
    *,
    listing_isin: str,
    listing_mic: str,
    ca_checked_through: date | None = None,
) -> ShareCountSnapshot | None:
    try:
        shares = Decimal(str(item.value or "").replace(",", ""))
    except (InvalidOperation, ValueError):
        return None
    if item.as_of is None or shares <= 0:
        return None
    retrieved = item.last_verified_at or item.retrieved_at
    return ShareCountSnapshot(
        shares=shares,
        as_of=item.as_of,
        current_through=item.current_through or item.as_of,
        last_verified_at=retrieved,
        source=item.source,
        corporate_action_status=(
            item.corporate_action_status
            if item.corporate_action_status
            in {"VERIFIED", "REFRESH_REQUIRED", "CONFLICT", "UNKNOWN", "UNAVAILABLE", "REJECTED"}
            else "UNKNOWN"
        ),
        status=item.status,
        evidence_id=item.evidence_id,
        source_url=item.source_url,
        document_hash=item.document_hash,
        corporate_actions_checked=(),
        semantic_type=canonical_share_semantic_type(item.evidence_locator or ""),
        integrity_hash=integrity_hash_for(
            isin=listing_isin,
            mic=listing_mic,
            shares=shares,
            as_of=item.as_of,
            source=item.source,
            document_hash=item.document_hash,
        ),
        evidence_ids=(item.evidence_id,),
        ca_checked_through=ca_checked_through,
    )


def validate_outstanding_shares(
    item: EvidenceItem,
    *,
    expected_isin: str,
    expected_mic: str,
    research_horizon: date,
    ca_checked_through: date | None,
    corporate_actions: tuple[CapitalEvent, ...] = (),
    policy: SourcePolicy | None = None,
) -> str:
    """Gates for TOTAL_OUTSTANDING. Fail closed. Never estimate or reverse-engineer."""
    policy = policy or SourcePolicy()
    if cannot_derive_shares(item.source or "") or cannot_derive_shares(item.field):
        return "REJECTED"
    if item.source_type in {"llm", "agent_claim"}:
        return "REJECTED"
    if str(item.isin or "").strip().upper() != expected_isin.strip().upper():
        return "REJECTED"
    if str(item.mic or "").strip().upper() != expected_mic.strip().upper():
        return "REJECTED"
    if item.identity_status != "PASS":
        return "REJECTED"
    if not policy.may_verify(item.source_url, source_type=item.source_type):
        return "REJECTED"
    if authority_tier_for(item.source_url, source_type=item.source_type, agent=item.agent) == "TIER_3":
        return "REJECTED"
    semantic = canonical_share_semantic_type(item.evidence_locator or "")
    if semantic != VALUATION_SHARE_SEMANTIC:
        return "REJECTED" if semantic != "UNKNOWN" else "UNKNOWN"
    unit = str(item.unit or item.raw_unit or "").strip().lower()
    if unit in _MONEY_UNITS:
        return "REJECTED"
    if item.as_of is None:
        return "UNKNOWN"
    try:
        shares = Decimal(str(item.value or "").replace(",", ""))
    except (InvalidOperation, ValueError):
        return "UNKNOWN"
    if shares <= 0:
        return "REJECTED"
    current = judge_currentness(
        field="shares_outstanding",
        as_of=item.as_of,
        retrieved_at=item.retrieved_at,
        current_through=item.current_through,
        last_verified_at=item.last_verified_at,
        document_date=item.document_date,
        freshness_status=item.freshness_status,
        corporate_action_status=str(item.corporate_action_status),
        corporate_actions=corporate_actions,
        research_horizon=research_horizon,
        ca_checked_through=ca_checked_through,
        freshness_class="latest_count_plus_ca_review",
    )
    if current == "CONFLICT":
        return "CONFLICT"
    if current == "REFRESH_REQUIRED":
        return "REFRESH_REQUIRED"
    if current != "CURRENT":
        return "UNKNOWN"
    for event in corporate_actions:
        impact = classify_share_count_impact(event.event_type)
        if (
            impact in {"SHARE_COUNT_INCREASE", "SHARE_COUNT_DECREASE", "POTENTIAL_CHANGE"}
            and event.event_date > item.as_of
            and event.event_date <= research_horizon
        ):
            return "REFRESH_REQUIRED"
    return "VERIFIED"


def compare_share_records(
    stored: ShareCountSnapshot | None,
    new: ShareCountSnapshot | None,
    *,
    research_horizon: date,
) -> str:
    if stored is None and new is None:
        return "UNKNOWN"
    if stored is None:
        return "NEWER_VALID_RECORD" if new is not None and new.status == "VERIFIED" else "UNKNOWN"
    if new is None:
        stored_horizon = corporate_action_horizon_status(
            as_of=stored.as_of,
            checked_through=stored.ca_checked_through or stored.current_through,
            research_horizon=research_horizon,
        )
        return "STALE_STORED" if stored_horizon != "CURRENT" else "UNKNOWN"
    if stored.as_of == new.as_of:
        if stored.shares == new.shares:
            return "MATCH"
        return "CONFLICT"
    if new.as_of > stored.as_of:
        stored_horizon = corporate_action_horizon_status(
            as_of=stored.as_of,
            checked_through=stored.ca_checked_through or stored.current_through,
            research_horizon=research_horizon,
        )
        if stored_horizon != "CURRENT":
            return "STALE_STORED" if new.status != "VERIFIED" else "NEWER_VALID_RECORD"
        if new.status == "VERIFIED":
            return "NEWER_VALID_RECORD"
        return "UNKNOWN"
    new_horizon = corporate_action_horizon_status(
        as_of=new.as_of,
        checked_through=new.ca_checked_through or new.current_through,
        research_horizon=research_horizon,
    )
    if new_horizon != "CURRENT":
        return "STALE_NEW"
    return "UNKNOWN"


class ShareRecordStore:
    """Append-only share snapshots keyed by ISIN+MIC. History is preserved."""

    def __init__(self) -> None:
        self._rows: dict[str, list[ShareCountSnapshot]] = {}

    @staticmethod
    def _key(isin: str, mic: str) -> str:
        return f"{isin.strip().upper()}.{mic.strip().upper()}"

    def history(self, isin: str, mic: str) -> tuple[ShareCountSnapshot, ...]:
        return tuple(self._rows.get(self._key(isin, mic), ()))

    def put(self, isin: str, mic: str, snapshot: ShareCountSnapshot) -> str:
        key = self._key(isin, mic)
        existing = self._rows.setdefault(key, [])
        outcome = compare_share_records(
            existing[-1] if existing else None,
            snapshot,
            research_horizon=snapshot.ca_checked_through or snapshot.current_through,
        )
        existing.append(snapshot)
        return outcome

    def latest(self, isin: str, mic: str) -> ShareCountSnapshot | None:
        rows = self._rows.get(self._key(isin, mic), ())
        return rows[-1] if rows else None
