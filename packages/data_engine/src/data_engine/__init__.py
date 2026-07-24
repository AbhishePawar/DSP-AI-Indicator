"""Data Engine public API.

The Data Engine is the platform's data-acquisition and normalization
layer. Concrete adapters: Yahoo Finance (OHLCV + fundamentals) and FRED
(macroeconomic series). Depends only on ``contracts`` and ``core``.
"""

from __future__ import annotations

from data_engine.adapters import BaseAdapter
from data_engine.adapters.fred import (
    CANONICAL_INDICATOR_CODES,
    FRED_METADATA,
    FredEconomicAdapter,
    build_fred_adapter,
    register_fred,
    supported_indicator_codes,
)
from data_engine.adapters.yahoo_finance import (
    YAHOO_FINANCE_FUNDAMENTALS_METADATA,
    YAHOO_FINANCE_METADATA,
    JsonHttpClient,
    UrllibJsonHttpClient,
    YahooFinanceAdapter,
    YahooFinanceFundamentalsAdapter,
    build_yahoo_finance_adapter,
    build_yahoo_finance_fundamentals_adapter,
    register_yahoo_finance,
    register_yahoo_finance_fundamentals,
)
from data_engine.builders import EconomicSeriesBuilder, FundamentalStatementsBuilder
from data_engine.cache import CachePort, InMemoryCache
from data_engine.config import DataEngineConfig
from data_engine.exceptions import (
    DataEngineError,
    InvalidProviderDataError,
    MissingFieldError,
    NormalizationError,
    ProviderRequestError,
    TransformationError,
)
from data_engine.models import EconomicRequest, FundamentalsRequest, PriceSeriesRequest
from data_engine.normalization import (
    AlternativeDataNormalizer,
    DefaultEconomicNormalizer,
    DefaultFundamentalNormalizer,
    DefaultMarketDataNormalizer,
    DuplicateDetectionStage,
    EconomicDataNormalizer,
    FundamentalNormalizer,
    MarketDataNormalizer,
    MissingValueValidationStage,
    NormalizedBar,
    NormalizedObservation,
    NormalizedStatement,
    OHLCConsistencyStage,
    RequiredFieldValidationStage,
    SortingVerificationStage,
    TimestampValidationStage,
    TransformationPipeline,
    ValidationPipeline,
    ValidationStage,
    VolumeValidationStage,
)
from data_engine.ports import (
    AlternativeDataPort,
    EconomicDataPort,
    FundamentalsDataPort,
    MarketDataPort,
)
from data_engine.providers import (
    AuthenticationType,
    DataCapability,
    ProviderBuilder,
    ProviderCapabilities,
    ProviderFactory,
    ProviderMetadata,
    ProviderRegistry,
    ProviderStatus,
    RateLimitPolicy,
)
from data_engine.raw_models import (
    RawAlternativeData,
    RawEconomicDataPoint,
    RawEconomicSeries,
    RawFundamentalData,
    RawMarketBar,
    RawMarketSeries,
)
from data_engine.services import (
    EconomicDataService,
    FundamentalsDataService,
    MarketDataService,
)

__all__ = [
    "AlternativeDataNormalizer",
    "AlternativeDataPort",
    "AuthenticationType",
    "BaseAdapter",
    "CANONICAL_INDICATOR_CODES",
    "CachePort",
    "DataCapability",
    "DataEngineConfig",
    "DataEngineError",
    "DefaultEconomicNormalizer",
    "DefaultFundamentalNormalizer",
    "DefaultMarketDataNormalizer",
    "DuplicateDetectionStage",
    "EconomicDataNormalizer",
    "EconomicDataPort",
    "EconomicDataService",
    "EconomicRequest",
    "EconomicSeriesBuilder",
    "FRED_METADATA",
    "FredEconomicAdapter",
    "FundamentalNormalizer",
    "FundamentalStatementsBuilder",
    "FundamentalsDataPort",
    "FundamentalsDataService",
    "FundamentalsRequest",
    "InMemoryCache",
    "InvalidProviderDataError",
    "JsonHttpClient",
    "MarketDataNormalizer",
    "MarketDataPort",
    "MarketDataService",
    "MissingFieldError",
    "MissingValueValidationStage",
    "NormalizationError",
    "NormalizedBar",
    "NormalizedObservation",
    "NormalizedStatement",
    "OHLCConsistencyStage",
    "PriceSeriesRequest",
    "ProviderBuilder",
    "ProviderCapabilities",
    "ProviderFactory",
    "ProviderMetadata",
    "ProviderRegistry",
    "ProviderRequestError",
    "ProviderStatus",
    "RateLimitPolicy",
    "RawAlternativeData",
    "RawEconomicDataPoint",
    "RawEconomicSeries",
    "RawFundamentalData",
    "RawMarketBar",
    "RawMarketSeries",
    "RequiredFieldValidationStage",
    "SortingVerificationStage",
    "TimestampValidationStage",
    "TransformationError",
    "TransformationPipeline",
    "UrllibJsonHttpClient",
    "ValidationPipeline",
    "ValidationStage",
    "VolumeValidationStage",
    "YAHOO_FINANCE_FUNDAMENTALS_METADATA",
    "YAHOO_FINANCE_METADATA",
    "YahooFinanceAdapter",
    "YahooFinanceFundamentalsAdapter",
    "build_fred_adapter",
    "build_yahoo_finance_adapter",
    "build_yahoo_finance_fundamentals_adapter",
    "register_fred",
    "register_yahoo_finance",
    "register_yahoo_finance_fundamentals",
    "supported_indicator_codes",
]

__version__ = "0.6.0"
