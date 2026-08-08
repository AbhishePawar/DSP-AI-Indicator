"""P1-05 — Buffett / investment-quality analysis is server-authoritative."""

from __future__ import annotations

import copy

import pytest
from fastapi.testclient import TestClient

from api_platform import create_app
from dsp_platform import (
    DSPPlatform,
    PlatformBuilder,
    PlatformConfiguration,
    build_composition_request,
    pipeline_result_public_dict,
)


@pytest.fixture
def client() -> TestClient:
    platform = (
        PlatformBuilder()
        .with_configuration(PlatformConfiguration(require_analysis_service=False))
        .auto_ready(True)
        .build()
    )
    return TestClient(create_app(platform=platform))


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


class TestP105ForgedClientRejected:
    @pytest.mark.parametrize(
        "field",
        [
            "buffett_score",
            "buffett_rating",
            "moat_score",
            "management_score",
            "quality_score",
            "capital_allocation_score",
            "governance_score",
            "buffett_conclusion",
            "investment_quality",
            "overall_buffett_rating",
        ],
    )
    def test_top_level_buffett_override_rejected(
        self, client: TestClient, field: str
    ) -> None:
        payload = _analyse_body(**{field: 100})
        response = client.post("/api/v1/analyse", json=payload)
        assert response.status_code == 422
        body = response.json()
        assert body["ok"] is False

    @pytest.mark.parametrize(
        "field",
        [
            "buffett_score",
            "moat_score",
            "management_score",
            "quality_score",
            "governance_score",
        ],
    )
    def test_smuggled_statement_buffett_fields_rejected(
        self, client: TestClient, field: str
    ) -> None:
        payload = _analyse_body()
        payload["financial_statements"]["statement_metadata"][field] = 100
        response = client.post("/api/v1/analyse", json=payload)
        assert response.status_code == 422
        body = response.json()
        assert body["error_code"] == "VALIDATION_ERROR"
        assert any("P1-05" in e for e in body["validation_errors"])

    def test_forged_recommendation_field_rejected_as_extra(
        self, client: TestClient
    ) -> None:
        payload = _analyse_body(recommendation="BUY")
        response = client.post("/api/v1/analyse", json=payload)
        assert response.status_code == 422
        body = response.json()
        assert body["ok"] is False


class TestP105ServerAuthority:
    def test_buffett_authority_present_and_server_owned(
        self, client: TestClient
    ) -> None:
        response = client.post("/api/v1/analyse", json=_analyse_body())
        assert response.status_code == 200
        payload = response.json()["payload"]
        authority = payload["buffett_authority"]
        assert authority["authority"] == "server"
        assert authority["client_overrides_accepted"] is False
        assert authority["methodology"] == "existing_pipeline_stages"
        factors = authority["factors"]
        assert "economic_moat" in factors
        assert "management_quality" in factors
        assert "business_quality" in factors
        assert "valuation" in factors
        # Honest path with full statements should produce BQ score.
        assert factors["business_quality"]["available"] is True
        assert factors["business_quality"]["score"] is not None
        assert authority["overall_score"] == factors["business_quality"]["score"]

    def test_forged_buffett_fields_cannot_override_server_result(
        self, client: TestClient
    ) -> None:
        clean = client.post("/api/v1/analyse", json=_analyse_body()).json()["payload"]
        clean_auth = clean["buffett_authority"]
        assert clean_auth["overall_score"] is not None

        forged = _analyse_body()
        forged["buffett_score"] = 100
        forged["moat_score"] = 100
        forged["management_score"] = 100
        forged["quality_score"] = 100
        forged["recommendation"] = "BUY"
        forged_resp = client.post("/api/v1/analyse", json=forged)
        assert forged_resp.status_code == 422

        # Honest re-run unchanged after rejected forgery attempt.
        again = client.post("/api/v1/analyse", json=_analyse_body()).json()["payload"][
            "buffett_authority"
        ]
        assert again == clean_auth

    def test_determinism_identical_inputs(self, client: TestClient) -> None:
        body = _analyse_body()
        a = client.post("/api/v1/analyse", json=body).json()["payload"][
            "buffett_authority"
        ]
        b = client.post("/api/v1/analyse", json=copy.deepcopy(body)).json()[
            "payload"
        ]["buffett_authority"]
        assert a == b

    def test_missing_income_fails_validation(self, client: TestClient) -> None:
        payload = _analyse_body()
        payload["financial_statements"]["income_statement"] = {}
        response = client.post("/api/v1/analyse", json=payload)
        assert response.status_code == 422
        assert any(
            "income_statement" in e for e in response.json()["validation_errors"]
        )


class TestP105MissingDataHonesty:
    def test_price_only_does_not_fabricate_positive_buffett_from_client(
        self, client: TestClient
    ) -> None:
        """Incomplete authenticated path still uses server stages; no client score."""
        response = client.post("/api/v1/analyse", json=_analyse_body())
        assert response.status_code == 200
        authority = response.json()["payload"]["buffett_authority"]
        assert authority["client_overrides_accepted"] is False
        # Valuation factor may be degraded without auth IV — must not invent.
        valuation = authority["factors"]["valuation"]
        if not valuation["available"]:
            assert valuation["status"] == "unavailable"
            assert valuation["score"] is None

    def test_pipeline_public_dict_buffett_authority_matches_bq_stage(self) -> None:
        platform = (
            PlatformBuilder()
            .with_configuration(PlatformConfiguration(require_analysis_service=False))
            .auto_ready(True)
            .build()
        )
        assert isinstance(platform, DSPPlatform)
        req = build_composition_request(
            ticker="ACM",
            company="Acme",
            current_market_price=70.0,
            financial_statements=_analyse_body()["financial_statements"],
        )
        envelope = platform.compose_intelligence(req)
        public = pipeline_result_public_dict(envelope.payload)
        authority = public["buffett_authority"]
        bq_stage = next(
            s
            for s in public["stage_summaries"]
            if s["stage"] == "business_quality_aggregator"
        )
        assert authority["overall_score"] == bq_stage["score"]
        assert authority["authority"] == "server"
        assert authority["buffett_reviewer"] is not None
        assert authority["buffett_reviewer"]["available"] is True
