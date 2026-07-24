"""Tests for data_engine.exceptions."""

from core.exceptions import DSPAIError
from data_engine.exceptions import (
    DataEngineError,
    NormalizationError,
    ProviderRequestError,
)


class TestDataEngineError:
    """Tests for the DataEngineError root exception."""

    def test_is_a_dspai_error(self) -> None:
        assert issubclass(DataEngineError, DSPAIError)

    def test_carries_message(self) -> None:
        error = DataEngineError("something went wrong")
        assert error.message == "something went wrong"
        assert str(error) == "something went wrong"


class TestProviderRequestError:
    """Tests for the Sprint 2.4 transport-failure exception."""

    def test_is_a_data_engine_error(self) -> None:
        assert issubclass(ProviderRequestError, DataEngineError)

    def test_is_not_a_normalization_error(self) -> None:
        assert not issubclass(ProviderRequestError, NormalizationError)

    def test_carries_message(self) -> None:
        error = ProviderRequestError("request to provider failed")
        assert error.message == "request to provider failed"
