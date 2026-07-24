"""Analyzer registry for discovery and instantiation."""

from __future__ import annotations

from typing import TypeVar

from core.registry import Registry
from economic.analyzers.base import Analyzer
from economic.analyzers.gdp import GdpAnalyzer
from economic.analyzers.inflation import InflationAnalyzer
from economic.analyzers.interest_rate import InterestRateAnalyzer
from economic.analyzers.liquidity import LiquidityAnalyzer
from economic.analyzers.pmi import PmiAnalyzer

T = TypeVar("T", bound=Analyzer)

_REGISTRY: Registry[type[Analyzer]] = Registry(kind="analyzer")
_REGISTRY.register("gdp", GdpAnalyzer)
_REGISTRY.register("inflation", InflationAnalyzer)
_REGISTRY.register("interest_rate", InterestRateAnalyzer)
_REGISTRY.register("pmi", PmiAnalyzer)
_REGISTRY.register("liquidity", LiquidityAnalyzer)


def register(name: str, analyzer_cls: type[T]) -> type[T]:
    """Register an analyzer class under a canonical name."""
    return _REGISTRY.register(name, analyzer_cls)


def get(name: str) -> Analyzer:
    """Instantiate a registered analyzer by name."""
    analyzer_cls = _REGISTRY.get(name)
    return analyzer_cls()


def list_analyzers() -> list[str]:
    """Return sorted names of all registered analyzers."""
    return _REGISTRY.list_names()
