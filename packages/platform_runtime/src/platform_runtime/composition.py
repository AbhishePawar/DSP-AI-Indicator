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
            service_version="0.3.0",
            region="local",
        )
        infra = InfrastructureBundle.create_offline(configuration=config)
        compliance = ComplianceBundle.create(
            flags=FeatureFlags(),
            database=infra.database,
        )
        consent_bridge = ComplianceBackedConsentStore(compliance.consents)
        security = SecurityBundle.create_with_infrastructure(
            infra,
            SecuritySettings(jwt_secret=jwt_secret, allow_passwordless=False),
            seed_admin=True,
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
        return {
            "infrastructure": {
                "database": self.infrastructure.diagnostics.database_adapter,
                "cache": self.infrastructure.diagnostics.cache_adapter,
            },
            "observability": self.observability.diagnostics(),
            "compliance_flags": {
                "research_mode": self.compliance.flags.research_mode,
                "sebi_mode": self.compliance.flags.sebi_mode,
            },
            "consent_source_of_truth": self.consent_source_of_truth,
            "startup_ok": self.validate_startup().ok,
        }
