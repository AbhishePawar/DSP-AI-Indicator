"""Financial field states and derivation provenance models.

Canonical policy: docs/FINANCIAL_DATA_DERIVATION_POLICY.md
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Any, Mapping

from financial.currency import CurrencyCode, CurrencyRef
from financial.metadata import UnitScale
from financial.period import PeriodType

__all__ = [
    "DERIVATION_ENGINE_VERSION",
    "FinancialValueStatus",
    "PeriodRule",
    "DerivationInput",
    "DerivedFinancialValue",
]

DERIVATION_ENGINE_VERSION = "financial-derivation-1.0.0"


class FinancialValueStatus(str, Enum):
    """Terminal state of a financial field (never guess)."""

    REPORTED = "reported"
    CALCULATED = "calculated"
    UNAVAILABLE = "unavailable"


class PeriodRule(str, Enum):
    """How a formula constrains input periods."""

    SAME_PERIOD = "same_period"
    SAME_PERIOD_TYPE = "same_period_type"
    GROWTH = "growth"


def _period_type_value(value: PeriodType | str | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, PeriodType):
        return value.value
    text = str(value).strip().lower()
    return text or None


def _unit_scale_value(value: UnitScale | str | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, UnitScale):
        return value.value
    text = str(value).strip().lower()
    return text or None


def _currency_code(value: CurrencyRef | CurrencyCode | str | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, CurrencyRef):
        return value.code.value
    if isinstance(value, CurrencyCode):
        return value.value
    text = str(value).strip().upper()
    return text or None


@dataclass(frozen=True, slots=True)
class DerivationInput:
    """One verified input to a derivation (or an unavailable slot)."""

    field_id: str
    value: float | None
    status: FinancialValueStatus = FinancialValueStatus.REPORTED
    period_type: PeriodType | str | None = None
    period_end: date | None = None
    fiscal_year: int | None = None
    fiscal_quarter: int | None = None
    unit_scale: UnitScale | str | None = None
    currency: CurrencyRef | CurrencyCode | str | None = None
    accounting_basis: str | None = None
    source: str = ""

    @property
    def period_type_key(self) -> str | None:
        return _period_type_value(self.period_type)

    @property
    def unit_scale_key(self) -> str | None:
        return _unit_scale_value(self.unit_scale)

    @property
    def currency_key(self) -> str | None:
        return _currency_code(self.currency)

    @property
    def accounting_basis_key(self) -> str | None:
        if self.accounting_basis is None:
            return None
        text = str(self.accounting_basis).strip().lower()
        return text or None

    def to_ref(self, *, converted_value: float | None = None) -> dict[str, Any]:
        return {
            "field_id": self.field_id,
            "value": self.value,
            "status": self.status.value,
            "period_type": self.period_type_key,
            "period_end": self.period_end.isoformat() if self.period_end else None,
            "fiscal_year": self.fiscal_year,
            "fiscal_quarter": self.fiscal_quarter,
            "unit_scale": self.unit_scale_key,
            "currency": self.currency_key,
            "accounting_basis": self.accounting_basis_key,
            "source": self.source,
            "converted_value": converted_value,
        }


@dataclass(frozen=True, slots=True)
class DerivedFinancialValue:
    """Result of reporting or deriving a financial field."""

    status: FinancialValueStatus
    value: float | None
    formula_id: str | None = None
    formula: str | None = None
    inputs: tuple[Mapping[str, Any], ...] = ()
    unavailable_reason: str | None = None
    calculation_version: str = DERIVATION_ENGINE_VERSION
    unit_scale: str | None = None
    currency: str | None = None
    accounting_basis: str | None = None
    period_type: str | None = None
    compatibility: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "value": self.value,
            "formula_id": self.formula_id,
            "formula": self.formula,
            "inputs": [dict(item) for item in self.inputs],
            "unavailable_reason": self.unavailable_reason,
            "calculation_version": self.calculation_version,
            "unit_scale": self.unit_scale,
            "currency": self.currency,
            "accounting_basis": self.accounting_basis,
            "period_type": self.period_type,
            "compatibility": dict(self.compatibility),
        }
