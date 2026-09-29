"""Authenticated earnings call transcript adapters.

Every vendor-specific field name lives in this file. Adapters:

- :class:`NullTranscriptAdapter` / :class:`InMemoryTranscriptAdapter` —
  safe defaults.
  date index (``/v4/earning_call_transcript``) plus per-quarter
  content fetch (``/v3/earning_call_transcript/{symbol}``).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime
from threading import Lock
from typing import Mapping

from contracts.domain.instrument import Instrument
from data_engine.connector_framework.http import JsonHttpClient, UrllibJsonHttpClient
from data_engine.connector_framework.models import (
    ConnectorCompanyIdentity,
    ConnectorProvenance,
    ProviderHealth,
    utc_now,
)
from data_engine.connector_framework.registry import PriorityProviderRegistry
from data_engine.exceptions import ProviderRequestError
from data_engine.transcripts.models import AuthenticatedTranscripts, EarningsCallTranscript
from data_engine.transcripts.service import TranscriptProviderPort, TranscriptQuery
from data_engine.transcripts.validation import validate_authenticated_transcripts

__all__ = [
    "InMemoryTranscriptAdapter",
    "NullTranscriptAdapter",
    "build_default_transcript_registry_from_env",
    "build_transcripts_bundle_from_mapping",
]


def build_transcripts_bundle_from_mapping(
    *, symbol: str, transcripts: list[EarningsCallTranscript], provenance: ConnectorProvenance
) -> AuthenticatedTranscripts:
    bundle = AuthenticatedTranscripts(
        identity=ConnectorCompanyIdentity(symbol=symbol.strip().upper()),
        transcripts=tuple(transcripts),
        provenance=provenance,
    )
    validate_authenticated_transcripts(bundle)
    return bundle


@dataclass
class NullTranscriptAdapter(TranscriptProviderPort):
    _provider_id: str = "null_transcripts"

    @property
    def provider_id(self) -> str:
        return self._provider_id

    def get_transcripts(self, query: TranscriptQuery) -> AuthenticatedTranscripts | None:
        return None

    def health(self) -> ProviderHealth:
        return ProviderHealth(
            provider_id=self.provider_id,
            healthy=True,
            authenticated=False,
            detail="null provider — no transcript feed configured",
        )


@dataclass
class InMemoryTranscriptAdapter(TranscriptProviderPort):
    api_key: str | None = None
    _provider_id: str = "memory_transcripts"
    _bundles: dict[str, AuthenticatedTranscripts] = field(default_factory=dict)
    _lock: Lock = field(default_factory=Lock, repr=False)

    @property
    def provider_id(self) -> str:
        return self._provider_id

    def put(self, bundle: AuthenticatedTranscripts) -> None:
        validate_authenticated_transcripts(bundle)
        with self._lock:
            self._bundles[bundle.identity.symbol.upper()] = bundle

    def get_transcripts(self, query: TranscriptQuery) -> AuthenticatedTranscripts | None:
        if not self.api_key:
            raise ProviderRequestError("memory transcript adapter requires api_key (authentication)")
        with self._lock:
            bundle = self._bundles.get(query.instrument.symbol.strip().upper())
        if bundle is None:
            return None
        transcripts = list(bundle.transcripts)
        if query.year is not None:
            transcripts = [t for t in transcripts if t.year == query.year]
        if query.quarter is not None:
            transcripts = [t for t in transcripts if t.quarter == query.quarter]
        transcripts.sort(key=lambda t: (t.year or 0, t.quarter or 0), reverse=True)
        transcripts = transcripts[: max(1, query.limit)]
        if not transcripts:
            return None
        return AuthenticatedTranscripts(
            identity=bundle.identity, transcripts=tuple(transcripts), provenance=bundle.provenance
        )

    def health(self) -> ProviderHealth:
        return ProviderHealth(
            provider_id=self.provider_id,
            healthy=True,
            authenticated=bool(self.api_key),
            detail="seeded in-memory authenticated transcripts" if self.api_key else "missing api_key",
        )


def build_default_transcript_registry_from_env() -> PriorityProviderRegistry[TranscriptProviderPort]:
    from data_engine.connector_framework.production_profile import (
        finalize_provider_registry,
        memory_adapter_allowed,
    )

    registry: PriorityProviderRegistry[TranscriptProviderPort] = PriorityProviderRegistry()

    if memory_adapter_allowed("DSP_TRANSCRIPT_MEMORY", connector="transcripts"):
        registry.register(
            InMemoryTranscriptAdapter(api_key="dev-memory-key"),
            provider_id="memory_transcripts",
            priority=90,
        )

    return finalize_provider_registry(
        registry,
        connector="transcripts",
        null_factory=NullTranscriptAdapter,
        null_provider_id="null_transcripts",
    )
