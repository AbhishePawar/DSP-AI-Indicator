"""Conservative eligibility gate for researched fundamental evidence.

This module does not authenticate a provider or authorize investment
recommendations. It only identifies evidence eligible for further
financial-input validation.
"""

from __future__ import annotations

import math

from dsp_platform.research_retrieval.models import (
    EvidenceFreshness,
    EvidenceStatus,
    ResearchEvidenceRecord,
    SourceTier,
)


def financial_evidence_rejection_reason(
    record: ResearchEvidenceRecord,
    *,
    ticker: str,
    metric_name: str,
    period: str,
    units: str,
) -> str | None:

    def normalize(value):
        return str(value or "").strip().casefold()

    if not all(normalize(v) for v in (
        ticker, metric_name, period, units
    )):
        return "missing_expected_identity"

    if record.status is not EvidenceStatus.VERIFIED:
        return "evidence_not_verified"

    if record.provenance.source_tier is not SourceTier.PRIMARY:
        return "primary_source_required"

    if record.freshness is not EvidenceFreshness.CURRENT:
        return "freshness_not_verified"

    if normalize(record.ticker) != normalize(ticker):
        return "ticker_mismatch"

    if normalize(record.metric_name) != normalize(metric_name):
        return "metric_mismatch"

    if normalize(record.provenance.effective_period) != normalize(period):
        return "period_mismatch"

    if normalize(record.units) != normalize(units):
        return "units_mismatch"

    if record.metric_value is None:
        return "missing_value"

    if isinstance(record.metric_value, bool):
        return "invalid_value"

    try:
        finite = math.isfinite(record.metric_value)
    except (TypeError, ValueError, OverflowError):
        finite = False

    if not finite:
        return "non_finite_value"

    if record.conflicts_with:
        return "conflicting_evidence"

    if record.rejection_reason:
        return "rejected_evidence"

    if not record.provenance.canonical_url:
        return "missing_source_url"

    if not record.provenance.content_hash:
        return "missing_document_hash"

    if not record.provenance.published_at:
        return "missing_publication_date"

    if not record.raw_excerpt.strip():
        return "missing_grounded_excerpt"

    return None
