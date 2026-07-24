"""Tests for data_engine.normalization.pipeline.TransformationPipeline."""

import pytest

from data_engine.exceptions import (
    InvalidProviderDataError,
    MissingFieldError,
    TransformationError,
)
from data_engine.normalization.pipeline import TransformationPipeline
from data_engine.normalization.validation import (
    RequiredFieldValidationStage,
    ValidationPipeline,
)


class TestTransformationPipeline:
    """Tests for the generic normalize -> validate -> construct -> return flow."""

    def test_runs_the_full_flow_in_order(self) -> None:
        pipeline: TransformationPipeline[int, int, str] = TransformationPipeline(
            coerce=lambda raw: raw * 2,
            construct=lambda normalized: f"value={normalized}",
        )
        assert pipeline.run([1, 2, 3]) == ("value=2", "value=4", "value=6")

    def test_raw_validation_runs_before_coercion(self) -> None:
        calls: list[str] = []

        class _RawItem:
            def __init__(self, value: int | None) -> None:
                self.value = value

        def _coerce(raw: _RawItem) -> int:
            calls.append("coerce")
            return raw.value  # type: ignore[return-value]

        pipeline: TransformationPipeline[_RawItem, int, int] = TransformationPipeline(
            coerce=_coerce,
            construct=lambda normalized: normalized,
            raw_validation=ValidationPipeline(
                [RequiredFieldValidationStage(field_names=("value",))]
            ),
        )
        with pytest.raises(MissingFieldError):
            pipeline.run([_RawItem(None)])
        assert "coerce" not in calls

    def test_normalization_error_propagates_unchanged(self) -> None:
        def _failing_coerce(raw: int) -> int:
            msg = "deliberately invalid"
            raise InvalidProviderDataError(msg)

        pipeline: TransformationPipeline[int, int, int] = TransformationPipeline(
            coerce=_failing_coerce,
            construct=lambda normalized: normalized,
        )
        with pytest.raises(InvalidProviderDataError, match="deliberately invalid"):
            pipeline.run([1])

    def test_unexpected_exception_is_wrapped_as_transformation_error(self) -> None:
        def _buggy_construct(normalized: int) -> int:
            raise ValueError("boom")

        pipeline: TransformationPipeline[int, int, int] = TransformationPipeline(
            coerce=lambda raw: raw,
            construct=_buggy_construct,
        )
        with pytest.raises(TransformationError) as exc_info:
            pipeline.run([1])
        assert isinstance(exc_info.value.__cause__, ValueError)

    def test_normalized_validation_runs_after_coercion(self) -> None:
        pipeline: TransformationPipeline[int, int, int] = TransformationPipeline(
            coerce=lambda raw: raw,
            construct=lambda normalized: normalized,
            normalized_validation=ValidationPipeline(
                [RequiredFieldValidationStage(field_names=("bit_length",))]
            ),
        )
        # int has a bit_length attribute, so this should pass validation.
        assert pipeline.run([5]) == (5,)
