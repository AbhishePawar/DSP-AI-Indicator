"""Core package public API.

Core is the platform's generic technical foundation: shared exceptions,
numeric validation utilities, and generic registry infrastructure used by
every engine. It contains no market, indicator, valuation, portfolio, or
recommendation logic — those domain concerns belong to Contracts (shared
domain vocabulary) and the engines that implement them.

See ``packages/core/README.md`` and
``docs/DSP_AI_INDICATOR_ARCHITECTURE.md`` for the platform-wide usage and
dependency rules that govern this package.
"""

from core.exceptions import DSPAIError, ValidationError
from core.registry import Registry
from core.validation import create_output_array, validate_period, validate_prices

__all__ = [
    "DSPAIError",
    "Registry",
    "ValidationError",
    "create_output_array",
    "validate_period",
    "validate_prices",
]

__version__ = "0.2.0"
