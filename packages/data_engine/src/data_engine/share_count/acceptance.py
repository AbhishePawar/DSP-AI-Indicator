"""Explicit DSP acceptance of current-outstanding evidence claims.

This is not a vendor adapter, not an AI interpreter, and not a valuation
engine. It converts an explicit CURRENT_OUTSTANDING claim into a
ShareCountSnapshot or fails closed.

Policy (deterministic, no "latest wins"):
- Only basis=current_outstanding is accepted.
- TIER_1_PRIMARY and TIER_2_SECONDARY may be accepted.
- TIER_3_DISCOVERY and TIER_4_NEWS_CONTEXT are never authority.
- validation_status must be validated.
- as_of is required and is never copied from retrieved_at.
- Multiple unequal counts, or equal counts with unequal as_of, are
  unresolved conflicts and are rejected. No average, median, or pick.
- Age is recorded in provenance metadata only; it is not a freshness gate.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from decimal import Decimal, InvalidOperation

from data_engine.exceptions import InvalidProviderDataError
from data_engine.share_count.models import (
    ShareCountBasis,
    ShareCountField,
    ShareCountProvenance,
    ShareCountSnapshot,
    ShareCountUnit,
)
from data_engine.share_count.validation import (
    assert_share_count_identity,
    validate_share_count_snapshot,
)

__all__ = [
    "ACCEPTANCE_PROVIDER_ID",
    "ACCEPTANCE_PROVIDER_NAME",
    "ADMISSIBLE_SOURCE_TIERS",
    "FORBIDDEN_SOURCE_TIERS",
    "ShareCountAcceptanceError",
    "ShareCountEvidenceClaim",
    "accept_current_outstanding_claims",
]

ACCEPTANCE_PROVIDER_ID = "dsp_share_count_evidence_acceptance"
ACCEPTANCE_PROVIDER_NAME = "DSP ShareCount evidence acceptance"
ADMISSIBLE_SOURCE_TIERS = frozenset({"TIER_1_PRIMARY", "TIER_2_SECONDARY"})
FORBIDDEN_SOURCE_TIERS = frozenset(
    {"TIER_3_DISCOVERY", "TIER_4_NEWS_CONTEXT"}
)
_REQUIRED_BASIS = ShareCountBasis.CURRENT_OUTSTANDING.value
_REQUIRED_UNIT = ShareCountUnit.SHARES.value
_REQUIRED_STATUS = "validated"
_OUTSTANDING_TOKENS = ("outstanding", "shares outstanding", "current shares")
_CURRENCY_OR_PERCENT = frozenset("%$€£¥₹")
_SCALE_TOKENS = (
    "million",
    "millions",
    "mn",
    "crore",
    "crores",
    "lakh",
    "lakhs",
    "billion",
    "bn",
)
_SEARCH_SNIPPET_SOURCE_TYPES = frozenset(
    {
        "search_snippet",
        "serp_snippet",
        "search_result",
        "search_result_snippet",
    }
)


class ShareCountAcceptanceError(InvalidProviderDataError):
    """Raised when share-count evidence cannot be explicitly accepted."""


@dataclass(frozen=True, slots=True)
class ShareCountEvidenceClaim:
    """DSP-owned claim extracted from validated external evidence.

    Not an ExternalEvidenceRecord and not a ShareCountSnapshot.
    """

    symbol: str
    shares: Decimal | float | int | str
    unit: str
    basis: str
    as_of: date | None
    source_url: str
    source_type: str
    source_tier: str
    evidence_reference: str
    retrieved_at: datetime
    fact_id: str
    validation_status: str
    exchange: str | None = None
    isin: str | None = None
    publication_date: date | None = None


def accept_current_outstanding_claims(
    claims: Sequence[ShareCountEvidenceClaim],
    *,
    symbol: str,
    exchange: str | None = None,
    isin: str | None = None,
) -> ShareCountSnapshot:
    """Accept CURRENT_OUTSTANDING claims or fail closed. Never invents a count."""
    if not claims:
        raise ShareCountAcceptanceError(
            "no admissible current-outstanding evidence"
        )
    admissible: list[ShareCountEvidenceClaim] = []
    for claim in claims:
        _validate_claim(claim)
        _assert_claim_identity(claim, symbol=symbol, exchange=exchange, isin=isin)
        admissible.append(claim)
    chosen = _resolve_unconflicted(admissible)
    snapshot = _snapshot_from_claim(chosen)
    try:
        validate_share_count_snapshot(snapshot)
        assert_share_count_identity(
            snapshot, symbol=symbol, exchange=exchange, isin=isin
        )
    except InvalidProviderDataError as exc:
        if isinstance(exc, ShareCountAcceptanceError):
            raise
        raise ShareCountAcceptanceError(str(exc)) from exc
    return snapshot


def _validate_claim(claim: ShareCountEvidenceClaim) -> None:
    if not isinstance(claim, ShareCountEvidenceClaim):
        raise ShareCountAcceptanceError(
            "share-count acceptance requires ShareCountEvidenceClaim"
        )
    status = str(claim.validation_status or "").strip().lower()
    if status != _REQUIRED_STATUS:
        raise ShareCountAcceptanceError(
            f"share-count evidence status must be validated, got {status!r}"
        )
    basis = str(claim.basis or "").strip().lower()
    if basis != _REQUIRED_BASIS:
        raise ShareCountAcceptanceError(
            "share-count evidence basis must be current_outstanding"
        )
    unit = str(claim.unit or "").strip().lower()
    if unit != _REQUIRED_UNIT:
        raise ShareCountAcceptanceError(
            "share-count unit must be shares; no silent scale or currency"
        )
    if any(marker in unit for marker in _CURRENCY_OR_PERCENT):
        raise ShareCountAcceptanceError(
            "share-count unit must be shares, not currency/percentage"
        )
    if any(tok in unit.split() for tok in _SCALE_TOKENS):
        raise ShareCountAcceptanceError(
            "share-count unit must be shares; millions/crores are not inferred"
        )
    if isinstance(claim.as_of, datetime) or not isinstance(claim.as_of, date):
        raise ShareCountAcceptanceError(
            "as_of is required and must be a date, not retrieved_at"
        )
    if not isinstance(claim.retrieved_at, datetime):
        raise ShareCountAcceptanceError("retrieved_at is required")
    if claim.retrieved_at.tzinfo is None:
        raise ShareCountAcceptanceError("retrieved_at must be timezone-aware")
    if not str(claim.source_url or "").strip():
        raise ShareCountAcceptanceError("source_url is required")
    source_type = str(claim.source_type or "").strip().lower()
    if not source_type:
        raise ShareCountAcceptanceError("source_type is required")
    if source_type in _SEARCH_SNIPPET_SOURCE_TYPES:
        raise ShareCountAcceptanceError(
            "search-result snippets cannot become share-count authority"
        )
    tier = str(claim.source_tier or "").strip()
    if tier in FORBIDDEN_SOURCE_TIERS:
        raise ShareCountAcceptanceError(
            "Tier 3/4 cannot become ShareCountSnapshot authority"
        )
    if tier not in ADMISSIBLE_SOURCE_TIERS:
        raise ShareCountAcceptanceError(
            f"source_tier {tier!r} cannot become share-count authority"
        )
    excerpt = str(claim.evidence_reference or "").strip().lower()
    if not excerpt:
        raise ShareCountAcceptanceError("evidence_reference is required")
    if not any(token in excerpt for token in _OUTSTANDING_TOKENS):
        raise ShareCountAcceptanceError(
            "evidence_reference does not explicitly support outstanding shares"
        )
    symbol = str(claim.symbol or "").strip().upper()
    if not symbol or "." in symbol:
        raise ShareCountAcceptanceError(
            "share-count identity rejected: symbol must be canonical"
        )
    if not str(claim.exchange or "").strip() and not str(claim.isin or "").strip():
        raise ShareCountAcceptanceError(
            "share-count identity rejected: exchange or ISIN is required"
        )
    _require_positive_shares(claim.shares)


def _require_positive_shares(raw: Decimal | float | int | str) -> Decimal:
    if isinstance(raw, bool):
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


def _assert_claim_identity(
    claim: ShareCountEvidenceClaim,
    *,
    symbol: str,
    exchange: str | None,
    isin: str | None,
) -> None:
    want = str(symbol or "").strip().upper()
    got = str(claim.symbol or "").strip().upper()
    if "." in want:
        raise ShareCountAcceptanceError(
            "share-count identity rejected: symbol must be canonical"
        )
    if not want or want != got:
        raise ShareCountAcceptanceError(
            f"share-count identity mismatch: requested {want or 'unknown'}, "
            f"got {got or 'unknown'}"
        )
    want_ex = str(exchange or "").strip().upper()
    got_ex = str(claim.exchange or "").strip().upper()
    if want_ex and got_ex and want_ex != got_ex:
        raise ShareCountAcceptanceError(
            f"share-count exchange mismatch: requested {want_ex}, got {got_ex}"
        )
    want_isin = str(isin or "").strip().upper()
    got_isin = str(claim.isin or "").strip().upper()
    if want_isin and got_isin and want_isin != got_isin:
        raise ShareCountAcceptanceError(
            f"share-count ISIN mismatch: requested {want_isin}, got {got_isin}"
        )


def _resolve_unconflicted(
    claims: Sequence[ShareCountEvidenceClaim],
) -> ShareCountEvidenceClaim:
    keys: set[tuple[Decimal, date]] = set()
    for claim in claims:
        shares = _require_positive_shares(claim.shares)
        keys.add((shares, claim.as_of))
    if len(keys) > 1:
        raise ShareCountAcceptanceError(
            "unresolved current-outstanding conflict; no silent choice"
        )
    preferred = [
        claim
        for claim in claims
        if str(claim.source_tier).strip() == "TIER_1_PRIMARY"
    ]
    return preferred[0] if preferred else claims[0]


def _snapshot_from_claim(claim: ShareCountEvidenceClaim) -> ShareCountSnapshot:
    if not isinstance(claim.as_of, date) or isinstance(claim.as_of, datetime):
        raise ShareCountAcceptanceError(
            "as_of is required and must be a date, not retrieved_at"
        )
    as_of_dt = datetime.combine(claim.as_of, time.min, tzinfo=UTC)
    retrieved = claim.retrieved_at.astimezone(UTC)
    age_days = (retrieved.date() - claim.as_of).days
    metadata = {
        "acceptance": "explicit_dsp_share_count_evidence",
        "source_tier": str(claim.source_tier),
        "source_url": str(claim.source_url).strip(),
        "evidence_reference": str(claim.evidence_reference).strip(),
        "fact_id": str(claim.fact_id).strip(),
        "as_of_date": claim.as_of.isoformat(),
        "as_of_age_days": str(age_days),
    }
    if claim.publication_date is not None:
        metadata["publication_date"] = claim.publication_date.isoformat()
    provenance = ShareCountProvenance(
        provider_id=ACCEPTANCE_PROVIDER_ID,
        provider_name=ACCEPTANCE_PROVIDER_NAME,
        source_type=str(claim.source_type).strip(),
        retrieved_at=claim.retrieved_at,
        as_of=as_of_dt,
        request_id=str(claim.fact_id).strip() or None,
        cache_hit=False,
        auth_mode="evidence_acceptance",
        endpoint=str(claim.source_url).strip(),
        metadata=metadata,
    )
    return ShareCountSnapshot(
        symbol=str(claim.symbol).strip().upper(),
        exchange=(str(claim.exchange).strip().upper() if claim.exchange else None),
        isin=(str(claim.isin).strip().upper() if claim.isin else None),
        shares=ShareCountField.of(claim.shares),
        basis=ShareCountBasis.CURRENT_OUTSTANDING,
        unit=ShareCountUnit.SHARES,
        as_of=as_of_dt,
        provenance=provenance,
    )
