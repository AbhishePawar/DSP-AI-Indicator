"""Validate authenticated filings bundles — reject invalid / fabricated envelopes."""

from __future__ import annotations

from data_engine.exceptions import InvalidProviderDataError
from data_engine.filings.models import FILING_TYPES, AuthenticatedFilings, Filing

__all__ = ["validate_authenticated_filings"]

_DISALLOWED_SOURCE = frozenset(
    {"", "example", "dummy", "placeholder", "fabricated", "estimated"}
)


def _validate_filing(filing: Filing, index: int) -> None:
    prefix = f"filings[{index}]"
    if not filing.filing_id or not str(filing.filing_id).strip():
        raise InvalidProviderDataError(f"{prefix} missing filing_id")
    if filing.filing_type not in FILING_TYPES:
        raise InvalidProviderDataError(
            f"{prefix}.filing_type must be one of {sorted(FILING_TYPES)}, "
            f"got {filing.filing_type!r}"
        )
    if not filing.title or not str(filing.title).strip():
        raise InvalidProviderDataError(f"{prefix} missing title")
    if not filing.url or not str(filing.url).strip():
        raise InvalidProviderDataError(f"{prefix} missing url")


def validate_authenticated_filings(bundle: AuthenticatedFilings) -> None:
    """Reject structurally invalid filings bundles. Never invent replacements."""
    if not bundle.identity.symbol or not str(bundle.identity.symbol).strip():
        raise InvalidProviderDataError("filings bundle missing identity.symbol")
    if not bundle.provenance.provider_id.strip():
        raise InvalidProviderDataError("filings bundle missing provider_id provenance")
    if not bundle.provenance.provider_name.strip():
        raise InvalidProviderDataError("filings bundle missing provider_name provenance")
    if bundle.provenance.source_type.strip().lower() in _DISALLOWED_SOURCE:
        raise InvalidProviderDataError(
            f"disallowed provenance source_type={bundle.provenance.source_type!r}"
        )
    if not bundle.filings:
        raise InvalidProviderDataError(
            "authenticated filings bundle must include at least one filing "
            "(use None from adapter when unavailable)"
        )
    for i, filing in enumerate(bundle.filings):
        _validate_filing(filing, i)
