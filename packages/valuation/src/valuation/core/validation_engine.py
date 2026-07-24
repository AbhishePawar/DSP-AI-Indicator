"""Reusable validation utilities for valuation inputs."""

from __future__ import annotations

import math
from typing import Mapping

from valuation.core.errors import ValidationError
from valuation.core.interfaces import ValidationProvider
from valuation.core.result_models import ValidationSummary

__all__ = ["ValidationEngine", "FieldRule"]


class FieldRule:
    """Declarative field rule (documentation helper)."""

    POSITIVE = "positive"
    NON_NEGATIVE = "non_negative"
    UNIT_INTERVAL = "unit_interval"
    SHARES = "shares"


class ValidationEngine(ValidationProvider):
    """Shared validation helpers returning :class:`ValidationSummary`."""

    def summarize(
        self, inputs: Mapping[str, float | int | None]
    ) -> ValidationSummary:
        """Collect validation issues without raising."""
        errors: list[str] = []
        checks: list[str] = []
        warnings: list[str] = []

        def num(name: str) -> float | None:
            if name not in inputs or inputs[name] is None:
                return None
            v = float(inputs[name])  # type: ignore[arg-type]
            if math.isnan(v):
                errors.append(f"{name} is NaN")
                return None
            if math.isinf(v):
                errors.append(f"{name} is infinite")
                return None
            return v

        # Resolve each field once (avoids duplicate NaN/inf error messages).
        shares = num("shares_outstanding")
        if shares is None:
            shares = num("share_count")
        if shares is not None:
            if shares <= 0:
                errors.append(f"share count must be positive, got {shares}")
            else:
                checks.append("shares > 0")

        rates: dict[str, float | None] = {
            "wacc": num("wacc"),
            "cost_of_equity": num("cost_of_equity"),
            "discount_rate": num("discount_rate"),
        }
        for rate_name, rate in rates.items():
            if rate is not None:
                if rate <= 0:
                    errors.append(f"{rate_name} must be > 0, got {rate}")
                else:
                    checks.append(f"{rate_name} > 0")

        tg = num("terminal_growth")
        disc = rates["wacc"]
        if disc is None:
            disc = rates["cost_of_equity"]
        if disc is None:
            disc = rates["discount_rate"]
        if tg is not None and disc is not None and tg >= disc:
            errors.append(
                f"terminal_growth must be < discount rate ({tg} >= {disc})"
            )
        elif tg is not None and disc is not None:
            checks.append("terminal_growth < discount")

        tax = num("tax_rate")
        if tax is not None:
            if not (0.0 <= tax < 1.0):
                errors.append(f"tax_rate out of range: {tax}")
            else:
                checks.append("tax_rate in [0, 1)")

        for name in ("book_value", "revenue"):
            v = num(name)
            if v is not None:
                if v <= 0:
                    errors.append(f"{name} must be positive, got {v}")
                else:
                    checks.append(f"{name} > 0")

        for name in ("debt", "cash"):
            v = num(name)
            if v is not None:
                if v < 0:
                    errors.append(f"{name} must be non-negative, got {v}")
                else:
                    checks.append(f"{name} >= 0")

        growth = num("growth")
        if growth is not None and (growth < -0.5 or growth > 0.5):
            warnings.append(f"growth assumption unusual: {growth}")

        years = num("forecast_years")
        if years is not None:
            if years < 1 or years > 30:
                errors.append(f"forecast_years out of range: {years}")
            else:
                checks.append("forecast_years in [1, 30]")

        return ValidationSummary(
            ok=not errors,
            checks=tuple(checks),
            errors=tuple(errors),
            warnings=tuple(warnings),
        )

    def validate(self, inputs: Mapping[str, float | int | None]) -> ValidationSummary:
        """Validate a generic numeric input mapping.

        Recognized keys (when present):
        shares_outstanding/share_count, growth, terminal_growth, wacc,
        cost_of_equity/discount_rate, tax_rate, book_value, debt, cash,
        revenue, forecast_years.

        Raises:
            ValidationError: when hard validation errors are present.
        """
        summary = self.summarize(inputs)
        if not summary.ok:
            raise ValidationError(
                "Validation failed: " + "; ".join(summary.errors)
            )
        return summary

    def require_positive(self, value: float, name: str) -> None:
        """Raise if ``value`` is not strictly positive."""
        if value <= 0 or math.isnan(value) or math.isinf(value):
            raise ValidationError(f"{name} must be positive, got {value}")

    def require_non_negative(self, value: float, name: str) -> None:
        """Raise if ``value`` is negative or non-finite."""
        if value < 0 or math.isnan(value) or math.isinf(value):
            raise ValidationError(f"{name} must be non-negative, got {value}")
