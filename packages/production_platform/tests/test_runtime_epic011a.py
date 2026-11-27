"""EPIC-011A — runtime validation, versioning, typed startup errors."""

from __future__ import annotations

import pytest

from production_platform import (
    DatabaseUnavailableError,
    Environment,
    InfrastructureBundle,
    ProductionBundle,
    ProductionConfiguration,
    RedisUnavailableError,
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

    @pytest.mark.parametrize("profile", ["staging", "production"])
    @pytest.mark.parametrize("key", ["DSP_ENVIRONMENT", "ENVIRONMENT"])
    @pytest.mark.parametrize("offline", ["force", "environment"])
    def test_strict_profiles_reject_offline(
        self, profile: str, key: str, offline: str
    ) -> None:
        environ = {
            key: profile,
            "DSP_REGION": "ap-south-1",
            "DSP_DATABASE_URL": "postgresql://user:pass@localhost:5432/dsp",
        }
        with pytest.raises(StartupError, match="does not permit offline"):
            (
                build_runtime_infrastructure(
                    environ=environ,
                    force_offline=offline == "force",
                    **({"strict": True} if offline == "force" else {}),
                )
                if offline == "force"
                else build_runtime_infrastructure(
                    environ={**environ, "DSP_INFRA_OFFLINE": "true"}
                )
            )

    def test_environment_alias_development_offline_still_works(self) -> None:
        infra = build_runtime_infrastructure(
            environ={"ENVIRONMENT": "development", "DSP_INFRA_OFFLINE": "true"}
        )
        assert infra.diagnostics.database_adapter == "InMemoryDatabasePort"

    def test_require_redis_rejects_missing_redis_url(self) -> None:
        with pytest.raises(RedisUnavailableError):
            build_runtime_infrastructure(
                environ={"DSP_ENVIRONMENT": "development"},
                require_redis=True,
            )

    def test_required_unhealthy_redis_fails_runtime(self) -> None:
        with pytest.raises(RedisUnavailableError):
            build_runtime_infrastructure(
                environ={
                    "DSP_ENVIRONMENT": "development",
                    "DSP_REDIS_URL": "redis://127.0.0.1:1/0",
                    "DSP_REDIS_FALLBACK": "false",
                    "DSP_REDIS_TIMEOUT": "0.05",
                }
            )

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
