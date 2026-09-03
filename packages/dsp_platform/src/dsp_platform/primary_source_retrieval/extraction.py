"""Extract candidate ExternalEvidenceRecord from a retrieved document.

This is not semantic truth verification, ShareCount acceptance, or
valuation. If the requested fact cannot be identified safely, return None.
"""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

from dsp_platform.external_evidence.models import (
    CURRENT_OUTSTANDING_FACT_IDS,
    WEIGHTED_AVERAGE_SHARES_FACT_IDS,
    EvidenceKind,
    EvidenceQuality,
    EvidenceValidationStatus,
    ExternalEvidenceIdentity,
    ExternalEvidenceRecord,
    ExternalEvidenceValidationError,
    SourceTier,
    SourceType,
)
from dsp_platform.external_evidence.validation import assert_identities_compatible
from dsp_platform.external_evidence_discovery.port import bound_evidence_excerpt
from dsp_platform.primary_source_retrieval.models import (
    RetrievedPrimarySourceDocument,
)

__all__ = ["extract_candidate_evidence"]

_OUTSTANDING_PHRASES = (
    "issued and outstanding",
    "shares outstanding",
    "outstanding shares",
    "outstanding share capital",
    "current outstanding shares",
    "current shares outstanding",
)
_ALWAYS_FORBIDDEN = (
    "weighted average",
    "weighted-average",
    "equity capital",
    "paid-up capital",
    "paid up capital",
    "earnings per share",
    "basic eps",
    "diluted eps",
    "market capitalization",
    "market cap",
    "open interest",
    "implied shares",
    "implying",
    "implies",
    "derived shares",
)
_SCALE_OR_MONEY = (
    "million",
    "millions",
    "crore",
    "crores",
    "lakh",
    "lakhs",
    "billion",
    "percent",
    "inr",
    "usd",
    "eur",
)
_SHARE_COUNT = re.compile(
    r"(?P<value>\d{1,3}(?:,\d{3})+|\d+)(?:\.(?P<frac>\d+))?\s+shares\b",
    re.IGNORECASE,
)
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


def extract_candidate_evidence(
    document: RetrievedPrimarySourceDocument,
    *,
    fact_id: str,
    requested_identity: ExternalEvidenceIdentity,
) -> ExternalEvidenceRecord | None:
    """Return one candidate record, or None when the fact is not defensible."""
    if not isinstance(document, RetrievedPrimarySourceDocument):
        return None
    assert_identities_compatible(requested_identity, document.identity)
    fact = str(fact_id or "").strip().lower()
    if fact in WEIGHTED_AVERAGE_SHARES_FACT_IDS:
        return None
    if fact not in CURRENT_OUTSTANDING_FACT_IDS:
        return None
    return _extract_current_outstanding(document)


def _extract_current_outstanding(
    document: RetrievedPrimarySourceDocument,
) -> ExternalEvidenceRecord | None:
    if document.as_of is None:
        return None
    sentences = _sentences(document.text)
    values: list[Decimal] = []
    excerpts: list[str] = []
    for sentence in sentences:
        lowered = sentence.lower()
        if not any(phrase in lowered for phrase in _OUTSTANDING_PHRASES):
            continue
        if _is_forbidden_claim(lowered):
            return None
        if any(tok in lowered for tok in _SCALE_OR_MONEY):
            return None
        if "%" in sentence or "$" in sentence:
            return None
        match = _SHARE_COUNT.search(sentence)
        if match is None:
            return None
        try:
            raw = match.group("value").replace(",", "")
            frac = match.group("frac")
            dec = Decimal(raw if frac is None else f"{raw}.{frac}")
        except (InvalidOperation, ValueError, TypeError):
            return None
        if not dec.is_finite() or dec <= 0:
            return None
        try:
            excerpt = bound_evidence_excerpt(sentence.strip())
        except ExternalEvidenceValidationError:
            return None
        values.append(dec)
        excerpts.append(excerpt)
    if len(values) != 1:
        return None
    return ExternalEvidenceRecord(
        fact_id="current_outstanding",
        identity=document.identity,
        evidence_kind=EvidenceKind.NUMERICAL,
        numeric_value=float(values[0]),
        unit="shares",
        as_of=document.as_of,
        publication_date=document.publication_date,
        source_url=document.locator,
        source_type=document.source_type
        if isinstance(document.source_type, SourceType)
        else SourceType.FILING,
        source_tier=document.source_tier
        if isinstance(document.source_tier, SourceTier)
        else SourceTier.TIER_1_PRIMARY,
        evidence_reference=excerpts[0],
        retrieved_at=document.retrieved_at,
        evidence_quality=EvidenceQuality.UNKNOWN,
        validation_status=EvidenceValidationStatus.CANDIDATE,
        may_influence_calculation=False,
        claimed_dsp_field=None,
        text_value=None,
    )


def _is_forbidden_claim(lowered: str) -> bool:
    if any(phrase in lowered for phrase in _ALWAYS_FORBIDDEN):
        return True
    if re.search(r"\beps\b", lowered):
        return True
    if re.search(r"\bvolume\b", lowered):
        return True
    if re.search(r"\bprice\b", lowered) and "share" in lowered:
        return True
    return not any(phrase in lowered for phrase in _OUTSTANDING_PHRASES)


def _sentences(text: str) -> list[str]:
    blob = str(text or "").strip()
    if not blob:
        return []
    parts = _SENTENCE_SPLIT.split(blob)
    return [part.strip() for part in parts if part.strip()]
