"""Enterprise platform composition root (PEP-004.1).

Composes PEP-001…004 bundles. Does not import investment engines or mutate
``/api/v1`` contracts.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from compliance import ComplianceBundle, FeatureFlags
from platform_runtime.consent_bridge import (
    ComplianceBackedConsentStore,
    consent_source_of_truth,
)
from platform_runtime.readiness import (
    ReadinessReport,
    StartupValidation,
    build_readiness_report,
    validate_enterprise_startup,
)
from production_platform import (
    Environment,
    InfrastructureBundle,
    ObservabilityBundle,
    ObservabilitySettings,
    ProductionBundle,
    ProductionConfiguration,
    build_runtime_infrastructure,
    resolve_application_version,
)
from security_platform import SecurityBundle, SecuritySettings

__all__ = ["EnterprisePlatform"]


@dataclass
class EnterprisePlatform:
    """Fully composed enterprise runtime (offline-capable)."""

    infrastructure: InfrastructureBundle
    observability: ObservabilityBundle
    production: ProductionBundle
    security: SecurityBundle
    compliance: ComplianceBundle
    consent_aligned: bool = True
    consent_source_of_truth: str = consent_source_of_truth

    @classmethod
    def create_offline(
        cls,
        *,
        jwt_secret: str = "dev-only-change-me",
        seed_admin_password: str | None = "StrongPass12",
        environment: Environment = Environment.TEST,
    ) -> EnterprisePlatform:
        """Compose all PEP bundles with in-memory / offline adapters."""
        config = ProductionConfiguration(
            environment=environment,
            service_name="dsp-ai-indicator",
            service_version=resolve_application_version(),
            region="local",
        )
        infra = InfrastructureBundle.create_offline(configuration=config)
        return cls._compose(
            infra,
            jwt_secret=jwt_secret,
            seed_admin_password=seed_admin_password,
            allow_passwordless=environment is not Environment.PRODUCTION,
        )

    @classmethod
    def from_environment(
        cls,
        *,
        environ: dict[str, str] | None = None,
        force_offline: bool = False,
        jwt_secret: str | None = None,
        seed_admin_password: str | None = None,
    ) -> EnterprisePlatform:
        """Env-driven composition — Postgres/Redis when available (EPIC-011A)."""
        import os

        env_map = dict(environ if environ is not None else os.environ)
        infra = build_runtime_infrastructure(
            environ=env_map, force_offline=force_offline
        )
        secret = jwt_secret or env_map.get("DSP_JWT_SECRET") or "dev-only-change-me"
        is_prod = infra.configuration.get().environment is Environment.PRODUCTION
        if is_prod and secret in {"dev-only-change-me", "dsp-auth-dev-secret", ""}:
            from production_platform import StartupError

            raise StartupError(
                "DSP_JWT_SECRET must be set to a non-default value in production"
            )
        password = seed_admin_password
        if password is None:
            password = env_map.get("DSP_SEED_ADMIN_PASSWORD")
        return cls._compose(
            infra,
            jwt_secret=secret,
            seed_admin_password=password if not is_prod or password else None,
            seed_admin=not is_prod or bool(password),
            allow_passwordless=not is_prod,
        )

    @classmethod
    def _compose(
        cls,
        infra: InfrastructureBundle,
        *,
        jwt_secret: str,
        seed_admin_password: str | None,
        seed_admin: bool = True,
        allow_passwordless: bool = False,
    ) -> EnterprisePlatform:
        config = infra.configuration.get()
        compliance = ComplianceBundle.create(
            flags=FeatureFlags(),
            database=infra.database,
        )
        consent_bridge = ComplianceBackedConsentStore(compliance.consents)
        security = SecurityBundle.create_with_infrastructure(
            infra,
            SecuritySettings(
                jwt_secret=jwt_secret, allow_passwordless=allow_passwordless
            ),
            seed_admin=seed_admin,
            seed_admin_password=seed_admin_password,
            consent_store=consent_bridge,
        )
        production = ProductionBundle.create(
            configuration=config,
            infrastructure=infra,
            with_observability=True,
            observability_settings=ObservabilitySettings(
                service_name=config.service_name,
                cert_in_log_retention_days=max(
                    180, config.india.cert_in_log_retention_days
                ),
            ),
        )
        obs = production.observability
        assert obs is not None
        return cls(
            infrastructure=infra,
            observability=obs,
            production=production,
            security=security,
            compliance=compliance,
            consent_aligned=True,
        )

    def validate_startup(self) -> StartupValidation:
        return validate_enterprise_startup(self)

    def readiness(self) -> ReadinessReport:
        return build_readiness_report(self)

    def diagnostics(self) -> dict[str, Any]:
        probes = self.infrastructure.health_checks()
        return {
            "infrastructure": {
                "database": self.infrastructure.diagnostics.database_adapter,
                "cache": self.infrastructure.diagnostics.cache_adapter,
                "redis_fallback": self.infrastructure.diagnostics.redis_fallback_active,
                "probes": probes,
                "notes": list(self.infrastructure.diagnostics.notes),
            },
            "observability": self.observability.diagnostics(),
            "compliance_flags": {
                "research_mode": self.compliance.flags.research_mode,
                "sebi_mode": self.compliance.flags.sebi_mode,
            },
            "consent_source_of_truth": self.consent_source_of_truth,
            "startup_ok": self.validate_startup().ok,
            "service_version": self.production.get_configuration().service_version,
        }
