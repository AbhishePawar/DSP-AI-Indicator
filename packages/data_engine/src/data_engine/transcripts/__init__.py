"""Authenticated earnings call transcripts (Data Connector Framework)."""

from __future__ import annotations

from data_engine.transcripts.adapters import (
    FinancialModelingPrepTranscriptAdapter,
    InMemoryTranscriptAdapter,
    NullTranscriptAdapter,
    build_default_transcript_registry_from_env,
    build_transcripts_bundle_from_mapping,
)
from data_engine.transcripts.models import AuthenticatedTranscripts, EarningsCallTranscript
from data_engine.transcripts.registry import TranscriptProviderRegistry
from data_engine.transcripts.service import (
    TranscriptProviderPort,
    TranscriptQuery,
    TranscriptService,
    TranscriptServiceMetrics,
)
from data_engine.transcripts.validation import validate_authenticated_transcripts

__all__ = [
    "AuthenticatedTranscripts",
    "EarningsCallTranscript",
    "FinancialModelingPrepTranscriptAdapter",
    "InMemoryTranscriptAdapter",
    "NullTranscriptAdapter",
    "TranscriptProviderPort",
    "TranscriptProviderRegistry",
    "TranscriptQuery",
    "TranscriptService",
    "TranscriptServiceMetrics",
    "build_default_transcript_registry_from_env",
    "build_transcripts_bundle_from_mapping",
    "validate_authenticated_transcripts",
]
