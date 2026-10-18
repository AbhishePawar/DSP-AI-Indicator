"""Tests for staging fail-closed behavior, storage validation, and health/readiness."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from production_platform.adapters.object_storage import (
    build_s3_storage,
)
from production_platform.production.exceptions import (
    ConfigurationError,
    DatabaseUnavailableError,
    ProviderError,
    StorageUnavailableError,
)
from production_platform.production.infrastructure import InfrastructureBundle
from production_platform.production.product_state_backup import (
    LEGACY_PRODUCT_STATE_TABLES,
    PRODUCT_STATE_TABLES,
)
from production_platform.production.runtime import build_runtime_infrastructure


def test_staging_offline_forbidden():
    """Staging must refuse explicit offline mode."""
    env = {"DSP_ENVIRONMENT": "staging", "DSP_INFRA_OFFLINE": "true"}
    with pytest.raises(
        ConfigurationError,
        match="explicit offline infrastructure is not permitted in staging",
    ):
        build_runtime_infrastructure(environ=env)

    env2 = {"DSP_ENVIRONMENT": "staging"}
    with pytest.raises(
        ConfigurationError,
        match="explicit offline infrastructure is not permitted in staging",
    ):
        build_runtime_infrastructure(environ=env2, force_offline=True)


def test_production_offline_forbidden():
    """Production must refuse explicit offline mode."""
    env = {"DSP_ENVIRONMENT": "production", "DSP_INFRA_OFFLINE": "true"}
    with pytest.raises(
        ConfigurationError,
        match="explicit offline infrastructure is not permitted in production",
    ):
        build_runtime_infrastructure(environ=env)


def test_development_offline_allowed():
    """Development preserves explicit offline mode."""
    env = {"DSP_ENVIRONMENT": "development", "DSP_INFRA_OFFLINE": "true"}
    bundle = build_runtime_infrastructure(environ=env)
    assert bundle.diagnostics.database_adapter == "InMemoryDatabasePort"
    assert "force_offline=true" in bundle.notes


def test_staging_database_failure_fails_closed():
    """Staging with configured DB fails closed when Postgres is unavailable."""
    env = {
        "DSP_ENVIRONMENT": "staging",
        "DSP_DATABASE_URL": "postgresql://baduser:badpass@127.0.0.1:54321/baddb",
    }
    with pytest.raises(DatabaseUnavailableError):
        build_runtime_infrastructure(environ=env)


def test_build_s3_storage_requires_bucket():
    """build_s3_storage fails closed on empty or whitespace bucket."""
    with pytest.raises(ConfigurationError, match="bucket must not be empty"):
        build_s3_storage(bucket="")

    with pytest.raises(ConfigurationError, match="bucket must not be empty"):
        build_s3_storage(bucket="   ")

    with pytest.raises(ConfigurationError, match="bucket must not be empty"):
        build_s3_storage(bucket=None)


def test_staging_storage_fails_closed_when_s3_configured_without_bucket():
    """Staging with s3 provider fails closed if bucket is missing."""
    env = {
        "DSP_ENVIRONMENT": "staging",
        "DSP_OBJECT_STORAGE_PROVIDER": "s3",
        "DSP_OBJECT_STORAGE_BUCKET": "",
    }
    with pytest.raises((ConfigurationError, StorageUnavailableError)):
        build_runtime_infrastructure(environ=env)


def test_staging_storage_fails_closed_when_s3_unavailable():
    """Staging with s3 provider fails closed if boto3 or S3 init fails."""
    env = {
        "DSP_ENVIRONMENT": "staging",
        "DSP_OBJECT_STORAGE_PROVIDER": "s3",
        "DSP_OBJECT_STORAGE_BUCKET": "test-bucket",
    }
    with patch(
        "production_platform.adapters.object_storage._load_boto3",
        side_effect=ProviderError("boto3 missing"),
    ):
        with pytest.raises(StorageUnavailableError):
            build_runtime_infrastructure(environ=env)


def test_development_storage_falls_back_with_note():
    """Development with s3 provider gracefully falls back to memory with a note."""
    env = {
        "DSP_ENVIRONMENT": "development",
        "DSP_OBJECT_STORAGE_PROVIDER": "s3",
        "DSP_OBJECT_STORAGE_BUCKET": "test-bucket",
    }
    with patch(
        "production_platform.adapters.object_storage._load_boto3",
        side_effect=ProviderError("boto3 missing"),
    ):
        bundle = InfrastructureBundle.from_environment(environ=env)
        assert bundle.diagnostics.storage_adapter == "InMemoryStoragePort"
        assert any("Object storage provider=s3 unavailable" in n for n in bundle.notes)


def test_health_checks_storage_probe_status():
    """Infrastructure health_checks reports storage probe details."""
    bundle = InfrastructureBundle.create_offline()
    probes = bundle.health_checks()
    assert "storage" in probes
    assert probes["storage"]["provider"] == "memory"
    assert probes["storage"]["adapter"] == "InMemoryStoragePort"
    assert probes["storage"]["status"] == "pass"


def test_active_report_snapshots_in_legacy_and_product_tables():
    """Verify active application persistence table api_report_snapshots is preserved."""
    assert "api_report_snapshots" in LEGACY_PRODUCT_STATE_TABLES
    assert "api_report_snapshots" in PRODUCT_STATE_TABLES
    assert "api_report_records" not in LEGACY_PRODUCT_STATE_TABLES
    assert "api_export_records" not in LEGACY_PRODUCT_STATE_TABLES
