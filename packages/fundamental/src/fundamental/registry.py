"""Analyzer registry for discovery and instantiation.

This module is the Fundamental Engine's own name -> ``Analyzer`` class
registry, following exactly the pattern established by ``dsp.registry``
for indicators: the underlying storage and lookup mechanism is Core's
generic :class:`core.registry.Registry`, so both engines share the same
"register by name, discover, look up" infrastructure instead of each
reimplementing it.

Unlike an indicator (which needs a ``period`` to be instantiated), every
analyzer takes no constructor arguments, so :func:`get` simply
instantiates the registered class.
"""

from __future__ import annotations

from typing import TypeVar

from core.registry import Registry
from fundamental.analyzers.base import Analyzer
from fundamental.analyzers.growth import GrowthAnalyzer
from fundamental.analyzers.leverage import LeverageAnalyzer
from fundamental.analyzers.profitability import ProfitabilityAnalyzer
from fundamental.analyzers.quality import QualityAnalyzer

T = TypeVar("T", bound=Analyzer)

_REGISTRY: Registry[type[Analyzer]] = Registry(kind="analyzer")
_REGISTRY.register("profitability", ProfitabilityAnalyzer)
_REGISTRY.register("growth", GrowthAnalyzer)
_REGISTRY.register("leverage", LeverageAnalyzer)
_REGISTRY.register("quality", QualityAnalyzer)


def register(name: str, analyzer_cls: type[T]) -> type[T]:
    """Register an analyzer class under a canonical name.

    Args:
        name: Unique identifier for the analyzer.
        analyzer_cls: Analyzer subclass to register.

    Returns:
        The registered analyzer class (for use as a decorator).

    Raises:
        ValueError: If the name is already registered to a different
            class.
    """
    return _REGISTRY.register(name, analyzer_cls)


def get(name: str) -> Analyzer:
    """Instantiate a registered analyzer by name.

    Args:
        name: Canonical analyzer identifier (e.g. ``"profitability"``).

    Returns:
        A new analyzer instance.

    Raises:
        KeyError: If the analyzer name is not registered.
    """
    analyzer_cls = _REGISTRY.get(name)
    return analyzer_cls()


def list_analyzers() -> list[str]:
    """Return sorted names of all registered analyzers."""
    return _REGISTRY.list_names()
