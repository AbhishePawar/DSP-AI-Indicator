"""Tests for fundamental.registry."""

import pytest

from fundamental.analyzers.base import Analyzer
from fundamental.models import FinancialSnapshot, FundamentalMetric
from fundamental.registry import get, list_analyzers, register


class TestDefaultRegistrations:
    """Every built-in analyzer must be registered under its own name."""

    def test_default_analyzers_are_registered(self) -> None:
        names = list_analyzers()
        assert {"profitability", "growth", "leverage", "quality"} <= set(names)

    def test_get_returns_a_fresh_instance(self) -> None:
        first = get("profitability")
        second = get("profitability")
        assert first is not second
        assert first.name == second.name == "profitability"

    def test_lookup_is_case_insensitive(self) -> None:
        assert get("PROFITABILITY").name == "profitability"

    def test_unknown_name_raises_key_error(self) -> None:
        with pytest.raises(KeyError):
            get("nonexistent_analyzer")


class TestRegisterCustomAnalyzer:
    """New analyzers can be added without touching the registry module."""

    def test_register_and_retrieve(self) -> None:
        class _EfficiencyAnalyzer(Analyzer):
            @property
            def name(self) -> str:
                return "test_efficiency"

            def analyze(
                self, snapshot: FinancialSnapshot
            ) -> tuple[FundamentalMetric, ...]:
                return ()

        register("test_efficiency", _EfficiencyAnalyzer)
        assert "test_efficiency" in list_analyzers()
        assert isinstance(get("test_efficiency"), _EfficiencyAnalyzer)

    def test_conflicting_registration_raises_value_error(self) -> None:
        class _Other(Analyzer):
            @property
            def name(self) -> str:
                return "profitability"

            def analyze(
                self, snapshot: FinancialSnapshot
            ) -> tuple[FundamentalMetric, ...]:
                return ()

        with pytest.raises(ValueError, match="already registered"):
            register("profitability", _Other)
