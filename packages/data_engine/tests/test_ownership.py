"""Tests for the authenticated ownership/shareholding connector domain."""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest
from contracts.domain.instrument import Instrument
from contracts.enums import AssetClass

from data_engine import (
    BseOwnershipAdapter,
    ConnectorField,
    ConnectorProvenance,
    FinancialModelingPrepOwnershipAdapter,
    InMemoryOwnershipAdapter,
    InvalidProviderDataError,
    NseOwnershipAdapter,
    NullOwnershipAdapter,
    OwnershipProviderRegistry,
    OwnershipQuery,
    OwnershipService,
    OwnershipStake,
    ProviderRequestError,
    ScreenerOwnershipAdapter,
    YahooFinanceOwnershipAdapter,
    build_default_ownership_registry_from_env,
    build_ownership_bundle_from_mapping,
)


def _instrument(symbol: str = "AAPL") -> Instrument:
    return Instrument(symbol=symbol, asset_class=AssetClass.EQUITY, currency="USD")


class _FakeJsonClient:
    def __init__(self, payload) -> None:
        self._payload = payload

    def get_json(self, url, *, params=None, headers=None):
        return self._payload


class TestNullAndInMemory:
    def test_null_always_unavailable(self) -> None:
        assert NullOwnershipAdapter().get_ownership(OwnershipQuery(instrument=_instrument())) is None

    def test_in_memory_requires_key(self) -> None:
        with pytest.raises(ProviderRequestError):
            InMemoryOwnershipAdapter().get_ownership(OwnershipQuery(instrument=_instrument()))

    def test_in_memory_put_and_get(self) -> None:
        adapter = InMemoryOwnershipAdapter(api_key="k")
        bundle = build_ownership_bundle_from_mapping(
            symbol="RELIANCE",
            as_of=date(2023, 12, 31),
            stakes=[
                OwnershipStake(
                    holder_type="promoter",
                    holder_name="Promoters",
                    percent_held=ConnectorField.of(50.3),
                    shares_held=ConnectorField.missing(),
                )
            ],
            provenance=ConnectorProvenance(
                provider_id="memory_ownership",
                provider_name="Memory",
                source_type="public_endpoint",
                retrieved_at=datetime.now(tz=UTC),
            ),
            promoter_holding_percent=ConnectorField.of(50.3),
        )
        adapter.put(bundle)
        result = adapter.get_ownership(OwnershipQuery(instrument=_instrument("RELIANCE")))
        assert result is not None
        assert result.promoter_holding_percent.to_float() == 50.3


class TestValidation:
    def test_rejects_out_of_range_percent(self) -> None:
        with pytest.raises(InvalidProviderDataError):
            build_ownership_bundle_from_mapping(
                symbol="AAPL",
                as_of=None,
                stakes=[
                    OwnershipStake(
                        holder_type="promoter",
                        holder_name=None,
                        percent_held=ConnectorField.of(150),
                        shares_held=ConnectorField.missing(),
                    )
                ],
                provenance=ConnectorProvenance(
                    provider_id="x",
                    provider_name="X",
                    source_type="public_endpoint",
                    retrieved_at=datetime.now(tz=UTC),
                ),
            )

    def test_rejects_unknown_holder_type(self) -> None:
        with pytest.raises(InvalidProviderDataError):
            build_ownership_bundle_from_mapping(
                symbol="AAPL",
                as_of=None,
                stakes=[
                    OwnershipStake(
                        holder_type="alien",
                        holder_name=None,
                        percent_held=ConnectorField.missing(),
                        shares_held=ConnectorField.missing(),
                    )
                ],
                provenance=ConnectorProvenance(
                    provider_id="x",
                    provider_name="X",
                    source_type="public_endpoint",
                    retrieved_at=datetime.now(tz=UTC),
                ),
            )


class TestYahooFinanceOwnershipAdapter:
    def test_disabled_raises(self) -> None:
        with pytest.raises(ProviderRequestError):
            YahooFinanceOwnershipAdapter(enabled=False).get_ownership(OwnershipQuery(instrument=_instrument()))

    def test_maps_major_holders_breakdown(self) -> None:
        payload = {
            "quoteSummary": {
                "result": [
                    {
                        "majorHoldersBreakdown": {
                            "insidersPercentHeld": {"raw": 0.02},
                            "institutionsPercentHeld": {"raw": 0.61},
                        }
                    }
                ]
            }
        }
        adapter = YahooFinanceOwnershipAdapter(enabled=True, http_client=_FakeJsonClient(payload))
        bundle = adapter.get_ownership(OwnershipQuery(instrument=_instrument()))
        assert bundle is not None
        assert bundle.institutional_holding_percent.to_float() == pytest.approx(61.0)


class TestFinancialModelingPrepOwnershipAdapter:
    def test_maps_institutional_ownership(self) -> None:
        payload = [
            {"investorName": "Vanguard", "weight": 0.08, "sharesNumber": 1000000},
            {"investorName": "BlackRock", "weight": 0.06, "sharesNumber": 900000},
        ]
        adapter = FinancialModelingPrepOwnershipAdapter(api_key="k", http_client=_FakeJsonClient(payload))
        bundle = adapter.get_ownership(OwnershipQuery(instrument=_instrument()))
        assert bundle is not None
        assert len(bundle.stakes) == 2
        assert bundle.institutional_holding_percent.to_float() == pytest.approx(14.0)


class TestNseAndBseOwnership:
    def test_nse_maps_shareholding_categories(self) -> None:
        payload = [
            {"category": "Promoter & Promoter Group", "percentage": 55.1, "no_of_shares": 100},
            {"category": "Public", "percentage": 44.9, "no_of_shares": 80},
        ]
        adapter = NseOwnershipAdapter(enabled=True, http_client=_FakeJsonClient(payload))
        bundle = adapter.get_ownership(OwnershipQuery(instrument=_instrument("RELIANCE")))
        assert bundle is not None
        assert bundle.promoter_holding_percent.to_float() == pytest.approx(55.1)
        assert bundle.public_holding_percent.to_float() == pytest.approx(44.9)

    def test_bse_requires_scrip_code(self) -> None:
        adapter = BseOwnershipAdapter(enabled=True)
        assert adapter.get_ownership(OwnershipQuery(instrument=_instrument("RELIANCE"))) is None


class TestScreenerOwnershipAdapter:
    def test_maps_quarterly_shareholding(self) -> None:
        payload = {
            "shareholding": {
                "quarterly": [
                    {
                        "date": "Sep 2023",
                        "promoters": 50.0,
                        "fii": 15.0,
                        "dii": 10.0,
                        "public": 25.0,
                    }
                ]
            }
        }
        adapter = ScreenerOwnershipAdapter(enabled=True, http_client=_FakeJsonClient(payload))
        bundle = adapter.get_ownership(OwnershipQuery(instrument=_instrument("RELIANCE")))
        assert bundle is not None
        assert bundle.as_of == date(2023, 9, 1)
        assert bundle.promoter_holding_percent.to_float() == pytest.approx(50.0)
        assert bundle.institutional_holding_percent.to_float() == pytest.approx(25.0)


class TestRegistryAndEnv:
    def test_registry_ordering(self) -> None:
        registry = OwnershipProviderRegistry()
        registry.register(NullOwnershipAdapter(), provider_id="null_ownership", priority=1000)
        registry.register(ScreenerOwnershipAdapter(enabled=True), provider_id="screener_ownership", priority=10)
        assert registry.ordered_ids() == ("screener_ownership", "null_ownership")

    def test_default_registry_falls_back_to_null(self, monkeypatch: pytest.MonkeyPatch) -> None:
        for key in (
            "DSP_OWNERSHIP_SCREENER_ENABLED",
            "DSP_OWNERSHIP_FMP_API_KEY",
            "DSP_OWNERSHIP_NSE_ENABLED",
            "DSP_OWNERSHIP_BSE_ENABLED",
            "DSP_OWNERSHIP_YAHOO_ENABLED",
            "DSP_OWNERSHIP_MEMORY",
        ):
            monkeypatch.delenv(key, raising=False)
        registry = build_default_ownership_registry_from_env()
        assert registry.ordered_ids() == ("null_ownership",)


class TestOwnershipService:
    def test_cache_hit(self) -> None:
        adapter = InMemoryOwnershipAdapter(api_key="k")
        adapter.put(
            build_ownership_bundle_from_mapping(
                symbol="AAPL",
                as_of=None,
                stakes=[
                    OwnershipStake(
                        holder_type="institutional_domestic",
                        holder_name=None,
                        percent_held=ConnectorField.of(10),
                        shares_held=ConnectorField.missing(),
                    )
                ],
                provenance=ConnectorProvenance(
                    provider_id="memory_ownership",
                    provider_name="Memory",
                    source_type="public_endpoint",
                    retrieved_at=datetime.now(tz=UTC),
                ),
            )
        )
        service = OwnershipService(adapter)
        query = OwnershipQuery(instrument=_instrument())
        service.get_ownership(query)
        second = service.get_ownership(query)
        assert second is not None
        assert service.metrics.cache_hits == 1
