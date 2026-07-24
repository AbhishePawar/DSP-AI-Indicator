"""Provider-neutral raw models for incoming provider data.

A raw model captures data *after* a provider adapter has mapped
vendor-specific field names onto a shared, provider-neutral shape, but
*before* any type coercion or validation has happened. Every value field
on a raw model is deliberately loosely typed — a raw model makes no
claim that its data is well-formed, only that some value was reported.

Raw models are **not** ``contracts`` types and never will be:

- ``contracts`` types are immutable, structurally validated, and
  represent the platform's stable, trusted domain vocabulary.
- Raw models represent exactly what a provider handed back, however
  messy, so that :mod:`data_engine.normalization` has something concrete
  to coerce, validate, and convert.

Turning a raw model into a ``contracts`` type is entirely the job of
:mod:`data_engine.normalization` — this module contains no conversion,
coercion, or validation logic of its own.
"""

from __future__ import annotations

from data_engine.raw_models.alternative import RawAlternativeData
from data_engine.raw_models.economic import RawEconomicDataPoint, RawEconomicSeries
from data_engine.raw_models.fundamentals import RawFundamentalData
from data_engine.raw_models.market import RawMarketBar, RawMarketSeries

__all__ = [
    "RawAlternativeData",
    "RawEconomicDataPoint",
    "RawEconomicSeries",
    "RawFundamentalData",
    "RawMarketBar",
    "RawMarketSeries",
]
