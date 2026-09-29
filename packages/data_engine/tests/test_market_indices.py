"""Benchmark index provider contract (Figma Dashboard market bar)."""

from __future__ import annotations

import pytest

from data_engine.connector_framework.production_profile import ConnectorConfigurationError
from data_engine.market_indices import (
    INDIA_BENCHMARK_INDICES,
    MarketIndexService,
    NullMarketIndexAdapter,
    build_default_index_adapter_from_env,
)


def test_catalogue_is_the_four_figma_indices() -> None:
    assert [i.label for i in INDIA_BENCHMARK_INDICES] == [
        "NIFTY 50",
        "SENSEX",
        "NIFTY IT",
        "NIFTY BANK",
    ]
    assert all(i.currency == "INR" for i in INDIA_BENCHMARK_INDICES)


def test_null_adapter_is_honestly_unavailable() -> None:
    svc = MarketIndexService(NullMarketIndexAdapter())
    snaps = svc.get_snapshots()
    assert len(snaps) == 4
    for snap in snaps:
        public = snap.to_public_dict()
        assert public["available"] is False
        assert public["value"] is None and public["change_percent"] is None
        assert public["sparkline"] == []


def test_env_factory_never_selects_fmp(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DSP_FMP_API_KEY", raising=False)
    monkeypatch.delenv("DSP_INVESTMENT_FMP_API_KEY", raising=False)
    monkeypatch.setenv("DSP_INVESTMENT_DATA_PROVIDER", "unavailable")
    assert isinstance(build_default_index_adapter_from_env(), NullMarketIndexAdapter)
    monkeypatch.setenv("DSP_FMP_API_KEY", "secret")
    assert isinstance(build_default_index_adapter_from_env(), NullMarketIndexAdapter)
    monkeypatch.setenv("DSP_INVESTMENT_DATA_PROVIDER", "fmp")
    with pytest.raises(ConnectorConfigurationError, match="not permitted"):
        build_default_index_adapter_from_env()
