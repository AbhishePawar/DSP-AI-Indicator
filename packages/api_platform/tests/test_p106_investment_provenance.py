"""P1-06 — durable investment provenance / decision lineage."""

from __future__ import annotations

import copy

import pytest
from fastapi.testclient import TestClient

from api_platform import create_app
from auth_test_helpers import bearer_headers, register_user
from dsp_platform import (
    PlatformBuilder,
    PlatformConfiguration,
)
from dsp_platform.investment_provenance import (
    RELEASE_IDENTITY,
    DatabaseInvestmentProvenanceStore,
    InvestmentProvenanceForbidden,
    build_investment_provenance,
    get_investment_provenance_store,
    redact_secrets,
    reset_investment_provenance_store_for_tests,
)
from production_platform import InMemoryDatabasePort


@pytest.fixture
def db() -> InMemoryDatabasePort:
    return InMemoryDatabasePort()


@pytest.fixture
def client(db: InMemoryDatabasePort) -> TestClient:
    platform = (
        PlatformBuilder()
        .with_configuration(PlatformConfiguration(require_analysis_service=False))
        .auto_ready(True)
        .build()
    )
    app_client = TestClient(create_app(platform=platform))
    # Bind shared DatabasePort after app boot (boot may wire a different adapter).
    reset_investment_provenance_store_for_tests(
        DatabaseInvestmentProvenanceStore(db)
    )
    return app_client


def _analyse_body(**overrides: object) -> dict:
    body: dict = {
        "ticker": "ACM",
        "exchange": "NYSE",
        "company": "Acme",
        "financial_statements": {
            "period": {
                "period_type": "annual",
                "period_end": "2024-12-31",
                "fiscal_year": 2024,
                "currency": "USD",
            },
            "income_statement": {
                "revenue": 1000.0,
                "cogs": 400.0,
                "gross_profit": 600.0,
                "ebit": 300.0,
                "ebitda": 350.0,
                "interest_expense": 20.0,
                "pretax_income": 280.0,
                "tax": 70.0,
                "net_income": 210.0,
                "weighted_shares": 100.0,
                "eps": 2.1,
            },
            "balance_sheet": {
                "cash": 150.0,
                "short_term_investments": 50.0,
                "accounts_receivable": 120.0,
                "inventory": 80.0,
                "current_assets": 450.0,
                "ppe": 400.0,
                "goodwill": 50.0,
                "intangibles": 50.0,
                "total_assets": 1000.0,
                "accounts_payable": 60.0,
                "short_term_debt": 50.0,
                "current_liabilities": 200.0,
                "long_term_debt": 200.0,
                "total_liabilities": 400.0,
                "retained_earnings": 300.0,
                "equity": 600.0,
                "total_equity": 600.0,
            },
            "cash_flow": {
                "operating_cash_flow": 250.0,
                "capex": -80.0,
                "free_cash_flow": 170.0,
                "dividends_paid": -50.0,
                "share_buybacks": -30.0,
                "debt_issued": 10.0,
                "debt_repaid": -40.0,
            },
            "statement_metadata": {"unit_scale": "millions"},
        },
        "current_market_price": 70.0,
    }
    body.update(overrides)
    return body


class TestP106Positive:
    def test_analyse_creates_durable_provenance(self, client: TestClient) -> None:
        response = client.post("/api/v1/analyse", json=_analyse_body())
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["ok"] is True
        assert body["provenance_persisted"] is True
        assert body["analysis_id"]
        assert body["audit_reference"] == body["analysis_id"]
        assert body["payload"]["analysis_id"] == body["analysis_id"]
        assert "source_evidence" in body["payload"]
        assert "buffett_authority" in body["payload"]

        got = client.get(f"/api/v1/analyse/provenance/{body['analysis_id']}")
        assert got.status_code == 200, got.text
        prov = got.json()["provenance"]
        assert prov["analysis_id"] == body["analysis_id"]
        assert prov["ticker"] == "ACM"
        assert prov["authority"] == "server"
        assert prov["release"]["epic"] == "EPS-003"
        assert prov["release"]["product_version"] == "2.0.0-rc.1"
        assert prov["release"]["label"] == RELEASE_IDENTITY["label"]
        assert prov["financial_validation"]["status"] in {
            "succeeded",
            "degraded",
            "unavailable",
        }
        assert "valuation" in prov
        assert "buffett" in prov
        assert "conclusion" in prov
        assert prov["input_fingerprint"]
        assert prov["result_fingerprint"]

    def test_multi_worker_read_same_provenance(self, db: InMemoryDatabasePort) -> None:
        platform = (
            PlatformBuilder()
            .with_configuration(PlatformConfiguration(require_analysis_service=False))
            .auto_ready(True)
            .build()
        )
        client_a = TestClient(create_app(platform=platform))
        reset_investment_provenance_store_for_tests(
            DatabaseInvestmentProvenanceStore(db)
        )
        resp = client_a.post("/api/v1/analyse", json=_analyse_body())
        assert resp.status_code == 200
        analysis_id = resp.json()["analysis_id"]

        # Worker B — new store instance, same DatabasePort.
        store_b = DatabaseInvestmentProvenanceStore(db)
        record = store_b.get(analysis_id)
        assert record is not None
        assert record.analysis_id == analysis_id
        assert record.ticker == "ACM"
        assert record.conclusion.get("recommendation") is not None or record.buffett

    def test_restart_survives(self, db: InMemoryDatabasePort) -> None:
        platform = (
            PlatformBuilder()
            .with_configuration(PlatformConfiguration(require_analysis_service=False))
            .auto_ready(True)
            .build()
        )
        client = TestClient(create_app(platform=platform))
        reset_investment_provenance_store_for_tests(
            DatabaseInvestmentProvenanceStore(db)
        )
        analysis_id = client.post("/api/v1/analyse", json=_analyse_body()).json()[
            "analysis_id"
        ]

        # Simulate process restart: drop process singleton, rebuild from DB.
        reset_investment_provenance_store_for_tests(
            DatabaseInvestmentProvenanceStore(db)
        )
        restored = get_investment_provenance_store().get(analysis_id)
        assert restored is not None
        assert restored.analysis_id == analysis_id
        assert restored.immutable is True

    def test_fingerprint_determinism(self) -> None:
        payload = {
            "ok": True,
            "metadata": {
                "pipeline_version": "1.0.0",
                "platform_version": "0.7.1",
                "package_versions": {"valuation": "1.0.0"},
            },
            "stage_summaries": [
                {
                    "stage": "financial",
                    "status": "succeeded",
                    "has_result": True,
                    "score": 70,
                    "label": "ok",
                },
                {
                    "stage": "valuation",
                    "status": "degraded",
                    "has_result": True,
                    "score": None,
                    "label": None,
                },
            ],
            "recommendation_summary": {"decision": "hold", "score": 55},
            "committee_summary": {"decision": "hold"},
            "buffett_authority": {
                "overall_score": 70,
                "overall_label": "good",
                "overall_status": "succeeded",
                "factors": {},
                "recommendation": "hold",
            },
        }
        a = build_investment_provenance(
            public_payload=payload,
            ticker="ACM",
            analysis_id="fixed-id",
            created_at="2026-08-08T00:00:00+00:00",
            financial_statements_digest={"period": {"fiscal_year": 2024}},
        )
        b = build_investment_provenance(
            public_payload=copy.deepcopy(payload),
            ticker="ACM",
            analysis_id="fixed-id",
            created_at="2026-08-08T00:00:00+00:00",
            financial_statements_digest={"period": {"fiscal_year": 2024}},
        )
        assert a.input_fingerprint == b.input_fingerprint
        assert a.result_fingerprint == b.result_fingerprint
        assert len(a.input_fingerprint) == 64
        assert a.input_fingerprint != a.result_fingerprint


class TestP106Negative:
    @pytest.mark.parametrize(
        "field",
        [
            "analysis_id",
            "audit_reference",
            "provenance",
            "audit_result",
            "source_evidence",
            "valuation_result",
            "buffett_result",
            "investment_conclusion",
        ],
    )
    def test_forged_top_level_provenance_rejected(
        self, client: TestClient, field: str
    ) -> None:
        payload = _analyse_body(**{field: "forged"})
        response = client.post("/api/v1/analyse", json=payload)
        assert response.status_code == 422

    def test_forged_nested_provenance_rejected(self, client: TestClient) -> None:
        payload = _analyse_body()
        payload["financial_statements"]["statement_metadata"]["provenance"] = {
            "source": "forged"
        }
        response = client.post("/api/v1/analyse", json=payload)
        assert response.status_code == 422
        assert any("P1-06" in e for e in response.json()["validation_errors"])

    def test_forged_buffett_and_recommendation_still_rejected(
        self, client: TestClient
    ) -> None:
        payload = _analyse_body(buffett_score=100, recommendation="BUY")
        response = client.post("/api/v1/analyse", json=payload)
        assert response.status_code == 422

    def test_secrets_redacted(self) -> None:
        dirty = {
            "api_key": "sk-live-secret",
            "authorization": "Bearer abc.def",
            "nested": {"password": "hunter2", "ok": 1},
        }
        clean = redact_secrets(dirty)
        assert clean["api_key"] == "[REDACTED]"
        assert clean["authorization"] == "[REDACTED]"
        assert clean["nested"]["password"] == "[REDACTED]"
        assert clean["nested"]["ok"] == 1

    def test_tenant_isolation_owner_mismatch(self, db: InMemoryDatabasePort) -> None:
        store = DatabaseInvestmentProvenanceStore(db)
        record = build_investment_provenance(
            public_payload={
                "ok": True,
                "metadata": {},
                "stage_summaries": [],
                "recommendation_summary": {"decision": "hold"},
                "committee_summary": {},
                "buffett_authority": {},
            },
            ticker="ACM",
            analysis_id="iso-1",
            owner_user_id="user-a",
            created_at="2026-08-08T00:00:00+00:00",
        )
        store.append(record)
        with pytest.raises(InvestmentProvenanceForbidden):
            store.get("iso-1", actor_user_id="user-b")
        assert store.get("iso-1", actor_user_id="user-a") is not None

    def test_unavailable_valuation_recorded_honestly(self) -> None:
        record = build_investment_provenance(
            public_payload={
                "ok": True,
                "metadata": {},
                "stage_summaries": [
                    {
                        "stage": "valuation",
                        "status": "failed",
                        "has_result": False,
                        "score": None,
                    }
                ],
                "recommendation_summary": {},
                "committee_summary": {},
                "buffett_authority": {
                    "factors": {
                        "valuation": {
                            "available": False,
                            "status": "unavailable",
                            "score": None,
                        }
                    },
                    "overall_status": "unavailable",
                    "overall_score": None,
                },
            },
            ticker="ACM",
            analysis_id="missing-val",
            created_at="2026-08-08T00:00:00+00:00",
        )
        assert record.valuation["status"] == "unavailable"
        assert record.valuation["available"] is False
        assert record.valuation["score"] is None

    def test_production_fail_closed_without_durable_store(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from dsp_platform.investment_provenance import InMemoryInvestmentProvenanceStore

        platform = (
            PlatformBuilder()
            .with_configuration(PlatformConfiguration(require_analysis_service=False))
            .auto_ready(True)
            .build()
        )
        # Boot in non-production, then force production + in-memory store to prove
        # analyse fail-closed (boot gate is covered by P0-06).
        client = TestClient(create_app(platform=platform))
        monkeypatch.setenv("DSP_ENVIRONMENT", "production")
        reset_investment_provenance_store_for_tests(InMemoryInvestmentProvenanceStore())
        response = client.post("/api/v1/analyse", json=_analyse_body())
        assert response.status_code == 503
        body = response.json()
        assert body["error_code"] == "AUDIT_PERSISTENCE_FAILED"


class TestP106QueryAndAuth:
    def test_list_by_ticker(self, client: TestClient) -> None:
        a = client.post("/api/v1/analyse", json=_analyse_body()).json()
        b = client.post("/api/v1/analyse", json=_analyse_body(ticker="MSFT")).json()
        listed = client.get("/api/v1/analyse/provenance", params={"ticker": "ACM"})
        assert listed.status_code == 200
        items = listed.json()["items"]
        ids = {i["analysis_id"] for i in items}
        assert a["analysis_id"] in ids
        assert b["analysis_id"] not in ids

    def test_cross_user_owned_provenance_denied(self, client: TestClient) -> None:
        # Unique ids — auth service is process-singleton across TestClients.
        register_user(client, user_id="p106-owner-a", username="p106prova")
        register_user(client, user_id="p106-owner-b", username="p106provb")
        ha = bearer_headers(client, username="p106prova")
        hb = bearer_headers(client, username="p106provb")
        created = client.post(
            "/api/v1/analyse", json=_analyse_body(), headers=ha
        ).json()
        analysis_id = created["analysis_id"]
        deny = client.get(
            f"/api/v1/analyse/provenance/{analysis_id}", headers=hb
        )
        assert deny.status_code == 403
        allow = client.get(
            f"/api/v1/analyse/provenance/{analysis_id}", headers=ha
        )
        assert allow.status_code == 200
