"""Citation / reference types — Portfolio never embeds upstream payloads."""

from __future__ import annotations

from dataclasses import dataclass

from core.exceptions import ValidationError

__all__ = [
    "ComparisonReportReference",
    "DecisionPackReference",
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
    digest = value.strip().lower()
    if not digest:
        msg = f"{field} must not be empty"
        raise ValidationError(msg)
    if len(digest) < 8:
        msg = f"{field} is too short to be a valid digest"
        raise ValidationError(msg)
    return digest


@dataclass(frozen=True, slots=True)
class DecisionPackReference:
    """Citation of a DecisionPack — never embeds the pack payload."""

    instrument_symbol: str
    digest: str

    def __post_init__(self) -> None:
        symbol = self.instrument_symbol.strip().upper()
        if not symbol:
            msg = "instrument_symbol must not be empty"
            raise ValidationError(msg)
        digest = _normalize_digest(self.digest, field="digest")
        object.__setattr__(self, "instrument_symbol", symbol)
        object.__setattr__(self, "digest", digest)


@dataclass(frozen=True, slots=True)
class ComparisonReportReference:
    """Citation of a ComparisonReport — never embeds the report payload."""

    digest: str
    methodology_id: str | None = None
    included_symbols: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        digest = _normalize_digest(self.digest, field="digest")
        methodology_id = (
            None
            if self.methodology_id is None
            else _normalize_id(self.methodology_id, field="methodology_id")
        )
        symbols = tuple(
            s.strip().upper() for s in self.included_symbols if s.strip()
        )
        if len(set(symbols)) != len(symbols):
            msg = "comparison report reference has duplicate included_symbols"
            raise ValidationError(msg)
        object.__setattr__(self, "digest", digest)
        object.__setattr__(self, "methodology_id", methodology_id)
        object.__setattr__(self, "included_symbols", symbols)
