"""DSP validation that may promote an untrusted AI candidate.

Reuses ``accept_current_outstanding_claims``. Does not construct
ShareCountSnapshot except through that existing acceptance path.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from data_engine import (
    ADMISSIBLE_SOURCE_TIERS,
    FORBIDDEN_SOURCE_TIERS,
    ShareCountAcceptanceError,
    ShareCountEvidenceClaim,
    ShareCountSnapshot,
    accept_current_outstanding_claims,
)
from dsp_platform.current_outstanding_protocol.models import (
    UntrustedShareCountAiCandidate,
)
from dsp_platform.external_evidence.models import ExternalEvidenceIdentity
from dsp_platform.external_evidence.validation import (
    assert_identities_compatible,
    normalize_identity_token,
    validate_external_evidence_identity,
)
from dsp_platform.primary_source_retrieval.models import RetrievedPrimarySourceDocument

__all__ = ["dsp_accept_untrusted_share_count_candidate"]

_OUTSTANDING_TOKENS = ("outstanding", "shares outstanding", "current shares")
_FORBIDDEN_CLAIM_TOKENS = (
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
    "implied shares",
    "implying",
    "implies",
    "derived shares",
    "authorized shares",
    "issued shares unless",
    "authorized share",
    "authorised share",
    "authorised shares",
    "free float",
    "free-float",
    "float shares",
    "floating shares",
)
_HISTORICAL_ONLY_TOKENS = (
    "historical-only",
    "historically outstanding",
    "not current",
    "former outstanding",
    "prior-year outstanding",
    "previous year outstanding",
    "stale outstanding",
)
_UNIT_SCALE = {
    "shares": Decimal(1),
    "share": Decimal(1),
    "million shares": Decimal("1000000"),
    "millions of shares": Decimal("1000000"),
    "mn shares": Decimal("1000000"),
    "billion shares": Decimal("1000000000"),
    "billions of shares": Decimal("1000000000"),
    "bn shares": Decimal("1000000000"),
}
_AMBIGUOUS_UNIT_MARKERS = (
    "%",
    "$",
    "€",
    "£",
    "¥",
    "₹",
    "percent",
    "inr",
    "usd",
    "eur",
    "crore",
    "lakh",
    "market cap",
    "market capitalization",
)


def dsp_accept_untrusted_share_count_candidate(
    candidate: object,
    *,
    document: RetrievedPrimarySourceDocument,
    requested_identity: ExternalEvidenceIdentity,
) -> ShareCountSnapshot:
    """Validate an AI candidate against a retrieved document, then accept.

    Never treats CanonicalAIDraft or the candidate itself as a snapshot.
    """
    if not isinstance(candidate, UntrustedShareCountAiCandidate):
        raise ShareCountAcceptanceError(
            "AI narrative and unvalidated output cannot create ShareCountSnapshot"
        )
    if not isinstance(document, RetrievedPrimarySourceDocument):
        raise ShareCountAcceptanceError(
            "share-count promotion requires RetrievedPrimarySourceDocument"
        )
    validate_external_evidence_identity(requested_identity)
    try:
        assert_identities_compatible(requested_identity, document.identity)
    except Exception as exc:
        raise ShareCountAcceptanceError(
            f"share-count identity mismatch: {exc}"
        ) from exc
    _assert_candidate_identity(candidate, requested_identity)
    excerpt = _require_supporting_excerpt(candidate, document)
    _require_current_relevance(candidate, excerpt)
    as_of = _require_explicit_as_of(candidate, document)
    shares, unit = _normalize_unit(candidate)
    source_url = str(candidate.source_reference or "").strip()
    if not source_url or source_url != str(document.locator).strip():
        raise ShareCountAcceptanceError(
            "source_url is required and must match the retrieved document"
        )
    tier = str(getattr(document.source_tier, "value", document.source_tier))
    if tier in FORBIDDEN_SOURCE_TIERS:
        raise ShareCountAcceptanceError(
            "Tier 3/4 cannot become ShareCountSnapshot authority"
        )
    if tier not in ADMISSIBLE_SOURCE_TIERS:
        raise ShareCountAcceptanceError(
            f"source_tier {tier!r} cannot become share-count authority"
        )
    source_type = str(getattr(document.source_type, "value", document.source_type))
    claim = ShareCountEvidenceClaim(
        symbol=requested_identity.symbol,
        exchange=requested_identity.exchange,
        isin=requested_identity.isin,
        shares=shares,
        unit=unit,
        basis="current_outstanding",
        as_of=as_of,
        publication_date=document.publication_date,
        source_url=source_url,
        source_type=source_type,
        source_tier=tier,
        evidence_reference=excerpt,
        retrieved_at=document.retrieved_at,
        fact_id="current_outstanding",
        validation_status="validated",
    )
    return accept_current_outstanding_claims(
        [claim],
        symbol=requested_identity.symbol,
        exchange=requested_identity.exchange,
        isin=requested_identity.isin,
    )


def _assert_candidate_identity(
    candidate: UntrustedShareCountAiCandidate,
    requested: ExternalEvidenceIdentity,
) -> None:
    claimed = str(candidate.company_identity or "").strip()
    if not claimed:
        raise ShareCountAcceptanceError(
            "share-count identity mismatch: AI candidate has no company identity"
        )
    if "." in claimed:
        raise ShareCountAcceptanceError(
            "share-count identity rejected: symbol must be canonical"
        )
    symbol = normalize_identity_token(requested.symbol)
    claimed_token = normalize_identity_token(claimed)
    ticker = normalize_identity_token(candidate.ticker)
    if ticker and ticker != symbol:
        raise ShareCountAcceptanceError(
            f"share-count identity mismatch: requested {symbol}, "
            f"got {ticker}"
        )
    claimed_exchange = normalize_identity_token(candidate.exchange) or None
    requested_exchange = normalize_identity_token(requested.exchange) or None
    if (
        claimed_exchange
        and requested_exchange
        and claimed_exchange != requested_exchange
    ):
        raise ShareCountAcceptanceError(
            "share-count identity mismatch: exchange disagreement "
            f"({requested_exchange!r} vs {claimed_exchange!r}); "
            "NSE/BSE are not converted"
        )
    claimed_isin = normalize_identity_token(candidate.isin) or None
    requested_isin = normalize_identity_token(requested.isin) or None
    if claimed_isin and requested_isin and claimed_isin != requested_isin:
        raise ShareCountAcceptanceError(
            "share-count identity mismatch: ISIN disagreement "
            f"({requested_isin!r} vs {claimed_isin!r})"
        )
    claimed_mic = normalize_identity_token(candidate.mic) or None
    requested_mic = normalize_identity_token(requested.mic) or None
    if claimed_mic and requested_mic and claimed_mic != requested_mic:
        raise ShareCountAcceptanceError(
            "share-count identity mismatch: MIC disagreement "
            f"({requested_mic!r} vs {claimed_mic!r}); "
            "XNSE/XBOM/ADR venues are not converted"
        )
    name = str(requested.company_name or "").strip()
    if claimed_token == symbol:
        return
    if name and claimed.casefold() == name.casefold():
        return
    raise ShareCountAcceptanceError(
        f"share-count identity mismatch: requested {symbol}, "
        f"got {claimed_token or claimed!r}"
    )


def _require_supporting_excerpt(
    candidate: UntrustedShareCountAiCandidate,
    document: RetrievedPrimarySourceDocument,
) -> str:
    excerpt = str(
        candidate.supporting_excerpt or candidate.evidence_reference or ""
    ).strip()
    if not excerpt:
        raise ShareCountAcceptanceError("evidence_reference is required")
    text = str(document.text or "")
    if excerpt not in text:
        raise ShareCountAcceptanceError(
            "supporting excerpt is not present in the retrieved document"
        )
    lowered = excerpt.lower()
    if not any(token in lowered for token in _OUTSTANDING_TOKENS):
        raise ShareCountAcceptanceError(
            "evidence_reference does not explicitly support outstanding shares"
        )
    if any(token in lowered for token in _FORBIDDEN_CLAIM_TOKENS):
        raise ShareCountAcceptanceError(
            "excerpt cannot establish current outstanding shares"
        )
    return excerpt


def _require_current_relevance(
    candidate: UntrustedShareCountAiCandidate,
    excerpt: str,
) -> None:
    blob = f"{excerpt} {candidate.explanation} {candidate.claim_type}".lower()
    if any(token in blob for token in _HISTORICAL_ONLY_TOKENS):
        raise ShareCountAcceptanceError(
            "historical-only share count cannot be treated as current outstanding"
        )
    claim_type = str(candidate.claim_type or "").strip().upper()
    if claim_type and claim_type not in {
        "CURRENT_OUTSTANDING",
        "CURRENT OUTSTANDING",
        "",
    }:
        raise ShareCountAcceptanceError(
            "historical-only share count cannot be treated as current outstanding"
        )


def _require_explicit_as_of(
    candidate: UntrustedShareCountAiCandidate,
    document: RetrievedPrimarySourceDocument,
) -> date:
    raw = candidate.as_of_date
    if raw is None or raw == "":
        raise ShareCountAcceptanceError(
            "as_of is required and must be a date, not retrieved_at"
        )
    if isinstance(raw, datetime):
        raise ShareCountAcceptanceError(
            "as_of is required and must be a date, not retrieved_at"
        )
    if isinstance(raw, date):
        parsed = raw
    elif isinstance(raw, str):
        try:
            parsed = date.fromisoformat(raw.strip())
        except ValueError as exc:
            raise ShareCountAcceptanceError(
                "as_of is required and must be a date, not retrieved_at"
            ) from exc
    else:
        raise ShareCountAcceptanceError(
            "as_of is required and must be a date, not retrieved_at"
        )
    if document.as_of is not None:
        if parsed != document.as_of:
            raise ShareCountAcceptanceError(
                "as_of is required and must match the document outstanding-share date"
            )
        return parsed
    if not _date_is_evidenced_in_text(parsed, str(document.text or "")):
        raise ShareCountAcceptanceError(
            "as_of is required and must be a date, not retrieved_at"
        )
    return parsed


def _date_is_evidenced_in_text(value: date, text: str) -> bool:
    blob = text.lower()
    if value.isoformat() in blob:
        return True
    month = value.strftime("%B")
    short = value.strftime("%b")
    day = value.day
    year = value.year
    forms = (
        f"{day} {month} {year}",
        f"{day} {short} {year}",
        f"{month} {day}, {year}",
        f"{short} {day}, {year}",
    )
    return any(form.lower() in blob for form in forms)


def _normalize_unit(
    candidate: UntrustedShareCountAiCandidate,
) -> tuple[Decimal, str]:
    unit = " ".join(str(candidate.unit or "").strip().lower().split())
    if not unit:
        raise ShareCountAcceptanceError(
            "share-count unit must be shares; no silent scale or currency"
        )
    if any(marker in unit for marker in _AMBIGUOUS_UNIT_MARKERS):
        raise ShareCountAcceptanceError(
            "share-count unit must be shares, not currency/percentage"
        )
    scale = _UNIT_SCALE.get(unit)
    if scale is None:
        raise ShareCountAcceptanceError(
            "share-count unit must be shares; no silent scale or currency"
        )
    shares = _require_positive_shares(candidate.claimed_share_count)
    normalized = shares * scale
    if not normalized.is_finite() or normalized <= 0:
        raise ShareCountAcceptanceError("share count must be > 0")
    return normalized, "shares"


def _require_positive_shares(raw: object) -> Decimal:
    if isinstance(raw, bool) or raw is None:
        raise ShareCountAcceptanceError("share count must be numeric")
    try:
        dec = raw if isinstance(raw, Decimal) else Decimal(str(raw))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ShareCountAcceptanceError("share count must be numeric") from exc
    if not dec.is_finite():
        raise ShareCountAcceptanceError("share count must be finite")
    if dec <= 0:
        raise ShareCountAcceptanceError("share count must be > 0")
    return dec
