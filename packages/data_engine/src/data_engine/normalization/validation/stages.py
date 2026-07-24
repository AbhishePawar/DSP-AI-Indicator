"""Concrete, reusable validation stages.

Each stage is parameterized by field names or key-extraction callables
rather than hard-coded to a specific raw or normalized type, so any of
them can be reused across market, fundamental, economic, or
alternative-data pipelines by simply pointing them at the right
attributes.

Presence/format stages (:class:`RequiredFieldValidationStage`,
:class:`MissingValueValidationStage`, :class:`TimestampValidationStage`)
are typically run against *raw* items, before coercion, to catch
garbage input with a clear, provider-attributed message as early as
possible. Semantic/collection stages (:class:`DuplicateDetectionStage`,
:class:`SortingVerificationStage`, :class:`OHLCConsistencyStage`,
:class:`VolumeValidationStage`) expect their named fields to already be
real numbers/datetimes — they perform no coercion themselves, since
that is the Normalizer's job.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import datetime
from typing import Any, TypeVar

from data_engine.exceptions import InvalidProviderDataError, MissingFieldError
from data_engine.normalization.validation.base import ValidationStage

T = TypeVar("T")

__all__ = [
    "DuplicateDetectionStage",
    "MissingValueValidationStage",
    "OHLCConsistencyStage",
    "RequiredFieldValidationStage",
    "SortingVerificationStage",
    "TimestampValidationStage",
    "VolumeValidationStage",
]

_DEFAULT_MISSING_SENTINELS: frozenset[Any] = frozenset({None, "", "N/A", "n/a", "-"})


class RequiredFieldValidationStage(ValidationStage[T]):
    """Fails if any named field is ``None`` on any item.

    Use this to enforce that a field was reported *at all*, before
    attempting any coercion. Compare with
    :class:`MissingValueValidationStage`, which also catches
    provider-specific "missing" sentinels beyond plain ``None``.
    """

    def __init__(self, *, field_names: Sequence[str]) -> None:
        """Initialize the stage.

        Args:
            field_names: Names of attributes that must be non-``None``
                on every item.
        """
        self._field_names = tuple(field_names)

    def validate(self, items: Sequence[T]) -> None:
        """Raise ``MissingFieldError`` if any field is ``None``."""
        for index, item in enumerate(items):
            for field_name in self._field_names:
                if getattr(item, field_name, None) is None:
                    msg = (
                        f"item at index {index} is missing required "
                        f"field '{field_name}'"
                    )
                    raise MissingFieldError(msg)


class MissingValueValidationStage(ValidationStage[T]):
    """Fails if any named field equals a configured "missing" sentinel.

    Providers often report missing data as an empty string, a literal
    ``"N/A"``, or a placeholder dash rather than omitting the field
    entirely. This stage catches those cases in addition to ``None``.
    """

    def __init__(
        self,
        *,
        field_names: Sequence[str],
        sentinels: frozenset[Any] = _DEFAULT_MISSING_SENTINELS,
    ) -> None:
        """Initialize the stage.

        Args:
            field_names: Names of attributes to check.
            sentinels: Values that count as "missing" in addition to
                being absent. Defaults to ``None``, empty string, and
                common provider placeholders.
        """
        self._field_names = tuple(field_names)
        self._sentinels = sentinels

    def validate(self, items: Sequence[T]) -> None:
        """Raise ``InvalidProviderDataError`` if a sentinel value is found."""
        for index, item in enumerate(items):
            for field_name in self._field_names:
                value = getattr(item, field_name, None)
                if value in self._sentinels:
                    msg = (
                        f"item at index {index} has a missing/sentinel "
                        f"value for field '{field_name}': {value!r}"
                    )
                    raise InvalidProviderDataError(msg)


class TimestampValidationStage(ValidationStage[T]):
    """Fails if a named field is not a timezone-aware ``datetime``.

    This stage does not parse strings or epoch numbers — it asserts
    that coercion has *already* happened. It exists so pipelines can
    defensively re-check timestamp integrity after normalization, and
    so other consumers of this framework that skip coercion can still
    validate timestamps that are already ``datetime`` instances.
    """

    def __init__(self, *, field_name: str = "timestamp") -> None:
        """Initialize the stage.

        Args:
            field_name: Name of the timestamp attribute to check.
        """
        self._field_name = field_name

    def validate(self, items: Sequence[T]) -> None:
        """Raise ``InvalidProviderDataError`` on a bad timestamp field."""
        for index, item in enumerate(items):
            value = getattr(item, self._field_name, None)
            if not isinstance(value, datetime):
                msg = (
                    f"item at index {index} has a non-datetime value "
                    f"for field '{self._field_name}': {value!r}"
                )
                raise InvalidProviderDataError(msg)
            if value.tzinfo is None:
                msg = (
                    f"item at index {index} has a timezone-naive "
                    f"timestamp for field '{self._field_name}': {value!r}"
                )
                raise InvalidProviderDataError(msg)


class DuplicateDetectionStage(ValidationStage[T]):
    """Fails if a key computed from each item repeats across the sequence."""

    def __init__(self, *, key: Callable[[T], Any]) -> None:
        """Initialize the stage.

        Args:
            key: Callable extracting the value to check for duplicates
                (e.g. ``lambda bar: bar.timestamp``).
        """
        self._key = key

    def validate(self, items: Sequence[T]) -> None:
        """Raise ``InvalidProviderDataError`` on the first duplicate key."""
        seen: set[Any] = set()
        for index, item in enumerate(items):
            key_value = self._key(item)
            if key_value in seen:
                msg = f"duplicate key {key_value!r} found at index {index}"
                raise InvalidProviderDataError(msg)
            seen.add(key_value)


class SortingVerificationStage(ValidationStage[T]):
    """Fails if items are not sorted in strictly ascending order by key."""

    def __init__(self, *, key: Callable[[T], Any]) -> None:
        """Initialize the stage.

        Args:
            key: Callable extracting the sort key from each item (e.g.
                ``lambda bar: bar.timestamp``).
        """
        self._key = key

    def validate(self, items: Sequence[T]) -> None:
        """Raise ``InvalidProviderDataError`` if items are out of order."""
        keys = [self._key(item) for item in items]
        for index in range(1, len(keys)):
            if keys[index] <= keys[index - 1]:
                msg = (
                    f"items are not sorted in strictly ascending order: "
                    f"key at index {index} ({keys[index]!r}) does not "
                    f"come after key at index {index - 1} ({keys[index - 1]!r})"
                )
                raise InvalidProviderDataError(msg)


class OHLCConsistencyStage(ValidationStage[T]):
    """Fails if open/high/low/close relationships are inconsistent.

    Expects the named fields to already be coerced to real numbers —
    this stage performs no type coercion itself.
    """

    def __init__(
        self,
        *,
        open_field: str = "open",
        high_field: str = "high",
        low_field: str = "low",
        close_field: str = "close",
    ) -> None:
        """Initialize the stage.

        Args:
            open_field: Name of the open-price attribute.
            high_field: Name of the high-price attribute.
            low_field: Name of the low-price attribute.
            close_field: Name of the close-price attribute.
        """
        self._open_field = open_field
        self._high_field = high_field
        self._low_field = low_field
        self._close_field = close_field

    def validate(self, items: Sequence[T]) -> None:
        """Raise ``InvalidProviderDataError`` on an inconsistent bar."""
        for index, item in enumerate(items):
            open_ = getattr(item, self._open_field)
            high = getattr(item, self._high_field)
            low = getattr(item, self._low_field)
            close = getattr(item, self._close_field)
            if low > high:
                msg = (
                    f"item at index {index} has low ({low}) greater "
                    f"than high ({high})"
                )
                raise InvalidProviderDataError(msg)
            if not low <= open_ <= high:
                msg = (
                    f"item at index {index} has open ({open_}) outside "
                    f"the [low, high] range ({low}, {high})"
                )
                raise InvalidProviderDataError(msg)
            if not low <= close <= high:
                msg = (
                    f"item at index {index} has close ({close}) outside "
                    f"the [low, high] range ({low}, {high})"
                )
                raise InvalidProviderDataError(msg)


class VolumeValidationStage(ValidationStage[T]):
    """Fails if a named volume field is present and negative."""

    def __init__(self, *, field_name: str = "volume") -> None:
        """Initialize the stage.

        Args:
            field_name: Name of the volume attribute to check.
        """
        self._field_name = field_name

    def validate(self, items: Sequence[T]) -> None:
        """Raise ``InvalidProviderDataError`` on negative volume."""
        for index, item in enumerate(items):
            value = getattr(item, self._field_name, None)
            if value is not None and value < 0:
                msg = (
                    f"item at index {index} has a negative value for "
                    f"field '{self._field_name}': {value!r}"
                )
                raise InvalidProviderDataError(msg)
