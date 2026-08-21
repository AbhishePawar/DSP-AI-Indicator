"""Phase 1 — client auth boot independent of investment connector credentials.

Proves:
A) Production create_app succeeds without investment credentials
B) Auth endpoints and readiness probes remain reachable in that condition
C) Investment adapter construction still fails closed (P1-03)
D) Valid Upstox configuration still selects Upstox adapters
E) P1-03 assert helper remains usable for investment/ops paths
F) Authentication modules do not import Upstox/investment adapters
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from data_engine.connector_framework.production_profile import (
    assert_production_investment_connectors_configured,
)
from data_engine.exceptions import ConnectorConfigurationError
from data_engine.financial_statement.adapters import build_default_statement_adapter_from_env
from data_engine.market_quote.adapters import build_default_quote_adapter_from_env
from dsp_platform import DSPPlatform, PlatformBuilder, PlatformConfiguration

_UPSTOX_TOKEN = "phase1-test-upstox-analytics-token-not-real"


@pytest.fixture()
def platform() -> DSPPlatform:
    return (
        PlatformBuilder()
        .with_configuration(PlatformConfiguration(require_analysis_service=False))
        .auto_ready(True)
        .build()
    )


def _strip_investment_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DSP_ENVIRONMENT", "production")
    monkeypatch.setenv("DSP_JWT_SECRET", "unit-test-production-secret-not-default")
    monkeypatch.setenv("DSP_AUTH_JWT_SECRET", "unit-test-production-secret-not-default")
    # Isolate investment-decoupling from Postgres/region runtime gates.
    monkeypatch.setenv("DSP_INFRA_OFFLINE", "1")
    monkeypatch.setattr(
        "api_platform.api.durable_product_stores.require_durable_product_database",
        lambda database: None,
    )
    for key in (
        "DSP_INVESTMENT_DATA_PROVIDER",
        "DSP_UPSTOX_ANALYTICS_TOKEN",
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


# --- TEST A -----------------------------------------------------------------


def test_a_production_api_boots_without_investment_config(
    monkeypatch: pytest.MonkeyPatch, platform: DSPPlatform
) -> None:
    from api_platform import create_app

    _strip_investment_credentials(monkeypatch)
    app = create_app(platform=platform, enable_security=False)
    assert app.title


# --- TEST B -----------------------------------------------------------------


def test_b_auth_endpoints_accessible_without_investment_config(
    monkeypatch: pytest.MonkeyPatch, platform: DSPPlatform
) -> None:
    from api_platform import create_app

    _strip_investment_credentials(monkeypatch)
    client = TestClient(create_app(platform=platform, enable_security=False))

    session = client.get("/api/v1/auth/session")
    assert session.status_code == 200

    openapi = client.get("/openapi.json")
    assert openapi.status_code == 200
    paths = openapi.json().get("paths", {})
    assert any("/auth/login" in path for path in paths)
    assert any("/auth/enterprise" in path or "/auth/rbac" in path for path in paths)


def test_b_ready_probe_accepts_traffic_without_upstox_token(
    monkeypatch: pytest.MonkeyPatch, platform: DSPPlatform
) -> None:
    """Cloud Run / Docker HEALTHCHECK must not require Upstox for API readiness."""
    from api_platform import create_app

    _strip_investment_credentials(monkeypatch)
    monkeypatch.setenv("DSP_INVESTMENT_DATA_PROVIDER", "upstox")
    client = TestClient(create_app(platform=platform, enable_security=False))

    ready = client.get("/api/v1/health/ready")
    assert ready.status_code == 200
    body = ready.json()
    assert body.get("ready") is True
    assert body.get("platform_ready") is True
    checks = {c["name"]: c for c in body.get("checks", [])}
    investment = checks.get("investment_data_provider")
    assert investment is not None
    assert investment["status"] == "fail"
    assert "DSP_UPSTOX_ANALYTICS_TOKEN" in investment["message"]


# --- TEST C -----------------------------------------------------------------


def test_c_investment_operations_fail_closed_without_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _strip_investment_credentials(monkeypatch)
    with pytest.raises(ConnectorConfigurationError, match="P1-03"):
        build_default_quote_adapter_from_env()
    with pytest.raises(ConnectorConfigurationError, match="P1-03|financial_statement"):
        build_default_statement_adapter_from_env()


def test_c_upstox_selected_without_token_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _strip_investment_credentials(monkeypatch)
    monkeypatch.setenv("DSP_INVESTMENT_DATA_PROVIDER", "upstox")
    with pytest.raises(ConnectorConfigurationError, match="DSP_UPSTOX_ANALYTICS_TOKEN"):
        build_default_quote_adapter_from_env()


# --- TEST D -----------------------------------------------------------------


def test_d_valid_upstox_configuration_still_works(
    monkeypatch: pytest.MonkeyPatch, platform: DSPPlatform
) -> None:
    from api_platform import create_app

    monkeypatch.setenv("DSP_ENVIRONMENT", "production")
    monkeypatch.setenv("DSP_JWT_SECRET", "unit-test-production-secret-not-default")
    monkeypatch.setenv("DSP_AUTH_JWT_SECRET", "unit-test-production-secret-not-default")
    monkeypatch.setenv("DSP_INFRA_OFFLINE", "1")
    monkeypatch.setattr(
        "api_platform.api.durable_product_stores.require_durable_product_database",
        lambda database: None,
    )
    monkeypatch.setenv("DSP_INVESTMENT_DATA_PROVIDER", "upstox")
    monkeypatch.setenv("DSP_UPSTOX_ANALYTICS_TOKEN", _UPSTOX_TOKEN)

    app = create_app(platform=platform, enable_security=False)
    assert app is not None

    quote = build_default_quote_adapter_from_env()
    statements = build_default_statement_adapter_from_env()
    assert type(quote).__name__ == "UpstoxQuoteAdapter"
    assert type(statements).__name__ == "UpstoxStatementAdapter"


# --- TEST E -----------------------------------------------------------------


def test_e_p103_assert_helper_still_enforces_investment_boundary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _strip_investment_credentials(monkeypatch)
    with pytest.raises(ConnectorConfigurationError, match="P1-03"):
        assert_production_investment_connectors_configured()

    monkeypatch.setenv("DSP_INVESTMENT_DATA_PROVIDER", "upstox")
    monkeypatch.setenv("DSP_UPSTOX_ANALYTICS_TOKEN", _UPSTOX_TOKEN)
    selected = assert_production_investment_connectors_configured()
    assert selected["market_quote"] == "UpstoxQuoteAdapter"
    assert selected["financial_statement"] == "UpstoxStatementAdapter"


# --- TEST F -----------------------------------------------------------------


_FORBIDDEN_IMPORT_ROOTS = (
    "data_engine.upstox",
    "data_engine.investment_data_provider",
    "data_engine.fmp_investment",
    "data_engine.market_quote",
    "data_engine.financial_statement",
    "data_engine.connector_framework.production_profile",
)


def _auth_source_roots() -> list[Path]:
    repo = Path(__file__).resolve().parents[3]
    return [
        repo / "packages" / "auth" / "src" / "auth",
        repo
        / "packages"
        / "api_platform"
        / "src"
        / "api_platform"
        / "api"
        / "routers"
        / "auth.py",
        repo
        / "packages"
        / "api_platform"
        / "src"
        / "api_platform"
        / "api"
        / "routers"
        / "institutional_auth.py",
        repo
        / "packages"
        / "api_platform"
        / "src"
        / "api_platform"
        / "api"
        / "routers"
        / "enterprise_auth_platform.py",
        repo / "packages" / "dsp_platform" / "src" / "dsp_platform" / "auth_facade.py",
    ]


def _iter_py_files(root: Path) -> list[Path]:
    if root.is_file():
        return [root]
    return sorted(root.rglob("*.py"))


def _imported_modules(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.append(node.module)
    return names


def test_f_auth_modules_do_not_import_upstox_or_investment_adapters() -> None:
    violations: list[str] = []
    for root in _auth_source_roots():
        if not root.exists():
            violations.append(f"missing auth path: {root}")
            continue
        for path in _iter_py_files(root):
            for mod in _imported_modules(path):
                if any(
                    mod == forbidden or mod.startswith(forbidden + ".")
                    for forbidden in _FORBIDDEN_IMPORT_ROOTS
                ):
                    violations.append(f"{path}: imports {mod}")
    assert violations == []
