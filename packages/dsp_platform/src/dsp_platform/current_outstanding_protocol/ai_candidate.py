"""Parse an untrusted share-count candidate from CanonicalAIDraft.

DSP-owned. Does not construct ShareCountSnapshot or ShareCountEvidenceClaim.
Ignores valuation/recommendation fields on CanonicalAIResearchOutput.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date

from dsp_platform.canonical_research_ai.models import CanonicalAIDraft
from dsp_platform.current_outstanding_protocol.models import (
    UntrustedShareCountAiCandidate,
)

__all__ = ["untrusted_candidate_from_ai_draft"]


def untrusted_candidate_from_ai_draft(
    draft: object,
) -> UntrustedShareCountAiCandidate | None:
    """Copy claimed extraction fields. Malformed drafts yield None."""
    if not isinstance(draft, CanonicalAIDraft):
        return None
    payload = draft.untrusted_extraction
    if not isinstance(payload, Mapping):
        return None
    company = _text(
        payload.get("company_identity") or payload.get("company")
    )
    unit = _text(payload.get("unit"))
    source = _text(
        payload.get("source_reference") or payload.get("source_url")
    )
    excerpt = _text(
        payload.get("supporting_excerpt")
        or payload.get("evidence_excerpt")
        or payload.get("evidence_reference")
    )
    evidence_ref = _text(payload.get("evidence_reference")) or excerpt
    if not company or not unit or not source or not excerpt:
        return None
    as_of = payload.get("as_of_date")
    if as_of is None:
        as_of = payload.get("as_of")
    if isinstance(as_of, str):
        as_of = as_of.strip() or None
    if isinstance(as_of, date):
        pass
    elif as_of is not None and not isinstance(as_of, str):
        return None
    count = payload.get("claimed_share_count")
    if count is None:
        count = payload.get("share_count")
    if count is None:
        count = payload.get("shares_outstanding")
    if count is None:
        return None
    return UntrustedShareCountAiCandidate(
        company_identity=company,
        claimed_share_count=count,
        unit=unit,
        as_of_date=as_of,
        source_reference=source,
        evidence_reference=evidence_ref,
        supporting_excerpt=excerpt,
        validation_status="untrusted",
        ticker=_text(payload.get("ticker")),
        exchange=_text(payload.get("exchange")),
        source_name=_text(payload.get("source_name")),
        source_type=_text(payload.get("source_type")),
        explanation=_text(payload.get("explanation")),
        claim_type=_text(payload.get("claim_type")) or "CURRENT_OUTSTANDING",
    )


def _text(value: object) -> str:
    if value is None or isinstance(value, bool):
        return ""
    if not isinstance(value, str):
        return ""
    return value.strip()
