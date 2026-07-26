"""Platform configuration models for integration (K1.0).

Presentation / composition only — no business logic. Wraps the existing
immutable ``PlatformConfig`` surface and adds capability toggles.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from dsp_platform.config import (
    CacheSettings,
    Environment,
    FeatureFlags,
    PlatformConfig,
    PlatformSecrets,
    ProviderSettings,
    TimeoutSettings,
)
from dsp_platform.platform_exceptions import PlatformConfigurationError

__all__ = [
    "DEFAULT_CAPABILITIES",
    "PlatformConfiguration",
]

DEFAULT_CAPABILITIES: tuple[str, ...] = (
    "analyze_company",
    "compare_companies",
    "run_workflow",
    "build_knowledge_graph",
    "ask_copilot",
    "export_report",
    "health_check",
    "get_platform_info",
    "compose_intelligence",
)


@dataclass(frozen=True, slots=True)
class PlatformConfiguration:
    """Immutable integration configuration for ``DSPPlatform`` / ``PlatformBuilder``.

    Attributes:
        environment: Deployment environment.
        providers: Provider registration and default ids.
        cache: Cache TTL settings.
        timeouts: Adapter timeout settings.
        features: Default analysis feature flags.
        secrets: Injected credentials (never from source control).
        enabled_capabilities: Capability names exposed by the platform.
        platform_name: Human-readable platform name.
        require_analysis_service: When True, analyze paths require a wired
            ``InvestmentAnalysisService``.
    """

    environment: Environment = Environment.DEVELOPMENT
    providers: ProviderSettings = field(default_factory=ProviderSettings)
    cache: CacheSettings = field(default_factory=CacheSettings)
    timeouts: TimeoutSettings = field(default_factory=TimeoutSettings)
    features: FeatureFlags = field(default_factory=FeatureFlags)
    secrets: PlatformSecrets = field(default_factory=PlatformSecrets)
    enabled_capabilities: tuple[str, ...] = DEFAULT_CAPABILITIES
    platform_name: str = "DSP AI Indicator"
    require_analysis_service: bool = True

    def __post_init__(self) -> None:
        name = self.platform_name.strip()
        if not name:
            msg = "platform_name must not be empty"
            raise PlatformConfigurationError(msg)
        caps = tuple(c.strip() for c in self.enabled_capabilities if c.strip())
        if not caps:
            msg = "enabled_capabilities must not be empty"
            raise PlatformConfigurationError(msg)
        seen: set[str] = set()
        for cap in caps:
            key = cap.lower()
            if key in seen:
                msg = f"duplicate capability: {cap!r}"
                raise PlatformConfigurationError(msg)
            seen.add(key)
        object.__setattr__(self, "platform_name", name)
        object.__setattr__(self, "enabled_capabilities", caps)

    def to_platform_config(self) -> PlatformConfig:
        """Project to the legacy composition-root ``PlatformConfig``."""
        return PlatformConfig(
            environment=self.environment,
            providers=self.providers,
            cache=self.cache,
            timeouts=self.timeouts,
            features=self.features,
            secrets=self.secrets,
        )

    @classmethod
    def from_platform_config(
        cls,
        config: PlatformConfig,
        *,
        enabled_capabilities: tuple[str, ...] = DEFAULT_CAPABILITIES,
        platform_name: str = "DSP AI Indicator",
        require_analysis_service: bool = True,
    ) -> PlatformConfiguration:
        """Build integration configuration from legacy ``PlatformConfig``."""
        return cls(
            environment=config.environment,
            providers=config.providers,
            cache=config.cache,
            timeouts=config.timeouts,
            features=config.features,
            secrets=config.secrets,
            enabled_capabilities=enabled_capabilities,
            platform_name=platform_name,
            require_analysis_service=require_analysis_service,
        )

    def has_capability(self, capability: str) -> bool:
        """Return True when ``capability`` is enabled (case-insensitive)."""
        key = capability.strip().lower()
        return any(c.lower() == key for c in self.enabled_capabilities)
