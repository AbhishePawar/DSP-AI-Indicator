"""Base scaffolding for Data Engine provider adapters.

An adapter is a concrete implementation of one of the abstract ports in
``data_engine.ports`` for a specific external data source. This module
only defines the shared shape every adapter follows.

Concrete official adapters (FRED, and exchange/filing adapters elsewhere
in the package) subclass ``BaseAdapter`` together with the port they
implement. Commercial market-data vendors are not implemented here.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

__all__ = ["BaseAdapter"]


class BaseAdapter(ABC):
    """Common shape every provider adapter should implement.

    ``BaseAdapter`` is deliberately minimal: it only standardizes how an
    adapter identifies itself for registration. Adapters combine this
    with one or more port interfaces from ``data_engine.ports``.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the canonical name this adapter registers under."""
