"""Economic Engine public API.

The Economic Engine analyzes a point-in-time :class:`EconomicSnapshot`
and returns a deterministic :class:`EconomicAssessment` with regime
classification, recommendation, reasoning, evidence, and detected
signals. See ``packages/economic/README.md``.

Sprint 6.0 is architecture only — no forecasting, no LLM, no ML.
"""

from economic.engine import EconomicEngine
from economic.enums import EconomicCondition, Recommendation
from economic.exceptions import EconomicError
from economic.models import (
    EconomicAssessment,
    EconomicSignal,
    EconomicSnapshot,
)

__all__ = [
    "EconomicAssessment",
    "EconomicCondition",
    "EconomicEngine",
    "EconomicError",
    "EconomicSignal",
    "EconomicSnapshot",
    "Recommendation",
]

__version__ = "0.1.1"
