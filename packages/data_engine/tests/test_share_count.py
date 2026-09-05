"""ShareCountSnapshot / NullShareCountPort — current outstanding share COUNT."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from contracts.domain.instrument import Instrument
from contracts.enums import AssetClass
from data_engine import (
    InMemoryShareCountAdapter,
    InvalidProviderDataError,
    NullShareCountAdapter,
    ShareCountBasis,
    ShareCountField,
    ShareCountPort,
    ShareCountProvenance,
    ShareCountService,
    ShareCountSnapshot,
    ShareCountUnit,
    assert_share_count_identity,
    build_default_share_count_adapter_from_env,
    build_share_count_from_mapping,
    validate_share_count_snapshot,
)

FIXED = datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)


def _provenance(**overrides) -> ShareCountProvenance:
    payload = {
        "provider_id": "memory_authenticated_share_count",
        "provider_name": "TEST-ONLY synthetic share count fixture",
        "source_type": "licensed_vendor",
        "retrieved_at": FIXED,
        "auth_mode": "api_key",
        "metadata": {"evidence_class": "test_fixture"},
    }
    payload.update(overrides)
    return ShareCountProvenance(**payload)


def _snapshot(
    *,
    symbol: str = "TEST",
    shares: Decimal | float | int | str | None = 100.0,
    exchange: str | None = "NYSE",
    isin: str | None = "US0000000001",
    basis: ShareCountBasis = ShareCountBasis.CURRENT_OUTSTANDING,
    unit: ShareCountUnit = ShareCountUnit.SHARES,
) -> ShareCountSnapshot:
    return build_share_count_from_mapping(
        symbol=symbol,
        payload={"exchange": exchange, "isin": isin, "shares": shares},
        provenance=_provenance(),
        basis=basis,
        unit=unit,
    )


def _instrument(**kwargs) -> Instrument:
    payload = {
        "symbol": "TEST",
        "asset_class": AssetClass.EQUITY,
        "currency": "USD",
        "exchange": "NYSE",
        "isin": "US0000000001",
    }
    payload.update(kwargs)
    return Instrument(**payload)


class TestShareCountSnapshot:
    def test_positive_finite_count_accepted(self) -> None:
        snap = _snapshot(shares=123_456_789)
        validate_share_count_snapshot(snap)
        assert snap.shares_value() == pytest.approx(123_456_789)
        assert snap.unit == ShareCountUnit.SHARES
        assert snap.basis == ShareCountBasis.CURRENT_OUTSTANDING

    def test_none_is_unavailable_not_zero(self) -> None:
        snap = ShareCountSnapshot(
            symbol="TEST",
            exchange="NYSE",
            isin=None,
            shares=ShareCountField.missing(),
            basis=ShareCountBasis.CURRENT_OUTSTANDING,
            unit=ShareCountUnit.SHARES,
            provenance=_provenance(),
        )
        validate_share_count_snapshot(snap)
        assert snap.shares_value() is None
        assert snap.shares_value() != 0

    def test_zero_rejected(self) -> None:
        with pytest.raises(InvalidProviderDataError, match="> 0"):
            _snapshot(shares=0)

    def test_negative_rejected(self) -> None:
        with pytest.raises(InvalidProviderDataError, match="> 0"):
            _snapshot(shares=-10)

    def test_non_numeric_rejected(self) -> None:
        with pytest.raises(InvalidProviderDataError, match="numeric"):
            ShareCountField.of("not-a-number")

    def test_percentage_rejected(self) -> None:
        with pytest.raises(InvalidProviderDataError, match="currency/percentage"):
            ShareCountField.of("10%")

    def test_currency_marker_rejected(self) -> None:
        with pytest.raises(InvalidProviderDataError, match="currency/percentage"):
            ShareCountField.of("$100")

    def test_non_finite_rejected(self) -> None:
        with pytest.raises(InvalidProviderDataError, match="finite"):
            ShareCountField.of(float("inf"))

    def test_explicit_unit_is_shares(self) -> None:
        snap = _snapshot()
        assert snap.unit == ShareCountUnit.SHARES
        assert str(snap.unit) == "shares"

    def test_current_outstanding_basis_for_valuation(self) -> None:
        snap = _snapshot(basis=ShareCountBasis.CURRENT_OUTSTANDING)
        assert snap.basis == ShareCountBasis.CURRENT_OUTSTANDING
        weighted = _snapshot(basis=ShareCountBasis.WEIGHTED_AVERAGE_BASIC)
        assert weighted.basis != ShareCountBasis.CURRENT_OUTSTANDING

    def test_provenance_drops_secrets(self) -> None:
        prov = _provenance(
            metadata={
                "endpoint": "/v1/shares",
                "api_key": "super-secret",
                "bearer_token": "abc",
            }
        )
        public = prov.to_dict()
        blob = str(public)
        assert "super-secret" not in blob
        assert "abc" not in blob
        assert "api_key" not in public["metadata"]
        assert public["metadata"]["endpoint"] == "/v1/shares"


class TestShareCountIdentity:
    def test_matching_isin_accepted(self) -> None:
        snap = _snapshot(isin="US0000000001")
        assert_share_count_identity(
            snap, symbol="TEST", exchange="NYSE", isin="US0000000001"
        )

    def test_mismatched_isin_fails_closed(self) -> None:
        snap = _snapshot(isin="US0000000001")
        with pytest.raises(InvalidProviderDataError, match="ISIN"):
            assert_share_count_identity(
                snap, symbol="TEST", exchange="NYSE", isin="INE467B01029"
            )

    def test_mismatched_exchange_fails_closed(self) -> None:
        snap = _snapshot(exchange="NYSE")
        with pytest.raises(InvalidProviderDataError, match="exchange"):
            assert_share_count_identity(
                snap, symbol="TEST", exchange="NSE", isin="US0000000001"
            )

    def test_missing_exchange_on_one_side_is_not_mismatch(self) -> None:
        snap = _snapshot(exchange=None, isin=None)
        assert_share_count_identity(snap, symbol="TEST", exchange="NYSE", isin=None)


class TestNullShareCountPort:
    def test_returns_unavailable(self) -> None:
        port: ShareCountPort = NullShareCountAdapter()
        assert port.get_share_count(_instrument()) is None
        health = port.health()
        assert health.authenticated is False
        assert health.provider_id.startswith("null")

    def test_never_estimates(self) -> None:
        port = NullShareCountAdapter()
        first = port.get_share_count(_instrument())
        second = port.get_share_count(_instrument(symbol="TCS", exchange="NSE"))
        assert first is None and second is None

    def test_factory_without_provider_is_null(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("DSP_SHARE_COUNT_MEMORY", raising=False)
        monkeypatch.delenv("DSP_ENVIRONMENT", raising=False)
        adapter = build_default_share_count_adapter_from_env()
        assert isinstance(adapter, NullShareCountAdapter)
        assert adapter.get_share_count(_instrument()) is None

    def test_factory_does_not_select_fmp_yahoo_or_upstox(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("DSP_INVESTMENT_DATA_PROVIDER", "upstox")
        monkeypatch.setenv("DSP_FMP_API_KEY", "not-used")
        monkeypatch.delenv("DSP_SHARE_COUNT_MEMORY", raising=False)
        adapter = build_default_share_count_adapter_from_env()
        assert isinstance(adapter, NullShareCountAdapter)
        assert "fmp" not in adapter.provider_id.lower()
        assert "yahoo" not in adapter.provider_id.lower()
        assert "upstox" not in adapter.provider_id.lower()

    def test_memory_adapter_requires_seed(self) -> None:
        adapter = InMemoryShareCountAdapter(api_key="k")
        assert adapter.get_share_count(_instrument()) is None
        adapter.put(_snapshot())
        got = adapter.get_share_count(_instrument())
        assert got is not None
        assert got.shares_value() == pytest.approx(100.0)

    def test_service_unavailable_on_null(self) -> None:
        service = ShareCountService(NullShareCountAdapter())
        assert service.get_share_count(_instrument()) is None
        assert service.metrics.unavailable >= 1
