"""Tests for the normalization exception hierarchy."""

from core.exceptions import DSPAIError
from data_engine.exceptions import (
    DataEngineError,
    InvalidProviderDataError,
    MissingFieldError,
    NormalizationError,
    TransformationError,
)


class TestNormalizationExceptionHierarchy:
    """Tests for how the normalization exceptions relate to each other."""

    def test_normalization_error_is_a_data_engine_error(self) -> None:
        assert issubclass(NormalizationError, DataEngineError)
        assert issubclass(NormalizationError, DSPAIError)

    def test_invalid_provider_data_error_is_a_normalization_error(self) -> None:
        assert issubclass(InvalidProviderDataError, NormalizationError)

    def test_missing_field_error_is_a_normalization_error(self) -> None:
        assert issubclass(MissingFieldError, NormalizationError)

    def test_transformation_error_is_a_data_engine_error(self) -> None:
        assert issubclass(TransformationError, DataEngineError)

    def test_transformation_error_is_not_a_normalization_error(self) -> None:
        assert not issubclass(TransformationError, NormalizationError)

    def test_exceptions_carry_a_message(self) -> None:
        error = InvalidProviderDataError("bad data")
        assert str(error) == "bad data"
