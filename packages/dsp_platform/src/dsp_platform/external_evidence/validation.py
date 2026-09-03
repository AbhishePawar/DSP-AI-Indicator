"""DSP-owned structural validation for external research evidence.

This module verifies shape, identity binding, temporal fields, and the
calculation-permission boundary. It does not verify semantic truth, scrape
the web, or ingest numbers into DSP engines.
"""

from __future__ import annotations

import math
from datetime import UTC, date, datetime
from urllib.parse import urlparse

from dsp_platform.external_evidence.models import (
    CANONICAL_CALCULATION_FACT_IDS,
    CURRENT_OUTSTANDING_FACT_IDS,
    PRIVATE_EVIDENCE_FIELD_NAMES,
    SEARCH_SNIPPET_SOURCE_TYPES,
    WEIGHTED_AVERAGE_SHARES_FACT_IDS,
    EvidenceKind,
    EvidenceQuality,
    EvidenceValidationStatus,
    ExternalEvidenceIdentity,
    ExternalEvidenceRecord,
    ExternalEvidenceValidationError,
    QualitativeEvidenceTopic,
    SourceTier,
    SourceType,
)

__all__ = [
    "assert_identities_compatible",
    "is_search_snippet_source",
    "normalize_identity_token",
    "validate_external_evidence_identity",
    "validate_external_evidence_record",
]


def normalize_identity_token(value: str | None) -> str:
    return str(value or "").strip().upper()


def is_search_snippet_source(source_type: SourceType | str) -> bool:
    raw = (
        source_type.value
        if isinstance(source_type, SourceType)
        else str(source_type)
    )
    return raw.strip().lower() in SEARCH_SNIPPET_SOURCE_TYPES


def validate_external_evidence_identity(
    identity: ExternalEvidenceIdentity,
) -> None:
    """Reject unbound or non-canonical company identity."""
    _validate_identity(identity)


def validate_external_evidence_record(record: ExternalEvidenceRecord) -> None:
    """Reject structurally invalid records. Does not verify truth."""
    if not isinstance(record, ExternalEvidenceRecord):
        raise ExternalEvidenceValidationError(
            f"expected ExternalEvidenceRecord, got {type(record).__name__}"
        )
    _validate_fact_id(record.fact_id)
    validate_external_evidence_identity(record.identity)
    _validate_enums(record)
    _validate_source_url(record.source_url)
    _validate_retrieved_at(record.retrieved_at)
    _validate_temporal_fields(record)
    _validate_reference(record.evidence_reference)
    _validate_kind_and_value(record)
    _validate_calculation_permission(record)
    _validate_validated_status_boundary(record)
    _reject_private_fields(record.to_dict())


def assert_identities_compatible(
    subject: ExternalEvidenceIdentity,
    record_identity: ExternalEvidenceIdentity,
) -> None:
    """Exact-match populated identity fields. Never fuzzy-match names."""
    _validate_identity(subject)
    _validate_identity(record_identity)
    subject_symbol = normalize_identity_token(subject.symbol)
    record_symbol = normalize_identity_token(record_identity.symbol)
    if subject_symbol != record_symbol:
        raise ExternalEvidenceValidationError(
            "identity mismatch: "
            f"subject symbol {subject_symbol!r} != "
            f"evidence symbol {record_symbol!r}"
        )
    subject_exchange = normalize_identity_token(subject.exchange) or None
    record_exchange = normalize_identity_token(record_identity.exchange) or None
    if subject_exchange and record_exchange and subject_exchange != record_exchange:
        raise ExternalEvidenceValidationError(
            "identity mismatch: exchange disagreement "
            f"({subject_exchange!r} vs {record_exchange!r}); "
            "NSE/BSE are not converted"
        )
    subject_isin = normalize_identity_token(subject.isin) or None
    record_isin = normalize_identity_token(record_identity.isin) or None
    if subject_isin and record_isin and subject_isin != record_isin:
        raise ExternalEvidenceValidationError(
            "identity mismatch: ISIN disagreement "
            f"({subject_isin!r} vs {record_isin!r})"
        )


def _validate_fact_id(fact_id: str) -> None:
    if not isinstance(fact_id, str) or not fact_id.strip():
        raise ExternalEvidenceValidationError(
            "fact_id is required and must be non-empty"
        )
    if fact_id != fact_id.strip():
        raise ExternalEvidenceValidationError(
            "fact_id must not have surrounding whitespace"
        )
    if fact_id.strip().lower() in PRIVATE_EVIDENCE_FIELD_NAMES:
        raise ExternalEvidenceValidationError(
            "fact_id must not be a private/secret field name"
        )


def _validate_identity(identity: ExternalEvidenceIdentity) -> None:
    if not isinstance(identity, ExternalEvidenceIdentity):
        raise ExternalEvidenceValidationError("company identity is required")
    symbol = identity.symbol
    if not isinstance(symbol, str) or not symbol.strip():
        raise ExternalEvidenceValidationError(
            "identity rejected: symbol is required "
            "(company name is not sufficient)"
        )
    if symbol != symbol.strip():
        raise ExternalEvidenceValidationError(
            "identity rejected: symbol has surrounding whitespace"
        )
    if "." in symbol:
        raise ExternalEvidenceValidationError(
            "identity rejected: exchange suffixes are not invented or "
            f"accepted on symbol {symbol!r}"
        )
    if symbol != symbol.upper():
        raise ExternalEvidenceValidationError(
            "identity rejected: symbol must be canonical uppercase "
            "without suffixes"
        )
    exchange = identity.exchange
    if exchange is not None:
        if not isinstance(exchange, str) or not exchange.strip():
            raise ExternalEvidenceValidationError(
                "identity rejected: empty exchange"
            )
        if exchange != exchange.strip().upper():
            raise ExternalEvidenceValidationError(
                "identity rejected: exchange must be canonical uppercase"
            )
    isin = identity.isin
    if isin is not None:
        if not isinstance(isin, str) or not isin.strip():
            raise ExternalEvidenceValidationError("identity rejected: empty ISIN")
        compact = isin.strip().upper()
        if compact != isin:
            raise ExternalEvidenceValidationError(
                "identity rejected: ISIN must be canonical uppercase "
                "without whitespace"
            )
        if len(compact) != 12 or not compact.isalnum():
            raise ExternalEvidenceValidationError(
                "identity rejected: ISIN is present but not a "
                "12-character identifier"
            )
    if exchange is None and isin is None:
        raise ExternalEvidenceValidationError(
            "identity rejected: symbol must be bound by exchange or ISIN"
        )
    if identity.company_name is not None and not str(identity.company_name).strip():
        raise ExternalEvidenceValidationError(
            "identity rejected: empty company_name"
        )


def _validate_enums(record: ExternalEvidenceRecord) -> None:
    if not isinstance(record.evidence_kind, EvidenceKind):
        raise ExternalEvidenceValidationError(
            "evidence_kind must be an explicit EvidenceKind"
        )
    if not isinstance(record.source_type, SourceType):
        raise ExternalEvidenceValidationError("source_type is required")
    if not isinstance(record.source_tier, SourceTier):
        raise ExternalEvidenceValidationError("source_tier is required")
    if not isinstance(record.evidence_quality, EvidenceQuality):
        raise ExternalEvidenceValidationError("evidence_quality is required")
    if not isinstance(record.validation_status, EvidenceValidationStatus):
        raise ExternalEvidenceValidationError("validation_status must be explicit")
    if record.topic is not None and not isinstance(
        record.topic, QualitativeEvidenceTopic
    ):
        raise ExternalEvidenceValidationError(
            "topic must be a QualitativeEvidenceTopic"
        )


def _validate_source_url(url: str) -> None:
    if not isinstance(url, str) or not url.strip():
        raise ExternalEvidenceValidationError(
            "source_url is required and must be non-empty"
        )
    if url != url.strip():
        raise ExternalEvidenceValidationError(
            "source_url must not have surrounding whitespace"
        )
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise ExternalEvidenceValidationError(
            "source_url rejected: only http/https URLs are accepted, "
            f"got {url!r}"
        )
    if not parsed.netloc:
        raise ExternalEvidenceValidationError(
            "source_url rejected: missing host"
        )
    if parsed.username or parsed.password:
        raise ExternalEvidenceValidationError(
            "source_url rejected: credentials in URL are not allowed"
        )


def _validate_retrieved_at(retrieved_at: datetime) -> None:
    if not isinstance(retrieved_at, datetime):
        raise ExternalEvidenceValidationError("retrieved_at is required")
    if retrieved_at.tzinfo is None:
        raise ExternalEvidenceValidationError(
            "retrieved_at must be timezone-aware"
        )


def _validate_temporal_fields(record: ExternalEvidenceRecord) -> None:
    if record.publication_date is not None and not isinstance(
        record.publication_date, date
    ):
        raise ExternalEvidenceValidationError(
            "publication_date must be a date when present"
        )
    if record.as_of is not None and not isinstance(record.as_of, date):
        raise ExternalEvidenceValidationError(
            "as_of must be a date when present"
        )
    retrieved_date = record.retrieved_at.astimezone(UTC).date()
    if record.as_of is None and record.evidence_kind is EvidenceKind.NUMERICAL:
        # Missing as_of is allowed for supporting evidence only.
        # retrieved_at is never copied into as_of.
        return
    if (
        record.as_of is not None
        and record.as_of == retrieved_date
        and record.as_of is record.retrieved_at
    ):
        raise ExternalEvidenceValidationError(
            "retrieved_at cannot substitute for as_of"
        )


def _validate_reference(reference: str) -> None:
    if not isinstance(reference, str) or not reference.strip():
        raise ExternalEvidenceValidationError(
            "evidence_reference / excerpt is required"
        )


def _validate_kind_and_value(record: ExternalEvidenceRecord) -> None:
    if record.evidence_kind is EvidenceKind.NUMERICAL:
        if record.numeric_value is None:
            raise ExternalEvidenceValidationError(
                "numerical evidence requires a numeric value"
            )
        if isinstance(record.numeric_value, bool) or not isinstance(
            record.numeric_value, (int, float)
        ):
            raise ExternalEvidenceValidationError(
                "numerical evidence value is not a finite number"
            )
        if not math.isfinite(float(record.numeric_value)):
            raise ExternalEvidenceValidationError(
                "numerical evidence must be finite "
                "(NaN and Infinity are rejected)"
            )
        if not isinstance(record.unit, str) or not record.unit.strip():
            raise ExternalEvidenceValidationError(
                "numerical evidence requires a unit"
            )
        if record.text_value is not None:
            raise ExternalEvidenceValidationError(
                "numerical evidence must not also carry a qualitative text_value"
            )
        if record.topic is not None:
            raise ExternalEvidenceValidationError(
                "numerical evidence must not carry a qualitative topic"
            )
        return
    if record.numeric_value is not None:
        raise ExternalEvidenceValidationError(
            "qualitative evidence must not carry a numeric_value"
        )
    if record.unit is not None:
        raise ExternalEvidenceValidationError(
            "qualitative evidence must not carry a unit"
        )
    if not isinstance(record.text_value, str) or not record.text_value.strip():
        raise ExternalEvidenceValidationError(
            "qualitative evidence requires text_value"
        )
    if record.topic is None:
        raise ExternalEvidenceValidationError(
            "qualitative evidence requires an explicit topic"
        )


def _validate_calculation_permission(record: ExternalEvidenceRecord) -> None:
    if record.may_influence_calculation is not False:
        raise ExternalEvidenceValidationError(
            "may_influence_calculation must be false: external evidence "
            "is not a DSP calculation input at this layer"
        )
    fact_key = record.fact_id.strip().lower()
    claimed = (record.claimed_dsp_field or "").strip().lower() or None
    if (
        fact_key in WEIGHTED_AVERAGE_SHARES_FACT_IDS
        and claimed in CURRENT_OUTSTANDING_FACT_IDS
    ):
        raise ExternalEvidenceValidationError(
            "weighted-average shares cannot be treated as current outstanding"
        )
    if claimed in CANONICAL_CALCULATION_FACT_IDS:
        raise ExternalEvidenceValidationError(
            "external evidence cannot claim a canonical DSP calculation field "
            f"({claimed!r}); approved ports remain authoritative"
        )


def _validate_validated_status_boundary(record: ExternalEvidenceRecord) -> None:
    if record.validation_status is not EvidenceValidationStatus.VALIDATED:
        return
    if record.source_tier is SourceTier.TIER_3_DISCOVERY:
        raise ExternalEvidenceValidationError(
            "Tier 3 discovery cannot become authoritative evidence"
        )
    if is_search_snippet_source(record.source_type):
        raise ExternalEvidenceValidationError(
            "search-result snippets cannot be stored as authoritative "
            "source documents"
        )


def _reject_private_fields(payload: object) -> None:
    found: list[str] = []

    def _walk(value: object) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                name = str(key)
                if name in PRIVATE_EVIDENCE_FIELD_NAMES:
                    found.append(name)
                _walk(item)
        elif isinstance(value, (list, tuple)):
            for item in value:
                _walk(item)

    _walk(payload)
    if found:
        raise ExternalEvidenceValidationError(
            f"evidence objects must not contain secrets or LLM metadata: {found}"
        )
