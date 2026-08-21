"""Strict auth vs investment credential boundary (A–G).

Proves DSP user authentication never depends on Upstox/investment credentials,
and Resend auth email does not require SMTP password.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from auth.credential_boundary import (
    AUTH_JWT_SECRET_ENV,
    RESEND_API_KEY_ENV,
    RESEND_FROM_ADDRESS_ENV,
)
from auth.email_delivery import ResendEmailAdapter, build_email_provider
from auth.enterprise_platform import (
    EnterpriseAuthPlatform,
    reset_enterprise_auth_platform_for_tests,
)
from auth.exceptions import ValidationError
from auth.service import AuthService, reset_auth_service_for_tests
from data_engine.exceptions import ConnectorConfigurationError
from data_engine.market_quote.adapters import build_default_quote_adapter_from_env
from dsp_platform import DSPPlatform, PlatformBuilder, PlatformConfiguration

_AUTH_JWT = "unit-test-auth-jwt-secret-not-default"
_RESEND_KEY = "re_test_boundary_key_not_real"
_UPSTOX_TOKEN = "phase-boundary-upstox-token-not-real"

_FORBIDDEN_AUTH_ENV_READS = (
    "DSP_UPSTOX_ANALYTICS_TOKEN",
    "DSP_UPSTOX_CLIENT_SECRET",
    "DSP_UPSTOX_ACCESS_TOKEN",
    "DSP_INVESTMENT_DATA_PROVIDER",
    "DSP_INVESTMENT_FMP_API_KEY",
)


@pytest.fixture()
def platform() -> DSPPlatform:
    return (
        PlatformBuilder()
        .with_configuration(PlatformConfiguration(require_analysis_service=False))
        .auto_ready(True)
        .build()
    )


def _strip_investment(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in (
        "DSP_INVESTMENT_DATA_PROVIDER",
        "DSP_UPSTOX_ANALYTICS_TOKEN",
        "DSP_UPSTOX_CLIENT_SECRET",
        "DSP_UPSTOX_ACCESS_TOKEN",
        "DSP_FMP_API_KEY",
        "DSP_INVESTMENT_FMP_API_KEY",
        "DSP_MARKET_QUOTE_API_KEY",
        "DSP_MARKET_QUOTE_BASE_URL",
        "DSP_MARKET_QUOTE_MEMORY",
        "DSP_FINANCIAL_STATEMENT_API_KEY",
        "DSP_FINANCIAL_STATEMENT_BASE_URL",
        "DSP_FINANCIAL_STATEMENT_MEMORY",
    ):
        monkeypatch.delenv(key, raising=False)


def _auth_boot_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DSP_ENVIRONMENT", "production")
    monkeypatch.setenv(AUTH_JWT_SECRET_ENV, _AUTH_JWT)
    monkeypatch.setenv(RESEND_API_KEY_ENV, _RESEND_KEY)
    monkeypatch.setenv(RESEND_FROM_ADDRESS_ENV, "auth@example.com")
    monkeypatch.setenv("DSP_INFRA_OFFLINE", "1")
    monkeypatch.delenv("DSP_SMTP_PASSWORD", raising=False)
    monkeypatch.delenv("DSP_SMTP_HOST", raising=False)
    monkeypatch.delenv("DSP_SMTP_USERNAME", raising=False)
    monkeypatch.delenv("DSP_SMTP_FROM_ADDRESS", raising=False)
    monkeypatch.delenv("DSP_JWT_SECRET", raising=False)
    monkeypatch.setattr(
        "api_platform.api.durable_product_stores.require_durable_product_database",
        lambda database: None,
    )
    _strip_investment(monkeypatch)


# --- A -------------------------------------------------------------------


def test_a_auth_boot_with_resend_without_upstox(
    monkeypatch: pytest.MonkeyPatch, platform: DSPPlatform
) -> None:
    from api_platform import create_app

    _auth_boot_env(monkeypatch)
    monkeypatch.setenv("DSP_INVESTMENT_DATA_PROVIDER", "upstox")
    app = create_app(platform=platform, enable_security=False)
    assert app.title


# --- B -------------------------------------------------------------------


def test_b_password_otp_email_auth_init_without_upstox(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from auth import (
        RoleRegistry,
        reset_role_registry_for_tests,
    )
    from auth.email_delivery import ConsoleEmailAdapter
    from auth.oauth_providers import OAuthProviderRegistry
    from auth.otp import OtpService
    from auth.sms import DevSmsAdapter
    from persistence import (
        InMemoryStorageProvider,
        PersistenceService,
        RepositoryRegistry,
        reset_persistence_service_for_tests,
        reset_repository_registry_for_tests,
    )

    _auth_boot_env(monkeypatch)
    monkeypatch.setenv("DSP_ENVIRONMENT", "development")
    monkeypatch.setenv("DSP_PASSWORD_HASHER", "pbkdf2")
    monkeypatch.setenv("DSP_INVESTMENT_DATA_PROVIDER", "upstox")
    monkeypatch.delenv("DSP_UPSTOX_ANALYTICS_TOKEN", raising=False)

    store = InMemoryStorageProvider()
    registry = RepositoryRegistry(storage=store)
    reset_repository_registry_for_tests(registry)
    ps = PersistenceService(registry)
    reset_persistence_service_for_tests(ps)
    reset_role_registry_for_tests(RoleRegistry())
    auth = AuthService(ps, jwt_secret=_AUTH_JWT)
    reset_auth_service_for_tests(auth)
    email = ConsoleEmailAdapter()
    otp = OtpService(DevSmsAdapter(), email=email)
    ent = EnterpriseAuthPlatform(
        auth,
        oauth=OAuthProviderRegistry({}),
        otp=otp,
        email=email,
    )
    reset_enterprise_auth_platform_for_tests(ent)

    reg = ent.register_email(
        name="Boundary User",
        email="boundary@example.com",
        password="StrongPass1!",
        confirm_password="StrongPass1!",
        username="boundary_user",
    )
    ent.verify_email(reg["verification_token"])
    session = ent.login_password(
        identifier="boundary@example.com",
        password="StrongPass1!",
    )
    assert session["user"]["email"] == "boundary@example.com"

    with pytest.raises(ValidationError, match="Email OTP is no longer supported"):
        ent.request_login_otp("boundary@example.com")

    mobile_req = ent.request_login_otp("+919876543210")
    assert mobile_req.get("channel") == "mobile"
    assert mobile_req.get("challenge_id")

    discovery = ent.provider_status()
    assert "providers" in discovery
    features = ent.schema()["features"]
    assert features["email_otp"] is False
    assert features["mobile_otp"] is True
    assert features["google_oauth"] is True

    reset_enterprise_auth_platform_for_tests(None)
    reset_auth_service_for_tests(None)
    reset_role_registry_for_tests(None)
    reset_persistence_service_for_tests(None)
    reset_repository_registry_for_tests(None)


# --- C -------------------------------------------------------------------


def test_c_missing_upstox_still_fail_closed_for_investment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _auth_boot_env(monkeypatch)
    monkeypatch.setenv("DSP_INVESTMENT_DATA_PROVIDER", "upstox")
    with pytest.raises(ConnectorConfigurationError, match="DSP_UPSTOX_ANALYTICS_TOKEN"):
        build_default_quote_adapter_from_env()


# --- D -------------------------------------------------------------------


def test_d_health_ready_while_investment_limitation_visible(
    monkeypatch: pytest.MonkeyPatch, platform: DSPPlatform
) -> None:
    from api_platform import create_app

    _auth_boot_env(monkeypatch)
    monkeypatch.setenv("DSP_INVESTMENT_DATA_PROVIDER", "upstox")
    client = TestClient(create_app(platform=platform, enable_security=False))
    ready = client.get("/api/v1/health/ready")
    assert ready.status_code == 200
    body = ready.json()
    assert body.get("ready") is True
    assert body.get("platform_ready") is True
    checks = {c["name"]: c for c in body.get("checks", [])}
    investment = checks["investment_data_provider"]
    assert investment["status"] == "fail"
    assert "investment_capability" in investment["message"]
    assert "DSP_UPSTOX_ANALYTICS_TOKEN" in investment["message"]
    assert "does not block auth" in investment["message"]


# --- E -------------------------------------------------------------------


def test_e_resend_mode_does_not_require_smtp_password(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(RESEND_API_KEY_ENV, _RESEND_KEY)
    monkeypatch.setenv(RESEND_FROM_ADDRESS_ENV, "auth@example.com")
    monkeypatch.delenv("DSP_SMTP_PASSWORD", raising=False)
    monkeypatch.delenv("DSP_SMTP_HOST", raising=False)
    monkeypatch.delenv("DSP_EMAIL_PROVIDER", raising=False)

    provider = build_email_provider()
    assert isinstance(provider, ResendEmailAdapter)
    assert provider.provider_name() == "resend"
    assert provider.is_available() is True

    class _Resp:
        def read(self) -> bytes:
            return b'{"id":"email_test"}'

        def __enter__(self) -> "_Resp":
            return self

        def __exit__(self, *args: object) -> None:
            return None

    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda *args, **kwargs: _Resp(),
    )
    result = provider.send(
        to="user@example.com",
        subject="magic",
        body="TOKEN=abc",
        purpose="magic_link",
    )
    assert result.ok is True
    assert result.provider == "resend"


# --- F -------------------------------------------------------------------


def test_f_auth_tests_and_sources_do_not_init_upstox_investment() -> None:
    auth_src = Path(__file__).resolve().parents[1] / "src" / "auth"
    offenders: list[str] = []
    for path in auth_src.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        tree = ast.parse(text, filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            else:
                continue
            for name in names:
                lowered = (name or "").lower()
                if any(
                    tok in lowered
                    for tok in (
                        "upstox",
                        "investment_data_provider",
                        "market_quote",
                        "data_engine.connector_framework.production_profile",
                    )
                ):
                    offenders.append(f"{path.name}:import {name}")
        for forbidden in _FORBIDDEN_AUTH_ENV_READS:
            if f'"{forbidden}"' in text or f"'{forbidden}'" in text:
                # credential_boundary.py documents investment names intentionally.
                if path.name == "credential_boundary.py":
                    continue
                offenders.append(f"{path.name}:env {forbidden}")
    assert offenders == []


def test_f_upstox_still_selected_when_token_present(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """G-adjacent: investment path intact with proper Upstox credentials."""
    monkeypatch.setenv("DSP_ENVIRONMENT", "production")
    monkeypatch.setenv("DSP_INVESTMENT_DATA_PROVIDER", "upstox")
    monkeypatch.setenv("DSP_UPSTOX_ANALYTICS_TOKEN", _UPSTOX_TOKEN)
    quote = build_default_quote_adapter_from_env()
    assert type(quote).__name__ == "UpstoxQuoteAdapter"
