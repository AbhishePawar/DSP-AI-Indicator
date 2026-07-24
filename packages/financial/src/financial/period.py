"""Financial reporting period models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Any

from financial.currency import CurrencyRef

__all__ = ["PeriodType", "FinancialPeriod"]


class PeriodType(str, Enum):
    """Supported reporting period kinds."""

    ANNUAL = "annual"
    QUARTERLY = "quarterly"
    TTM = "ttm"
    HALF_YEAR = "half_year"
    CUSTOM = "custom"


@dataclass(frozen=True, slots=True)
class FinancialPeriod:
    """Canonical reporting period metadata.

    Attributes:
        period_type: Annual / quarterly / TTM / half-year / custom.
        fiscal_year: Fiscal year label (e.g. 2024).
        fiscal_quarter: 1–4 when quarterly; ``None`` otherwise.
        period_end: Period end date (required for validation).
        reporting_date: Filing / report date when known.
        period_length_days: Optional explicit length.
        currency: Statement currency for this period.
        audited: Whether figures are audited.
        restated: Whether this period reflects a restatement.
        source: Opaque provider / document label (not an API client).
    """

    period_type: PeriodType
    period_end: date
    fiscal_year: int | None = None
    fiscal_quarter: int | None = None
    reporting_date: date | None = None
    period_length_days: int | None = None
    currency: CurrencyRef = CurrencyRef()
    audited: bool = False
    restated: bool = False
    source: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "period_type": self.period_type.value,
            "period_end": self.period_end.isoformat(),
            "fiscal_year": self.fiscal_year,
            "fiscal_quarter": self.fiscal_quarter,
            "reporting_date": (
                self.reporting_date.isoformat() if self.reporting_date else None
            ),
            "period_length_days": self.period_length_days,
            "currency": self.currency.to_dict(),
            "audited": self.audited,
            "restated": self.restated,
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FinancialPeriod:
        period_type = PeriodType(str(data["period_type"]))
        period_end = date.fromisoformat(str(data["period_end"]))
        reporting_raw = data.get("reporting_date")
        reporting_date = (
            date.fromisoformat(str(reporting_raw)) if reporting_raw else None
        )
        currency_raw = data.get("currency")
        if isinstance(currency_raw, dict):
            currency = CurrencyRef.from_dict(currency_raw)
        else:
            currency = CurrencyRef.parse(currency_raw)
        return cls(
            period_type=period_type,
            period_end=period_end,
            fiscal_year=data.get("fiscal_year"),
            fiscal_quarter=data.get("fiscal_quarter"),
            reporting_date=reporting_date,
            period_length_days=data.get("period_length_days"),
            currency=currency,
            audited=bool(data.get("audited", False)),
            restated=bool(data.get("restated", False)),
            source=str(data.get("source") or ""),
        )

    def key(self) -> tuple[str, str, int | None, int | None]:
        """Hashable identity for duplicate-period detection."""
        return (
            self.period_type.value,
            self.period_end.isoformat(),
            self.fiscal_year,
            self.fiscal_quarter,
        )
