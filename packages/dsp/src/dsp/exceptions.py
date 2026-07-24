"""Exceptions specific to the Indicator Engine.

``IndicatorError`` previously lived in ``core.exceptions``, but Core must
never contain engine-specific vocabulary. It now lives here, deriving from
``core.exceptions.DSPAIError``, following the pattern every future engine
should use for its own domain-specific errors.
"""

from __future__ import annotations

from core.exceptions import DSPAIError


class IndicatorError(DSPAIError):
    """Raised when indicator computation fails."""
