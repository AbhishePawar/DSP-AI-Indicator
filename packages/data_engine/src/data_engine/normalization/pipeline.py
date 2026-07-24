"""Generic normalize → validate → construct → return transformation pipeline.

``TransformationPipeline`` is the reusable orchestrator every concrete
normalizer is expected to build on, rather than hand-rolling its own
try/except control flow. It executes exactly the sequence mandated by
the Data Engine architecture:

    Normalize -> Validate -> Construct Contracts -> Return Canonical Objects

By injecting the coercion, validation, and construction steps as plain
callables/``ValidationPipeline`` instances, the same
``TransformationPipeline`` class works for market bars, fundamental
statements, economic observations, or any future raw/contract pair
without any changes to this module.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Generic, TypeVar

from data_engine.exceptions import NormalizationError, TransformationError
from data_engine.normalization.validation.base import ValidationPipeline

TRaw = TypeVar("TRaw")
TNormalized = TypeVar("TNormalized")
TContract = TypeVar("TContract")

__all__ = ["TransformationPipeline"]


@dataclass(frozen=True, slots=True)
class TransformationPipeline(Generic[TRaw, TNormalized, TContract]):
    """Composable raw -> normalized -> validated -> contract pipeline.

    Attributes:
        coerce: Converts one raw item into one normalized (strictly
            typed) record. This is the "Normalize" step.
        construct: Converts one normalized record into one ``contracts``
            object. This is the "Construct Contracts" step.
        raw_validation: Optional pipeline run against the full sequence
            of *raw* items before coercion, to catch malformed input
            with provider-attributed diagnostics as early as possible.
        normalized_validation: Optional pipeline run against the full
            sequence of *normalized* records before construction, to
            catch semantic issues (duplicates, ordering, OHLC
            consistency, etc.) that require strictly-typed values.
    """

    coerce: Callable[[TRaw], TNormalized]
    construct: Callable[[TNormalized], TContract]
    raw_validation: ValidationPipeline[TRaw] | None = field(default=None)
    normalized_validation: ValidationPipeline[TNormalized] | None = field(default=None)

    def run(self, raw_items: Sequence[TRaw]) -> tuple[TContract, ...]:
        """Execute the full normalize -> validate -> construct -> return flow.

        Args:
            raw_items: The raw items to transform.

        Returns:
            The constructed ``contracts`` objects, one per raw item, in
            the same order as ``raw_items``.

        Raises:
            NormalizationError: If a validation stage or a coercion
                helper determines that a specific raw item is
                malformed. This propagates unchanged so callers can
                distinguish bad provider data from a pipeline bug.
            TransformationError: If any other, unexpected exception is
                raised while running the pipeline (for example a
                ``contracts`` validation failure that slipped past the
                configured validation stages). The original exception
                is chained via ``__cause__``.
        """
        try:
            if self.raw_validation is not None:
                self.raw_validation.run(raw_items)

            normalized = tuple(self.coerce(item) for item in raw_items)

            if self.normalized_validation is not None:
                self.normalized_validation.run(normalized)

            return tuple(self.construct(item) for item in normalized)
        except NormalizationError:
            raise
        except Exception as exc:
            msg = f"transformation pipeline failed: {exc}"
            raise TransformationError(msg) from exc
