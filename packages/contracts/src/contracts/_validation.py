"""Internal structural-validation helpers for domain contracts.

These helpers perform only generic, structural sanity checks: type,
finiteness, numeric range, non-emptiness, and timezone-awareness. They
intentionally contain no business logic and no domain-specific rules.

This module is private to the Contracts package (see the leading
underscore) and is not part of its public API.
"""

from __future__ import annotations

import math
from datetime import datetime

from contracts.exceptions import ContractValidationError


def ensure_non_empty_str(value: str, *, field_name: str) -> str:
    """Ensure a string field is non-empty after stripping whitespace.

    Args:
        value: The string to validate.
        field_name: Name of the field, used in the error message.

    Returns:
        The original value, unchanged.

    Raises:
        ContractValidationError: If the value is not a string, or is
            empty/whitespace-only.
    """
    if not isinstance(value, str) or not value.strip():
        msg = f"{field_name} must be a non-empty string"
        raise ContractValidationError(msg)
    return value


def ensure_finite(value: float, *, field_name: str) -> float:
    """Ensure a numeric field is a finite number (not NaN or infinite).

    Args:
        value: The number to validate.
        field_name: Name of the field, used in the error message.

    Returns:
        The value coerced to ``float``.

    Raises:
        ContractValidationError: If the value is not numeric, is a
            ``bool``, or is NaN/infinite.
    """
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        msg = f"{field_name} must be numeric, got {type(value).__name__}"
        raise ContractValidationError(msg)
    if not math.isfinite(value):
        msg = f"{field_name} must be finite, got {value}"
        raise ContractValidationError(msg)
    return float(value)


def ensure_in_range(
    value: float,
    *,
    field_name: str,
    minimum: float = 0.0,
    maximum: float = 1.0,
) -> float:
    """Ensure a numeric field falls within an inclusive range.

    Args:
        value: The number to validate.
        field_name: Name of the field, used in the error message.
        minimum: Inclusive lower bound.
        maximum: Inclusive upper bound.

    Returns:
        The original value, unchanged.

    Raises:
        ContractValidationError: If the value is outside ``[minimum, maximum]``.
    """
    if not minimum <= value <= maximum:
        msg = f"{field_name} must be between {minimum} and {maximum}, got {value}"
        raise ContractValidationError(msg)
    return value


def ensure_timezone_aware(value: datetime, *, field_name: str) -> datetime:
    """Ensure a datetime field carries explicit timezone information.

    Args:
        value: The datetime to validate.
        field_name: Name of the field, used in the error message.

    Returns:
        The original value, unchanged.

    Raises:
        ContractValidationError: If the datetime is naive (has no ``tzinfo``).
    """
    if value.tzinfo is None:
        msg = f"{field_name} must be timezone-aware, got a naive datetime"
        raise ContractValidationError(msg)
    return value
