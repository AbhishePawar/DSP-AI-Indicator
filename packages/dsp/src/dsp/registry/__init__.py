"""Indicator registry for discovery and instantiation.

This module is the Indicator Engine's own name -> ``Indicator`` class
registry. It contains all indicator-specific behavior (how to instantiate
an indicator with a period); the underlying storage and lookup mechanism
is Core's generic :class:`core.registry.Registry`, so every engine that
needs the same "register by name, discover, look up" capability builds
on the same shared infrastructure instead of reimplementing it.
"""

from collections.abc import Callable
from typing import TypeVar

from core.registry import Registry
from dsp.indicators.base import Indicator
from dsp.indicators.momentum import RSI
from dsp.indicators.moving_averages import EMA, SMA, WMA

T = TypeVar("T", bound=Indicator)

_REGISTRY: Registry[type[Indicator]] = Registry(kind="indicator")
_REGISTRY.register("sma", SMA)
_REGISTRY.register("ema", EMA)
_REGISTRY.register("wma", WMA)
_REGISTRY.register("rsi", RSI)


def register(name: str, indicator_cls: type[T]) -> type[T]:
    """Register an indicator class under a canonical name.

    Args:
        name: Unique identifier for the indicator.
        indicator_cls: Indicator subclass to register.

    Returns:
        The registered indicator class (for use as a decorator).

    Raises:
        ValueError: If the name is already registered to a different class.
    """
    return _REGISTRY.register(name, indicator_cls)


def get(name: str, period: int) -> Indicator:
    """Instantiate a registered indicator by name.

    Args:
        name: Canonical indicator identifier (e.g., ``"sma"``).
        period: Lookback window size.

    Returns:
        Configured indicator instance.

    Raises:
        KeyError: If the indicator name is not registered.
    """
    indicator_cls = _REGISTRY.get(name)
    return indicator_cls(period)


def list_indicators() -> list[str]:
    """Return sorted names of all registered indicators."""
    return _REGISTRY.list_names()


def compute(name: str, prices: object, period: int) -> object:
    """Compute a registered indicator by name.

    Args:
        name: Canonical indicator identifier.
        prices: One-dimensional price observations.
        period: Lookback window size.

    Returns:
        Computed indicator values.
    """
    return get(name, period).compute(prices)


def indicator_factory(name: str) -> Callable[[int], Indicator]:
    """Return a factory function that creates indicators by period.

    Args:
        name: Canonical indicator identifier.

    Returns:
        Callable accepting a period and returning an indicator instance.
    """

    def factory(period: int) -> Indicator:
        return get(name, period)

    return factory
