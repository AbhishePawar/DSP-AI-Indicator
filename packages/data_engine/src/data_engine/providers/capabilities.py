"""Structured provider capability model.

Represents what a provider can supply as a single frozenset of
``DataCapability`` flags rather than one boolean field per capability, so
registry filtering (see
:class:`~data_engine.providers.registry.ProviderRegistry`) is a set
operation instead of a chain of ``if`` statements, and adding a new
capability in the future means adding one ``DataCapability`` member —
never a dataclass field, and never a constructor signature change.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from data_engine.providers.enums import DataCapability

__all__ = ["ProviderCapabilities"]


@dataclass(frozen=True, slots=True)
class ProviderCapabilities:
    """Structured, set-based description of what a provider can supply.

    Attributes:
        flags: The set of capabilities this provider declares support
            for. Prefer the named boolean properties (``market_data``,
            ``crypto``, etc.) or ``has``/``has_all``/``has_any`` over
            constructing or reading this set directly.
    """

    flags: frozenset[DataCapability] = field(default_factory=frozenset)

    @classmethod
    def from_flags(
        cls,
        *,
        market_data: bool = False,
        fundamentals: bool = False,
        economic_data: bool = False,
        alternative_data: bool = False,
        intraday: bool = False,
        daily: bool = False,
        options: bool = False,
        crypto: bool = False,
        forex: bool = False,
        news: bool = False,
        etf: bool = False,
        indices: bool = False,
        mutual_funds: bool = False,
    ) -> ProviderCapabilities:
        """Build capabilities from individual named booleans.

        This is the ergonomic constructor most call sites should use:
        it reads like the flat list of capability flags a provider
        author expects to fill in, while still producing the
        structured, set-based representation internally.

        Args:
            market_data: Whether the provider supplies market/price data.
            fundamentals: Whether it supplies financial statements.
            economic_data: Whether it supplies macroeconomic data.
            alternative_data: Whether it supplies alternative/behavioral
                data.
            intraday: Whether it supplies intraday price bars.
            daily: Whether it supplies daily price bars.
            options: Whether it supplies options data.
            crypto: Whether it supplies cryptocurrency data.
            forex: Whether it supplies foreign-exchange data.
            news: Whether it supplies news data.
            etf: Whether it supplies ETF data.
            indices: Whether it supplies index data.
            mutual_funds: Whether it supplies mutual fund data.

        Returns:
            A ``ProviderCapabilities`` instance with exactly the named
            flags set.
        """
        selected = {
            DataCapability.MARKET_DATA: market_data,
            DataCapability.FUNDAMENTALS: fundamentals,
            DataCapability.ECONOMIC_DATA: economic_data,
            DataCapability.ALTERNATIVE_DATA: alternative_data,
            DataCapability.INTRADAY: intraday,
            DataCapability.DAILY: daily,
            DataCapability.OPTIONS: options,
            DataCapability.CRYPTO: crypto,
            DataCapability.FOREX: forex,
            DataCapability.NEWS: news,
            DataCapability.ETF: etf,
            DataCapability.INDICES: indices,
            DataCapability.MUTUAL_FUNDS: mutual_funds,
        }
        flags = frozenset(
            capability for capability, enabled in selected.items() if enabled
        )
        return cls(flags=flags)

    def has(self, capability: DataCapability) -> bool:
        """Return whether a single capability is supported."""
        return capability in self.flags

    def has_all(self, *capabilities: DataCapability) -> bool:
        """Return whether every given capability is supported."""
        return set(capabilities).issubset(self.flags)

    def has_any(self, *capabilities: DataCapability) -> bool:
        """Return whether at least one given capability is supported."""
        return bool(set(capabilities) & self.flags)

    @property
    def market_data(self) -> bool:
        """Whether this provider supplies market/price data."""
        return self.has(DataCapability.MARKET_DATA)

    @property
    def fundamentals(self) -> bool:
        """Whether this provider supplies financial statements."""
        return self.has(DataCapability.FUNDAMENTALS)

    @property
    def economic_data(self) -> bool:
        """Whether this provider supplies macroeconomic data."""
        return self.has(DataCapability.ECONOMIC_DATA)

    @property
    def alternative_data(self) -> bool:
        """Whether this provider supplies alternative/behavioral data."""
        return self.has(DataCapability.ALTERNATIVE_DATA)

    @property
    def intraday(self) -> bool:
        """Whether this provider supplies intraday price bars."""
        return self.has(DataCapability.INTRADAY)

    @property
    def daily(self) -> bool:
        """Whether this provider supplies daily price bars."""
        return self.has(DataCapability.DAILY)

    @property
    def options(self) -> bool:
        """Whether this provider supplies options data."""
        return self.has(DataCapability.OPTIONS)

    @property
    def crypto(self) -> bool:
        """Whether this provider supplies cryptocurrency data."""
        return self.has(DataCapability.CRYPTO)

    @property
    def forex(self) -> bool:
        """Whether this provider supplies foreign-exchange data."""
        return self.has(DataCapability.FOREX)

    @property
    def news(self) -> bool:
        """Whether this provider supplies news data."""
        return self.has(DataCapability.NEWS)

    @property
    def etf(self) -> bool:
        """Whether this provider supplies ETF data."""
        return self.has(DataCapability.ETF)

    @property
    def indices(self) -> bool:
        """Whether this provider supplies index data."""
        return self.has(DataCapability.INDICES)

    @property
    def mutual_funds(self) -> bool:
        """Whether this provider supplies mutual fund data."""
        return self.has(DataCapability.MUTUAL_FUNDS)
