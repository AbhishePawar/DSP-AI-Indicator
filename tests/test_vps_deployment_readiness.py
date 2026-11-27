"""VPS deployment readiness — PORT binding and production wiring."""

from __future__ import annotations

from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_START_API = _REPO / "scripts" / "start-api.sh"
_COMPOSE = _REPO / "docker/docker-compose.production.yml"
_DOCKERFILE = _REPO / "docker" / "backend" / "Dockerfile"


class TestStartApiPortBinding:
    def test_honors_explicit_runtime_port(self) -> None:
        text = _START_API.read_text(encoding="utf-8")
        assert 'PORT="${PORT:-${DSP_API_PORT:-8000}}"' in text
        assert '--port "${PORT}"' in text
        # Preserve the explicit runtime port override.
        assert '--port "${DSP_API_PORT' not in text

    def test_binds_all_interfaces(self) -> None:
        text = _START_API.read_text(encoding="utf-8")
        assert 'HOST="${DSP_API_HOST:-0.0.0.0}"' in text
        assert "uvicorn api_platform.api.app:app" in text


class TestVpsDeployWiring:
    def test_production_infrastructure_contract(self) -> None:
        text = _COMPOSE.read_text(encoding="utf-8")

        assert "DSP_ENVIRONMENT: production" in text
        assert "DSP_REGION: ${DSP_REGION:-ap-south-1}" in text
        assert "../.env.production" in text
        assert "docker/backend/Dockerfile" in text
        assert "docker/frontend/Dockerfile" in text
        assert "postgres:16-alpine" in text
        assert "redis:7-alpine" in text
        assert "POSTGRES_PASSWORD:?" in text
        assert "service_healthy" in text

    def test_provider_credentials_remain_external(self) -> None:
        text = (
            _REPO / ".env.production.example"
        ).read_text(encoding="utf-8")

        for key in (
            "DSP_DATABASE_URL",
            "DSP_UPSTOX_ANALYTICS_TOKEN",
            "GEMINI_API_KEY",
            "DSP_INVESTMENT_DATA_PROVIDER",
        ):
            assert f"{key}=" in text

    def test_obsolete_deployment_files_are_absent(self) -> None:
        for name in (
            "cloudbuild.yaml",
            "cloudbuild-frontend.yaml",
            "scripts/deploy-google-email-auth.sh",
        ):
            assert not (_REPO / name).exists()


class TestDockerfilePsycopgContract:
    def test_runtime_verifies_psycopg_before_api_import(self) -> None:
        text = _DOCKERFILE.read_text(encoding="utf-8")
        builder_idx = text.index("BUILDER PSYCOPG OK")
        api_idx = text.index("API IMPORT OK")
        runtime_pg_idx = text.index("RUNTIME PSYCOPG OK")
        runtime_api_idx = text.index("RUNTIME API IMPORT OK")
        assert builder_idx < api_idx
        assert runtime_pg_idx < runtime_api_idx
