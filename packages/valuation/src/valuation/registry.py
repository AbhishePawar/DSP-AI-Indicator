"""Valuation method registry for discovery and instantiation."""

from __future__ import annotations

from typing import TypeVar

from core.registry import Registry
from valuation.methods.base import ValuationMethodRunner
from valuation.methods.book_value import BookValueMethod
from valuation.methods.dcf import DcfMethod
from valuation.methods.earnings_multiple import EarningsMultipleMethod
from valuation.methods.owner_earnings import OwnerEarningsMethod
from valuation.methods.residual_income import ResidualIncomeMethod

T = TypeVar("T", bound=ValuationMethodRunner)

_REGISTRY: Registry[type[ValuationMethodRunner]] = Registry(kind="valuation method")
_REGISTRY.register("dcf", DcfMethod)
_REGISTRY.register("owner_earnings", OwnerEarningsMethod)
_REGISTRY.register("earnings_multiple", EarningsMultipleMethod)
_REGISTRY.register("book_value", BookValueMethod)
_REGISTRY.register("residual_income", ResidualIncomeMethod)


def register(name: str, method_cls: type[T]) -> type[T]:
    """Register a valuation method class under a canonical name."""
    return _REGISTRY.register(name, method_cls)


def get(name: str) -> ValuationMethodRunner:
    """Instantiate a registered valuation method by name."""
    method_cls = _REGISTRY.get(name)
    return method_cls()


def list_methods() -> list[str]:
    """Return sorted names of all registered valuation methods."""
    return _REGISTRY.list_names()
