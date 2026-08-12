"""EPIC-D005 unified data orchestrator tests."""

from __future__ import annotations

from data_engine import (
    DataOrchestrator,
    DataOrchestratorRequest,
    UNAVAILABLE_MESSAGE,
)


def _prov(provider_id: str = "p1") -> dict:
    return {
        "provider_id": provider_id,
        "provider_name": "Test",
        "source_type": "licensed_vendor",
        "retrieved_at": "2026-07-28T00:00:00+00:00",
    }


class TestOrchestrator:
    def test_all_unavailable_by_default(self) -> None:
        orch = DataOrchestrator(
            fetch_market_quote=lambda: None,
            fetch_financial_statements=lambda: None,
            fetch_corporate_actions=lambda: None,
            fetch_historical_series=lambda: None,
            health_market_quote=lambda: {
                "provider_id": "mq",
                "healthy": True,
                "authenticated": False,
            },
            health_financial_statements=lambda: {
                "provider_id": "fs",
                "healthy": True,
                "authenticated": False,
            },
            health_corporate_actions=lambda: {
                "provider_id": "ca",
                "healthy": True,
                "authenticated": False,
            },
            health_historical_series=lambda: {
                "provider_id": "hs",
                "healthy": True,
                "authenticated": False,
            },
        )
        bundle = orch.get_bundle(DataOrchestratorRequest(symbol="AAPL"))
        assert bundle.retrieval.any_available is False
        assert bundle.market_quote.status.message == UNAVAILABLE_MESSAGE
        assert bundle.financial_statements.payload is None
        public = bundle.to_public_dict()
        assert list(public["provenance"].keys()) == [
            "market_quote",
            "financial_statements",
            "corporate_actions",
            "historical_series",
        ]

    def test_partial_provider_failure(self) -> None:
        def boom() -> dict | None:
            raise RuntimeError("upstream down")

        orch = DataOrchestrator(
            fetch_market_quote=lambda: {
                "authenticated": True,
                "fields": {"current_price": 10.0},
                "provenance": _prov("mq"),
            },
            fetch_financial_statements=boom,
            fetch_corporate_actions=lambda: None,
            fetch_historical_series=lambda: {
                "authenticated": True,
                "bars": [{"date": "2024-01-02", "close": 10}],
                "provenance": _prov("hs"),
            },
            health_market_quote=lambda: {
                "provider_id": "mq",
                "healthy": True,
                "authenticated": True,
            },
            health_financial_statements=lambda: {
                "provider_id": "fs",
                "healthy": False,
                "authenticated": False,
            },
            health_corporate_actions=lambda: {
                "provider_id": "ca",
                "healthy": True,
                "authenticated": False,
            },
            health_historical_series=lambda: {
                "provider_id": "hs",
                "healthy": True,
                "authenticated": True,
            },
        )
        bundle = orch.get_bundle(DataOrchestratorRequest(symbol="AAPL"))
        assert bundle.retrieval.partial is True
        assert "market_quote" in bundle.retrieval.sections_ok
        assert "historical_series" in bundle.retrieval.sections_ok
        assert "financial_statements" in bundle.retrieval.sections_error
        assert "corporate_actions" in bundle.retrieval.sections_unavailable
        assert bundle.financial_statements.status.message == UNAVAILABLE_MESSAGE
        assert orch.metrics.partial_responses == 1

    def test_determinism_section_order(self) -> None:
        orch = DataOrchestrator(
            fetch_market_quote=lambda: {
                "authenticated": True,
                "provenance": _prov("mq"),
            },
            fetch_financial_statements=lambda: {
                "authenticated": True,
                "provenance": _prov("fs"),
            },
            fetch_corporate_actions=lambda: {
                "authenticated": True,
                "provenance": _prov("ca"),
            },
            fetch_historical_series=lambda: {
                "authenticated": True,
                "provenance": _prov("hs"),
            },
            health_market_quote=lambda: {"provider_id": "mq", "healthy": True},
            health_financial_statements=lambda: {
                "provider_id": "fs",
                "healthy": True,
            },
            health_corporate_actions=lambda: {"provider_id": "ca", "healthy": True},
            health_historical_series=lambda: {"provider_id": "hs", "healthy": True},
        )
        a = orch.get_bundle(DataOrchestratorRequest(symbol="AAPL")).to_public_dict()
        b = orch.get_bundle(DataOrchestratorRequest(symbol="AAPL")).to_public_dict()
        assert list(a["provenance"].keys()) == list(b["provenance"].keys())
        assert a["retrieval"]["sections_ok"] == b["retrieval"]["sections_ok"]
        assert a["retrieval"]["all_available"] is True

    def test_selective_includes(self) -> None:
        calls = {"mq": 0, "fs": 0, "ca": 0, "hs": 0}

        def mq() -> dict:
            calls["mq"] += 1
            return {"authenticated": True, "provenance": _prov("mq")}

        def fs() -> dict:
            calls["fs"] += 1
            return {"authenticated": True, "provenance": _prov("fs")}

        orch = DataOrchestrator(
            fetch_market_quote=mq,
            fetch_financial_statements=fs,
            fetch_corporate_actions=lambda: (_ for _ in ()).throw(AssertionError()),
            fetch_historical_series=lambda: (_ for _ in ()).throw(AssertionError()),
            health_market_quote=lambda: {"provider_id": "mq", "healthy": True},
            health_financial_statements=lambda: {
                "provider_id": "fs",
                "healthy": True,
            },
            health_corporate_actions=lambda: {"provider_id": "ca", "healthy": True},
            health_historical_series=lambda: {"provider_id": "hs", "healthy": True},
        )
        bundle = orch.get_bundle(
            DataOrchestratorRequest(
                symbol="AAPL",
                include_corporate_actions=False,
                include_historical_series=False,
            )
        )
        assert calls["mq"] == 1
        assert calls["fs"] == 1
        assert bundle.corporate_actions.status.status == "unavailable"
        assert "market_quote" in bundle.retrieval.sections_requested
        assert "corporate_actions" not in bundle.retrieval.sections_requested

    def test_health_aggregation(self) -> None:
        orch = DataOrchestrator(
            fetch_market_quote=lambda: None,
            fetch_financial_statements=lambda: None,
            fetch_corporate_actions=lambda: None,
            fetch_historical_series=lambda: None,
            health_market_quote=lambda: {
                "provider_id": "mq",
                "healthy": True,
                "authenticated": True,
            },
            health_financial_statements=lambda: {
                "provider_id": "fs",
                "healthy": True,
                "authenticated": False,
            },
            health_corporate_actions=lambda: {
                "provider_id": "ca",
                "healthy": False,
                "authenticated": False,
            },
            health_historical_series=lambda: {
                "provider_id": "hs",
                "healthy": True,
                "authenticated": False,
            },
        )
        health = orch.health().to_dict()
        assert health["overall_ok"] is False
        assert health["overall_authenticated"] is True
        assert list(health["providers"].keys()) == [
            "corporate_actions",
            "financial_statements",
            "historical_series",
            "market_quote",
        ]

    def test_company_resolution(self) -> None:
        orch = DataOrchestrator(
            fetch_market_quote=lambda: None,
            fetch_financial_statements=lambda: None,
            fetch_corporate_actions=lambda: None,
            fetch_historical_series=lambda: None,
            health_market_quote=lambda: {"provider_id": "mq", "healthy": True},
            health_financial_statements=lambda: {
                "provider_id": "fs",
                "healthy": True,
            },
            health_corporate_actions=lambda: {"provider_id": "ca", "healthy": True},
            health_historical_series=lambda: {"provider_id": "hs", "healthy": True},
            resolve_company=lambda: {
                "symbol": "AAPL",
                "company_name": "Apple Inc",
                "provider_company_id": "AAPL-USD",
                "currency": "USD",
            },
        )
        bundle = orch.get_bundle(DataOrchestratorRequest(symbol="AAPL"))
        assert bundle.identity.company_name == "Apple Inc"
        assert bundle.identity.resolved_by == "financial_statements"
