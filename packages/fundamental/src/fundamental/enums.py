"""Enumerations internal to the Fundamental Engine.

These enums are presentation/formatting vocabulary for how a computed
:class:`~fundamental.models.FundamentalMetric` should be rendered
in human-readable text (percentage, currency, or plain ratio). They are
not shared platform vocabulary and therefore live here rather than in
``contracts.enums`` — no other engine needs to know how the Fundamental
Engine chooses to format its own numbers.
"""

from __future__ import annotations

from enum import StrEnum

__all__ = ["MetricUnit"]


class MetricUnit(StrEnum):
    """How a :class:`~fundamental.models.FundamentalMetric` value should be
    interpreted for display purposes.
    """

    RATIO = "ratio"
    PERCENT = "percent"
    CURRENCY = "currency"
