"""Service registry for platform dependency injection (K1.0).

Registers frozen public façade instances by name / capability. Does not
perform business analysis or invent services.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from dsp_platform.platform_exceptions import ServiceRegistryError

__all__ = [
    "ServiceDescriptor",
    "ServiceRegistry",
]


@dataclass(frozen=True, slots=True)
class ServiceDescriptor:
    """Immutable descriptor for one registered platform service."""

    name: str
    capability: str
    version: str
    service: Any

    def __post_init__(self) -> None:
        if not self.name.strip():
            msg = "service name must not be empty"
            raise ServiceRegistryError(msg)
        if not self.capability.strip():
            msg = "service capability must not be empty"
            raise ServiceRegistryError(msg)
        if not self.version.strip():
            msg = "service version must not be empty"
            raise ServiceRegistryError(msg)
        if self.service is None:
            msg = f"service {self.name!r} must not be None"
            raise ServiceRegistryError(msg)


class ServiceRegistry:
    """Mutable registration map used only at composition / lifecycle time.

    Once handed to a running ``DSPPlatform``, callers should treat registered
    services as read-only dependencies.
    """

    def __init__(self) -> None:
        self._by_name: dict[str, ServiceDescriptor] = {}

    def register(
        self,
        name: str,
        service: Any,
        *,
        capability: str,
        version: str = "1.0.0",
        replace: bool = False,
    ) -> ServiceDescriptor:
        """Register a service under ``name`` for ``capability``."""
        key = name.strip().lower()
        if not key:
            msg = "service name must not be empty"
            raise ServiceRegistryError(msg)
        if key in self._by_name and not replace:
            msg = f"duplicate service registration: {name!r}"
            raise ServiceRegistryError(msg)
        descriptor = ServiceDescriptor(
            name=name.strip(),
            capability=capability.strip(),
            version=version.strip(),
            service=service,
        )
        self._by_name[key] = descriptor
        return descriptor

    def get(self, name: str) -> Any:
        """Return the registered service instance by name."""
        return self.get_descriptor(name).service

    def get_descriptor(self, name: str) -> ServiceDescriptor:
        """Return the full descriptor by name."""
        key = name.strip().lower()
        if key not in self._by_name:
            msg = f"unknown service: {name!r}"
            raise ServiceRegistryError(msg)
        return self._by_name[key]

    def get_by_capability(self, capability: str) -> tuple[ServiceDescriptor, ...]:
        """Return all descriptors matching ``capability`` (case-insensitive)."""
        key = capability.strip().lower()
        return tuple(
            d for d in self._by_name.values() if d.capability.lower() == key
        )

    def has(self, name: str) -> bool:
        """Return True when ``name`` is registered."""
        return name.strip().lower() in self._by_name

    def list_services(self) -> tuple[ServiceDescriptor, ...]:
        """Return all descriptors in registration order (stable by name)."""
        return tuple(
            self._by_name[k] for k in sorted(self._by_name.keys())
        )

    def list_capabilities(self) -> tuple[str, ...]:
        """Return unique capability names sorted alphabetically."""
        caps = {d.capability for d in self._by_name.values()}
        return tuple(sorted(caps, key=str.lower))

    def require(self, name: str) -> Any:
        """Alias for :meth:`get` — raises if missing."""
        return self.get(name)

    def __len__(self) -> int:
        return len(self._by_name)

    def __contains__(self, name: object) -> bool:
        if not isinstance(name, str):
            return False
        return self.has(name)
