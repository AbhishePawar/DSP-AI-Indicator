"""VPS deployment readiness — container port binding and Google-free production wiring."""

from __future__ import annotations

from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_START_API = _REPO / "scripts" / "start-api.sh"
_COMPOSE = _REPO / "docker" / "docker-compose.production.yml"
_ENV_EXAMPLE = _REPO / ".env.production.example"
_DOCKERFILE = _REPO / "docker" / "backend" / "Dockerfile"
_CADDY = _REPO / "docker" / "Caddyfile"


class TestStartApiPortBinding:
    def test_honors_container_port(self) -> None:
        text = _START_API.read_text(encoding="utf-8")
        assert 'PORT="${PORT:-${DSP_API_PORT:-8000}}"' in text
        assert '--port "${PORT}"' in text
        assert '--port "${DSP_API_PORT' not in text

    def test_binds_all_interfaces(self) -> None:
        text = _START_API.read_text(encoding="utf-8")
        assert 'HOST="${DSP_API_HOST:-0.0.0.0}"' in text
        assert "uvicorn api_platform.api.app:app" in text


class TestGoogleDeployFilesRemoved:
    def test_cloud_build_and_gcloud_deploy_script_are_gone(self) -> None:
        assert not (_REPO / "cloudbuild.yaml").exists()
        assert not (_REPO / "cloudbuild-frontend.yaml").exists()
        assert not (_REPO / "scripts" / "deploy-google-email-auth.sh").exists()


class TestVpsComposeWiring:
    def test_production_compose_is_caddy_api_and_web_only(self) -> None:
        text = _COMPOSE.read_text(encoding="utf-8")
        assert "caddy:2.8-alpine" in text
        assert "docker/backend/Dockerfile" in text
        assert "docker/frontend/Dockerfile" in text
        assert "postgres:" not in text
        assert "redis:" not in text
        assert "gcr.io" not in text
        assert "pkg.dev" not in text
        assert "cloudsql" not in text
        assert "gcloud" not in text
        assert "DSP_REDIS_URL:" not in text
        assert "sslmode=require" in text
        assert '"8000:8000"' not in text
        assert '"5432:5432"' not in text

    def test_caddy_keeps_api_on_the_public_host(self) -> None:
        text = _CADDY.read_text(encoding="utf-8")
        assert "handle /api/v1/*" in text
        assert "reverse_proxy api:8000" in text
        assert "reverse_proxy web:3000" in text
        assert "DSP_API_DOMAIN" not in text

    def test_env_example_points_at_neon_direct_tls(self) -> None:
        text = _ENV_EXAMPLE.read_text(encoding="utf-8")
        assert "sslmode=require" in text
        assert "neon.tech" in text
        assert "DSP_REDIS_URL=" not in text
        assert "https://dspaiindicator.com/api/v1" in text
        assert "run.app" not in text
        assert "@postgres:" not in text


class TestDockerfilePsycopgContract:
    def test_runtime_verifies_psycopg_before_api_import(self) -> None:
        text = _DOCKERFILE.read_text(encoding="utf-8")
        builder_idx = text.index("BUILDER PSYCOPG OK")
        api_idx = text.index("API IMPORT OK")
        runtime_pg_idx = text.index("RUNTIME PSYCOPG OK")
        runtime_api_idx = text.index("RUNTIME API IMPORT OK")
        assert builder_idx < api_idx
        assert runtime_pg_idx < runtime_api_idx
