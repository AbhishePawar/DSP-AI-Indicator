"""API-level tests for staging safety, bootstrap fail-closed, and readiness status."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from api_platform.api.app import create_app
from api_platform.api.infra_bootstrap import bootstrap_production_infrastructure


def test_bootstrap_staging_offline_forbidden():
    """bootstrap_production_infrastructure refuses offline flag in staging."""
    with patch.dict(os.environ, {"DSP_ENVIRONMENT": "staging"}):
        with pytest.raises(
            RuntimeError, match="offline infrastructure is not permitted in staging"
        ):
            bootstrap_production_infrastructure(force_offline=True)


def test_bootstrap_staging_error_does_not_degrade_offline():
    """bootstrap_production_infrastructure in staging raises instead of degrading offline."""
    with patch.dict(
        os.environ,
        {
            "DSP_ENVIRONMENT": "staging",
            "DSP_DATABASE_URL": "postgresql://bad:bad@127.0.0.1:54321/baddb",
        },
    ):
        with pytest.raises(Exception):
            bootstrap_production_infrastructure()


def test_readiness_returns_503_when_staging_database_probe_fails():
    """When database check fails in staging, /health/ready returns 503."""
    app = create_app()
    client = TestClient(app)

    # Mock infrastructure health_checks to report database failure in staging
    mock_infra = MagicMock()
    mock_infra.health_checks.return_value = {
        "database": False,
        "database_adapter": "InMemoryDatabasePort",
        "redis": {"status": "skip"},
        "storage": {
            "status": "pass",
            "provider": "memory",
            "adapter": "InMemoryStoragePort",
        },
    }
    app.state.api.infrastructure = mock_infra

    with patch.dict(
        os.environ,
        {"DSP_ENVIRONMENT": "staging", "DSP_DATABASE_URL": "postgresql://host/db"},
    ):
        resp = client.get("/health/ready")
        assert resp.status_code == 503
        data = resp.json()
        assert data["platform_status"] == "unhealthy"
        assert data["ready"] is False
        assert any(
            c["name"] == "database" and c["status"] == "fail" for c in data["checks"]
        )


def test_readiness_returns_503_when_staging_storage_probe_fails():
    """When storage check fails in staging, /health/ready returns 503."""
    app = create_app()
    client = TestClient(app)

    mock_infra = MagicMock()
    mock_infra.health_checks.return_value = {
        "database": True,
        "database_adapter": "PostgresDatabasePort",
        "redis": {"status": "skip"},
        "storage": {
            "status": "fail",
            "provider": "s3",
            "adapter": "InMemoryStoragePort",
        },
    }
    app.state.api.infrastructure = mock_infra

    with patch.dict(
        os.environ, {"DSP_ENVIRONMENT": "staging", "DSP_OBJECT_STORAGE_PROVIDER": "s3"}
    ):
        resp = client.get("/health/ready")
        assert resp.status_code == 503
        data = resp.json()
        assert data["platform_status"] == "unhealthy"
        assert data["ready"] is False
        assert any(
            c["name"] == "storage" and c["status"] == "fail" for c in data["checks"]
        )
