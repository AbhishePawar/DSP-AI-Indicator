"""Shared enumerations used across all domain contracts.

These enumerations provide a controlled vocabulary for concepts that recur
across every engine in the platform: asset classification, statement and
series framing, signal direction, recommendation actions, and provenance
tagging. Defining them once here prevents each future engine from inventing
its own incompatible vocabulary for the same concept.
"""

from __future__ import annotations

from enum import StrEnum


class AssetClass(StrEnum):
    """Broad classification of a tradable instrument."""

    EQUITY = "equity"
    FIXED_INCOME = "fixed_income"
    COMMODITY = "commodity"
    CURRENCY = "currency"
    CRYPTO = "crypto"
    DERIVATIVE = "derivative"
    ETF = "etf"
    INDEX = "index"
    FUND = "fund"


class BarFrequency(StrEnum):
    """Sampling frequency of a price bar series."""

    TICK = "tick"
    MINUTE_1 = "1min"
    MINUTE_5 = "5min"
    MINUTE_15 = "15min"
    MINUTE_30 = "30min"
    HOURLY = "1hour"
    DAILY = "1day"
    WEEKLY = "1week"
    MONTHLY = "1month"


class StatementPeriodType(StrEnum):
    """Reporting period type for a fundamental statement."""

    ANNUAL = "annual"
    QUARTERLY = "quarterly"
    TRAILING_TWELVE_MONTHS = "ttm"


class EconomicFrequency(StrEnum):
    """Observation frequency for an economic data series."""

    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"


class SignalDirection(StrEnum):
    """Directional bias expressed by an analytical signal."""

    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


class RecommendationAction(StrEnum):
    """Discrete investment action produced by the AI Investment Committee."""

    STRONG_BUY = "strong_buy"
    BUY = "buy"
    HOLD = "hold"
    SELL = "sell"
    STRONG_SELL = "strong_sell"


class AnalyticalStance(StrEnum):
    """BUY / HOLD / SELL stance from an analytical engine.

    Distinct from :class:`RecommendationAction`, which is the committee's
    terminal vocabulary (including strong variants). Engines that emit a
    simple directional stance use this enum so the committee can consume
    a contracts-stable type without importing engine packages.
    """

    BUY = "buy"
    HOLD = "hold"
    SELL = "sell"


class ValuationConfidence(StrEnum):
    """Confidence label for an aggregated intrinsic-value assessment.

    Shared-kernel vocabulary so the committee can gate directional MoS
    votes without depending on the Valuation Engine package.
    """

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INSUFFICIENT = "insufficient"


class EngineSource(StrEnum):
    """Identifies which platform engine produced a piece of data.

    Used strictly as a provenance tag on contract instances (see
    :class:`~contracts.domain.explanation.Explanation` and
    :class:`~contracts.domain.evidence.Evidence`). The Contracts package
    does not import the engines themselves; this enum only names them so
    that provenance can be recorded without creating a real dependency.
    """

    DATA_ENGINE = "data_engine"
    INDICATOR_ENGINE = "indicator_engine"
    FUNDAMENTAL_ENGINE = "fundamental_engine"
    ECONOMIC_ENGINE = "economic_engine"
    VALUATION_ENGINE = "valuation_engine"
    BEHAVIORAL_ENGINE = "behavioral_engine"
    PORTFOLIO_ENGINE = "portfolio_engine"
    RISK_ENGINE = "risk_engine"
    AI_COMMITTEE = "ai_committee"
    RESEARCH_ENGINE = "research_engine"
