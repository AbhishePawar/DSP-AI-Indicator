"""Base scaffolding for Data Engine provider adapters.

An adapter is a concrete implementation of one of the abstract ports in
``data_engine.ports`` for a specific external data source — a market-data
vendor, a fundamentals API, and so on. No concrete adapter is implemented
in this package: this module only defines the shared shape every future
adapter should follow.

Concrete adapters (e.g. a Yahoo Finance adapter implementing
``MarketDataPort``) are intentionally out of scope for this sprint. They
will live in their own modules under this package once a real provider
integration is undertaken, each subclassing ``BaseAdapter`` together with
the specific port(s) it implements, e.g.::

    class YahooFinanceAdapter(BaseAdapter, MarketDataPort):
        ...
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
