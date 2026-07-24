"""Exceptions specific to the Fundamental Engine.

Following the pattern established by ``dsp.exceptions.IndicatorError``,
this engine defines its own domain-specific exception deriving from
``core.exceptions.DSPAIError`` rather than reusing a bare built-in
exception or inventing a new root hierarchy.
"""

from __future__ import annotations

from core.exceptions import DSPAIError


class FundamentalError(DSPAIError):
    """Raised when fundamental analysis fails.

    Covers snapshot construction failures, unknown analyzer/metric
    names, analyzer execution failures, and missing business rules —
    mirroring how :class:`dsp.exceptions.IndicatorError` covers the
    equivalent failure modes in the Indicator Engine.
    """
