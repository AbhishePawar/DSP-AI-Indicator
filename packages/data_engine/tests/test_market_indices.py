"""Benchmark index provider contract (Figma Dashboard market bar)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pytest

from data_engine.connector_framework.production_profile import ConnectorConfigurationError
from data_engine.exceptions import ProviderRequestError
from data_engine.market_indices import (
    INDIA_BENCHMARK_INDICES,
    SPARKLINE_POINTS,
    FinancialModelingPrepIndexAdapter,
    MarketIndexService,
    NullMarketIndexAdapter,
    build_default_index_adapter_from_env,
)


class _FakeHttp:
    def __init__(self, quote: Any, history: Any, *, fail_history: bool = False) -> None:
        self.quote = quote
        self.history = history
        self.fail_history = fail_history
        self.calls: list[tuple[str, dict[str, str]]] = []

    def get_json(self, url: str, *, params: Mapping[str, str] | None = None, headers=None):  # noqa: ANN001
        self.calls.append((url, dict(params or {})))
        if "/quote/" in url:
            return self.quote
        if self.fail_history:
            raise ProviderRequestError("history unavailable")
        return self.history


def test_catalogue_is_the_four_figma_indices() -> None:
    assert [i.label for i in INDIA_BENCHMARK_INDICES] == ["NIFTY 50", "SENSEX", "NIFTY IT", "NIFTY BANK"]
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


def test_fmp_adapter_passes_through_provider_values() -> None:
    quote = [{"symbol": "^NSEI", "price": 25000.5, "change": -120.25, "changesPercentage": -0.48, "previousClose": 25120.75, "timestamp": 1758787200}]
    history = {"historical": [{"date": f"2026-09-{25 - i:02d}", "close": 25000 + i} for i in range(15)]}
    http = _FakeHttp(quote, history)
    adapter = FinancialModelingPrepIndexAdapter(api_key="k", http_client=http)
    snap = adapter.get_snapshot(INDIA_BENCHMARK_INDICES[0])
    assert snap is not None and snap.available
    assert snap.value == 25000.5 and snap.change == -120.25 and snap.change_percent == -0.48
    assert len(snap.sparkline) == SPARKLINE_POINTS
    # newest-first from provider → oldest → newest for the sparkline
    assert snap.sparkline[-1] == 25000.0 and snap.sparkline[0] == 25011.0
    assert snap.provenance is not None and snap.provenance.provider_id == "fmp_market_index"
    # Provider symbol never leaks into the public identity
    assert snap.to_public_dict()["index_id"] == "NIFTY50"
    assert http.calls[0][1] == {"apikey": "k"}


def test_history_failure_keeps_quote() -> None:
    quote = [{"price": 80000.0, "change": 10.0, "changesPercentage": 0.01}]
    adapter = FinancialModelingPrepIndexAdapter(api_key="k", http_client=_FakeHttp(quote, None, fail_history=True))
    snap = adapter.get_snapshot(INDIA_BENCHMARK_INDICES[1])
    assert snap is not None and snap.value == 80000.0 and snap.sparkline == ()


def test_empty_quote_is_unavailable_per_index() -> None:
    adapter = FinancialModelingPrepIndexAdapter(api_key="k", http_client=_FakeHttp([], None))
    svc = MarketIndexService(adapter)
    assert all(not s.available for s in svc.get_snapshots())


def test_missing_key_fails_closed() -> None:
    with pytest.raises(ProviderRequestError):
        FinancialModelingPrepIndexAdapter(api_key="").get_snapshot(INDIA_BENCHMARK_INDICES[0])


def test_env_factory_follows_investment_provider_policy(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DSP_FMP_API_KEY", raising=False)
    monkeypatch.delenv("DSP_INVESTMENT_FMP_API_KEY", raising=False)
    monkeypatch.setenv("DSP_INVESTMENT_DATA_PROVIDER", "unavailable")
    assert isinstance(build_default_index_adapter_from_env(), NullMarketIndexAdapter)
    monkeypatch.setenv("DSP_INVESTMENT_DATA_PROVIDER", "fmp")
    assert isinstance(build_default_index_adapter_from_env(), NullMarketIndexAdapter)
    monkeypatch.setenv("DSP_FMP_API_KEY", "secret")
    assert isinstance(build_default_index_adapter_from_env(), FinancialModelingPrepIndexAdapter)
    monkeypatch.setenv("DSP_INVESTMENT_DATA_PROVIDER", "bogus")
    with pytest.raises(ConnectorConfigurationError):
        build_default_index_adapter_from_env()
