"""Generic coercion helpers shared by concrete normalizers.

These helpers turn a loosely-typed raw value (``Any``) into a strict
Python type, raising a :mod:`data_engine.exceptions` normalization
error with a provider-attributed message on failure. They contain no
provider-specific logic — every provider's raw values funnel through
the same functions once they have been placed into a raw model's named
fields.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

from data_engine.exceptions import InvalidProviderDataError, MissingFieldError

__all__ = [
    "coerce_date",
    "coerce_float",
    "coerce_optional_float",
    "coerce_timestamp",
]


def coerce_timestamp(
    value: Any, *, provider_id: str, field_name: str = "timestamp"
) -> datetime:
    """Coerce a raw timestamp value into a timezone-aware ``datetime``.

    Accepts an already-parsed ``datetime``, a Unix epoch ``int``/
    ``float``, or an ISO-8601 string. Naive values are assumed to be
    UTC rather than rejected, since many providers omit timezone
    information but report UTC-aligned data.

    Args:
        value: The raw timestamp as reported by the provider.
        provider_id: Identifier of the provider, used to attribute
            errors.
        field_name: Name of the field being coerced, used to attribute
            errors.

    Returns:
        A timezone-aware ``datetime`` in UTC (or the offset the
        provider reported, if any).

    Raises:
        MissingFieldError: If ``value`` is ``None``.
        InvalidProviderDataError: If ``value`` cannot be interpreted as
            a timestamp.
    """
    if value is None:
        msg = f"provider '{provider_id}' is missing required field '{field_name}'"
        raise MissingFieldError(msg)
    if isinstance(value, datetime):
        return value if value.tzinfo is not None else value.replace(tzinfo=UTC)
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=UTC)
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError as exc:
            msg = (
                f"provider '{provider_id}' returned an unparsable "
                f"value for '{field_name}': {value!r}"
            )
            raise InvalidProviderDataError(msg) from exc
        return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)
    msg = (
        f"provider '{provider_id}' returned an unsupported type for "
        f"'{field_name}': {type(value).__name__}"
    )
    raise InvalidProviderDataError(msg)


def coerce_float(
    value: Any,
    *,
    provider_id: str,
    field_name: str,
    required: bool = True,
    default: float = 0.0,
) -> float:
    """Coerce a raw numeric value into a ``float``.

    Args:
        value: The raw value as reported by the provider.
        provider_id: Identifier of the provider, used to attribute
            errors.
        field_name: Name of the field being coerced, used to attribute
            errors.
        required: If ``True``, ``None`` raises ``MissingFieldError``.
            If ``False``, ``None`` returns ``default``.
        default: Value returned when ``value`` is ``None`` and
            ``required`` is ``False``.

    Returns:
        The coerced ``float`` value.

    Raises:
        MissingFieldError: If ``value`` is ``None`` and ``required`` is
            ``True``.
        InvalidProviderDataError: If ``value`` cannot be interpreted as
            a number.
    """
    if value is None:
        if required:
            msg = f"provider '{provider_id}' is missing required field '{field_name}'"
            raise MissingFieldError(msg)
        return default
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        msg = (
            f"provider '{provider_id}' returned a non-numeric value "
            f"for '{field_name}': {value!r}"
        )
        raise InvalidProviderDataError(msg) from exc


def coerce_optional_float(
    value: Any,
    *,
    provider_id: str,
    field_name: str,
) -> float | None:
    """Coerce a raw numeric value into ``float | None``.

    Unlike :func:`coerce_float` with ``required=False``, a missing value
    returns ``None`` rather than a numeric default — the correct
    semantics for as-reported financial line items.

    Args:
        value: The raw value as reported by the provider.
        provider_id: Identifier of the provider, used to attribute
            errors.
        field_name: Name of the field being coerced, used to attribute
            errors.

    Returns:
        The coerced ``float``, or ``None`` when ``value`` is ``None``.

    Raises:
        InvalidProviderDataError: If ``value`` is present but cannot be
            interpreted as a number.
    """
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        msg = (
            f"provider '{provider_id}' returned a non-numeric value "
            f"for '{field_name}': {value!r}"
        )
        raise InvalidProviderDataError(msg) from exc


def coerce_date(
    value: Any, *, provider_id: str, field_name: str = "period_end"
) -> date:
    """Coerce a raw calendar value into a ``date``.

    Accepts an already-parsed ``date``/``datetime``, a Unix epoch
    ``int``/``float`` (interpreted as UTC), or an ISO-8601 / ``YYYY-MM-DD``
    string.

    Args:
        value: The raw period-end value as reported by the provider.
        provider_id: Identifier of the provider, used to attribute
            errors.
        field_name: Name of the field being coerced, used to attribute
            errors.

    Returns:
        A calendar ``date``.

    Raises:
        MissingFieldError: If ``value`` is ``None``.
        InvalidProviderDataError: If ``value`` cannot be interpreted as
            a date.
    """
    if value is None:
        msg = f"provider '{provider_id}' is missing required field '{field_name}'"
        raise MissingFieldError(msg)
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=UTC).date()
    if isinstance(value, str):
        text = value.strip()
        try:
            if "T" in text or " " in text:
                parsed = datetime.fromisoformat(text)
                return parsed.date()
            return date.fromisoformat(text[:10])
        except ValueError as exc:
            msg = (
                f"provider '{provider_id}' returned an unparsable "
                f"value for '{field_name}': {value!r}"
            )
            raise InvalidProviderDataError(msg) from exc
    msg = (
        f"provider '{provider_id}' returned an unsupported type for "
        f"'{field_name}': {type(value).__name__}"
    )
    raise InvalidProviderDataError(msg)
