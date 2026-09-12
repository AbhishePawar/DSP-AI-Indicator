"""Independent outstanding-share authority for valuation inputs."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from math import isfinite


@dataclass(frozen=True, slots=True)
class ShareCount:
    ticker: str
    shares: float
    as_of: date
    source: str

    def __post_init__(self) -> None:
        if not self.ticker.strip() or not isfinite(self.shares) or self.shares <= 0:
            raise ValueError("share count requires a ticker and positive finite shares")
        if not self.source.strip():
            raise ValueError("share count source is required")

    def to_dict(self) -> dict[str, object]:
        return {
            "ticker": self.ticker,
            "shares": self.shares,
            "as_of": self.as_of.isoformat(),
            "source": self.source,
        }


class ShareCountPort(ABC):
    """Port deliberately separate from financial statements and market quotes."""

    @abstractmethod
    def get_outstanding_shares(self, ticker: str) -> ShareCount | None:
        """Return authenticated outstanding shares or ``None``."""


class InMemoryShareCountPort(ShareCountPort):
    def __init__(self, rows: tuple[ShareCount, ...] = ()) -> None:
        self._rows = {row.ticker.strip().upper(): row for row in rows}

    def get_outstanding_shares(self, ticker: str) -> ShareCount | None:
        return self._rows.get(ticker.strip().upper())


__all__ = ["InMemoryShareCountPort", "ShareCount", "ShareCountPort"]
