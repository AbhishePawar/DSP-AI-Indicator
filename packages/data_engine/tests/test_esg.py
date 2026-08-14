"""Tests for the authenticated ESG score connector domain."""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest
from contracts.domain.instrument import Instrument
from contracts.enums import AssetClass

from data_engine import (
    ConnectorField,
    ConnectorProvenance,
    EsgProviderRegistry,
    EsgQuery,
    EsgService,
    FinancialModelingPrepEsgAdapter,
    InMemoryEsgAdapter,
    InvalidProviderDataError,
    NullEsgAdapter,
    ProviderRequestError,
    YahooFinanceEsgAdapter,
    build_default_esg_registry_from_env,
    build_esg_score_from_mapping,
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


class _FakeJsonClient:
    def __init__(self, payload) -> None:
        self._payload = payload

    def get_json(self, url, *, params=None, headers=None):
        return self._payload


class TestNullAndInMemory:
    def test_null_always_unavailable(self) -> None:
        assert NullEsgAdapter().get_esg_score(EsgQuery(instrument=_instrument())) is None

    def test_in_memory_requires_key(self) -> None:
        with pytest.raises(ProviderRequestError):
            InMemoryEsgAdapter().get_esg_score(EsgQuery(instrument=_instrument()))

    def test_in_memory_put_and_get(self) -> None:
        adapter = InMemoryEsgAdapter(api_key="k")
        bundle = build_esg_score_from_mapping(
            symbol="AAPL",
            as_of=date(2023, 12, 31),
            environmental_score=ConnectorField.of(20.0),
            social_score=ConnectorField.of(15.0),
            governance_score=ConnectorField.of(10.0),
            total_score=ConnectorField.of(45.0),
            controversy_level="low",
            provenance=_provenance("memory_esg"),
        )
        adapter.put(bundle)
        result = adapter.get_esg_score(EsgQuery(instrument=_instrument()))
        assert result is not None
        assert result.total_score.to_float() == 45.0


class TestValidation:
    def test_rejects_invalid_controversy_level(self) -> None:
        with pytest.raises(InvalidProviderDataError):
            build_esg_score_from_mapping(
                symbol="AAPL",
                as_of=None,
                environmental_score=ConnectorField.of(20.0),
                social_score=ConnectorField.missing(),
                governance_score=ConnectorField.missing(),
                total_score=ConnectorField.missing(),
                controversy_level="extreme",
                provenance=_provenance(),
            )

    def test_rejects_all_scores_missing(self) -> None:
        with pytest.raises(InvalidProviderDataError):
            build_esg_score_from_mapping(
                symbol="AAPL",
                as_of=None,
                environmental_score=ConnectorField.missing(),
                social_score=ConnectorField.missing(),
                governance_score=ConnectorField.missing(),
                total_score=ConnectorField.missing(),
                controversy_level=None,
                provenance=_provenance(),
            )


class TestYahooFinanceEsgAdapter:
    def test_disabled_raises(self) -> None:
        with pytest.raises(ProviderRequestError):
            YahooFinanceEsgAdapter(enabled=False).get_esg_score(EsgQuery(instrument=_instrument()))

    def test_maps_esg_scores_module(self) -> None:
        payload = {
            "quoteSummary": {
                "result": [
                    {
                        "esgScores": {
                            "environmentScore": {"raw": 5.2},
                            "socialScore": {"raw": 8.1},
                            "governanceScore": {"raw": 6.4},
                            "totalEsg": {"raw": 19.7},
                            "highestControversy": 2,
                        }
                    }
                ]
            }
        }
        adapter = YahooFinanceEsgAdapter(enabled=True, http_client=_FakeJsonClient(payload))
        bundle = adapter.get_esg_score(EsgQuery(instrument=_instrument()))
        assert bundle is not None
        assert bundle.total_score.to_float() == pytest.approx(19.7)
        assert bundle.controversy_level == "moderate"


class TestFinancialModelingPrepEsgAdapter:
    def test_maps_latest_entry(self) -> None:
        payload = [
            {
                "date": "2023-09-30",
                "environmentalScore": 55.0,
                "socialScore": 60.0,
                "governanceScore": 70.0,
                "ESGScore": 61.6,
            }
        ]
        adapter = FinancialModelingPrepEsgAdapter(api_key="k", http_client=_FakeJsonClient(payload))
        bundle = adapter.get_esg_score(EsgQuery(instrument=_instrument()))
        assert bundle is not None
        assert bundle.as_of == date(2023, 9, 30)
        assert bundle.total_score.to_float() == pytest.approx(61.6)

    def test_requires_api_key(self) -> None:
        with pytest.raises(ProviderRequestError):
            FinancialModelingPrepEsgAdapter(api_key="").get_esg_score(EsgQuery(instrument=_instrument()))

    def test_empty_payload_returns_none(self) -> None:
        adapter = FinancialModelingPrepEsgAdapter(api_key="k", http_client=_FakeJsonClient([]))
        assert adapter.get_esg_score(EsgQuery(instrument=_instrument())) is None


class TestRegistryAndEnv:
    def test_registry_ordering(self) -> None:
        registry = EsgProviderRegistry()
        registry.register(NullEsgAdapter(), provider_id="null_esg", priority=1000)
        registry.register(FinancialModelingPrepEsgAdapter(api_key="k"), provider_id="fmp_esg", priority=10)
        assert registry.ordered_ids() == ("fmp_esg", "null_esg")

    def test_default_registry_falls_back_to_null(self, monkeypatch: pytest.MonkeyPatch) -> None:
        for key in ("DSP_ESG_FMP_API_KEY", "DSP_ESG_YAHOO_ENABLED", "DSP_ESG_MEMORY"):
            monkeypatch.delenv(key, raising=False)
        registry = build_default_esg_registry_from_env()
        assert registry.ordered_ids() == ("null_esg",)


class TestEsgService:
    def test_cache_hit(self) -> None:
        adapter = InMemoryEsgAdapter(api_key="k")
        adapter.put(
            build_esg_score_from_mapping(
                symbol="AAPL",
                as_of=None,
                environmental_score=ConnectorField.of(10.0),
                social_score=ConnectorField.missing(),
                governance_score=ConnectorField.missing(),
                total_score=ConnectorField.missing(),
                controversy_level=None,
                provenance=_provenance("memory_esg"),
            )
        )
        service = EsgService(adapter)
        query = EsgQuery(instrument=_instrument())
        service.get_esg_score(query)
        second = service.get_esg_score(query)
        assert second is not None
        assert service.metrics.cache_hits == 1
