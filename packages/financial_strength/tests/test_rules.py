"""Boundary tests for Financial Strength helpers."""

from __future__ import annotations

from financial_strength.rules import _map_ratio, mean_present
from financial_strength.signals import assessment_score_01, ratio_value, safe_getattr


def test_helpers() -> None:
    assert mean_present([]) is None
    assert mean_present([None, 0.5, 1.0]) == 0.75
    assert _map_ratio(None, good=1.0, bad=0.0) is None
    assert _map_ratio(2.0, good=2.0, bad=0.5) == 1.0
    assert _map_ratio(0.2, good=0.3, bad=2.0, invert=True) == 1.0
    assert _map_ratio(2.0, good=0.3, bad=2.0, invert=True) == 0.0
    assert safe_getattr(None, "a") is None
    assert assessment_score_01(None, "x") is None

    class Ratio:
        def __init__(self, name: str, value: float) -> None:
            self.name = name
            self.value = value

    assert ratio_value((Ratio("roe", 0.2),), "roe") == 0.2
