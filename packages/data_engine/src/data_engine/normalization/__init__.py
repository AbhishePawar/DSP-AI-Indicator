"""Canonical raw-to-contracts normalization and transformation framework.

This package converts provider-specific raw models
(:mod:`data_engine.raw_models`) into validated ``contracts`` domain
objects, following exactly one process for every provider:

    Raw Model -> Normalizer -> Validation Pipeline -> contracts Model

Contents:

- :mod:`data_engine.normalization.normalizers` — abstract normalizer
  interfaces (``MarketDataNormalizer``, ``FundamentalNormalizer``,
  ``EconomicDataNormalizer``, ``AlternativeDataNormalizer``).
- :mod:`data_engine.normalization.defaults` — ready-to-use, generic
  normalizer implementations (currently ``DefaultMarketDataNormalizer``).
- :mod:`data_engine.normalization.validation` — composable validation
  stages and the ``ValidationPipeline`` that runs them.
- :mod:`data_engine.normalization.records` — strictly-typed
  intermediate records produced by the "Normalize" step.
- :mod:`data_engine.normalization.coercion` — generic raw-value
  coercion helpers shared by normalizers.
- :mod:`data_engine.normalization.pipeline` — the reusable
  ``TransformationPipeline`` orchestrator every normalizer builds on.

See ``packages/data_engine/README.md`` for the full architecture,
dependency, and design-decision write-up.
"""

from __future__ import annotations

from data_engine.normalization.defaults import (
    DefaultEconomicNormalizer,
    DefaultFundamentalNormalizer,
    DefaultMarketDataNormalizer,
)
from data_engine.normalization.normalizers import (
    AlternativeDataNormalizer,
    EconomicDataNormalizer,
    FundamentalNormalizer,
    MarketDataNormalizer,
)
from data_engine.normalization.pipeline import TransformationPipeline
from data_engine.normalization.records import (
    NormalizedBar,
    NormalizedObservation,
    NormalizedStatement,
)
from data_engine.normalization.validation import (
    DuplicateDetectionStage,
    MissingValueValidationStage,
    OHLCConsistencyStage,
    RequiredFieldValidationStage,
    SortingVerificationStage,
    TimestampValidationStage,
    ValidationPipeline,
    ValidationStage,
    VolumeValidationStage,
)

__all__ = [
    "AlternativeDataNormalizer",
    "DefaultEconomicNormalizer",
    "DefaultFundamentalNormalizer",
    "DefaultMarketDataNormalizer",
    "DuplicateDetectionStage",
    "EconomicDataNormalizer",
    "FundamentalNormalizer",
    "MarketDataNormalizer",
    "MissingValueValidationStage",
    "NormalizedBar",
    "NormalizedObservation",
    "NormalizedStatement",
    "OHLCConsistencyStage",
    "RequiredFieldValidationStage",
    "SortingVerificationStage",
    "TimestampValidationStage",
    "TransformationPipeline",
    "ValidationPipeline",
    "ValidationStage",
    "VolumeValidationStage",
]
