"""Citation / reference types — Quantitative Risk never embeds upstream payloads."""

from __future__ import annotations

from dataclasses import dataclass

from core.exceptions import ValidationError

__all__ = [
    "BenchmarkReference",
    "HistoricalReturnsReference",
    "MarketDataReference",
    "MonitoringReference",
    "PortfolioReference",
    "ResearchReference",
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


def _normalize_digest(value: str, *, field: str) -> str:
    cleaned = value.strip().lower()
    if not cleaned or len(cleaned) < 8:
        msg = f"broken references: {field} digest invalid"
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
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        portfolio_id = _normalize_id(self.portfolio_id, field="portfolio_id")
        notes = tuple(n.strip() for n in self.notes if n.strip())
        object.__setattr__(self, "portfolio_id", portfolio_id)
        object.__setattr__(self, "notes", notes)


@dataclass(frozen=True, slots=True)
class BenchmarkReference:
    """Citation of a benchmark series / identity — never embeds series payloads."""

    benchmark_id: str
    digest: str | None = None

    def __post_init__(self) -> None:
        benchmark_id = _normalize_id(self.benchmark_id, field="benchmark_id")
        digest = (
            None
            if self.digest is None
            else _normalize_digest(self.digest, field="benchmark")
        )
        object.__setattr__(self, "benchmark_id", benchmark_id)
        object.__setattr__(self, "digest", digest)


@dataclass(frozen=True, slots=True)
class MarketDataReference:
    """Citation of a market-data port snapshot / request — never embeds bars."""

    series_id: str
    as_of: str
    digest: str | None = None

    def __post_init__(self) -> None:
        series_id = _normalize_id(self.series_id, field="series_id")
        as_of = self.as_of.strip()
        if not as_of:
            msg = "broken references: MarketDataReference as_of invalid"
            raise ValidationError(msg)
        digest = (
            None
            if self.digest is None
            else _normalize_digest(self.digest, field="market_data")
        )
        object.__setattr__(self, "series_id", series_id)
        object.__setattr__(self, "as_of", as_of)
        object.__setattr__(self, "digest", digest)


@dataclass(frozen=True, slots=True)
class HistoricalReturnsReference:
    """Citation of a historical-returns port snapshot — never embeds returns."""

    series_id: str
    window_id: str
    digest: str | None = None

    def __post_init__(self) -> None:
        series_id = _normalize_id(self.series_id, field="series_id")
        window_id = _normalize_id(self.window_id, field="window_id")
        digest = (
            None
            if self.digest is None
            else _normalize_digest(self.digest, field="historical_returns")
        )
        object.__setattr__(self, "series_id", series_id)
        object.__setattr__(self, "window_id", window_id)
        object.__setattr__(self, "digest", digest)


@dataclass(frozen=True, slots=True)
class ResearchReference:
    """Optional citation of a ResearchReport — never embeds research payloads."""

    research_id: str
    digest: str | None = None

    def __post_init__(self) -> None:
        research_id = _normalize_id(self.research_id, field="research_id")
        digest = (
            None
            if self.digest is None
            else _normalize_digest(self.digest, field="research")
        )
        object.__setattr__(self, "research_id", research_id)
        object.__setattr__(self, "digest", digest)
