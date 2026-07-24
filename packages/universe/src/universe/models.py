"""Investment universe membership models."""

from __future__ import annotations

from dataclasses import dataclass, field

from contracts import Instrument
from core.exceptions import ValidationError

from universe.exceptions import UniverseError

__all__ = [
    "InvestmentUniverse",
    "UniverseEntry",
    "instrument_identity_key",
]


def instrument_identity_key(instrument: Instrument) -> tuple[str, str, str, str]:
    """Stable identity for duplicate detection and ordering.

    Membership is by symbol + asset class + currency + exchange (empty when
    unset). Universe membership does **not** imply ownership.
    """
    exchange = (instrument.exchange or "").strip().upper()
    return (
        instrument.symbol,
        instrument.asset_class.value,
        instrument.currency,
        exchange,
    )


@dataclass(frozen=True, slots=True)
class UniverseEntry:
    """One instrument in a universe with optional user tags.

    Tags are explicit user/research metadata for future sector grouping.
    Sector/industry come from ``Instrument`` when supplied — never inferred.
    """

    instrument: Instrument
    tags: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        cleaned = frozenset(t.strip().lower() for t in self.tags if t.strip())
        object.__setattr__(self, "tags", cleaned)


def _entry_sort_key(entry: UniverseEntry) -> tuple[str, str, str, str, str]:
    key = instrument_identity_key(entry.instrument)
    name = (entry.instrument.name or "").upper()
    return (*key, name)


@dataclass
class InvestmentUniverse:
    """Deterministic collection of instruments (watchlist / research set).

    Membership is not ownership. Portfolio holdings are a later phase.
    """

    name: str = "default"
    _entries: dict[tuple[str, str, str, str], UniverseEntry] = field(
        default_factory=dict, init=False, repr=False
    )

    def __post_init__(self) -> None:
        name = self.name.strip()
        if not name:
            msg = "universe name must not be empty"
            raise ValidationError(msg)
        self.name = name

    def add(
        self,
        instrument: Instrument,
        *,
        tags: frozenset[str] | set[str] | tuple[str, ...] = (),
    ) -> bool:
        """Add an instrument. Returns ``False`` if already present (no-op)."""
        key = instrument_identity_key(instrument)
        if key in self._entries:
            return False
        self._entries[key] = UniverseEntry(
            instrument=instrument,
            tags=frozenset(tags),
        )
        return True

    def remove(self, instrument: Instrument) -> bool:
        """Remove an instrument. Returns ``False`` if not present."""
        key = instrument_identity_key(instrument)
        if key not in self._entries:
            return False
        del self._entries[key]
        return True

    def contains(self, instrument: Instrument) -> bool:
        return instrument_identity_key(instrument) in self._entries

    def __len__(self) -> int:
        return len(self._entries)

    def __bool__(self) -> bool:
        return bool(self._entries)

    def clear(self) -> None:
        self._entries.clear()

    def entries(self) -> tuple[UniverseEntry, ...]:
        """Return entries in deterministic order."""
        return tuple(sorted(self._entries.values(), key=_entry_sort_key))

    def instruments(self) -> tuple[Instrument, ...]:
        """Return instruments in deterministic order."""
        return tuple(entry.instrument for entry in self.entries())

    def require_non_empty(self) -> None:
        if not self._entries:
            msg = f"universe {self.name!r} is empty"
            raise UniverseError(msg)

    @classmethod
    def from_instruments(
        cls,
        instruments: tuple[Instrument, ...] | list[Instrument],
        *,
        name: str = "default",
    ) -> InvestmentUniverse:
        universe = cls(name=name)
        for instrument in instruments:
            universe.add(instrument)
        return universe
