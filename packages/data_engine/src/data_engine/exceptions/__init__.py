"""Exceptions specific to the Data Engine.

Mirrors the pattern established by ``dsp.exceptions``: an engine-specific
base deriving from ``core.exceptions.DSPAIError``. Concrete adapters may
add their own specific errors (e.g. a timeout or rate-limit error) here
once a real provider integration exists, rather than those being
invented speculatively now.

The normalization exception family below was added in Sprint 2.3
alongside :mod:`data_engine.normalization`. The hierarchy separates two
distinct failure categories so callers can catch the level of
granularity they need:

- ``NormalizationError`` and its subclasses (``InvalidProviderDataError``,
  ``MissingFieldError``) indicate that a specific piece of *provider
  data* was malformed. These are raised by validation stages and
  coercion helpers while inspecting one item at a time, and always
  carry a message that attributes the problem to a provider/field.
- ``TransformationError`` indicates that the *pipeline itself* could not
  complete — for example an unexpected exception raised while
  constructing a ``contracts`` object from data that had already passed
  validation. ``TransformationPipeline`` raises this to wrap any
  failure that is not already a ``NormalizationError``, so callers that
  only care about "did the whole pipeline succeed" can catch a single,
  predictable exception type at the top level.

``ProviderRequestError`` was added in Sprint 2.4 alongside the first
concrete adapter (Yahoo Finance). It is a sibling of
``NormalizationError``, not a subclass: ``NormalizationError`` means
"a response was received but its data is bad"; ``ProviderRequestError``
means "no usable response was received at all" (a network error, a
timeout, a non-2xx status, or a response body that isn't even valid
JSON). Keeping them separate lets a caller distinguish "the provider is
unreachable/broken" from "the provider answered but sent bad data."
"""

from __future__ import annotations

from core.exceptions import DSPAIError

__all__ = [
    "DataEngineError",
    "InvalidProviderDataError",
    "MissingFieldError",
    "NormalizationError",
    "ProviderRequestError",
    "TransformationError",
]


class DataEngineError(DSPAIError):
    """Base exception for all Data Engine errors."""


class NormalizationError(DataEngineError):
    """Base exception for raw-to-contracts normalization failures.

    Raised when a normalizer or validation stage determines that a
    specific raw provider item cannot be trusted enough to become a
    ``contracts`` object.
    """


class InvalidProviderDataError(NormalizationError):
    """Raised when raw provider data is structurally invalid or unusable.

    Examples include unparsable timestamps, non-numeric price fields,
    duplicate keys, out-of-order series, inconsistent OHLC relationships,
    and negative volume.
    """


class MissingFieldError(NormalizationError):
    """Raised when a required field is absent from raw provider data."""


class TransformationError(DataEngineError):
    """Raised when the transformation pipeline itself fails.

    This is distinct from ``NormalizationError``: it signals that
    something went wrong in the pipeline's orchestration (normalize,
    validate, or construct) that was *not* already reported as a
    ``NormalizationError`` — for example a ``contracts`` validation
    failure surfacing after data had already passed the Validation
    Pipeline, which would indicate a gap in the pipeline's own checks
    rather than a plain data-quality issue.
    """


class ProviderRequestError(DataEngineError):
    """Raised when a request to an external provider could not be completed.

    Covers transport-level failures: network errors, timeouts, non-2xx
    HTTP status codes, and response bodies that cannot even be parsed
    as JSON. Raised by the HTTP layer an adapter uses, before any
    normalization is attempted — there is no provider data to evaluate
    yet, only a failed attempt to retrieve it.
    """
