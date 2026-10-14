from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts" / "validate_env.py"


def production_env(**overrides: str) -> dict[str, str]:
    env = {
        "DSP_ENVIRONMENT": "production",
        "DSP_JWT_SECRET": "x" * 48,
        "DSP_SEED_ADMIN_PASSWORD": "Synthetic-Admin-Password-2026",
        "GEMINI_API_KEY": "synthetic-gemini-test-key",
        "OPENAI_API_KEY_5": "synthetic-openai-test-key",
        "DSP_CORS_ORIGINS": "https://app.example.com",
        "DSP_ENABLE_SECURITY": "true",
        "DSP_REQUIRE_ADMIN_AUTH": "true",
        "DSP_RATE_LIMIT_ENABLED": "true",
        "DSP_HSTS_ENABLED": "true",
        "DSP_INDIA_TIMEZONE": "Asia/Kolkata",
        "DSP_INDIA_CURRENCY": "INR",
        "DSP_APP_VERSION": "2.0.0-rc.1",
        "DSP_DATABASE_URL": (
            "postgresql://dsp:SecurePass123@ep-test.neon.tech/dsp?sslmode=require"
        ),
        "DSP_PUBLIC_DOMAIN": "app.example.com",
    }
    env.update(overrides)
    return {**os.environ, **env}


def run_validator(**overrides: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(VALIDATOR), "production"],
        env=production_env(**overrides),
        capture_output=True,
        text=True,
        check=False,
    )


def test_accepts_external_tls_postgres_and_real_domain() -> None:
    result = run_validator()
    assert result.returncode == 0, result.stdout + result.stderr


def test_rejects_placeholder_production_domain() -> None:
    result = run_validator(DSP_PUBLIC_DOMAIN="app.your-domain.example")
    assert result.returncode != 0
    assert "real public hostname" in result.stderr


def test_rejects_placeholder_database_host() -> None:
    result = run_validator(
        DSP_DATABASE_URL=(
            "postgresql://USER:PASSWORD@YOUR-NEON-HOST/DBNAME?sslmode=require"
        )
    )
    assert result.returncode != 0
    assert "real external PostgreSQL hostname" in result.stderr


def test_rejects_database_without_tls() -> None:
    result = run_validator(
        DSP_DATABASE_URL="postgresql://dsp:SecurePass123@ep-test.neon.tech/dsp"
    )
    assert result.returncode != 0
    assert "must require TLS" in result.stderr

def test_rejects_mixed_http_cors_origins() -> None:
    result = run_validator(
        DSP_CORS_ORIGINS="https://app.example.com,http://localhost:3000"
    )
    assert result.returncode != 0
    assert "exact HTTPS origins" in result.stderr


def test_rejects_domain_with_scheme_or_path() -> None:
    result = run_validator(DSP_PUBLIC_DOMAIN="https://app.example.com/path")
    assert result.returncode != 0
    assert "hostname only" in result.stderr

def test_requires_both_direct_ai_provider_keys() -> None:
    result = run_validator(GEMINI_API_KEY="", OPENAI_API_KEY_5="")
    assert result.returncode != 0
    assert (
        "Dual-provider verification requires both direct provider keys"
        in result.stderr
    )


def test_rejects_weak_seed_admin_password() -> None:
    result = run_validator(DSP_SEED_ADMIN_PASSWORD="short")
    assert result.returncode != 0
    assert "DSP_SEED_ADMIN_PASSWORD looks like a template" in result.stderr

def test_rejects_template_jwt_secret() -> None:
    result = run_validator(
        DSP_JWT_SECRET="CHANGE_ME_USE_SECRET_MANAGER_MIN_32_CHARS"
    )
    assert result.returncode != 0
    assert "DSP_JWT_SECRET must be a strong secret" in result.stderr
