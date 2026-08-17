"""Canonical financial derivation engine.

NEVER GUESS DATA.
CALCULATE ONLY WHEN THE FORMULA AND ALL REQUIRED VERIFIED INPUTS ARE KNOWN.
LABEL CALCULATED VALUES AS CALCULATED.
OTHERWISE RETURN UNAVAILABLE.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence

from financial.derivation.compatibility import (
    CompatibilityError,
    assess_compatibility,
)
from financial.derivation.formulas import get_formula
from financial.derivation.models import (
    DERIVATION_ENGINE_VERSION,
    DerivationInput,
    DerivedFinancialValue,
    FinancialValueStatus,
)

__all__ = ["FinancialDerivationEngine", "as_reported", "derive"]


def _unavailable(
    reason: str,
    *,
    formula_id: str | None = None,
    formula: str | None = None,
    inputs: Sequence[Mapping] = (),
    compatibility: Mapping[str, object] | None = None,
) -> DerivedFinancialValue:
    return DerivedFinancialValue(
        status=FinancialValueStatus.UNAVAILABLE,
        value=None,
        formula_id=formula_id,
        formula=formula,
        inputs=tuple(dict(item) for item in inputs),
        unavailable_reason=reason,
        calculation_version=DERIVATION_ENGINE_VERSION,
        compatibility=dict(compatibility or {}),
    )


def _is_valid_number(value: float | None) -> bool:
    if value is None:
        return False
    try:
        number = float(value)
    except (TypeError, ValueError):
        return False
    return math.isfinite(number)


class FinancialDerivationEngine:
    """Fail-closed derivation: reported, calculated, or unavailable."""

    version = DERIVATION_ENGINE_VERSION

    def reported(self, item: DerivationInput) -> DerivedFinancialValue:
        """Preserve a provider-reported value. Never relabel calculated as reported."""
        if item.status is FinancialValueStatus.CALCULATED:
            return _unavailable(
                "calculated_cannot_be_reported",
                inputs=(item.to_ref(),),
            )
        if item.status is FinancialValueStatus.UNAVAILABLE or not _is_valid_number(
            item.value
        ):
            return _unavailable(
                "missing_input",
                inputs=(item.to_ref(),),
            )
        return DerivedFinancialValue(
            status=FinancialValueStatus.REPORTED,
            value=float(item.value),  # type: ignore[arg-type]
            formula_id=None,
            formula=None,
            inputs=(item.to_ref(),),
            unit_scale=item.unit_scale_key,
            currency=item.currency_key,
            accounting_basis=item.accounting_basis_key,
            period_type=item.period_type_key,
            calculation_version=self.version,
        )

    def derive(
        self,
        formula_id: str,
        inputs: Mapping[str, DerivationInput] | Sequence[DerivationInput],
    ) -> DerivedFinancialValue:
        spec = get_formula(formula_id)
        if spec is None:
            return _unavailable("unknown_formula", formula_id=formula_id)

        by_id = _index_inputs(inputs)
        ordered: list[DerivationInput] = []
        refs: list[dict] = []
        for name in spec.required_inputs:
            item = by_id.get(name)
            if item is None:
                return _unavailable(
                    "missing_input",
                    formula_id=spec.formula_id,
                    formula=spec.formula,
                    inputs=tuple(i.to_ref() for i in by_id.values()),
                )
            refs.append(item.to_ref())
            if item.status is FinancialValueStatus.UNAVAILABLE:
                return _unavailable(
                    "missing_input",
                    formula_id=spec.formula_id,
                    formula=spec.formula,
                    inputs=tuple(refs),
                )
            if not _is_valid_number(item.value):
                return _unavailable(
                    "missing_input",
                    formula_id=spec.formula_id,
                    formula=spec.formula,
                    inputs=tuple(refs),
                )
            ordered.append(item)

        try:
            compatible = assess_compatibility(ordered, period_rule=spec.period_rule)
        except CompatibilityError as exc:
            return _unavailable(
                exc.reason,
                formula_id=spec.formula_id,
                formula=spec.formula,
                inputs=tuple(item.to_ref() for item in ordered),
            )

        result = spec.compute(compatible.values)
        if result is None:
            return _unavailable(
                "division_by_zero",
                formula_id=spec.formula_id,
                formula=spec.formula,
                inputs=compatible.refs,
                compatibility=compatible.snapshot(),
            )

        return DerivedFinancialValue(
            status=FinancialValueStatus.CALCULATED,
            value=result,
            formula_id=spec.formula_id,
            formula=spec.formula,
            inputs=compatible.refs,
            calculation_version=self.version,
            unit_scale="ratio" if spec.output_kind == "ratio" else compatible.unit_scale,
            currency=compatible.currency,
            accounting_basis=compatible.accounting_basis,
            period_type=compatible.period_type,
            compatibility=compatible.snapshot(),
        )


def _index_inputs(
    inputs: Mapping[str, DerivationInput] | Sequence[DerivationInput],
) -> dict[str, DerivationInput]:
    if isinstance(inputs, Mapping):
        return {str(key): value for key, value in inputs.items()}
    indexed: dict[str, DerivationInput] = {}
    for item in inputs:
        indexed[item.field_id] = item
    return indexed


_ENGINE = FinancialDerivationEngine()


def as_reported(item: DerivationInput) -> DerivedFinancialValue:
    return _ENGINE.reported(item)


def derive(
    formula_id: str,
    inputs: Mapping[str, DerivationInput] | Sequence[DerivationInput],
) -> DerivedFinancialValue:
    return _ENGINE.derive(formula_id, inputs)
