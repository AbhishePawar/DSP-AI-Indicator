"""Authenticated earnings call transcript adapters.

Every vendor-specific field name lives in this file. Adapters:

- :class:`NullTranscriptAdapter` / :class:`InMemoryTranscriptAdapter` —
  safe defaults.
- :class:`FinancialModelingPrepTranscriptAdapter` — FMP's transcript
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
    "FinancialModelingPrepTranscriptAdapter",
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


@dataclass
class FinancialModelingPrepTranscriptAdapter(TranscriptProviderPort):
    """FMP earnings call transcript adapter.

    Lists available (year, quarter) pairs via the transcript-dates
    index, then fetches transcript content for the requested — or most
    recent — calls, bounded by ``query.limit``.
    """

    api_key: str
    dates_url: str = "https://financialmodelingprep.com/api/v4/earning_call_transcript"
    content_url: str = "https://financialmodelingprep.com/api/v3/earning_call_transcript"
    timeout_seconds: float = 20.0
    http_client: JsonHttpClient | None = None
    _provider_id: str = "fmp_transcripts"

    @property
    def provider_id(self) -> str:
        return self._provider_id

    def _client(self) -> JsonHttpClient:
        return self.http_client or UrllibJsonHttpClient(timeout_seconds=self.timeout_seconds)

    def get_transcripts(self, query: TranscriptQuery) -> AuthenticatedTranscripts | None:
        if not self.api_key.strip():
            raise ProviderRequestError("financial modeling prep transcript adapter requires api_key")
        symbol = query.instrument.symbol.strip().upper()

        if query.year is not None and query.quarter is not None:
            pairs: list[tuple[int, int]] = [(query.year, query.quarter)]
        else:
            index_payload = self._client().get_json(self.dates_url, params={"symbol": symbol, "apikey": self.api_key})
            if not isinstance(index_payload, list) or not index_payload:
                return None
            pairs = []
            for item in index_payload:
                if not isinstance(item, Mapping):
                    continue
                quarter = item.get("quarter")
                year = item.get("year")
                if quarter is None or year is None:
                    continue
                try:
                    pairs.append((int(year), int(quarter)))
                except (TypeError, ValueError):
                    continue
            pairs.sort(reverse=True)
            pairs = pairs[: max(1, query.limit)]

        if not pairs:
            return None

        transcripts: list[EarningsCallTranscript] = []
        for year, quarter in pairs:
            content_payload = self._client().get_json(
                f"{self.content_url}/{symbol}",
                params={"quarter": str(quarter), "year": str(year), "apikey": self.api_key},
            )
            if not isinstance(content_payload, list) or not content_payload:
                continue
            entry = content_payload[0]
            if not isinstance(entry, Mapping):
                continue
            content = str(entry.get("content") or "").strip() or None
            date_raw = str(entry.get("date") or "").strip()
            call_date = None
            if date_raw:
                try:
                    call_date = datetime.fromisoformat(date_raw.replace(" ", "T")).date()
                except ValueError:
                    call_date = None
            if content is None:
                continue
            transcripts.append(
                EarningsCallTranscript(
                    transcript_id=f"fmp-{symbol}-{year}-Q{quarter}",
                    quarter=quarter,
                    year=year,
                    call_date=call_date,
                    title=f"{symbol} Q{quarter} {year} Earnings Call Transcript",
                    content=content,
                    source="Financial Modeling Prep",
                )
            )
        if not transcripts:
            return None
        provenance = ConnectorProvenance(
            provider_id=self.provider_id,
            provider_name="Financial Modeling Prep",
            source_type="licensed_vendor",
            retrieved_at=utc_now(),
            auth_mode="api_key",
            metadata={"content_url": self.content_url},
        )
        return build_transcripts_bundle_from_mapping(symbol=symbol, transcripts=transcripts, provenance=provenance)

    def health(self) -> ProviderHealth:
        ok = bool(self.api_key.strip())
        return ProviderHealth(
            provider_id=self.provider_id, healthy=ok, authenticated=ok,
            detail="configured" if ok else "missing api_key",
        )


def build_default_transcript_registry_from_env() -> PriorityProviderRegistry[TranscriptProviderPort]:
    registry: PriorityProviderRegistry[TranscriptProviderPort] = PriorityProviderRegistry()

    fmp_key = os.environ.get("DSP_TRANSCRIPT_FMP_API_KEY", "").strip()
    if fmp_key:
        registry.register(
            FinancialModelingPrepTranscriptAdapter(api_key=fmp_key),
            provider_id="fmp_transcripts",
            priority=10,
        )

    if os.environ.get("DSP_TRANSCRIPT_MEMORY", "").lower() in {"1", "true", "yes"}:
        registry.register(
            InMemoryTranscriptAdapter(api_key="dev-memory-key"),
            provider_id="memory_transcripts",
            priority=90,
        )

    registry.register(NullTranscriptAdapter(), provider_id="null_transcripts", priority=1000)
    return registry
