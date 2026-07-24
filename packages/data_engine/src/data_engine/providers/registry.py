"""Provider registration and discovery for the Data Engine.

Tracks *which* adapters are available and *what* they can do, built on
Core's generic ``core.registry.Registry`` rather than a bespoke dict —
the same pattern ``dsp.registry`` already uses for indicators. It has no
knowledge of any specific vendor: adapters are registered by whoever
wires up the engine, not by this module, and callers discover/select
providers by id or by declared capability.
"""

from __future__ import annotations

from core.registry import Registry
from data_engine.adapters import BaseAdapter
from data_engine.exceptions import DataEngineError
from data_engine.providers.enums import DataCapability, ProviderStatus
from data_engine.providers.metadata import ProviderMetadata

__all__ = ["ProviderRegistry"]

_UNRANKED_PRIORITY = float("inf")


class ProviderRegistry:
    """Name-keyed registry of provider adapters and their metadata.

    Wraps ``core.registry.Registry`` to additionally track each
    provider's ``ProviderMetadata``, so callers can discover which
    registered provider(s) support a given capability, or select the
    best-ranked one, without ever importing a concrete adapter.
    """

    def __init__(self) -> None:
        """Initialize an empty provider registry."""
        self._adapters: Registry[BaseAdapter] = Registry(kind="provider")
        self._metadata: dict[str, ProviderMetadata] = {}

    def register(
        self, adapter: BaseAdapter, metadata: ProviderMetadata
    ) -> BaseAdapter:
        """Register a provider adapter with its metadata.

        Args:
            adapter: The adapter instance to register.
            metadata: Structured metadata describing the adapter.

        Returns:
            The registered adapter, unchanged.

        Raises:
            ValueError: If ``metadata.provider_id`` is already
                registered to a different adapter.
        """
        self._adapters.register(metadata.provider_id, adapter)
        self._metadata[metadata.provider_id] = metadata
        return adapter

    def get(self, provider_id: str) -> BaseAdapter:
        """Look up a registered adapter by id.

        Args:
            provider_id: Provider id to look up. Matching is
                case-insensitive.

        Returns:
            The registered adapter.

        Raises:
            KeyError: If ``provider_id`` is not registered.
        """
        return self._adapters.get(provider_id)

    def get_metadata(self, provider_id: str) -> ProviderMetadata:
        """Look up a registered provider's metadata.

        Args:
            provider_id: Provider id to look up. Matching is
                case-insensitive.

        Returns:
            The provider's registered metadata.

        Raises:
            KeyError: If ``provider_id`` is not registered.
        """
        self._adapters.get(provider_id)
        return self._metadata[provider_id.strip().lower()]

    def list_names(self) -> list[str]:
        """Return the sorted ids of all registered providers."""
        return self._adapters.list_names()

    def filter_by_capability(self, *capabilities: DataCapability) -> tuple[str, ...]:
        """Return ids of every ACTIVE provider supporting all capabilities.

        Providers whose ``status`` is not ``ProviderStatus.ACTIVE`` are
        excluded from discovery even if their declared capabilities
        match — they remain reachable via ``get``/``get_metadata`` by
        explicit id, since that is a deliberate, direct request rather
        than automatic selection.

        Args:
            *capabilities: One or more capabilities every returned
                provider must support. Passing no capabilities returns
                every ACTIVE provider.

        Returns:
            Provider ids, sorted alphabetically, of every registered,
            active provider whose declared capabilities include all of
            ``capabilities``.
        """
        matches = [
            provider_id
            for provider_id, metadata in self._metadata.items()
            if metadata.status is ProviderStatus.ACTIVE
            and metadata.capabilities.has_all(*capabilities)
        ]
        return tuple(sorted(matches))

    def select_preferred(self, *capabilities: DataCapability) -> BaseAdapter:
        """Select the best-matching registered adapter for capabilities.

        Among ACTIVE providers supporting every requested capability,
        prefers the lowest ``priority`` value (``None`` sorts last),
        breaking ties by provider id for determinism.

        Args:
            *capabilities: Capabilities the selected provider must
                support.

        Returns:
            The selected adapter instance.

        Raises:
            DataEngineError: If no active registered provider supports
                all requested capabilities.
        """
        candidates = self.filter_by_capability(*capabilities)
        if not candidates:
            names = ", ".join(capability.value for capability in capabilities)
            msg = f"No active provider supports required capabilities: {names}"
            raise DataEngineError(msg)

        def sort_key(provider_id: str) -> tuple[float, str]:
            priority = self._metadata[provider_id].priority
            rank = float(priority) if priority is not None else _UNRANKED_PRIORITY
            return (rank, provider_id)

        best_id = min(candidates, key=sort_key)
        return self._adapters.get(best_id)

    def __contains__(self, provider_id: str) -> bool:
        """Return whether ``provider_id`` is registered (case-insensitive)."""
        return provider_id in self._adapters

    def __len__(self) -> int:
        """Return the number of registered providers."""
        return len(self._adapters)
