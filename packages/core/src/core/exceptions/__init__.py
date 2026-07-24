"""Generic, engine-agnostic exceptions for the platform.

This hierarchy is intentionally free of any engine-specific vocabulary.
``DSPAIError`` is the root every engine's own exceptions should derive
from (directly or via an intermediate engine-specific base), and
``ValidationError`` covers generic input-validation failures raised by
``core.validation``. Domain-specific exceptions — for example an
indicator computation error — belong in the engine that owns that
domain (see ``dsp.exceptions.IndicatorError`` for the Indicator Engine's
own exception, which derives from ``DSPAIError``).
"""


class DSPAIError(Exception):
    """Base exception for all platform errors.

    Every engine-specific exception hierarchy in the platform should
    ultimately derive from this class, directly or through an
    intermediate base defined by that engine.
    """

    def __init__(self, message: str) -> None:
        """Initialize the exception with a descriptive message.

        Args:
            message: Human-readable description of the error.
        """
        super().__init__(message)
        self.message = message


class ValidationError(DSPAIError):
    """Raised when input data fails generic validation checks.

    Used by ``core.validation`` for numeric/structural checks (e.g. an
    invalid period, a non-finite value). Engines that need their own
    domain-specific validation errors should define them in their own
    package, deriving from ``DSPAIError``.
    """
