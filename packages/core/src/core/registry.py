"""Generic, name-keyed registry infrastructure.

This module provides a minimal registry any platform engine can use to
register and discover pluggable implementations by name — indicators,
valuation models, AI agents, data providers, and similar extension points.
It has no knowledge of what is being registered; domain-specific behavior
(e.g. instantiating an indicator with a period) belongs to the engine that
owns the registry instance, not to this module.

This is the shared infrastructure behind the Extensibility design
principle: every engine that needs "register a new X by name, discover
all registered X, look one up" should build on :class:`Registry` rather
than reimplementing the same dict-based pattern independently.
"""

from __future__ import annotations

from typing import Generic, TypeVar

T = TypeVar("T")


class Registry(Generic[T]):
    """A generic, name-keyed registry for pluggable implementations.

    Names are matched case-insensitively. Registering the same name with
    an identical item is a no-op; registering the same name with a
    different item is treated as a conflict.
    """

    __slots__ = ("_items", "_kind")

    def __init__(self, *, kind: str = "item") -> None:
        """Initialize an empty registry.

        Args:
            kind: Human-readable label for what this registry stores,
                used only to phrase error messages (e.g. ``"indicator"``,
                ``"valuation model"``, ``"data provider"``).
        """
        self._items: dict[str, T] = {}
        self._kind = kind

    def register(self, name: str, item: T) -> T:
        """Register an item under a canonical name.

        Args:
            name: Identifier to register the item under. Matching is
                case-insensitive.
            item: The value to register (a class, factory, instance, or
                any other object the caller chooses to store).

        Returns:
            The registered item, unchanged (convenient for decorator use).

        Raises:
            ValueError: If ``name`` is already registered to a different
                item.
        """
        key = name.lower()
        existing = self._items.get(key)
        if existing is not None and existing is not item:
            msg = f"{self._kind} '{key}' is already registered to {existing!r}"
            raise ValueError(msg)
        self._items[key] = item
        return item

    def get(self, name: str) -> T:
        """Look up a registered item by name.

        Args:
            name: Identifier to look up. Matching is case-insensitive.

        Returns:
            The item registered under ``name``.

        Raises:
            KeyError: If ``name`` is not registered.
        """
        key = name.lower()
        if key not in self._items:
            available = ", ".join(sorted(self._items))
            msg = f"Unknown {self._kind} '{name}'. Available: {available}"
            raise KeyError(msg)
        return self._items[key]

    def list_names(self) -> list[str]:
        """Return the sorted names of all registered items."""
        return sorted(self._items)

    def __contains__(self, name: str) -> bool:
        """Return whether ``name`` is registered (case-insensitive)."""
        return name.lower() in self._items

    def __len__(self) -> int:
        """Return the number of registered items."""
        return len(self._items)
