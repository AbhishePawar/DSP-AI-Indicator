"""Tests for fundamental.exceptions."""

from core.exceptions import DSPAIError
from fundamental.exceptions import FundamentalError


class TestFundamentalError:
    """Tests for FundamentalError's place in the exception hierarchy."""

    def test_is_a_dspai_error(self) -> None:
        assert issubclass(FundamentalError, DSPAIError)

    def test_carries_message(self) -> None:
        error = FundamentalError("something went wrong")
        assert error.message == "something went wrong"
        assert str(error) == "something went wrong"
