"""Currency primitives for the Financial Statement Domain."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

__all__ = ["CurrencyCode", "CurrencyRef"]


class CurrencyCode(str, Enum):
    """ISO-style currency codes used in research statements.

    Provider-agnostic — no exchange or market API coupling.
    """

    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    INR = "INR"
    JPY = "JPY"
    CNY = "CNY"
    CHF = "CHF"
    CAD = "CAD"
    AUD = "AUD"
    HKD = "HKD"
    SGD = "SGD"
    OTHER = "OTHER"


@dataclass(frozen=True, slots=True)
class CurrencyRef:
    """Immutable currency reference for a statement or company."""

    code: CurrencyCode = CurrencyCode.USD
    label: str = ""

    def to_dict(self) -> dict[str, str]:
        return {"code": self.code.value, "label": self.label}

    @classmethod
    def from_dict(cls, data: dict) -> CurrencyRef:
        raw = str(data.get("code") or "USD").upper()
        try:
            code = CurrencyCode(raw)
        except ValueError:
            code = CurrencyCode.OTHER
        return cls(code=code, label=str(data.get("label") or ""))

    @classmethod
    def parse(cls, value: str | CurrencyCode | CurrencyRef | None) -> CurrencyRef:
        """Normalize free-form currency input into a :class:`CurrencyRef`."""
        if value is None:
            return cls()
        if isinstance(value, CurrencyRef):
            return value
        if isinstance(value, CurrencyCode):
            return cls(code=value)
        text = str(value).strip().upper()
        if not text:
            return cls()
        try:
            return cls(code=CurrencyCode(text))
        except ValueError:
            return cls(code=CurrencyCode.OTHER, label=text)
