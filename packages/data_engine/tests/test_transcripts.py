"""Tests for the authenticated earnings call transcript connector domain."""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest
from contracts.domain.instrument import Instrument
from contracts.enums import AssetClass

from data_engine import (
    ConnectorProvenance,
    EarningsCallTranscript,
    InMemoryTranscriptAdapter,
    InvalidProviderDataError,
    NullTranscriptAdapter,
    ProviderRequestError,
    TranscriptProviderRegistry,
    TranscriptQuery,
    TranscriptService,
    build_default_transcript_registry_from_env,
    build_transcripts_bundle_from_mapping,
)


def _instrument(symbol: str = "AAPL") -> Instrument:
    return Instrument(symbol=symbol, asset_class=AssetClass.EQUITY, currency="USD")


def _provenance(provider_id: str = "x") -> ConnectorProvenance:
    return ConnectorProvenance(
        provider_id=provider_id,
        provider_name="X",
        source_type="public_endpoint",
        retrieved_at=datetime.now(tz=UTC),
    )


def _transcript(**overrides) -> EarningsCallTranscript:
    defaults = dict(
        transcript_id="t-2023-q3",
        quarter=3,
        year=2023,
        call_date=date(2023, 8, 3),
        title="AAPL Q3 2023 Earnings Call Transcript",
        content="Operator: Welcome to the call...",
    )
    defaults.update(overrides)
    return EarningsCallTranscript(**defaults)


class _FakeJsonClient:
    def __init__(self, payload=None, *, sequence=None) -> None:
        self._payload = payload
        self._sequence = sequence
        self._i = 0

    def get_json(self, url, *, params=None, headers=None):
        if self._sequence is not None:
            result = self._sequence[min(self._i, len(self._sequence) - 1)]
            self._i += 1
            return result
        return self._payload


class TestNullAndInMemory:
    def test_null_always_unavailable(self) -> None:
        assert NullTranscriptAdapter().get_transcripts(TranscriptQuery(instrument=_instrument())) is None

    def test_in_memory_requires_key(self) -> None:
        with pytest.raises(ProviderRequestError):
            InMemoryTranscriptAdapter().get_transcripts(TranscriptQuery(instrument=_instrument()))

    def test_in_memory_put_and_get_with_filters(self) -> None:
        adapter = InMemoryTranscriptAdapter(api_key="k")
        bundle = build_transcripts_bundle_from_mapping(
            symbol="AAPL",
            transcripts=[
                _transcript(transcript_id="t-2023-q2", quarter=2, year=2023),
                _transcript(transcript_id="t-2023-q3", quarter=3, year=2023),
            ],
            provenance=_provenance("memory_transcripts"),
        )
        adapter.put(bundle)
        result = adapter.get_transcripts(TranscriptQuery(instrument=_instrument(), quarter=2, year=2023))
        assert result is not None
        assert len(result.transcripts) == 1
        assert result.transcripts[0].transcript_id == "t-2023-q2"


class TestValidation:
    def test_rejects_missing_title(self) -> None:
        with pytest.raises(InvalidProviderDataError):
            build_transcripts_bundle_from_mapping(
                symbol="AAPL",
                transcripts=[_transcript(title="")],
                provenance=_provenance(),
            )

    def test_rejects_no_url_and_no_content(self) -> None:
        with pytest.raises(InvalidProviderDataError):
            build_transcripts_bundle_from_mapping(
                symbol="AAPL",
                transcripts=[_transcript(content=None, url=None)],
                provenance=_provenance(),
            )

    def test_rejects_empty_transcripts(self) -> None:
        with pytest.raises(InvalidProviderDataError):
            build_transcripts_bundle_from_mapping(symbol="AAPL", transcripts=[], provenance=_provenance())


class TestFinancialModelingPrepTranscriptAdapterAbsent:
    def test_fmp_transcript_adapter_is_not_exported(self) -> None:
        import data_engine

        assert not hasattr(data_engine, "FinancialModelingPrepTranscriptAdapter")


class TestRegistryAndEnv:
    def test_registry_ordering(self) -> None:
        registry = TranscriptProviderRegistry()
        registry.register(NullTranscriptAdapter(), provider_id="null_transcripts", priority=1000)
        registry.register(InMemoryTranscriptAdapter(api_key="k"), provider_id="memory_transcripts", priority=10)
        assert registry.ordered_ids() == ("memory_transcripts", "null_transcripts")
        assert "fmp_transcripts" not in registry.ordered_ids()

    def test_default_registry_falls_back_to_null(self, monkeypatch: pytest.MonkeyPatch) -> None:
        for key in ("DSP_TRANSCRIPT_FMP_API_KEY", "DSP_TRANSCRIPT_MEMORY"):
            monkeypatch.delenv(key, raising=False)
        registry = build_default_transcript_registry_from_env()
        assert registry.ordered_ids() == ("null_transcripts",)


class TestTranscriptService:
    def test_cache_hit(self) -> None:
        adapter = InMemoryTranscriptAdapter(api_key="k")
        adapter.put(
            build_transcripts_bundle_from_mapping(
                symbol="AAPL",
                transcripts=[_transcript()],
                provenance=_provenance("memory_transcripts"),
            )
        )
        service = TranscriptService(adapter)
        query = TranscriptQuery(instrument=_instrument())
        service.get_transcripts(query)
        second = service.get_transcripts(query)
        assert second is not None
        assert service.metrics.cache_hits == 1
