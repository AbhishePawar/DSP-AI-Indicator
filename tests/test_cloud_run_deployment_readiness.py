"""Cloud Run deployment readiness — PORT binding + production wiring."""

from __future__ import annotations

from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_START_API = _REPO / "scripts" / "start-api.sh"
_CLOUDBUILD = _REPO / "cloudbuild.yaml"
_DOCKERFILE = _REPO / "docker" / "backend" / "Dockerfile"


class TestStartApiPortBinding:
    def test_unix_lf_line_endings(self) -> None:
        raw = _START_API.read_bytes()
        assert b"\r\n" not in raw
        assert raw.startswith(b"#!/bin/sh\n")

    def test_honors_cloud_run_port(self) -> None:
        text = _START_API.read_text(encoding="utf-8")
        assert 'PORT="${PORT:-${DSP_API_PORT:-8000}}"' in text
        assert '--port "${PORT}"' in text
        # Must not bind solely to DSP_API_PORT (Cloud Run injects PORT).
        assert '--port "${DSP_API_PORT' not in text

    def test_binds_all_interfaces(self) -> None:
        text = _START_API.read_text(encoding="utf-8")
        assert 'HOST="${DSP_API_HOST:-0.0.0.0}"' in text
        assert "uvicorn api_platform.api.app:app" in text


class TestCloudBuildDeployWiring:
    def test_sets_production_database_region_and_no_upstox(self) -> None:
        text = _CLOUDBUILD.read_text(encoding="utf-8")
        assert "DSP_ENVIRONMENT=production" in text
        assert "DSP_REGION=ap-south-1" in text
        assert "DSP_INVESTMENT_DATA_PROVIDER=none" in text
        assert "DSP_INVESTMENT_DATA_PROVIDER=upstox" not in text
        assert "DSP_DATABASE_URL=dsp-database-url:latest" in text
        assert "--remove-secrets=DSP_UPSTOX_ANALYTICS_TOKEN" in text
        assert "--clear-command" in text
        assert "--clear-args" in text
        assert "dsp-upstox-analytics-token" not in text
        update_secrets = [
            line.strip()
            for line in text.splitlines()
            if line.strip().startswith("- --update-secrets=")
        ]
        assert update_secrets, "Cloud Build must declare --update-secrets"
        assert all("DSP_UPSTOX_ANALYTICS_TOKEN=" not in line for line in update_secrets)
        assert (
            "--add-cloudsql-instances="
            "project-34de429e-3c43-4ae7-b75:asia-south1:dsp-postgres"
        ) in text
        assert "--port=8000" in text
        assert "--region=$_REGION" in text
        assert "_REGION: asia-south1" in text
        # No FMP wiring in Cloud Run production path.
        assert "FMP" not in text

    def test_injects_gemini_api_key_from_secret_manager_version_1(self) -> None:
        text = _CLOUDBUILD.read_text(encoding="utf-8")
        secrets = [
            line.strip()
            for line in text.splitlines()
            if "--update-secrets=" in line and not line.lstrip().startswith("#")
        ]
        env = [
            line.strip()
            for line in text.splitlines()
            if "--update-env-vars=" in line and not line.lstrip().startswith("#")
        ]
        assert len(secrets) == 1
        secret_arg = secrets[0]
        assert "GEMINI_API_KEY=dsp-gemini-api-key:1" in secret_arg
        assert "dsp-gemini-api-key:latest" not in secret_arg
        deploy_runtime = "\n".join(secrets + env)
        assert "DEFAULT_AI_PROVIDER" not in deploy_runtime
        assert "DSP_AI_DEFAULT_PROVIDER" not in deploy_runtime
        assert "AI_ENABLED" not in deploy_runtime
        assert "activation_ready" not in deploy_runtime


class TestDockerfilePsycopgContract:
    def test_strips_crlf_from_start_api_script(self) -> None:
        text = _DOCKERFILE.read_text(encoding="utf-8")
        assert "sed -i 's/\\r$//' /app/scripts/start-api.sh" in text

    def test_runtime_verifies_psycopg_before_api_import(self) -> None:
        text = _DOCKERFILE.read_text(encoding="utf-8")
        builder_idx = text.index("BUILDER PSYCOPG OK")
        api_idx = text.index("API IMPORT OK")
        runtime_pg_idx = text.index("RUNTIME PSYCOPG OK")
        runtime_api_idx = text.index("RUNTIME API IMPORT OK")
        assert builder_idx < api_idx
        assert runtime_pg_idx < runtime_api_idx
