"""P1-10 — Authenticity hard-fail contracts (merge/release blocking).

These tests make authenticity violations fail with explicit CI codes.
They complement P1-09 (critical journey) and must never soft-pass.

evidence_class for any fixture path remains test_fixture — never G2 live.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api_platform import create_app
from auth_test_helpers import bearer_headers, register_user
from data_engine import (
    FinancialStatementService,
    InMemoryAuthenticatedQuoteAdapter,
    InMemoryAuthenticatedStatementAdapter,
    MarketQuoteService,
)
from data_engine.connector_framework.production_profile import (
    adapter_is_production_unsafe,
)
from data_engine.exceptions import ConnectorConfigurationError
from data_engine.financial_statement.adapters import (
    NullAuthenticatedStatementAdapter,
    build_default_statement_adapter_from_env,
)
from data_engine.market_quote.adapters import (
    NullAuthenticatedQuoteAdapter,
    build_default_quote_adapter_from_env,
)
from dsp_platform import PlatformBuilder, PlatformConfiguration
from dsp_platform.financial_statements import reset_financial_statement_service_for_tests
from dsp_platform.investment_provenance import (
    RELEASE_IDENTITY,
    DatabaseInvestmentProvenanceStore,
    reset_investment_provenance_store_for_tests,
)
from dsp_platform.market_quotes import reset_market_quote_service_for_tests
from dsp_platform.p109_e2e_fixture import (
    P109_EVIDENCE_CLASS,
    P109_FIXTURE_TICKER,
    build_p109_quote,
    build_p109_statements,
)
from production_platform import InMemoryDatabasePort

ROOT = Path(__file__).resolve().parents[3]
EVIDENCE_PATH = ROOT / "artifacts" / "p110_authenticity_hard_fail_evidence.json"

# Explicit CI failure codes (must appear in AssertionError messages).
PRODUCTION_NULL_FALLBACK_DETECTED = "PRODUCTION_NULL_FALLBACK_DETECTED"
PRODUCTION_MEMORY_FALLBACK_DETECTED = "PRODUCTION_MEMORY_FALLBACK_DETECTED"
CLIENT_IDENTITY_SPOOF_ACCEPTED = "CLIENT_IDENTITY_SPOOF_ACCEPTED"
CLIENT_VALUATION_OVERRIDE_DETECTED = "CLIENT_VALUATION_OVERRIDE_DETECTED"
CLIENT_BUFFETT_OVERRIDE_DETECTED = "CLIENT_BUFFETT_OVERRIDE_DETECTED"
PROVENANCE_FORGERY_DETECTED = "PROVENANCE_FORGERY_DETECTED"
DATA_UNAVAILABLE_NOT_HONESTLY_HANDLED = "DATA_UNAVAILABLE_NOT_HONESTLY_HANDLED"
RELEASE_IDENTITY_STALE = "RELEASE_IDENTITY_STALE"


def hard_fail(condition: bool, code: str, detail: str = "") -> None:
    """Fail with a legible authenticity code (no soft-assert)."""
    if not condition:
        message = f"{code}: {detail}" if detail else code
        raise AssertionError(message)


def _write_evidence(payload: dict) -> None:
    EVIDENCE_PATH.parent.mkdir(parents=True, exist_ok=True)
    EVIDENCE_PATH.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )


@pytest.fixture()
def db() -> InMemoryDatabasePort:
    return InMemoryDatabasePort()


@pytest.fixture()
def client(db: InMemoryDatabasePort, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DSP_ENVIRONMENT", "development")
    monkeypatch.delenv("DSP_P109_E2E_FIXTURE", raising=False)

    quote_adapter = InMemoryAuthenticatedQuoteAdapter(api_key="p110-fixture-key")
    stmt_adapter = InMemoryAuthenticatedStatementAdapter(api_key="p110-fixture-key")
    quote_adapter.put(build_p109_quote())
    stmt_adapter.put(build_p109_statements())
    reset_market_quote_service_for_tests(MarketQuoteService(quote_adapter))
    reset_financial_statement_service_for_tests(
        FinancialStatementService(stmt_adapter)
    )

    platform = (
        PlatformBuilder()
        .with_configuration(PlatformConfiguration(require_analysis_service=False))
        .auto_ready(True)
        .build()
    )
    api = TestClient(create_app(platform=platform, enable_security=False))
    reset_investment_provenance_store_for_tests(DatabaseInvestmentProvenanceStore(db))
    yield api
    reset_market_quote_service_for_tests(None)
    reset_financial_statement_service_for_tests(None)
    reset_investment_provenance_store_for_tests(None)


def _statements_body() -> dict:
    return {
        "period": {
            "period_type": "annual",
            "period_end": "2024-12-31",
            "fiscal_year": 2024,
            "currency": "USD",
        },
        "income_statement": {
            "revenue": 100.0,
            "net_income": 10.0,
            "operating_income": 12.0,
        },
        "balance_sheet": {
            "total_equity": 50.0,
            "total_assets": 80.0,
            "total_debt": 10.0,
            "cash_and_equivalents": 5.0,
        },
        "cash_flow": {"operating_cash_flow": 15.0},
        "statement_metadata": {
            "source": "authenticated_fundamentals",
            "evidence_class": P109_EVIDENCE_CLASS,
            "unit_scale": "actual",
            "statement_basis": "consolidated",
        },
    }


class TestProductionConnectorAuthenticity:
    @pytest.fixture(autouse=True)
    def _clear_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        for key in (
            "DSP_ENVIRONMENT",
            "DSP_MARKET_QUOTE_API_KEY",
            "DSP_MARKET_QUOTE_BASE_URL",
            "DSP_MARKET_QUOTE_MEMORY",
            "DSP_FINANCIAL_STATEMENT_API_KEY",
            "DSP_FINANCIAL_STATEMENT_BASE_URL",
            "DSP_FINANCIAL_STATEMENT_MEMORY",
            "DSP_FMP_API_KEY",
            "DSP_INVESTMENT_FMP_API_KEY",
        ):
            monkeypatch.delenv(key, raising=False)

    def test_production_null_quote_hard_fails(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("DSP_ENVIRONMENT", "production")
        try:
            adapter = build_default_quote_adapter_from_env()
        except ConnectorConfigurationError as exc:
            hard_fail(
                "P1-03" in str(exc),
                PRODUCTION_NULL_FALLBACK_DETECTED,
                f"unexpected error: {exc}",
            )
            return
        hard_fail(
            False,
            PRODUCTION_NULL_FALLBACK_DETECTED,
            f"production selected {type(adapter).__name__}",
        )

    def test_production_null_statements_hard_fails(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("DSP_ENVIRONMENT", "production")
        try:
            adapter = build_default_statement_adapter_from_env()
        except ConnectorConfigurationError as exc:
            hard_fail(
                "P1-03" in str(exc) or "financial_statement" in str(exc),
                PRODUCTION_NULL_FALLBACK_DETECTED,
                f"unexpected error: {exc}",
            )
            return
        hard_fail(
            False,
            PRODUCTION_NULL_FALLBACK_DETECTED,
            f"production selected {type(adapter).__name__}",
        )

    def test_production_memory_quote_hard_fails(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("DSP_ENVIRONMENT", "production")
        monkeypatch.setenv("DSP_MARKET_QUOTE_MEMORY", "1")
        try:
            adapter = build_default_quote_adapter_from_env()
        except ConnectorConfigurationError as exc:
            hard_fail(
                "in-memory" in str(exc) or "P1-03" in str(exc),
                PRODUCTION_MEMORY_FALLBACK_DETECTED,
                f"unexpected error: {exc}",
            )
            return
        hard_fail(
            False,
            PRODUCTION_MEMORY_FALLBACK_DETECTED,
            f"production selected {type(adapter).__name__}",
        )

    def test_production_memory_statements_hard_fails(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("DSP_ENVIRONMENT", "production")
        monkeypatch.setenv("DSP_FINANCIAL_STATEMENT_MEMORY", "1")
        try:
            adapter = build_default_statement_adapter_from_env()
        except ConnectorConfigurationError as exc:
            hard_fail(
                "in-memory" in str(exc) or "P1-03" in str(exc),
                PRODUCTION_MEMORY_FALLBACK_DETECTED,
                f"unexpected error: {exc}",
            )
            return
        hard_fail(
            False,
            PRODUCTION_MEMORY_FALLBACK_DETECTED,
            f"production selected {type(adapter).__name__}",
        )

    def test_production_api_boot_rejects_null_connectors(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("DSP_ENVIRONMENT", "production")
        monkeypatch.setenv("DSP_JWT_SECRET", "unit-test-production-secret-not-default")
        platform = (
            PlatformBuilder()
            .with_configuration(PlatformConfiguration(require_analysis_service=False))
            .auto_ready(True)
            .build()
        )
        try:
            create_app(platform=platform, enable_security=False)
        except ConnectorConfigurationError as exc:
            hard_fail(
                "P1-03" in str(exc),
                PRODUCTION_NULL_FALLBACK_DETECTED,
                f"unexpected error: {exc}",
            )
            return
        hard_fail(
            False,
            PRODUCTION_NULL_FALLBACK_DETECTED,
            "create_app allowed Null connectors in production",
        )

    def test_null_adapters_classified_unsafe(self) -> None:
        hard_fail(
            adapter_is_production_unsafe(NullAuthenticatedQuoteAdapter()),
            PRODUCTION_NULL_FALLBACK_DETECTED,
            "NullAuthenticatedQuoteAdapter must be unsafe",
        )
        hard_fail(
            adapter_is_production_unsafe(NullAuthenticatedStatementAdapter()),
            PRODUCTION_NULL_FALLBACK_DETECTED,
            "NullAuthenticatedStatementAdapter must be unsafe",
        )


class TestIdentityAuthenticity:
    def test_x_user_id_alone_cannot_authorize(self, client: TestClient) -> None:
        spoof = {"X-User-Id": "p110-attacker"}
        for path in (
            "/api/v1/saas/organizations",
            "/api/v1/enterprise/organizations",
            "/api/v1/ops/secrets",
            "/api/v1/admin/schema",
        ):
            status = client.get(path, headers=spoof).status_code
            hard_fail(
                status in {401, 403},
                CLIENT_IDENTITY_SPOOF_ACCEPTED,
                f"{path} returned {status} for X-User-Id-only request",
            )

    def test_authenticated_principal_ignores_spoofed_header(
        self, client: TestClient
    ) -> None:
        register_user(client, user_id="p110-real", username="p110real")
        headers = bearer_headers(client, username="p110real")
        created = client.post(
            "/api/v1/enterprise/organizations",
            headers={**headers, "X-User-Id": "attacker"},
            json={
                "name": "P110 Org",
                "slug": "p110-org-auth",
                "owner_user_id": "attacker",
            },
        )
        hard_fail(
            created.status_code == 200,
            CLIENT_IDENTITY_SPOOF_ACCEPTED,
            f"org create failed: {created.text}",
        )
        owner = created.json()["result"]["owner_user_id"]
        hard_fail(
            owner == "p110-real",
            CLIENT_IDENTITY_SPOOF_ACCEPTED,
            f"owner became {owner!r} under spoofed X-User-Id",
        )


class TestValuationAndBuffettAuthenticity:
    def test_client_iv_mos_recommendation_rejected(self, client: TestClient) -> None:
        register_user(
            client,
            user_id="p110-val",
            username="p110val",
            roles=["administrator"],
        )
        headers = bearer_headers(client, username="p110val")
        forged = {
            "ticker": P109_FIXTURE_TICKER,
            "company": "DSP Fixture Corp",
            "current_market_price": 25.0,
            "recommendation": "BUY",
            "valuation_signals": {
                "intrinsic_value_per_share": 9999.0,
                "margin_of_safety": 0.99,
                "current_market_price": 25.0,
            },
            "financial_statements": _statements_body(),
        }
        resp = client.post("/api/v1/analyse", headers=headers, json=forged)
        hard_fail(
            resp.status_code == 422,
            CLIENT_VALUATION_OVERRIDE_DETECTED,
            f"status={resp.status_code} body={resp.text[:500]}",
        )
        body = resp.json()
        hard_fail(
            body.get("ok") is False,
            CLIENT_VALUATION_OVERRIDE_DETECTED,
            "forged valuation request marked ok=true",
        )

    def test_client_buffett_override_rejected(self, client: TestClient) -> None:
        register_user(
            client,
            user_id="p110-buf",
            username="p110buf",
            roles=["administrator"],
        )
        headers = bearer_headers(client, username="p110buf")
        forged = {
            "ticker": P109_FIXTURE_TICKER,
            "company": "DSP Fixture Corp",
            "current_market_price": 25.0,
            "buffett_score": 100,
            "buffett_rating": "excellent",
            "financial_statements": _statements_body(),
        }
        # Smuggle via statement metadata as well.
        forged["financial_statements"]["statement_metadata"]["buffett_score"] = 100
        resp = client.post("/api/v1/analyse", headers=headers, json=forged)
        hard_fail(
            resp.status_code == 422,
            CLIENT_BUFFETT_OVERRIDE_DETECTED,
            f"status={resp.status_code} body={resp.text[:500]}",
        )


class TestProvenanceAuthenticity:
    def test_forged_provenance_fields_rejected(self, client: TestClient) -> None:
        register_user(
            client,
            user_id="p110-prov",
            username="p110prov",
            roles=["administrator"],
        )
        headers = bearer_headers(client, username="p110prov")
        forged = {
            "ticker": P109_FIXTURE_TICKER,
            "company": "DSP Fixture Corp",
            "current_market_price": 25.0,
            "provenance": {"source": "forged"},
            "source_evidence": {"provider": "invented"},
            "financial_statements": _statements_body(),
        }
        resp = client.post("/api/v1/analyse", headers=headers, json=forged)
        hard_fail(
            resp.status_code == 422,
            PROVENANCE_FORGERY_DETECTED,
            f"status={resp.status_code} body={resp.text[:500]}",
        )

    def test_nested_provenance_forgery_rejected(self, client: TestClient) -> None:
        register_user(
            client,
            user_id="p110-prov2",
            username="p110prov2",
            roles=["administrator"],
        )
        headers = bearer_headers(client, username="p110prov2")
        body = {
            "ticker": P109_FIXTURE_TICKER,
            "company": "DSP Fixture Corp",
            "current_market_price": 25.0,
            "financial_statements": _statements_body(),
        }
        body["financial_statements"]["statement_metadata"]["provenance"] = {
            "source": "forged"
        }
        resp = client.post("/api/v1/analyse", headers=headers, json=body)
        hard_fail(
            resp.status_code == 422,
            PROVENANCE_FORGERY_DETECTED,
            f"nested provenance accepted: {resp.text[:500]}",
        )
        errors = " ".join(resp.json().get("validation_errors") or [])
        hard_fail(
            "P1-06" in errors or "provenance" in errors.lower(),
            PROVENANCE_FORGERY_DETECTED,
            f"errors={errors}",
        )


class TestHonestUnavailable:
    def test_missing_symbol_does_not_fabricate_values(
        self, client: TestClient
    ) -> None:
        register_user(
            client,
            user_id="p110-miss",
            username="p110miss",
            roles=["administrator"],
        )
        headers = bearer_headers(client, username="p110miss")
        quote = client.get(
            "/api/v1/market/quote?symbol=ZZZZNOPE110",
            headers=headers,
        )
        hard_fail(
            quote.status_code == 200,
            DATA_UNAVAILABLE_NOT_HONESTLY_HANDLED,
            f"quote status={quote.status_code}",
        )
        q = quote.json()
        hard_fail(
            q.get("available") is False
            or q.get("fields", {}).get("current_price") in (None, 0),
            DATA_UNAVAILABLE_NOT_HONESTLY_HANDLED,
            f"fabricated quote for missing symbol: {q}",
        )
        # Analyse with no statements must not invent IV/MoS.
        resp = client.post(
            "/api/v1/analyse",
            headers=headers,
            json={
                "ticker": "ZZZZNOPE110",
                "company": "Missing",
                "current_market_price": 25.0,
                "financial_statements": {
                    "period": {
                        "period_type": "annual",
                        "period_end": "2024-12-31",
                        "currency": "USD",
                    },
                    "income_statement": {},
                    "balance_sheet": {},
                    "cash_flow": {},
                },
            },
        )
        # Either validation fail-closed or honest unavailable — never fake success numbers.
        if resp.status_code == 200:
            payload = resp.json().get("payload") or {}
            text = json.dumps(payload).lower()
            hard_fail(
                "9999" not in text and '"buy"' not in text,
                DATA_UNAVAILABLE_NOT_HONESTLY_HANDLED,
                "suspicious fabricated conclusion in unavailable path",
            )
            stages = payload.get("stage_summaries") or []
            valuation = next(
                (s for s in stages if s.get("stage") == "valuation"), None
            )
            if valuation is not None:
                hard_fail(
                    valuation.get("status")
                    in {"succeeded", "degraded", "unavailable"},
                    DATA_UNAVAILABLE_NOT_HONESTLY_HANDLED,
                    f"valuation status={valuation.get('status')}",
                )
        else:
            hard_fail(
                resp.status_code in {400, 422},
                DATA_UNAVAILABLE_NOT_HONESTLY_HANDLED,
                f"unexpected status={resp.status_code}",
            )


class TestReleaseIdentityAndEvidence:
    def test_release_identity_rc_not_stale_ga(self) -> None:
        hard_fail(
            RELEASE_IDENTITY.get("epic") == "EPS-003",
            RELEASE_IDENTITY_STALE,
            f"epic={RELEASE_IDENTITY.get('epic')}",
        )
        hard_fail(
            RELEASE_IDENTITY.get("product_version") == "2.0.0-rc.1",
            RELEASE_IDENTITY_STALE,
            f"version={RELEASE_IDENTITY.get('product_version')}",
        )
        hard_fail(
            RELEASE_IDENTITY.get("channel") == "rc",
            RELEASE_IDENTITY_STALE,
            f"channel={RELEASE_IDENTITY.get('channel')}",
        )
        hard_fail(
            RELEASE_IDENTITY.get("decision") == "RELEASE_CANDIDATE",
            RELEASE_IDENTITY_STALE,
            f"decision={RELEASE_IDENTITY.get('decision')}",
        )

    def test_fixture_evidence_class_never_live_vendor(self) -> None:
        hard_fail(
            P109_EVIDENCE_CLASS == "test_fixture",
            "FIXTURE_MISCLASSIFIED_AS_LIVE",
            f"evidence_class={P109_EVIDENCE_CLASS}",
        )

    def test_write_p110_evidence_artifact(self, client: TestClient) -> None:
        """Positive control + evidence for the release gate summary."""
        register_user(
            client,
            user_id="p110-ok",
            username="p110ok",
            roles=["administrator"],
        )
        headers = bearer_headers(client, username="p110ok")
        quote = client.get(
            f"/api/v1/market/quote?symbol={P109_FIXTURE_TICKER}",
            headers=headers,
        )
        hard_fail(quote.status_code == 200, DATA_UNAVAILABLE_NOT_HONESTLY_HANDLED)
        q = quote.json()
        hard_fail(q.get("available") is True, DATA_UNAVAILABLE_NOT_HONESTLY_HANDLED)
        price = q["fields"]["current_price"]

        stmts = client.get(
            f"/api/v1/fundamentals/statements?symbol={P109_FIXTURE_TICKER}&limit=1",
            headers=headers,
        )
        hard_fail(stmts.status_code == 200, DATA_UNAVAILABLE_NOT_HONESTLY_HANDLED)
        period = stmts.json()["periods"][0]
        analyse = client.post(
            "/api/v1/analyse",
            headers=headers,
            json={
                "ticker": P109_FIXTURE_TICKER,
                "company": "DSP Fixture Corp",
                "current_market_price": float(price),
                "financial_statements": {
                    "period": {
                        "period_type": period["period_type"],
                        "period_end": period["period_end"],
                        "fiscal_year": period.get("fiscal_year"),
                        "currency": period.get("reporting_currency") or "USD",
                    },
                    "income_statement": dict(period.get("income_statement") or {}),
                    "balance_sheet": dict(period.get("balance_sheet") or {}),
                    "cash_flow": dict(period.get("cash_flow") or {}),
                    "statement_metadata": {
                        "source": "authenticated_fundamentals",
                        "evidence_class": P109_EVIDENCE_CLASS,
                        "unit_scale": period.get("unit_scale") or "actual",
                        "statement_basis": period.get("statement_basis")
                        or "consolidated",
                    },
                },
            },
        )
        hard_fail(
            analyse.status_code == 200,
            DATA_UNAVAILABLE_NOT_HONESTLY_HANDLED,
            analyse.text[:500],
        )
        body = analyse.json()
        hard_fail(body.get("ok") is True, DATA_UNAVAILABLE_NOT_HONESTLY_HANDLED)
        hard_fail(bool(body.get("analysis_id")), DATA_UNAVAILABLE_NOT_HONESTLY_HANDLED)
        authority = (body.get("payload") or {}).get("buffett_authority") or {}
        hard_fail(
            authority.get("client_overrides_accepted") is False
            or "overall_score" in authority
            or "overall_status" in authority,
            CLIENT_BUFFETT_OVERRIDE_DETECTED,
            f"buffett_authority={authority}",
        )

        _write_evidence(
            {
                "ok": True,
                "gate": "P1-10",
                "g2_claim": False,
                "evidence_class": P109_EVIDENCE_CLASS,
                "analysis_id": body.get("analysis_id"),
                "release_identity": dict(RELEASE_IDENTITY),
                "codes_enforced": [
                    PRODUCTION_NULL_FALLBACK_DETECTED,
                    PRODUCTION_MEMORY_FALLBACK_DETECTED,
                    CLIENT_IDENTITY_SPOOF_ACCEPTED,
                    CLIENT_VALUATION_OVERRIDE_DETECTED,
                    CLIENT_BUFFETT_OVERRIDE_DETECTED,
                    PROVENANCE_FORGERY_DETECTED,
                    DATA_UNAVAILABLE_NOT_HONESTLY_HANDLED,
                    RELEASE_IDENTITY_STALE,
                ],
            }
        )
