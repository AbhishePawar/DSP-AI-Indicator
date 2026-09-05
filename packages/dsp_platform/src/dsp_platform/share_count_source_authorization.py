"""Static authorization catalog for share-count sources.

A working API is not approval. Written commercial permission is required
before a T2 connector may promote. GOV-001 classifies official issuer and
exchange disclosures as T1 evidence *classes*; live NSE/BSE scrapers are
not production connectors.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

__all__ = [
    "SOURCE_CATALOG",
    "SourceAuthorization",
    "SourceAuthorizationError",
    "SourceAuthorizationStatus",
    "SourceAuthorityClass",
    "SourceRole",
    "assert_source_authorized",
    "get_source_authorization",
    "iter_sources_for_role",
]


class SourceAuthorizationStatus(StrEnum):
    APPROVED = "APPROVED"
    PENDING = "PENDING"
    REJECTED = "REJECTED"


class SourceAuthorityClass(StrEnum):
    """T1–T4 authority class. A working API is not T1 and is not a license."""

    T1 = "T1"
    T2 = "T2"
    T3 = "T3"
    T4 = "T4"


class SourceRole(StrEnum):
    SHARE_COUNT_OBSERVATION = "share_count_observation"
    CORPORATE_ACTION_COMPLETENESS = "corporate_action_completeness"
    IDENTITY = "identity"
    DISCOVERY = "discovery"
    PROMOTION = "promotion"


@dataclass(frozen=True, slots=True)
class SourceAuthorization:
    source_id: str
    status: SourceAuthorizationStatus
    roles: frozenset[SourceRole]
    authority_class: SourceAuthorityClass
    scope: str
    notes: str


SOURCE_CATALOG: dict[str, SourceAuthorization] = {
    "promoted_snapshot_artifact": SourceAuthorization(
        source_id="promoted_snapshot_artifact",
        status=SourceAuthorizationStatus.APPROVED,
        roles=frozenset(
            {
                SourceRole.SHARE_COUNT_OBSERVATION,
                SourceRole.IDENTITY,
            }
        ),
        authority_class=SourceAuthorityClass.T1,
        scope="Already-signed production snapshot JSON. Not a live feed.",
        notes="May reuse count/as_of. Cannot silently extend complete_through.",
    ),
    "t1_issuer_disclosure": SourceAuthorization(
        source_id="t1_issuer_disclosure",
        status=SourceAuthorizationStatus.APPROVED,
        roles=frozenset({SourceRole.SHARE_COUNT_OBSERVATION, SourceRole.IDENTITY}),
        authority_class=SourceAuthorityClass.T1,
        scope="Specific issuer IR/filing document after DSP validation.",
        notes="Not a generic crawl of all IR sites. One document ≠ a universe feed.",
    ),
    "t1_corporate_action_completeness": SourceAuthorization(
        source_id="t1_corporate_action_completeness",
        status=SourceAuthorizationStatus.APPROVED,
        roles=frozenset({SourceRole.CORPORATE_ACTION_COMPLETENESS, SourceRole.IDENTITY}),
        authority_class=SourceAuthorityClass.T1,
        scope=(
            "DSP-owned attested CA corpus (complete_through proven). "
            "Not the live NSE/BSE HTTP connector."
        ),
        notes="GOV-001 official exchange/issuer CA class after DSP attestation.",
    ),
    "manual_promotion": SourceAuthorization(
        source_id="manual_promotion",
        status=SourceAuthorizationStatus.APPROVED,
        roles=frozenset({SourceRole.PROMOTION}),
        authority_class=SourceAuthorityClass.T1,
        scope="Human sign-and-package of a VALIDATED candidate.",
        notes="Refresh never writes promoted_share_counts/*.json.",
    ),
    "nse_public_api_connector": SourceAuthorization(
        source_id="nse_public_api_connector",
        status=SourceAuthorizationStatus.PENDING,
        roles=frozenset(
            {SourceRole.CORPORATE_ACTION_COMPLETENESS, SourceRole.IDENTITY}
        ),
        authority_class=SourceAuthorityClass.T1,
        scope="Live nseindia.com JSON. Cookie/WAF. No written production API contract.",
        notes="CA source class only. Does not publish total outstanding.",
    ),
    "bse_public_api_connector": SourceAuthorization(
        source_id="bse_public_api_connector",
        status=SourceAuthorizationStatus.PENDING,
        roles=frozenset(
            {SourceRole.CORPORATE_ACTION_COMPLETENESS, SourceRole.IDENTITY}
        ),
        authority_class=SourceAuthorityClass.T1,
        scope="Live BSE announcement JSON. No written production API contract.",
        notes="CA source class only. Does not publish total outstanding.",
    ),
    "twelve_data_statistics": SourceAuthorization(
        source_id="twelve_data_statistics",
        status=SourceAuthorizationStatus.PENDING,
        roles=frozenset({SourceRole.SHARE_COUNT_OBSERVATION, SourceRole.IDENTITY}),
        authority_class=SourceAuthorityClass.T2,
        scope="Statistics API shares_outstanding. No DSP commercial/display license.",
        notes="1C preferred technically; 1C-R did not authorize production use.",
    ),
    "upstox_market_data": SourceAuthorization(
        source_id="upstox_market_data",
        status=SourceAuthorizationStatus.REJECTED,
        roles=frozenset(),
        authority_class=SourceAuthorityClass.T2,
        scope="Authenticated quotes/statements only.",
        notes="No total shares outstanding product.",
    ),
    "gemini_grounding": SourceAuthorization(
        source_id="gemini_grounding",
        status=SourceAuthorizationStatus.REJECTED,
        roles=frozenset({SourceRole.DISCOVERY}),
        authority_class=SourceAuthorityClass.T3,
        scope="Discovery only if ever unblocked. Never observation or promotion.",
        notes="Stage 1D forensic FAILED/BLOCKED. No share-count authority.",
    ),
    "screener_aggregator": SourceAuthorization(
        source_id="screener_aggregator",
        status=SourceAuthorizationStatus.REJECTED,
        roles=frozenset({SourceRole.DISCOVERY}),
        authority_class=SourceAuthorityClass.T3,
        scope="GOV-001 Tier 3 aggregator.",
        notes="Cannot promote.",
    ),
    "yahoo_finance": SourceAuthorization(
        source_id="yahoo_finance",
        status=SourceAuthorizationStatus.REJECTED,
        roles=frozenset({SourceRole.DISCOVERY}),
        authority_class=SourceAuthorityClass.T3,
        scope="Aggregator quotes. Not outstanding authority.",
        notes="T3 discovery only.",
    ),
    "google_search": SourceAuthorization(
        source_id="google_search",
        status=SourceAuthorizationStatus.REJECTED,
        roles=frozenset({SourceRole.DISCOVERY}),
        authority_class=SourceAuthorityClass.T3,
        scope="Search snippets. Never outstanding authority.",
        notes="Discovery only. Snippets are not evidence.",
    ),
    "unverified_web": SourceAuthorization(
        source_id="unverified_web",
        status=SourceAuthorizationStatus.REJECTED,
        roles=frozenset({SourceRole.DISCOVERY}),
        authority_class=SourceAuthorityClass.T4,
        scope="Untrusted/unverified pages.",
        notes="Never authoritative.",
    ),
}


def get_source_authorization(source_id: str) -> SourceAuthorization | None:
    return SOURCE_CATALOG.get(str(source_id or "").strip())


def assert_source_authorized(source_id: str, role: SourceRole) -> SourceAuthorization:
    """Fail closed unless the source is APPROVED for this role."""
    record = get_source_authorization(source_id)
    if record is None:
        raise SourceAuthorizationError(
            SourceAuthorizationStatus.REJECTED,
            f"unknown source {source_id!r} cannot be used for {role}",
        )
    if record.status is SourceAuthorizationStatus.REJECTED:
        raise SourceAuthorizationError(
            record.status,
            f"source {source_id!r} is REJECTED for share-count use",
        )
    if record.status is SourceAuthorizationStatus.PENDING:
        raise SourceAuthorizationError(
            record.status,
            f"source {source_id!r} is PENDING and cannot promote or refresh",
        )
    if role not in record.roles:
        raise SourceAuthorizationError(
            record.status,
            f"source {source_id!r} is not authorized for role {role}",
        )
    return record


def iter_sources_for_role(
    role: SourceRole, *, status: SourceAuthorizationStatus | None = None
) -> tuple[SourceAuthorization, ...]:
    rows = [row for row in SOURCE_CATALOG.values() if role in row.roles]
    if status is not None:
        rows = [row for row in rows if row.status is status]
    return tuple(rows)


class SourceAuthorizationError(Exception):
    def __init__(self, status: SourceAuthorizationStatus, detail: str) -> None:
        self.status = status
        super().__init__(detail)
