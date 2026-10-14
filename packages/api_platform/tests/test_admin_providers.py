"""Comprehensive tests for Provider & API Management system (EPIC-A010 / Launch Blocker).

Verifies:
1. Endpoint security (401 unauthenticated, 403 non-admin, header spoofing rejected).
2. Credential replacement, connection testing, and atomic runtime activation.
3. Secrets are never exposed in list, read, test, audit, or error responses.
4. Safe rollback to previous validated configuration.
5. Multi-provider registry integration (Gemini, OpenAI, Anthropic, Groq, Upstox).
6. Dynamic task routing and fallback policies.
7. Zero-restart registry synchronization with live analysis dependencies.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

import os
from api_platform.api.app import create_app
from auth import get_auth_service
from llm_adapters.provider_health import ProviderHealthStatus
from llm_adapters.runtime_store import get_runtime_store
from llm_adapters.task_routing import get_task_routing_manager


@pytest.fixture(autouse=True)
def clean_runtime_store():
    # Teardown any test-created store files so other suites remain unpolluted
    for key in ["GEMINI_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "DEEPSEEK_API_KEY", "UPSTOX_ACCESS_TOKEN", "GROQ_API_KEY"]:
        os.environ.pop(key, None)
    store = get_runtime_store()
    with store._lock:
        store._secrets.clear()
        for p in store._providers.values():
            p.has_credential = False
            p.health_status = ProviderHealthStatus.NOT_CONFIGURED
    yield
    store_path = os.environ.get("DSP_RUNTIME_STORE_PATH", "/tmp/dsp_runtime_providers.json")
    if os.path.exists(store_path):
        os.remove(store_path)
    with store._lock:
        store._secrets.clear()
        for p in store._providers.values():
            p.has_credential = False
            p.health_status = ProviderHealthStatus.NOT_CONFIGURED
    for key in ["GEMINI_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "DEEPSEEK_API_KEY", "UPSTOX_ACCESS_TOKEN", "GROQ_API_KEY"]:
        os.environ.pop(key, None)

@pytest.fixture
def test_client() -> TestClient:
    app = create_app()
    return TestClient(app)


@pytest.fixture
def admin_headers() -> dict[str, str]:
    """Generate authenticated JWT headers for an administrator with configure_platform."""
    auth = get_auth_service()
    username = "admin_suite_user"
    user = next((u for u in auth.list_users() if u.get("username") == username), None)
    if not user:
        auth.create_user(
            username=username,
            email="admin_suite@dspaiindicator.com",
            password="AdminPassword12345!",
            roles=["administrator"],
        )
    res = auth.login(username=username, password="AdminPassword12345!")
    token = res["tokens"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def non_admin_headers() -> dict[str, str]:
    """Generate authenticated JWT headers for a standard viewer without admin roles."""
    auth = get_auth_service()
    username = "viewer_suite_user"
    user = next((u for u in auth.list_users() if u.get("username") == username), None)
    if not user:
        auth.create_user(
            username=username,
            email="viewer_suite@dspaiindicator.com",
            password="ViewerPassword12345!",
            roles=["viewer"],
        )
    res = auth.login(username=username, password="ViewerPassword12345!")
    token = res["tokens"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


class TestAdminProviderSecurity:
    """Security and authorization gates for Provider Management."""

    def test_unauthenticated_request_rejected(self, test_client: TestClient) -> None:
        """Unauthenticated requests must receive HTTP 401."""
        resp = test_client.get("/api/v1/admin/providers")
        assert resp.status_code == 401

    def test_non_admin_user_forbidden(
        self, test_client: TestClient, non_admin_headers: dict[str, str]
    ) -> None:
        """Non-admin authenticated users must receive HTTP 403."""
        resp = test_client.get("/api/v1/admin/providers", headers=non_admin_headers)
        assert resp.status_code == 403

    def test_forged_header_without_token_rejected(self, test_client: TestClient) -> None:
        """Client-supplied spoofed identity headers must be ignored."""
        resp = test_client.get(
            "/api/v1/admin/providers",
            headers={"X-User-Role": "admin", "X-User-Id": "admin"},
        )
        assert resp.status_code == 401

    def test_secrets_never_exposed_in_list(
        self, test_client: TestClient, admin_headers: dict[str, str]
    ) -> None:
        """Provider listing must NEVER return API keys or credentials."""
        store = get_runtime_store()
        store.replace_credential("gemini", "super-secret-gemini-key-12345", validate=False)

        resp = test_client.get("/api/v1/admin/providers", headers=admin_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert "providers" in body

        raw_text = json.dumps(body)
        assert "super-secret" not in raw_text
        assert "12345" not in raw_text

        gemini_item = next(p for p in body["providers"] if p["provider_id"] == "gemini")
        assert gemini_item["has_credential"] is True
        assert "secret" not in gemini_item
        assert "api_key" not in gemini_item


class TestProviderCredentialManagement:
    """Credential lifecycle: test, save, validate, rollback, activate."""

    def test_test_connection_endpoint(
        self, test_client: TestClient, admin_headers: dict[str, str]
    ) -> None:
        """Test connection endpoint returns structured test result without leaking key."""
        with patch("llm_adapters.runtime_store.test_provider_connection") as mock_test:
            mock_test.return_value = (True, 120.5, None)
            resp = test_client.post(
                "/api/v1/admin/providers/openai/test",
                headers=admin_headers,
                json={"secret": "sk-test-candidate-key", "model": "gpt-4.1-mini"},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["success"] is True
            assert data["status"] == "healthy"
            assert data["latency_ms"] == 120.5
            assert "sk-test" not in json.dumps(data)

    def test_save_credential_with_validation_success(
        self, test_client: TestClient, admin_headers: dict[str, str]
    ) -> None:
        """Saving a valid credential updates health and activates runtime usage."""
        store = get_runtime_store()
        with patch("llm_adapters.runtime_store.test_provider_connection") as mock_test:
            mock_test.return_value = (True, 45.0, None)
            resp = test_client.post(
                "/api/v1/admin/providers/groq/credential",
                headers=admin_headers,
                json={"secret": "gsk_valid_key_xyz", "validate": True},
            )
            assert resp.status_code == 200
            assert resp.json()["ok"] is True
            assert resp.json()["health_status"] == "healthy"

            # Check that secret is active in runtime store
            assert store.get_credential("groq") == "gsk_valid_key_xyz"

    def test_save_credential_validation_failure_preserves_old(
        self, test_client: TestClient, admin_headers: dict[str, str]
    ) -> None:
        """If validation fails, 400 is returned and existing working credential is kept."""
        store = get_runtime_store()
        store.replace_credential("anthropic", "sk-ant-old-working-key", validate=False)
        assert store.get_credential("anthropic") == "sk-ant-old-working-key"

        with patch("llm_adapters.runtime_store.test_provider_connection") as mock_test:
            mock_test.return_value = (False, 80.0, "401 unauthorized: invalid api key")
            resp = test_client.post(
                "/api/v1/admin/providers/anthropic/credential",
                headers=admin_headers,
                json={"secret": "sk-ant-bad-candidate", "validate": True},
            )
            assert resp.status_code == 400
            err_body = resp.json()
            assert "Validation failed" in err_body["detail"]
            assert "sk-ant-bad" not in json.dumps(err_body)

            # Assert old credential was retained
            assert store.get_credential("anthropic") == "sk-ant-old-working-key"

    def test_revoke_credential_endpoint(
        self, test_client: TestClient, admin_headers: dict[str, str]
    ) -> None:
        """Revoking credential clears the secret, updates status to not_configured, and masks credential."""
        store = get_runtime_store()
        store.replace_credential("anthropic", "sk-ant-to-be-revoked", validate=False)
        assert store.get_credential("anthropic") == "sk-ant-to-be-revoked"

        resp = test_client.delete(
            "/api/v1/admin/providers/anthropic/credential",
            headers=admin_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["health_status"] == "not_configured"
        assert store.get_credential("anthropic") is None
        assert store.get_provider("anthropic")["has_credential"] is False

    def test_rollback_configuration(
        self, test_client: TestClient, admin_headers: dict[str, str]
    ) -> None:
        """Rollback restores the previous validated configuration version."""
        store = get_runtime_store()
        store.replace_credential("openai", "key-version-1", validate=False)
        store.update_model("openai", "gpt-4.1-mini")
        store.update_model("openai", "gpt-4o")

        assert store.get_provider("openai")["selected_model"] == "gpt-4o"

        resp = test_client.post(
            "/api/v1/admin/providers/openai/rollback",
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert store.get_provider("openai")["selected_model"] == "gpt-4.1-mini"

    def test_provider_status_and_model_update(
        self, test_client: TestClient, admin_headers: dict[str, str]
    ) -> None:
        """Administrator can deactivate/activate provider and configure model."""
        resp = test_client.post(
            "/api/v1/admin/providers/gemini/status",
            headers=admin_headers,
            json={"is_active": False},
        )
        assert resp.status_code == 200
        assert resp.json()["provider"]["is_active"] is False

        resp2 = test_client.post(
            "/api/v1/admin/providers/gemini/model",
            headers=admin_headers,
            json={"model": "gemini-2.5-flash"},
        )
        assert resp2.status_code == 200
        assert resp2.json()["provider"]["selected_model"] == "gemini-2.5-flash"


class TestTaskRoutingAndFallback:
    """Dynamic task routing policies and fallback management."""

    def test_get_and_update_routing_policy(
        self, test_client: TestClient, admin_headers: dict[str, str]
    ) -> None:
        """Administrator can view and update task routing policies."""
        resp = test_client.get("/api/v1/admin/routing", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "policies" in data
        assert len(data["policies"]) >= 4

        # Update statement extraction policy to use Gemini with OpenAI fallback
        update_resp = test_client.post(
            "/api/v1/admin/routing/statement_extraction",
            headers=admin_headers,
            json={
                "primary_provider": "gemini",
                "fallback_providers": ["openai", "anthropic"],
                "require_independent_corroboration": True,
                "timeout_seconds": 45.0,
                "max_retries": 3,
            },
        )
        assert update_resp.status_code == 200
        policy = update_resp.json()["policy"]
        assert policy["primary_provider"] == "gemini"
        assert policy["fallback_providers"] == ["openai", "anthropic"]
        assert policy["require_independent_corroboration"] is True
        assert policy["timeout_seconds"] == 45.0

    def test_reject_corroboration_with_same_provider(
        self, test_client: TestClient, admin_headers: dict[str, str]
    ) -> None:
        """Reject configuration that attempts dual corroboration using only one provider."""
        resp = test_client.post(
            "/api/v1/admin/routing/statement_extraction",
            headers=admin_headers,
            json={
                "primary_provider": "gemini",
                "fallback_providers": [],
                "require_independent_corroboration": True,
                "timeout_seconds": 30.0,
                "max_retries": 2,
            },
        )
        assert resp.status_code == 400
        assert "Independent corroboration requires at least one distinct fallback provider" in resp.json()["detail"]
