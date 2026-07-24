"""Provider factory for the Data Engine.

Whereas :class:`~data_engine.providers.registry.ProviderRegistry` tracks
already-constructed adapter instances, ``ProviderFactory`` tracks *how to
construct* an adapter for a given provider id from a plain configuration
mapping (e.g. values loaded from environment variables or a config
file). This keeps adapter construction — which may need API keys, base
URLs, timeouts, and so on — decoupled from adapter usage.

No builder is registered here for any real provider. That is left to
whichever module defines a concrete adapter.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from core.registry import Registry
from data_engine.adapters import BaseAdapter

__all__ = ["ProviderBuilder", "ProviderFactory"]

ProviderBuilder = Callable[[Mapping[str, Any]], BaseAdapter]
"""A callable that builds a concrete adapter instance from configuration."""


class ProviderFactory:
    """Builds provider adapter instances from configuration.

    Registering a builder here does not register the resulting adapter
    with a ``ProviderRegistry`` — construction and registration are
    deliberately kept separate so each can be tested and reasoned about
    independently. See ``packages/data_engine/README.md`` for the
    expected wiring sequence.
    """

    def __init__(self) -> None:
        """Initialize an empty provider factory."""
        self._builders: Registry[ProviderBuilder] = Registry(kind="provider builder")

    def register_builder(
        self, provider_id: str, builder: ProviderBuilder
    ) -> ProviderBuilder:
        """Register a callable that builds an adapter from configuration.

        Args:
            provider_id: Identifier the builder is registered under.
                Should match the ``provider_id`` the resulting
                adapter's ``ProviderMetadata`` will declare.
            builder: A callable accepting a configuration mapping and
                returning a constructed ``BaseAdapter`` instance.

        Returns:
            The registered builder, unchanged (convenient for
            decorator use).

        Raises:
            ValueError: If ``provider_id`` is already registered to a
                different builder.
        """
        return self._builders.register(provider_id, builder)

    def create(
        self, provider_id: str, config: Mapping[str, Any] | None = None
    ) -> BaseAdapter:
        """Construct a provider adapter instance from configuration.

        Args:
            provider_id: Identifier of the builder to invoke.
            config: Configuration mapping passed to the builder.
                Defaults to an empty mapping.

        Returns:
            A newly constructed adapter instance.

        Raises:
            KeyError: If no builder is registered under ``provider_id``.
        """
        builder = self._builders.get(provider_id)
        return builder(config or {})

    def is_registered(self, provider_id: str) -> bool:
        """Return whether a builder is registered for ``provider_id``."""
        return provider_id in self._builders
