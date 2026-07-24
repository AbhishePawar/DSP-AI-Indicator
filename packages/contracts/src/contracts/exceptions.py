"""Exceptions raised by the Contracts package.

The Contracts package defines its own minimal exception hierarchy so that it
never depends on ``core`` (per the platform dependency rules in
``docs/DSP_AI_INDICATOR_ARCHITECTURE.md``, ``core`` depends on ``contracts`` —
not the reverse). Engines that depend on both packages may bridge these
exceptions into their own hierarchy if useful, but Contracts itself must
remain fully self-contained.
"""

from __future__ import annotations


class ContractError(Exception):
    """Base exception for all Contracts package errors."""

    def __init__(self, message: str) -> None:
        """Initialize the exception with a descriptive message.

        Args:
            message: Human-readable description of the error.
        """
        super().__init__(message)
        self.message = message


class ContractValidationError(ContractError):
    """Raised when a domain contract fails structural validation.

    This covers only structural, data-integrity checks (for example, a
    price bar whose high is below its low, or a required field that is
    empty). It never represents a business-rule violation — those are
    the responsibility of the engine that owns that rule.
    """
