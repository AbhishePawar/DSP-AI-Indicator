"""Untrusted AI web-evidence claims → T3 discovery locators.

AI may discover Screener and other internet sources. Discovery records
never become ShareCountSnapshot. DSP promotion remains the only
acceptance path. This module does not call HTTP or providers.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from typing import Any
from urllib.parse import urlparse

from dsp_platform.canonical_research_ai.models import CanonicalAIDraft
from dsp_platform.external_evidence.models import (
    EvidenceKind,
    EvidenceQuality,
    EvidenceValidationStatus,
    ExternalEvidenceIdentity,
    ExternalEvidenceRecord,
    QualitativeEvidenceTopic,
    SourceTier,
    SourceType,
)
from dsp_platform.external_evidence.validation import (
    assert_identities_compatible,
    validate_external_evidence_record,
)
from dsp_platform.external_evidence_discovery.models import (
    ExternalEvidenceDiscoveryRequest,
    ExternalEvidenceDiscoveryResult,
)
from dsp_platform.external_evidence_discovery.port import bound_evidence_excerpt

__all__ = [
    "APPROVED_SECONDARY_WEB_HOSTS",
    "UntrustedWebEvidenceClaim",
    "discovery_result_from_untrusted_web_claims",
    "untrusted_web_claims_from_ai_draft",
]

# Empty until governance explicitly registers a secondary web host.
APPROVED_SECONDARY_WEB_HOSTS: frozenset[str] = frozenset()
_SCREENER_HOSTS = frozenset({"screener.in", "www.screener.in"})


@dataclass(frozen=True, slots=True)
class UntrustedWebEvidenceClaim:
    """AI-discovered internet claim. Discovery only. Never a snapshot."""

    company_identity: str
    source_url: str
    evidence_excerpt: str
    claimed_share_count: object | None = None
    unit: str = ""
    as_of: date | str | None = None
    ticker: str = ""
    exchange: str = ""
    source_name: str = ""
    source_type: str = ""
    evidence_reference: str = ""
    explanation: str = ""
    claim_type: str = "CURRENT_OUTSTANDING"

    def to_dict(self) -> dict[str, Any]:
        as_of = self.as_of
        return {
            "company_identity": self.company_identity,
            "ticker": self.ticker,
            "exchange": self.exchange,
            "claimed_share_count": self.claimed_share_count,
            "unit": self.unit,
            "as_of": as_of.isoformat() if isinstance(as_of, date) else as_of,
            "source_name": self.source_name,
            "source_url": self.source_url,
            "source_type": self.source_type,
            "evidence_excerpt": self.evidence_excerpt,
            "evidence_reference": self.evidence_reference,
            "explanation": self.explanation,
            "claim_type": self.claim_type,
            "trusted": False,
            "source_tier": SourceTier.TIER_3_DISCOVERY.value,
            "may_influence_calculation": False,
            "may_create_snapshot": False,
        }


def untrusted_web_claims_from_ai_draft(
    draft: object,
) -> tuple[UntrustedWebEvidenceClaim, ...]:
    """Copy untrusted web claims from a CanonicalAIDraft. Never a snapshot."""
    if not isinstance(draft, CanonicalAIDraft):
        return ()
    payload = draft.untrusted_extraction
    if not isinstance(payload, Mapping):
        return ()
    raw_rows = payload.get("web_claims")
    if raw_rows is None and payload.get("source_url"):
        raw_rows = (payload,)
    if not isinstance(raw_rows, (list, tuple)):
        return ()
    claims: list[UntrustedWebEvidenceClaim] = []
    for row in raw_rows:
        parsed = _claim_from_mapping(row)
        if parsed is not None:
            claims.append(parsed)
    return tuple(claims)


def discovery_result_from_untrusted_web_claims(
    request: ExternalEvidenceDiscoveryRequest,
    claims: Sequence[UntrustedWebEvidenceClaim],
) -> ExternalEvidenceDiscoveryResult:
    """Map AI web claims to T3 locator records. Numbers stay untrusted."""
    records: list[ExternalEvidenceRecord] = []
    for claim in claims:
        record = _locator_record(request, claim)
        if record is None:
            continue
        validate_external_evidence_record(record)
        records.append(record)
    return ExternalEvidenceDiscoveryResult(
        request=request,
        records=tuple(records),
    )


def _claim_from_mapping(row: object) -> UntrustedWebEvidenceClaim | None:
    if not isinstance(row, Mapping):
        return None
    company = _text(
        row.get("company_identity") or row.get("company") or row.get("ticker")
    )
    url = _text(row.get("source_url") or row.get("source_reference"))
    excerpt = _text(
        row.get("evidence_excerpt")
        or row.get("supporting_excerpt")
        or row.get("evidence_reference")
    )
    if not company or not url or not excerpt:
        return None
    as_of = row.get("as_of_date")
    if as_of is None:
        as_of = row.get("as_of")
    if isinstance(as_of, str):
        as_of = as_of.strip() or None
    count = row.get("claimed_share_count")
    if count is None:
        count = row.get("shares_outstanding")
    return UntrustedWebEvidenceClaim(
        company_identity=company,
        source_url=url,
        evidence_excerpt=excerpt,
        claimed_share_count=count,
        unit=_text(row.get("unit")),
        as_of=as_of if isinstance(as_of, (date, str)) or as_of is None else None,
        ticker=_text(row.get("ticker")),
        exchange=_text(row.get("exchange")),
        source_name=_text(row.get("source_name")),
        source_type=_text(row.get("source_type")),
        evidence_reference=_text(row.get("evidence_reference")) or excerpt,
        explanation=_text(row.get("explanation")),
        claim_type=_text(row.get("claim_type")) or "CURRENT_OUTSTANDING",
    )


def _locator_record(
    request: ExternalEvidenceDiscoveryRequest,
    claim: UntrustedWebEvidenceClaim,
) -> ExternalEvidenceRecord | None:
    try:
        assert_identities_compatible(
            request.identity, _claimed_identity(claim, request)
        )
    except Exception:
        return None
    try:
        excerpt = bound_evidence_excerpt(claim.evidence_excerpt.strip())
    except Exception:
        return None
    host = (urlparse(claim.source_url).hostname or "").lower()
    source_type = _source_type(claim, host)
    name = claim.source_name or host or "web"
    locator_note = (
        f"Untrusted AI locator via {name}. Not share-count authority. {excerpt}"
    )
    try:
        text_value = bound_evidence_excerpt(locator_note[:500].strip())
    except Exception:
        text_value = excerpt
    return ExternalEvidenceRecord(
        fact_id=request.fact_id,
        identity=request.identity,
        evidence_kind=EvidenceKind.QUALITATIVE,
        text_value=text_value,
        topic=QualitativeEvidenceTopic.OTHER_QUALITATIVE,
        as_of=None,
        publication_date=None,
        source_url=claim.source_url.strip(),
        source_type=source_type,
        source_tier=_discovery_tier(host),
        evidence_reference=excerpt,
        retrieved_at=request.retrieved_at,
        evidence_quality=EvidenceQuality.UNKNOWN,
        validation_status=EvidenceValidationStatus.CANDIDATE,
        may_influence_calculation=False,
        claimed_dsp_field=None,
    )


def _claimed_identity(
    claim: UntrustedWebEvidenceClaim,
    request: ExternalEvidenceDiscoveryRequest,
) -> ExternalEvidenceIdentity:
    requested = request.identity
    ticker = str(claim.ticker or "").strip().upper()
    if ticker:
        symbol = ticker.split(".", 1)[0]
    else:
        company = str(claim.company_identity or "").strip()
        name = str(requested.company_name or "").strip()
        if name and company.casefold() == name.casefold():
            symbol = requested.symbol
        else:
            symbol = company.split(".", 1)[0].strip().upper() or requested.symbol
    exchange = (
        str(claim.exchange or requested.exchange or "").strip().upper() or None
    )
    return ExternalEvidenceIdentity(
        symbol=symbol or requested.symbol,
        exchange=exchange or requested.exchange,
        isin=requested.isin,
        company_name=requested.company_name,
        mic=requested.mic,
    )


def _discovery_tier(host: str) -> SourceTier:
    if host in APPROVED_SECONDARY_WEB_HOSTS:
        return SourceTier.TIER_2_SECONDARY
    if host in _SCREENER_HOSTS:
        return SourceTier.TIER_3_DISCOVERY
    return SourceTier.TIER_3_DISCOVERY


def _source_type(claim: UntrustedWebEvidenceClaim, host: str) -> SourceType:
    raw = (claim.source_type or "").strip().lower()
    if raw in {item.value for item in SourceType}:
        parsed = SourceType(raw)
        if parsed in {
            SourceType.SEARCH_SNIPPET,
            SourceType.SERP_SNIPPET,
            SourceType.SEARCH_RESULT,
            SourceType.SEARCH_RESULT_SNIPPET,
        }:
            return parsed
    if host in _SCREENER_HOSTS:
        return SourceType.COMPANY_WEBSITE
    if raw in {"filing", "annual report", "regulatory"}:
        return SourceType.SEARCH_RESULT
    return SourceType.SEARCH_RESULT


def _text(value: object) -> str:
    if value is None or isinstance(value, bool):
        return ""
    if not isinstance(value, str):
        return ""
    return value.strip()
