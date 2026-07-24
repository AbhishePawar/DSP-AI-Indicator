"""Tests for the Indicator Engine's own exception hierarchy."""

from core.exceptions import DSPAIError
from dsp.exceptions import IndicatorError


class TestIndicatorError:
    """Tests for IndicatorError's placement in the exception hierarchy."""

    def test_derives_from_core_base_error(self) -> None:
        assert issubclass(IndicatorError, DSPAIError)

    def test_carries_message(self) -> None:
        error = IndicatorError("computation failed")
        assert error.message == "computation failed"
        assert str(error) == "computation failed"

    def test_is_importable_from_dsp_public_api(self) -> None:
        from dsp import IndicatorError as PublicIndicatorError

        assert PublicIndicatorError is IndicatorError
