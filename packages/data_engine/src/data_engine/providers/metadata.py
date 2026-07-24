"""Provider metadata model for the Data Engine.

``ProviderMetadata`` is the single, structured description of a
registered provider: identity, versioning, declared capabilities,
rate-limit envelope, authentication requirements, selection priority,
and operational status. It carries no logic of its own beyond structural
validation — it is a data container that
:class:`~data_engine.providers.registry.ProviderRegistry` uses to answer
"which registered provider(s) can do X".
"""

from __future__ import annotations

from dataclasses import dataclass, field

from data_engine.exceptions import DataEngineError
from data_engine.providers.capabilities import ProviderCapabilities
from data_engine.providers.enums import AuthenticationType, ProviderStatus

__all__ = ["ProviderMetadata", "RateLimitPolicy"]


@dataclass(frozen=True, slots=True)
class RateLimitPolicy:
    """Describes a provider's declared rate-limit envelope.

    This is descriptive metadata only — the Data Engine does not
    enforce these limits itself. A concrete adapter (or a decorator
    wrapping one) is responsible for actually respecting them; this
    type exists so the information can be recorded and inspected
    uniformly across providers.

    Attributes:
        requests_per_minute: Maximum requests allowed per minute.
            ``None`` means no known/declared limit.
        requests_per_day: Maximum requests allowed per day. ``None``
            means no known/declared limit.
        concurrent_requests: Maximum number of in-flight requests the
            provider tolerates. ``None`` means no known/declared limit.
    """

    requests_per_minute: int | None = None
    requests_per_day: int | None = None
    concurrent_requests: int | None = None


@dataclass(frozen=True, slots=True)
class ProviderMetadata:
    """Immutable, structured description of a registered provider.

    Attributes:
        provider_id: Stable, machine-readable identifier used to
            register and look up this provider (e.g.
            ``"yahoo_finance"``). Normalized to lowercase.
        name: Human-readable display name (e.g. ``"Yahoo Finance"``).
        version: Version of the adapter implementation itself — not the
            vendor's API version.
        description: Short human-readable description of the provider.
        homepage: Optional URL to the provider's homepage or API docs.
        capabilities: Structured description of what data this
            provider can supply.
        rate_limit: Optional declared rate-limit envelope.
        auth_type: How this provider authenticates requests.
        priority: Ordering hint used by
            ``ProviderRegistry.select_preferred`` when multiple
            providers support the same capability (lower is preferred).
            ``None`` sorts last.
        status: Operational status of this provider registration.
    """

    provider_id: str
    name: str
    version: str = "0.1.0"
    description: str = ""
    homepage: str | None = None
    capabilities: ProviderCapabilities = field(default_factory=ProviderCapabilities)
    rate_limit: RateLimitPolicy | None = None
    auth_type: AuthenticationType = AuthenticationType.NONE
    priority: int | None = None
    status: ProviderStatus = ProviderStatus.ACTIVE

    def __post_init__(self) -> None:
        """Normalize and validate identifying fields.

        Raises:
            DataEngineError: If ``provider_id`` or ``name`` is empty.
        """
        provider_id = self.provider_id.strip().lower()
        if not provider_id:
            msg = "provider_id must not be empty"
            raise DataEngineError(msg)
        if not self.name.strip():
            msg = "name must not be empty"
            raise DataEngineError(msg)

        object.__setattr__(self, "provider_id", provider_id)
