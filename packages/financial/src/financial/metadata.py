"""Company / statement metadata for the Financial Statement Domain."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from financial.currency import CurrencyRef

__all__ = [
    "AccountingStandard",
    "UnitScale",
    "CompanyMetadata",
    "StatementMetadata",
]


class AccountingStandard(str, Enum):
    """Accounting framework tags (research metadata only)."""

    IFRS = "ifrs"
    US_GAAP = "us_gaap"
    IND_AS = "ind_as"
    OTHER = "other"
    UNKNOWN = "unknown"


class UnitScale(str, Enum):
    """Numeric unit scale for statement figures."""

    ACTUAL = "actual"
    THOUSANDS = "thousands"
    MILLIONS = "millions"
    BILLIONS = "billions"


@dataclass(frozen=True, slots=True)
class CompanyMetadata:
    """Immutable company identity metadata (provider-agnostic)."""

    company: str = ""
    ticker: str = ""
    exchange: str = ""
    isin: str = ""
    sector: str = ""
    industry: str = ""
    country: str = ""
    accounting_standard: AccountingStandard = AccountingStandard.UNKNOWN
    reporting_currency: CurrencyRef = CurrencyRef()

    def to_dict(self) -> dict[str, Any]:
        return {
            "company": self.company,
            "ticker": self.ticker,
            "exchange": self.exchange,
            "isin": self.isin,
            "sector": self.sector,
            "industry": self.industry,
            "country": self.country,
            "accounting_standard": self.accounting_standard.value,
            "reporting_currency": self.reporting_currency.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CompanyMetadata:
        std_raw = str(data.get("accounting_standard") or "unknown").lower()
        try:
            std = AccountingStandard(std_raw)
        except ValueError:
            std = AccountingStandard.OTHER
        currency_raw = data.get("reporting_currency")
        if isinstance(currency_raw, dict):
            currency = CurrencyRef.from_dict(currency_raw)
        else:
            currency = CurrencyRef.parse(currency_raw)
        return cls(
            company=str(data.get("company") or ""),
            ticker=str(data.get("ticker") or ""),
            exchange=str(data.get("exchange") or ""),
            isin=str(data.get("isin") or ""),
            sector=str(data.get("sector") or ""),
            industry=str(data.get("industry") or ""),
            country=str(data.get("country") or ""),
            accounting_standard=std,
            reporting_currency=currency,
        )


@dataclass(frozen=True, slots=True)
class StatementMetadata:
    """Statement-level units / provenance metadata."""

    unit_scale: UnitScale = UnitScale.ACTUAL
    currency: CurrencyRef = CurrencyRef()
    source: str = ""
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "unit_scale": self.unit_scale.value,
            "currency": self.currency.to_dict(),
            "source": self.source,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StatementMetadata:
        scale_raw = str(data.get("unit_scale") or "actual").lower()
        try:
            scale = UnitScale(scale_raw)
        except ValueError:
            scale = UnitScale.ACTUAL
        currency_raw = data.get("currency")
        if isinstance(currency_raw, dict):
            currency = CurrencyRef.from_dict(currency_raw)
        else:
            currency = CurrencyRef.parse(currency_raw)
        return cls(
            unit_scale=scale,
            currency=currency,
            source=str(data.get("source") or ""),
            notes=str(data.get("notes") or ""),
        )
