"""Source selection policy: implemented ≠ production-authorized."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from dsp_platform.share_count_source_authorization import (
    SOURCE_CATALOG,
    SourceAuthorization,
    SourceAuthorizationStatus,
    SourceAuthorityClass,
    SourceRole,
)

__all__ = [
    "EXCHANGE_ARCHIVE_HOSTS",
    "EXCHANGE_DOCUMENT_HOSTS",
    "EXCHANGE_JSON_HOSTS",
    "ConnectorAvailability",
    "SourcePolicyRecord",
    "iter_source_policy",
    "policy_for",
]


class ConnectorAvailability(StrEnum):
    IMPLEMENTED = "IMPLEMENTED"
    AVAILABLE = "AVAILABLE"
    PENDING_AUTHORIZATION = "PENDING_AUTHORIZATION"
    REJECTED = "REJECTED"


EXCHANGE_JSON_HOSTS = frozenset(
    {
        "nseindia.com",
        "www.nseindia.com",
        "bseindia.com",
        "www.bseindia.com",
        "api.bseindia.com",
    }
)
EXCHANGE_ARCHIVE_HOSTS = frozenset({"nsearchives.nseindia.com"})
EXCHANGE_DOCUMENT_HOSTS = EXCHANGE_JSON_HOSTS | EXCHANGE_ARCHIVE_HOSTS

_IMPLEMENTED = frozenset(
    {
        "nse_public_api_connector",
        "bse_public_api_connector",
        "t1_issuer_disclosure",
        "t1_corporate_action_completeness",
        "promoted_snapshot_artifact",
        "manual_promotion",
    }
)
_EVIDENCE_TYPES = {
    "nse_public_api_connector": ("corporate_actions", "corporate_announcements"),
    "bse_public_api_connector": ("corporate_announcements",),
    "t1_issuer_disclosure": ("current_outstanding",),
    "t1_corporate_action_completeness": ("corporate_action_completeness",),
    "promoted_snapshot_artifact": ("current_outstanding",),
    "manual_promotion": ("promotion",),
    "twelve_data_statistics": ("current_outstanding",),
    "gemini_grounding": ("discovery",),
}


@dataclass(frozen=True, slots=True)
class SourcePolicyRecord:
    source_id: str
    tier: SourceAuthorityClass
    authority: SourceAuthorizationStatus
    availability: ConnectorAvailability
    supported_exchanges: tuple[str, ...]
    supported_evidence_types: tuple[str, ...]
    license_state: str
    implemented: bool


def _availability(record: SourceAuthorization) -> ConnectorAvailability:
    if record.status is SourceAuthorizationStatus.REJECTED:
        return ConnectorAvailability.REJECTED
    if record.status is SourceAuthorizationStatus.PENDING:
        return ConnectorAvailability.PENDING_AUTHORIZATION
    if record.source_id in _IMPLEMENTED:
        return ConnectorAvailability.AVAILABLE
    return ConnectorAvailability.IMPLEMENTED


def _exchanges(source_id: str) -> tuple[str, ...]:
    if source_id in {"nse_public_api_connector"}:
        return ("XNSE",)
    if source_id in {"bse_public_api_connector"}:
        return ("XBOM",)
    if source_id in {
        "t1_issuer_disclosure",
        "t1_corporate_action_completeness",
        "promoted_snapshot_artifact",
        "manual_promotion",
    }:
        return ("XNSE", "XBOM")
    return ()


def policy_for(source_id: str) -> SourcePolicyRecord | None:
    record = SOURCE_CATALOG.get(str(source_id or "").strip())
    if record is None:
        return None
    return SourcePolicyRecord(
        source_id=record.source_id,
        tier=record.authority_class,
        authority=record.status,
        availability=_availability(record),
        supported_exchanges=_exchanges(record.source_id),
        supported_evidence_types=_EVIDENCE_TYPES.get(record.source_id, ()),
        license_state=record.notes,
        implemented=record.source_id in _IMPLEMENTED,
    )


def iter_source_policy() -> tuple[SourcePolicyRecord, ...]:
    return tuple(policy_for(source_id) for source_id in SOURCE_CATALOG)
