"""Exceptions specific to the AI Investment Committee.

Following the pattern established by ``dsp.exceptions.IndicatorError``
and ``fundamental.exceptions.FundamentalError``, this package defines
its own domain-specific exception deriving from
``core.exceptions.DSPAIError``.
"""

from __future__ import annotations

from core.exceptions import DSPAIError


class CommitteeError(DSPAIError):
    """Raised when committee deliberation fails.

    Covers instrument mismatches between member inputs, empty member
    sets, and failures while forming or aggregating opinions.
    """
