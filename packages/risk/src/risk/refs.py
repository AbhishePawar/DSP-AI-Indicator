"""Citation / reference types — Risk never embeds upstream payloads."""

from __future__ import annotations

from dataclasses import dataclass

from core.exceptions import ValidationError
from portfolio import PortfolioMonitoringStatus

__all__ = [
    "MonitoringReference",
    "PortfolioReference",
    "_normalize_id",
]


def _normalize_id(value: str, *, field: str) -> str:
    cleaned = value.strip().lower()
    if not cleaned:
        msg = f"{field} must not be empty"
        raise ValidationError(msg)
    if any(ch.isspace() for ch in cleaned):
        msg = f"{field} must not contain whitespace"
        raise ValidationError(msg)
    return cleaned


@dataclass(frozen=True, slots=True)
class PortfolioReference:
    """Citation of a Portfolio — never embeds the Portfolio payload."""

    portfolio_id: str
    snapshot_id: str | None = None

    def __post_init__(self) -> None:
        portfolio_id = _normalize_id(self.portfolio_id, field="portfolio_id")
        snapshot_id = (
            None
            if self.snapshot_id is None
            else _normalize_id(self.snapshot_id, field="snapshot_id")
        )
        object.__setattr__(self, "portfolio_id", portfolio_id)
        object.__setattr__(self, "snapshot_id", snapshot_id)


@dataclass(frozen=True, slots=True)
class MonitoringReference:
    """Citation of Portfolio Monitoring state — never embeds monitoring payloads."""

    portfolio_id: str
    status: PortfolioMonitoringStatus | None = None
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        portfolio_id = _normalize_id(self.portfolio_id, field="portfolio_id")
        notes = tuple(n.strip() for n in self.notes if n.strip())
        object.__setattr__(self, "portfolio_id", portfolio_id)
        object.__setattr__(self, "notes", notes)
