"""Edge / boundary tests for Economic Moat rules and signals."""

from __future__ import annotations

from economic_moat.rules import mean_present
from economic_moat.signals import assessment_score_01, ratio_value, safe_getattr


def test_mean_present_handles_empty_and_partial() -> None:
    assert mean_present([]) is None
    assert mean_present([None, None]) is None
    assert mean_present([None, 0.5, 1.0]) == 0.75


def test_safe_getattr_and_ratio_helpers() -> None:
    class Ratio:
        def __init__(self, name: str, value: float) -> None:
            self.name = name
            self.value = value

    class Bag:
        profitability = (Ratio("roic", 0.2), Ratio("roe", 0.3))

    assert safe_getattr(None, "a", "b") is None
    assert safe_getattr(Bag(), "profitability") is not None
    assert ratio_value(Bag().profitability, "roic") == 0.2
    assert ratio_value(Bag().profitability, "missing") is None
    assert assessment_score_01(None, "x") is None
