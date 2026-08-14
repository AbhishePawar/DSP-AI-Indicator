"""Production PostgreSQL honesty — driver shipping + explicit failure.

Covers the Cloud Run regression where a configured DSN silently degraded to
InMemoryDatabasePort and startup reported an opaque adapter error.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

from production_platform.adapters.postgres import (
    build_postgres,
    redact_dsn_secrets,
    try_build_postgres,
)
from production_platform.production.exceptions import (
    ConfigurationError,
    DatabaseUnavailableError,
    ProviderError,
    StartupError,
)
from production_platform.production.infrastructure import InfrastructureBundle
from production_platform.production.runtime import build_runtime_infrastructure

_REPO_ROOT = Path(__file__).resolve().parents[3]

# Unroutable port so connection attempts fail fast when psycopg is installed.
_DEAD_DSN = "postgresql://dsp:secret-pass@127.0.0.1:1/dsp"
_PRODUCTION_ENV = {
    "DSP_ENVIRONMENT": "production",
    "DSP_REGION": "asia-south1",
    "DSP_DATABASE_URL": _DEAD_DSN,
    "DSP_DATABASE_TIMEOUT": "0.05",
}


class TestPsycopgInstallPath:
    """The API image installs ``.[api]``, so the driver must live there."""

    def test_root_api_extra_declares_psycopg(self) -> None:
        pyproject = tomllib.loads(
            (_REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
        )
        api_extra = pyproject["project"]["optional-dependencies"]["api"]
        assert any(dep.startswith("psycopg") for dep in api_extra), (
            "root [api] extra must ship psycopg; the production API image is "
            "built with pip install '.[api]'"
        )

    def test_backend_image_installs_api_extra(self) -> None:
        dockerfile = (_REPO_ROOT / "docker" / "backend" / "Dockerfile").read_text(
            encoding="utf-8"
        )
        assert '".[api]"' in dockerfile


class TestProductionFailsExplicitly:
    def test_production_dsn_configured_but_postgres_unavailable(self) -> None:
        with pytest.raises(DatabaseUnavailableError) as excinfo:
            build_runtime_infrastructure(
                environ=dict(_PRODUCTION_ENV), strict=True, require_database=True
            )
        assert "unavailable" in str(excinfo.value)

    def test_production_failure_states_a_reason(self) -> None:
        """Startup must explain why (driver missing / connect failed)."""
        with pytest.raises(DatabaseUnavailableError) as excinfo:
            build_runtime_infrastructure(
                environ=dict(_PRODUCTION_ENV), strict=True, require_database=True
            )
        message = str(excinfo.value)
        assert "psycopg" in message or "connect failed" in message

    def test_production_failure_never_leaks_password(self) -> None:
        with pytest.raises((DatabaseUnavailableError, StartupError)) as excinfo:
            build_runtime_infrastructure(
                environ=dict(_PRODUCTION_ENV), strict=True, require_database=True
            )
        assert "secret-pass" not in str(excinfo.value)

    def test_production_composition_does_not_select_in_memory(self) -> None:
        """No InMemoryDatabasePort may be returned for a production profile."""
        with pytest.raises((ProviderError, ConfigurationError, ImportError)):
            InfrastructureBundle.from_environment(environ=dict(_PRODUCTION_ENV))


class TestDevelopmentAndOfflineUnchanged:
    def test_development_still_falls_back_with_a_note(self) -> None:
        infra = InfrastructureBundle.from_environment(
            environ={
                "DSP_ENVIRONMENT": "development",
                "DSP_DATABASE_URL": _DEAD_DSN,
                "DSP_DATABASE_TIMEOUT": "0.05",
            }
        )
        assert infra.diagnostics.database_adapter == "InMemoryDatabasePort"
        assert infra.database.ping() is True
        assert any("PostgreSQL unavailable" in note for note in infra.notes)

    def test_development_note_never_leaks_password(self) -> None:
        infra = InfrastructureBundle.from_environment(
            environ={
                "DSP_ENVIRONMENT": "development",
                "DSP_DATABASE_URL": _DEAD_DSN,
                "DSP_DATABASE_TIMEOUT": "0.05",
            }
        )
        assert all("secret-pass" not in note for note in infra.notes)

    def test_force_offline_unchanged(self) -> None:
        infra = build_runtime_infrastructure(
            environ={"DSP_ENVIRONMENT": "development"}, force_offline=True
        )
        assert infra.diagnostics.database_adapter == "InMemoryDatabasePort"
        assert infra.database.ping() is True


class TestAdapterBuilders:
    def test_try_build_postgres_still_returns_none(self) -> None:
        assert try_build_postgres(None) is None
        assert try_build_postgres(_DEAD_DSN, connect_timeout=0.05) is None

    def test_build_postgres_rejects_blank_dsn(self) -> None:
        with pytest.raises(ConfigurationError):
            build_postgres("   ")

    def test_build_postgres_raises_on_unavailable(self) -> None:
        with pytest.raises((ProviderError, ImportError)):
            build_postgres(_DEAD_DSN, connect_timeout=0.05)


class TestRedaction:
    def test_uri_password_redacted(self) -> None:
        out = redact_dsn_secrets(
            "connection to postgresql://dsp:secret-pass@/dsp failed"
        )
        assert "secret-pass" not in out
        assert "dsp:***@" in out

    def test_keyword_password_redacted(self) -> None:
        assert "secret-pass" not in redact_dsn_secrets("password=secret-pass host=x")
        assert "secret-pass" not in redact_dsn_secrets("password='secret-pass'")
