"""Period / basis / unit / currency compatibility for derivation.

Explicit unit-scale conversion to ACTUAL is allowed.
FX conversion is not supported in this package — currency mismatch is
unavailable (CV-001 / financial integrity: no silent FX).
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date

from financial.derivation.models import DerivationInput, PeriodRule

__all__ = [
    "ALLOWED_ACCOUNTING_BASIS",
    "UNIT_SCALE_TO_ACTUAL",
    "unit_scale_factor",
    "CompatibilityError",
    "CompatibleInputs",
    "assess_compatibility",
]

ALLOWED_ACCOUNTING_BASIS = frozenset({"consolidated", "standalone"})

# Explicit multiply-to-ACTUAL factors (no FX). Aliases match integrity gates.
UNIT_SCALE_TO_ACTUAL: dict[str, float] = {
    "actual": 1.0,
    "absolute": 1.0,
    "units": 1.0,
    "unit": 1.0,
    "thousand": 1_000.0,
    "thousands": 1_000.0,
    "million": 1_000_000.0,
    "millions": 1_000_000.0,
    "billion": 1_000_000_000.0,
    "billions": 1_000_000_000.0,
    "lakh": 100_000.0,
    "lakhs": 100_000.0,
    "crore": 10_000_000.0,
    "crores": 10_000_000.0,
}


class CompatibilityError(Exception):
    """Input set is not compatible for a registered formula."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def unit_scale_factor(unit_scale: str | None) -> float | None:
    """Return multiply-to-ACTUAL factor, or None if unknown/missing."""
    if unit_scale is None or not str(unit_scale).strip():
        return None
    return UNIT_SCALE_TO_ACTUAL.get(str(unit_scale).strip().lower())


class CompatibleInputs:
    """Converted numeric inputs plus a compatibility snapshot."""

    def __init__(
        self,
        values: dict[str, float],
        refs: tuple[dict, ...],
        *,
        unit_scale: str | None,
        currency: str | None,
        accounting_basis: str | None,
        period_type: str | None,
        converted_to_actual: bool,
    ) -> None:
        self.values = values
        self.refs = refs
        self.unit_scale = unit_scale
        self.currency = currency
        self.accounting_basis = accounting_basis
        self.period_type = period_type
        self.converted_to_actual = converted_to_actual

    def snapshot(self) -> dict[str, object]:
        return {
            "unit_scale": self.unit_scale,
            "currency": self.currency,
            "accounting_basis": self.accounting_basis,
            "period_type": self.period_type,
            "converted_to_actual": self.converted_to_actual,
        }


def assess_compatibility(
    inputs: Sequence[DerivationInput],
    *,
    period_rule: PeriodRule,
) -> CompatibleInputs:
    _check_periods(inputs, period_rule)
    basis = _check_accounting_basis(inputs)
    currency = _check_currency(inputs)
    unit_scale, converted, values, refs = _convert_units(inputs)
    period_type = _common_period_type(inputs)
    return CompatibleInputs(
        values,
        refs,
        unit_scale=unit_scale,
        currency=currency,
        accounting_basis=basis,
        period_type=period_type,
        converted_to_actual=converted,
    )


def _common_period_type(inputs: Sequence[DerivationInput]) -> str | None:
    types = {item.period_type_key for item in inputs if item.period_type_key}
    if len(types) == 1:
        return next(iter(types))
    return None


def _check_periods(inputs: Sequence[DerivationInput], period_rule: PeriodRule) -> None:
    types = [item.period_type_key for item in inputs]
    ends = [item.period_end for item in inputs]
    specified_types = [t for t in types if t is not None]
    specified_ends = [e for e in ends if e is not None]

    if specified_types and len(specified_types) != len(inputs):
        raise CompatibilityError("period_mismatch")
    if specified_types and len(set(specified_types)) > 1:
        raise CompatibilityError("period_mismatch")

    if period_rule is PeriodRule.SAME_PERIOD:
        if specified_ends and len(specified_ends) != len(inputs):
            raise CompatibilityError("period_mismatch")
        if specified_ends and len(set(specified_ends)) > 1:
            raise CompatibilityError("period_mismatch")
        return

    if period_rule is PeriodRule.SAME_PERIOD_TYPE:
        return

    # GROWTH: period_type required and identical; period_end required and distinct.
    if any(t is None for t in types) or len(set(types)) != 1:
        raise CompatibilityError("period_mismatch")
    if any(e is None for e in ends):
        raise CompatibilityError("period_mismatch")
    unique_ends: set[date] = set(ends)  # type: ignore[arg-type]
    if len(unique_ends) != len(ends):
        raise CompatibilityError("period_mismatch")


def _check_accounting_basis(inputs: Sequence[DerivationInput]) -> str | None:
    raw = [item.accounting_basis_key for item in inputs]
    specified = [b for b in raw if b is not None]
    if not specified:
        return None
    if len(specified) != len(inputs):
        raise CompatibilityError("accounting_basis_mismatch")
    invalid = [b for b in specified if b not in ALLOWED_ACCOUNTING_BASIS]
    if invalid:
        raise CompatibilityError("accounting_basis_mismatch")
    if len(set(specified)) > 1:
        raise CompatibilityError("accounting_basis_mismatch")
    return specified[0]


def _check_currency(inputs: Sequence[DerivationInput]) -> str | None:
    codes = [item.currency_key for item in inputs]
    specified = [c for c in codes if c is not None]
    if not specified:
        return None
    if len(specified) != len(inputs):
        raise CompatibilityError("currency_mismatch")
    if len(set(specified)) > 1:
        raise CompatibilityError("currency_mismatch")
    return specified[0]


def _convert_units(
    inputs: Sequence[DerivationInput],
) -> tuple[str | None, bool, dict[str, float], tuple[dict, ...]]:
    keys = [item.unit_scale_key for item in inputs]
    specified = [k for k in keys if k is not None]
    if specified and len(specified) != len(inputs):
        raise CompatibilityError("unit_mismatch")

    factors: list[float] = []
    for key in keys:
        if key is None:
            factors.append(1.0)
            continue
        factor = unit_scale_factor(key)
        if factor is None:
            raise CompatibilityError("unit_mismatch")
        factors.append(factor)

    scales_differ = len(set(factors)) > 1
    if scales_differ:
        values = {
            item.field_id: float(item.value) * factor  # type: ignore[arg-type]
            for item, factor in zip(inputs, factors, strict=True)
        }
        refs = tuple(
            item.to_ref(converted_value=values[item.field_id])
            for item in inputs
        )
        return "actual", True, values, refs

    values = {item.field_id: float(item.value) for item in inputs}  # type: ignore[arg-type]
    refs = tuple(item.to_ref(converted_value=None) for item in inputs)
    unit = specified[0] if specified else None
    return unit, False, values, refs
