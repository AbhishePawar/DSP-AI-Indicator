"""EPIC-011A — runtime validation, versioning, typed startup errors."""

from __future__ import annotations

import pytest

from production_platform import (
    DatabaseUnavailableError,
    Environment,
    InfrastructureBundle,
    ProductionBundle,
    ProductionConfiguration,
    StartupError,
    build_runtime_infrastructure,
    normalize_version,
    resolve_application_version,
    validate_runtime_environment,
)


class TestVersioning:
    def test_normalize_strips_v_prefix(self) -> None:
        assert normalize_version("v1.0.0") == "1.0.0"
        assert normalize_version("  2.0.2  ") == "2.0.2"
        assert normalize_version("") is None

    def test_resolve_prefers_env(self) -> None:
        assert resolve_application_version({"DSP_APP_VERSION": "v9.9.9"}) == "9.9.9"


class TestRuntimeValidation:
    def test_development_ok_without_database(self) -> None:
        report = validate_runtime_environment(
            {"DSP_ENVIRONMENT": "development"}, strict=False
        )
        assert report.ok is True
        assert report.environment == "development"

    def test_production_requires_database_and_region(self) -> None:
        report = validate_runtime_environment(
            {"DSP_ENVIRONMENT": "production"},
            strict=True,
        )
        assert report.ok is False
        assert "DSP_DATABASE_URL" in report.missing_required
        assert "DSP_REGION" in report.missing_required
        with pytest.raises(StartupError):
            report.raise_if_invalid()

    def test_production_valid_when_required_present(self) -> None:
        report = validate_runtime_environment(
            {
                "DSP_ENVIRONMENT": "production",
                "DSP_REGION": "ap-south-1",
                "DSP_DATABASE_URL": "postgresql://user:pass@localhost:5432/dsp",
                "DSP_APP_VERSION": "1.0.0",
            },
            strict=True,
        )
        # Config validates; DB connectivity checked later at build time.
        assert "DSP_DATABASE_URL" not in report.missing_required
        assert "DSP_REGION" not in report.missing_required

    def test_build_offline_force(self) -> None:
        infra = build_runtime_infrastructure(
            environ={"DSP_ENVIRONMENT": "development"},
            force_offline=True,
        )
        assert infra.diagnostics.database_adapter == "InMemoryDatabasePort"
        assert infra.database.ping() is True

    def test_production_build_fails_without_live_postgres(self) -> None:
        with pytest.raises((DatabaseUnavailableError, StartupError)):
            build_runtime_infrastructure(
                environ={
                    "DSP_ENVIRONMENT": "production",
                    "DSP_REGION": "ap-south-1",
                    "DSP_DATABASE_URL": "postgresql://invalid:invalid@127.0.0.1:1/dsp",
                    "DSP_DATABASE_TIMEOUT": "0.05",
                },
                strict=True,
                require_database=True,
            )


class TestProductionBundleFromEnvironment:
    def test_from_environment_offline(self) -> None:
        bundle = ProductionBundle.from_environment(force_offline=True)
        assert bundle.infrastructure is not None
        assert bundle.liveness().live is True
        assert bundle.readiness().ready is True
        names = {c.name for c in bundle.readiness().checks}
        assert "database" in names
        assert "redis_stack" in names or "redis" in names

    def test_default_service_version_aligned(self) -> None:
        cfg = ProductionConfiguration(environment=Environment.TEST)
        assert cfg.service_version  # non-empty; from VERSION / default
        assert normalize_version(cfg.service_version) == cfg.service_version


class TestInfrastructureHealthProbes:
    def test_health_checks_include_redis_block(self) -> None:
        infra = InfrastructureBundle.create_offline()
        probes = infra.health_checks()
        assert "redis" in probes
        assert probes["redis"]["status"] == "skip"
        assert probes["database"] is True
        assert probes["database_status"] == "pass"
        assert probes["storage"]["status"] == "skip"


class TestStagingFailClosed:
    def test_staging_configured_database_failure_does_not_fall_back(self) -> None:
        with pytest.raises((DatabaseUnavailableError, StartupError)):
            build_runtime_infrastructure(
                environ={
                    "DSP_ENVIRONMENT": "staging",
                    "DSP_REGION": "ap-south-1",
                    "DSP_DATABASE_URL": "postgresql://invalid:invalid@127.0.0.1:1/dsp",
                    "DSP_DATABASE_TIMEOUT": "0.05",
                }
            )

    def test_staging_storage_failure_does_not_fall_back(self, monkeypatch) -> None:
        from production_platform.adapters import object_storage
        from production_platform.production.exceptions import StartupError

        def fail_boto3():
            raise ImportError("boto3 missing in test")

        monkeypatch.setattr(object_storage, "_load_boto3", fail_boto3)
        with pytest.raises(StartupError, match="Object storage provider=s3 unavailable"):
            InfrastructureBundle.from_environment(
                environ={
                    "DSP_ENVIRONMENT": "staging",
                    "DSP_OBJECT_STORAGE_PROVIDER": "s3",
                    "DSP_OBJECT_STORAGE_BUCKET": "dsp-test-bucket",
                }
            )

    def test_staging_requires_database_and_region_by_default(self) -> None:
        report = validate_runtime_environment({"DSP_ENVIRONMENT": "staging"})
        assert report.ok is False
        assert "DSP_DATABASE_URL" in report.missing_required
        assert "DSP_REGION" in report.missing_required

    def test_staging_rejects_offline_override(self) -> None:
        with pytest.raises(StartupError, match="only permitted for development/test"):
            build_runtime_infrastructure(
                environ={"DSP_ENVIRONMENT": "staging"},
                force_offline=True,
            )

    def test_staging_rejects_missing_bucket_for_explicit_s3_provider(self) -> None:
        report = validate_runtime_environment(
            {
                "DSP_ENVIRONMENT": "staging",
                "DSP_REGION": "ap-south-1",
                "DSP_DATABASE_URL": "postgresql://user:pass@localhost:5432/dsp",
                "DSP_OBJECT_STORAGE_PROVIDER": "s3",
            }
        )
        assert report.ok is False
        assert "DSP_OBJECT_STORAGE_BUCKET" in report.missing_required


    def test_direct_offline_builder_rejects_staging(self) -> None:
        from production_platform.production.exceptions import ConfigurationError

        with pytest.raises(ConfigurationError, match="only permitted for development/test"):
            InfrastructureBundle.from_environment(
                environ={"DSP_ENVIRONMENT": "staging"},
                force_offline=True,
            )
