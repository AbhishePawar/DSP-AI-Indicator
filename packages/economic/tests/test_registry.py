"""Tests for EconomicError and registry."""

from __future__ import annotations

import pytest

from core.exceptions import DSPAIError

from economic.analyzers import GdpAnalyzer
from economic.exceptions import EconomicError
from economic.registry import get, list_analyzers, register


class TestEconomicError:
    """Exception hierarchy."""

    def test_is_dspai_error(self) -> None:
        assert issubclass(EconomicError, DSPAIError)

    def test_raise_and_catch(self) -> None:
        with pytest.raises(EconomicError):
            raise EconomicError("failed")


class TestRegistry:
    """Analyzer registry."""

    def test_default_analyzers_registered(self) -> None:
        names = list_analyzers()
        assert "gdp" in names
        assert "inflation" in names
        assert "interest_rate" in names
        assert "pmi" in names
        assert "liquidity" in names

    def test_get_instantiates(self) -> None:
        analyzer = get("gdp")
        assert isinstance(analyzer, GdpAnalyzer)

    def test_unknown_raises(self) -> None:
        with pytest.raises(KeyError):
            get("not_registered")

    def test_register_custom(self) -> None:
        class Custom(GdpAnalyzer):
            @property
            def name(self) -> str:
                return "custom_gdp"

        register("custom_gdp_test", Custom)
        assert get("custom_gdp_test").name == "custom_gdp"
