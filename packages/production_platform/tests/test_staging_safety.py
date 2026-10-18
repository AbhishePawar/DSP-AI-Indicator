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
    StartupError,
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


def test_staging_requires_database_configuration():
    """Staging must fail closed instead of silently using an in-memory database."""
    env = {"DSP_ENVIRONMENT": "staging"}
    with pytest.raises(StartupError, match="DSP_DATABASE_URL"):
        build_runtime_infrastructure(environ=env)


def test_staging_local_storage_is_supported_and_persistent(tmp_path):
    """Local filesystem storage is the configured primary artifact store."""
    env = {
        "DSP_ENVIRONMENT": "staging",
        "DSP_OBJECT_STORAGE_PROVIDER": "local",
        "DSP_OBJECT_STORAGE_LOCAL_ROOT": str(tmp_path),
    }
    bundle = InfrastructureBundle.from_environment(environ=env)
    assert bundle.diagnostics.storage_adapter == "LocalFirstS3OverflowStoragePort"
    bundle.storage.put("reports/staging-check.txt", b"local-storage-ok")
    assert bundle.storage.get("reports/staging-check.txt") == b"local-storage-ok"


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


def test_local_storage_overflow_uses_s3_only_for_new_objects(tmp_path, monkeypatch):
    """At 95% disk use, only new objects overflow to the separate S3 prefix."""
    from types import SimpleNamespace

    from production_platform.production.storage import LocalFirstS3OverflowStoragePort

    class FakeS3:
        def __init__(self):
            self.objects = {}

        def put(self, key, data, *, content_type=None):
            self.objects[key] = data

        def get(self, key):
            return self.objects.get(key)

        def delete(self, key):
            self.objects.pop(key, None)

    fake_s3 = FakeS3()
    monkeypatch.setattr(
        "production_platform.production.storage.shutil.disk_usage",
        lambda _path: SimpleNamespace(total=100, used=95, free=5),
    )
    store = LocalFirstS3OverflowStoragePort(tmp_path, overflow_storage=fake_s3)
    store.put("reports/new.txt", b"overflow")
    assert fake_s3.objects == {"overflow/reports/new.txt": b"overflow"}
    assert store.get("reports/new.txt") == b"overflow"

    # Existing local files are updated in place and are never moved to S3.
    local = LocalFirstS3OverflowStoragePort(
        tmp_path, overflow_storage=fake_s3, threshold=0.99
    )
    monkeypatch.setattr(
        "production_platform.production.storage.shutil.disk_usage",
        lambda _path: SimpleNamespace(total=100, used=50, free=50),
    )
    local.put("reports/existing.txt", b"old")
    monkeypatch.setattr(
        "production_platform.production.storage.shutil.disk_usage",
        lambda _path: SimpleNamespace(total=100, used=99, free=1),
    )
    local.put("reports/existing.txt", b"updated")
    assert local.get("reports/existing.txt") == b"updated"
    assert "overflow/reports/existing.txt" not in fake_s3.objects


def test_local_storage_overflow_fails_explicitly_without_s3(tmp_path, monkeypatch):
    """Never silently fill the disk past the configured overflow threshold."""
    from types import SimpleNamespace

    from production_platform.production.storage import LocalFirstS3OverflowStoragePort

    monkeypatch.setattr(
        "production_platform.production.storage.shutil.disk_usage",
        lambda _path: SimpleNamespace(total=100, used=95, free=5),
    )
    store = LocalFirstS3OverflowStoragePort(tmp_path)
    with pytest.raises(ProviderError, match="95% overflow threshold"):
        store.put("reports/new.txt", b"data")


def test_staging_rejects_s3_as_primary_storage(monkeypatch):
    """S3 is an offsite backup/overflow target, not the primary artifact store."""
    from production_platform.production.database import InMemoryDatabasePort

    class FakePostgresPort(InMemoryDatabasePort):
        """Local test double whose adapter name is not the memory fallback."""

    env = {
        "DSP_ENVIRONMENT": "staging",
        "DSP_DATABASE_URL": "postgresql://test:test@127.0.0.1:5432/test",
        "DSP_OBJECT_STORAGE_PROVIDER": "s3",
        "DSP_OBJECT_STORAGE_BUCKET": "test-bucket",
        "DSP_OBJECT_STORAGE_REGION": "ap-south-1",
    }
    monkeypatch.setattr(
        "production_platform.adapters.postgres.build_postgres",
        lambda *args, **kwargs: FakePostgresPort(),
    )
    monkeypatch.setattr(
        "production_platform.adapters.object_storage.build_s3_storage",
        lambda **kwargs: object(),
    )
    with pytest.raises(
        StorageUnavailableError,
        match="requires DSP_OBJECT_STORAGE_PROVIDER=local",
    ):
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
