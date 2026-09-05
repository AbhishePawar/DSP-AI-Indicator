"""Extract candidate ExternalEvidenceRecord from a retrieved document.

This is not semantic truth verification, ShareCount acceptance, or
valuation. If the requested fact cannot be identified safely, return None.
"""

from __future__ import annotations

import re
from datetime import date
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

__all__ = ["extract_candidate_evidence", "extract_paid_up_equity_shares"]

_OUTSTANDING_PHRASES = (
    "issued and outstanding",
    "shares outstanding",
    "outstanding shares",
    "outstanding share capital",
    "current outstanding shares",
    "current shares outstanding",
    "equity shares outstanding",
    "equity shares currently outstanding",
    "total number of equity shares outstanding",
    "total equity shares currently outstanding",
)
_SHARE_COUNT = re.compile(
    r"(?P<value>\d{1,3}(?:,\d{2})+,\d{3}|\d{1,3}(?:,\d{3})+|\d+)"
    r"(?:\.(?P<frac>\d+))?"
    r"(?:\s*\([^)]{0,80}\))?"
    r"\s+(?:equity\s+)?shares\b",
    re.IGNORECASE,
)
_OUTSTANDING_ANCHORED = re.compile(
    r"(?:issued and outstanding|equity shares currently outstanding|"
    r"equity shares outstanding|shares outstanding|outstanding shares|"
    r"total equity shares currently outstanding|"
    r"total number of equity shares outstanding)"
    r"(?:[^0-9]{0,48})?"
    r"(?P<value>\d{1,3}(?:,\d{2})+,\d{3}|\d{1,3}(?:,\d{3})+|\d{4,})",
    re.IGNORECASE,
)
_PAID_UP_CAPITAL = re.compile(
    r"paid[- ]up equity share capital[^.]{0,160}?"
    r"(?:rs\.?|inr|₹)\s*(?P<amount>[\d,]+(?:\.\d+)?)"
    r"(?:\s*(?P<scale>crore|crores|lakh|lakhs|million))?",
    re.IGNORECASE,
)
_FACE_VALUE = re.compile(
    r"face value[^.]{0,80}?(?:of\s+)?(?:rs\.?|inr|₹)\s*(?P<fv>[\d]+(?:\.\d+)?)",
    re.IGNORECASE,
)
_DERIVATION_REQUIRED = (
    "issued",
    "fully paid",
)
_DERIVATION_FORBIDDEN = (
    "weighted average",
    "weighted-average",
    "free-float",
    "free float",
    "authorized share",
    "authorised share",
    "authorized capital",
    "authorised capital",
    "partly paid",
    "partly-paid",
    "treasury",
    "preference share",
    "multiple class",
    "different face value",
    "market cap",
    "market capitalization",
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
    "free-float",
    "free float",
    "float shares",
    "authorized shares",
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
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")
_MONTHS = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}
_AS_OF_MDY = re.compile(
    r"\bas (?:of|at|on)\s+(?P<month>[A-Za-z]+)\s+(?P<day>\d{1,2}),\s+(?P<year>\d{4})\b",
    re.IGNORECASE,
)
_AS_OF_DMY = re.compile(
    r"\bas (?:of|at|on)\s+(?P<day>\d{1,2})\s+(?P<month>[A-Za-z]+)\s+(?P<year>\d{4})\b",
    re.IGNORECASE,
)
_AS_OF_ISO = re.compile(
    r"\bas of\s+(?P<iso>\d{4}-\d{2}-\d{2})\b",
    re.IGNORECASE,
)


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
    sentences = _candidate_windows(document.text)
    values: list[Decimal] = []
    excerpts: list[str] = []
    as_of_dates: list[date] = []
    for sentence in sentences:
        lowered = sentence.lower()
        if not any(phrase in lowered for phrase in _OUTSTANDING_PHRASES):
            continue
        if _is_forbidden_claim(lowered):
            continue
        if any(tok in lowered for tok in _SCALE_OR_MONEY):
            continue
        if "%" in sentence or "$" in sentence:
            continue
        match = _OUTSTANDING_ANCHORED.search(sentence) or _SHARE_COUNT.search(sentence)
        if match is None:
            continue
        try:
            raw = match.group("value").replace(",", "")
            frac = match.groupdict().get("frac")
            dec = Decimal(raw if not frac else f"{raw}.{frac}")
        except (InvalidOperation, ValueError, TypeError):
            continue
        if not dec.is_finite() or dec <= 0:
            continue
        as_of = document.as_of or _as_of_from_sentence(sentence)
        if as_of is None:
            continue
        excerpt = _bounded_excerpt(sentence)
        if excerpt is None:
            continue
        values.append(dec)
        excerpts.append(excerpt)
        as_of_dates.append(as_of)
    unique = set(values)
    if len(unique) != 1:
        return None
    return ExternalEvidenceRecord(
        fact_id="current_outstanding",
        identity=document.identity,
        evidence_kind=EvidenceKind.NUMERICAL,
        numeric_value=float(values[0]),
        unit="shares",
        as_of=as_of_dates[0],
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


def _as_of_from_sentence(sentence: str) -> date | None:
    iso = _AS_OF_ISO.search(sentence)
    if iso is not None:
        try:
            return date.fromisoformat(iso.group("iso"))
        except ValueError:
            return None
    mdy = _AS_OF_MDY.search(sentence)
    if mdy is not None:
        return _calendar_date(mdy.group("year"), mdy.group("month"), mdy.group("day"))
    dmy = _AS_OF_DMY.search(sentence)
    if dmy is not None:
        return _calendar_date(dmy.group("year"), dmy.group("month"), dmy.group("day"))
    return None


def _calendar_date(year: str, month: str, day: str) -> date | None:
    month_num = _MONTHS.get(month.strip().casefold())
    if month_num is None:
        return None
    try:
        return date(int(year), month_num, int(day))
    except ValueError:
        return None


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


def _bounded_excerpt(sentence: str) -> str | None:
    text = " ".join(str(sentence or "").split())
    if not text:
        return None
    try:
        return bound_evidence_excerpt(text)
    except ExternalEvidenceValidationError:
        return None


def _candidate_windows(text: str) -> list[str]:
    windows = _sentences(str(text or "").replace("\n", " "))
    lines = [line.strip() for line in str(text or "").splitlines() if line.strip()]
    for index in range(len(lines)):
        windows.append(" ".join(lines[index : index + 3]))
    return windows


def _sentences(text: str) -> list[str]:
    blob = str(text or "").strip()
    if not blob:
        return []
    parts = _SENTENCE_SPLIT.split(blob)
    return [part.strip() for part in parts if part.strip()]


def extract_paid_up_equity_shares(
    document: RetrievedPrimarySourceDocument,
) -> ExternalEvidenceRecord | None:
    """Derive outstanding equity shares from paid-up capital / face value.

    Requires issued-and-fully-paid proof. Does not silently invent a count.
    """
    blob = str(document.text or "").strip()
    if not blob:
        return None
    lowered = blob.casefold()
    if any(token in lowered for token in _DERIVATION_FORBIDDEN):
        return None
    if not all(token in lowered for token in _DERIVATION_REQUIRED):
        return None
    capital_hits = list(_PAID_UP_CAPITAL.finditer(blob))
    face_hits = list(_FACE_VALUE.finditer(blob))
    if len(capital_hits) != 1 or len(face_hits) != 1:
        return None
    amount = _parse_decimal(capital_hits[0].group("amount"))
    face = _parse_decimal(face_hits[0].group("fv"))
    if amount is None or face is None or amount <= 0 or face <= 0:
        return None
    scale = (capital_hits[0].group("scale") or "").casefold()
    rupees = _scale_to_rupees(amount, scale)
    shares, remainder = divmod(rupees, face)
    if remainder != 0:
        return None
    if shares <= 0 or not shares.is_finite():
        return None
    as_of = document.as_of or _as_of_from_sentence(blob)
    if as_of is None:
        for sentence in _sentences(blob):
            as_of = _as_of_from_sentence(sentence)
            if as_of is not None:
                break
    if as_of is None:
        return None
    excerpt = (
        f"Derived outstanding equity shares = paid-up equity share capital "
        f"/ face value = {rupees} / {face} = {int(shares)} issued and fully paid "
        f"equity shares as of {as_of.isoformat()}."
    )
    try:
        bounded = bound_evidence_excerpt(excerpt)
    except ExternalEvidenceValidationError:
        return None
    return ExternalEvidenceRecord(
        fact_id="current_outstanding",
        identity=document.identity,
        evidence_kind=EvidenceKind.NUMERICAL,
        numeric_value=float(shares),
        unit="shares",
        as_of=as_of,
        publication_date=document.publication_date,
        source_url=document.locator,
        source_type=document.source_type
        if isinstance(document.source_type, SourceType)
        else SourceType.FILING,
        source_tier=document.source_tier
        if isinstance(document.source_tier, SourceTier)
        else SourceTier.TIER_1_PRIMARY,
        evidence_reference=bounded,
        retrieved_at=document.retrieved_at,
        evidence_quality=EvidenceQuality.UNKNOWN,
        validation_status=EvidenceValidationStatus.CANDIDATE,
        may_influence_calculation=False,
        claimed_dsp_field=None,
        text_value=None,
    )


def _parse_decimal(raw: str | None) -> Decimal | None:
    try:
        return Decimal(str(raw or "").replace(",", ""))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _scale_to_rupees(amount: Decimal, scale: str) -> Decimal:
    if scale in {"crore", "crores"}:
        return amount * Decimal("10000000")
    if scale in {"lakh", "lakhs"}:
        return amount * Decimal("100000")
    if scale == "million":
        return amount * Decimal("1000000")
    return amount
