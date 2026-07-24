"""Internal domain models for the Economic Engine.

:class:`EconomicSnapshot`, :class:`EconomicSignal`, and
:class:`EconomicAssessment` are engine-local — not ``contracts`` types.
Cross-engine communication in a later sprint will map
:class:`EconomicAssessment` onto shared Contracts vocabulary
(``Signal`` / ``Evidence`` / eventually a dedicated context type).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from contracts.domain.evidence import Evidence
from contracts.enums import SignalDirection
from core.exceptions import ValidationError

from economic.enums import EconomicCondition, Recommendation


@dataclass(frozen=True, slots=True)
class EconomicSnapshot:
    """Point-in-time macroeconomic inputs for one analysis run.

    Rates and growth figures are expressed as decimals (e.g. ``0.025``
    for 2.5%). PMI is an index typically near 50. Optional fields that
    are ``None`` mean "not available" and cause the corresponding
    analyzer to emit a neutral / insufficient-data signal.

    Attributes:
        as_of: Calendar date the snapshot describes.
        gdp_growth: Real GDP growth rate (decimal).
        cpi_inflation: Consumer-price inflation rate (decimal).
        interest_rate: Policy / short-term interest rate (decimal).
        interest_rate_change: Change in the policy rate since the prior
            observation (decimal). Used to detect rapid hikes/easing.
        unemployment: Unemployment rate (decimal). Reserved for future
            analyzers; unused by Sprint 6.0 analyzers.
        pmi: Purchasing Managers' Index (typically 0–100).
        currency_trend: Signed currency-strength reading (positive =
            strengthening). Reserved for future analyzers.
        liquidity_indicator: Normalized liquidity score in ``[0.0, 1.0]``
            when provided (higher = more ample liquidity).
        country: ISO 3166-1 alpha-2 country code, normalized uppercase.
    """

    as_of: date
    gdp_growth: float | None = None
    cpi_inflation: float | None = None
    interest_rate: float | None = None
    interest_rate_change: float | None = None
    unemployment: float | None = None
    pmi: float | None = None
    currency_trend: float | None = None
    liquidity_indicator: float | None = None
    country: str = "US"

    def __post_init__(self) -> None:
        """Normalize country and validate optional numeric bounds.

        Raises:
            ValidationError: If ``country`` is empty or
                ``liquidity_indicator`` is outside ``[0.0, 1.0]``.
        """
        country = self.country.strip().upper()
        if not country:
            msg = "country must not be empty"
            raise ValidationError(msg)
        if self.liquidity_indicator is not None and not (
            0.0 <= self.liquidity_indicator <= 1.0
        ):
            msg = "liquidity_indicator must be in [0.0, 1.0] when provided"
            raise ValidationError(msg)
        object.__setattr__(self, "country", country)


@dataclass(frozen=True, slots=True)
class EconomicSignal:
    """One deterministic macroeconomic observation.

    Attributes:
        name: Canonical signal identifier (e.g. ``"gdp"``, ``"pmi"``).
        direction: Bullish / bearish / neutral bias.
        observation: Short label (e.g. ``"Strong GDP Growth"``).
        reasoning: Human-readable rationale.
        value: Underlying numeric reading, if available.
        threshold: Reference threshold used in the rule, if any.
    """

    name: str
    direction: SignalDirection
    observation: str
    reasoning: str
    value: float | None = None
    threshold: float | None = None

    def __post_init__(self) -> None:
        """Normalize name and validate non-empty text fields.

        Raises:
            ValidationError: If ``name``, ``observation``, or
                ``reasoning`` is empty.
        """
        name = self.name.strip().lower()
        if not name:
            msg = "name must not be empty"
            raise ValidationError(msg)
        observation = self.observation.strip()
        if not observation:
            msg = "observation must not be empty"
            raise ValidationError(msg)
        reasoning = self.reasoning.strip()
        if not reasoning:
            msg = "reasoning must not be empty"
            raise ValidationError(msg)
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "observation", observation)
        object.__setattr__(self, "reasoning", reasoning)


@dataclass(frozen=True, slots=True)
class EconomicAssessment:
    """Complete Economic Engine output for one snapshot.

    Attributes:
        overall_condition: Macro regime classification.
        recommendation: Deterministic BUY / HOLD / SELL stance.
        reasoning: Summary of why this assessment was reached.
        evidence: ``contracts.Evidence`` items derived from detected
            signals (explainability trail for downstream engines).
        detected_signals: Every :class:`EconomicSignal` produced by
            the analyzers that ran.
        as_of: Snapshot date that was analyzed.
        assessed_at: Timezone-aware timestamp of the analysis run.
        country: Country code from the snapshot.
    """

    overall_condition: EconomicCondition
    recommendation: Recommendation
    reasoning: str
    evidence: tuple[Evidence, ...]
    detected_signals: tuple[EconomicSignal, ...]
    as_of: date
    assessed_at: datetime
    country: str

    def __post_init__(self) -> None:
        """Validate non-empty reasoning and freeze collections.

        Raises:
            ValidationError: If ``reasoning`` is empty or
                ``detected_signals`` is empty.
        """
        reasoning = self.reasoning.strip()
        if not reasoning:
            msg = "reasoning must not be empty"
            raise ValidationError(msg)
        signals = tuple(self.detected_signals)
        if not signals:
            msg = "detected_signals must not be empty"
            raise ValidationError(msg)
        object.__setattr__(self, "reasoning", reasoning)
        object.__setattr__(self, "detected_signals", signals)
        object.__setattr__(self, "evidence", tuple(self.evidence))
