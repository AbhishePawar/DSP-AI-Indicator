"""Validate authenticated transcript bundles — reject invalid / fabricated envelopes."""

from __future__ import annotations

from data_engine.exceptions import InvalidProviderDataError
from data_engine.transcripts.models import AuthenticatedTranscripts, EarningsCallTranscript

__all__ = ["validate_authenticated_transcripts"]

_DISALLOWED_SOURCE = frozenset(
    {"", "example", "dummy", "placeholder", "fabricated", "estimated"}
)


def _validate_transcript(transcript: EarningsCallTranscript, index: int) -> None:
    prefix = f"transcripts[{index}]"
    if not transcript.transcript_id or not str(transcript.transcript_id).strip():
        raise InvalidProviderDataError(f"{prefix} missing transcript_id")
    if not transcript.title or not str(transcript.title).strip():
        raise InvalidProviderDataError(f"{prefix} missing title")
    if not transcript.url and not transcript.content:
        raise InvalidProviderDataError(f"{prefix} must have at least a url or content")


def validate_authenticated_transcripts(bundle: AuthenticatedTranscripts) -> None:
    """Reject structurally invalid transcript bundles. Never invent replacements."""
    if not bundle.identity.symbol or not str(bundle.identity.symbol).strip():
        raise InvalidProviderDataError("transcripts bundle missing identity.symbol")
    if not bundle.provenance.provider_id.strip():
        raise InvalidProviderDataError("transcripts bundle missing provider_id provenance")
    if not bundle.provenance.provider_name.strip():
        raise InvalidProviderDataError("transcripts bundle missing provider_name provenance")
    if bundle.provenance.source_type.strip().lower() in _DISALLOWED_SOURCE:
        raise InvalidProviderDataError(
            f"disallowed provenance source_type={bundle.provenance.source_type!r}"
        )
    if not bundle.transcripts:
        raise InvalidProviderDataError(
            "authenticated transcripts bundle must include at least one transcript "
            "(use None from adapter when unavailable)"
        )
    for i, transcript in enumerate(bundle.transcripts):
        _validate_transcript(transcript, i)
