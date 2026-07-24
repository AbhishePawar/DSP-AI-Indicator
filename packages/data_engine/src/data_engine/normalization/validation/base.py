"""Composable validation stage and pipeline abstractions.

A :class:`ValidationStage` is a single, focused check applied to a
sequence of items (raw models, normalized records, or any other object
with named attributes). A :class:`ValidationPipeline` composes an
ordered list of stages and runs them in sequence, stopping at the first
failure.

Stages are deliberately generic (parameterized by field names or
key-extraction callables) rather than hard-coded to one raw model type,
so the same stage class can validate ``RawMarketBar`` sequences,
normalized bar sequences, or any future item type that exposes the
right attributes.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import Generic, TypeVar

T = TypeVar("T")

__all__ = ["ValidationPipeline", "ValidationStage"]


class ValidationStage(ABC, Generic[T]):
    """A single, composable check applied to a sequence of items.

    Implementations must not mutate ``items`` — a stage either passes
    silently or raises a :class:`data_engine.exceptions.NormalizationError`
    subclass describing exactly what failed and where.
    """

    @abstractmethod
    def validate(self, items: Sequence[T]) -> None:
        """Check ``items``, raising on the first failure found.

        Args:
            items: The sequence of items to check. Implementations may
                assume this sequence will not be mutated during
                validation.

        Raises:
            NormalizationError: If any item fails this stage's check.
        """


class ValidationPipeline(Generic[T]):
    """An ordered, composable sequence of :class:`ValidationStage` checks.

    Stages run in the order they were provided. The pipeline stops and
    propagates the exception as soon as any stage raises, so callers
    always get the *first* problem found rather than a batch of errors.
    """

    def __init__(self, stages: Sequence[ValidationStage[T]]) -> None:
        """Initialize the pipeline with an ordered list of stages.

        Args:
            stages: The validation stages to run, in order.
        """
        self._stages: tuple[ValidationStage[T], ...] = tuple(stages)

    @property
    def stages(self) -> tuple[ValidationStage[T], ...]:
        """Return the configured stages, in run order."""
        return self._stages

    def run(self, items: Sequence[T]) -> None:
        """Run every configured stage against ``items``, in order.

        Args:
            items: The sequence of items to validate.

        Raises:
            NormalizationError: Propagated from whichever stage fails
                first. No later stages run once one has failed.
        """
        for stage in self._stages:
            stage.validate(items)
