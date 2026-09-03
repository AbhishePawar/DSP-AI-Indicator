"""Explicit DSP mapping from validated external evidence to ShareCountSnapshot.

This is not an AI interpreter, not a ShareCountPort, and not a valuation
engine. ValidatedExternalEvidencePackage remains non-canonical until this
function is called explicitly.

Production compose / analyse / Upstox paths do not call this module.
"""

from __future__ import annotations

from collections.abc import Sequence

from data_engine.share_count import (
    FORBIDDEN_SOURCE_TIERS,
    ShareCountAcceptanceError,
    ShareCountEvidenceClaim,
    ShareCountSnapshot,
    accept_current_outstanding_claims,
)
from dsp_platform.external_evidence.models import (
    CURRENT_OUTSTANDING_FACT_IDS,
    WEIGHTED_AVERAGE_SHARES_FACT_IDS,
    EvidenceKind,
    EvidenceValidationStatus,
    ExternalEvidenceRecord,
    ValidatedExternalEvidencePackage,
)

__all__ = [
    "accept_share_count_from_validated_evidence",
]

_WAS_REASON = "weighted-average shares cannot become current outstanding"
_FORBIDDEN_FACT_REASONS = {
    **dict.fromkeys(WEIGHTED_AVERAGE_SHARES_FACT_IDS, _WAS_REASON),
    "equity_capital": "equity capital cannot become current outstanding",
    "paid_up_capital": "equity capital cannot become current outstanding",
    "authorized_shares": "authorized shares cannot become current outstanding",
    "issued_shares": "issued shares cannot become current outstanding",
    "market_cap": "market cap / price cannot become current outstanding",
    "market_capitalization": (
        "market cap / price cannot become current outstanding"
    ),
    "volume": "volume cannot become current outstanding",
    "open_interest": "open interest cannot become current outstanding",
    "oi": "open interest cannot become current outstanding",
    "eps": "EPS cannot become current outstanding",
    "eps_basic": "EPS cannot become current outstanding",
    "eps_diluted": "EPS cannot become current outstanding",
    "net_income": "net-income/EPS-derived shares cannot become current outstanding",
    "price": "market cap / price cannot become current outstanding",
    "current_price": "market cap / price cannot become current outstanding",
}


def accept_share_count_from_validated_evidence(
    package: object,
    *,
    symbol: str,
    exchange: str | None = None,
    isin: str | None = None,
) -> ShareCountSnapshot:
    """Convert validated CURRENT_OUTSTANDING evidence into a snapshot.

    AI narrative, candidate evidence, and rejected evidence cannot enter.
    """
    if not isinstance(package, ValidatedExternalEvidencePackage):
        raise ShareCountAcceptanceError(
            "AI narrative and unvalidated output cannot create ShareCountSnapshot"
        )
    if package.canonical_calculation_inputs():
        raise ShareCountAcceptanceError(
            "external evidence remains noncanonical until explicit DSP acceptance"
        )
    _assert_subject_identity(
        package, symbol=symbol, exchange=exchange, isin=isin
    )
    claims, forbidden_reason, blocked_tier = _claims_from_package(
        package.records,
        symbol=symbol,
        exchange=exchange,
        isin=isin,
    )
    if not claims:
        if forbidden_reason is not None:
            raise ShareCountAcceptanceError(forbidden_reason)
        if blocked_tier:
            raise ShareCountAcceptanceError(
                "Tier 3/4 cannot become ShareCountSnapshot authority"
            )
        raise ShareCountAcceptanceError(
            "no admissible current-outstanding evidence"
        )
    return accept_current_outstanding_claims(
        claims,
        symbol=symbol,
        exchange=exchange,
        isin=isin,
    )


def _assert_subject_identity(
    package: ValidatedExternalEvidencePackage,
    *,
    symbol: str,
    exchange: str | None,
    isin: str | None,
) -> None:
    want = str(symbol or "").strip().upper()
    got = str(package.subject.symbol or "").strip().upper()
    if "." in want or "." in got:
        raise ShareCountAcceptanceError(
            "share-count identity rejected: symbol must be canonical"
        )
    if not want or want != got:
        raise ShareCountAcceptanceError(
            f"share-count identity mismatch: requested {want or 'unknown'}, "
            f"got {got or 'unknown'}"
        )
    want_ex = str(exchange or "").strip().upper()
    got_ex = str(package.subject.exchange or "").strip().upper()
    if want_ex and got_ex and want_ex != got_ex:
        raise ShareCountAcceptanceError(
            f"share-count exchange mismatch: requested {want_ex}, got {got_ex}"
        )
    want_isin = str(isin or "").strip().upper()
    got_isin = str(package.subject.isin or "").strip().upper()
    if want_isin and got_isin and want_isin != got_isin:
        raise ShareCountAcceptanceError(
            f"share-count ISIN mismatch: requested {want_isin}, got {got_isin}"
        )


def _claims_from_package(
    records: Sequence[ExternalEvidenceRecord],
    *,
    symbol: str,
    exchange: str | None,
    isin: str | None,
) -> tuple[list[ShareCountEvidenceClaim], str | None, bool]:
    claims: list[ShareCountEvidenceClaim] = []
    forbidden_reason: str | None = None
    blocked_tier = False
    for record in records:
        fact_id = str(getattr(record, "fact_id", "") or "").strip().lower()
        if fact_id in _FORBIDDEN_FACT_REASONS:
            forbidden_reason = forbidden_reason or _FORBIDDEN_FACT_REASONS[fact_id]
            continue
        if fact_id not in CURRENT_OUTSTANDING_FACT_IDS:
            continue
        status = getattr(record, "validation_status", None)
        if status is not EvidenceValidationStatus.VALIDATED:
            raise ShareCountAcceptanceError(
                "share-count evidence status must be validated, "
                f"got {getattr(status, 'value', status)!r}"
            )
        kind = getattr(record, "evidence_kind", None)
        if kind is not EvidenceKind.NUMERICAL:
            raise ShareCountAcceptanceError(
                "current-outstanding evidence must be a numerical share count"
            )
        identity = record.identity
        _assert_record_identity(
            identity, symbol=symbol, exchange=exchange, isin=isin
        )
        tier = str(getattr(record.source_tier, "value", record.source_tier))
        if tier in FORBIDDEN_SOURCE_TIERS:
            blocked_tier = True
            continue
        if record.as_of is None:
            raise ShareCountAcceptanceError(
                "as_of is required and must be a date, not retrieved_at"
            )
        if record.numeric_value is None:
            raise ShareCountAcceptanceError("share count must be numeric")
        claims.append(
            ShareCountEvidenceClaim(
                symbol=identity.symbol,
                exchange=identity.exchange,
                isin=identity.isin,
                shares=record.numeric_value,
                unit=str(record.unit or ""),
                basis="current_outstanding",
                as_of=record.as_of,
                publication_date=record.publication_date,
                source_url=record.source_url,
                source_type=str(record.source_type.value),
                source_tier=tier,
                evidence_reference=record.evidence_reference,
                retrieved_at=record.retrieved_at,
                fact_id=record.fact_id,
                validation_status=str(record.validation_status.value),
            )
        )
    return claims, forbidden_reason, blocked_tier


def _assert_record_identity(
    identity: object,
    *,
    symbol: str,
    exchange: str | None,
    isin: str | None,
) -> None:
    want = str(symbol or "").strip().upper()
    got = str(getattr(identity, "symbol", "") or "").strip().upper()
    if "." in got or not want or want != got:
        raise ShareCountAcceptanceError(
            f"share-count identity mismatch: requested {want or 'unknown'}, "
            f"got {got or 'unknown'}"
        )
    want_ex = str(exchange or "").strip().upper()
    got_ex = str(getattr(identity, "exchange", "") or "").strip().upper()
    if want_ex and got_ex and want_ex != got_ex:
        raise ShareCountAcceptanceError(
            f"share-count exchange mismatch: requested {want_ex}, got {got_ex}"
        )
    want_isin = str(isin or "").strip().upper()
    got_isin = str(getattr(identity, "isin", "") or "").strip().upper()
    if want_isin and got_isin and want_isin != got_isin:
        raise ShareCountAcceptanceError(
            f"share-count ISIN mismatch: requested {want_isin}, got {got_isin}"
        )
