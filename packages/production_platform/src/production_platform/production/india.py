"""India-first operational profile and future ports (PEP-002 architecture)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

from production_platform.production.configuration import IndiaSettings
from production_platform.production.exceptions import ProviderError
from production_platform.production.interfaces import MarketCalendarPort

__all__ = [
    "IndiaOperationalProfile",
    "NullDigiLockerPort",
    "NullPanVerificationPort",
    "NullUpiPort",
    "StaticIndiaMarketCalendar",
    "build_india_profile",
]


# Seed holidays for architecture/tests — not a licensed exchange calendar.
_STATIC_HOLIDAYS: frozenset[date] = frozenset(
    {
        date(2026, 1, 26),  # Republic Day
        date(2026, 3, 3),  # Holi (illustrative)
        date(2026, 8, 15),  # Independence Day
        date(2026, 10, 2),  # Gandhi Jayanti
        date(2026, 11, 14),  # Diwali (illustrative seed)
    }
)


class StaticIndiaMarketCalendar:
    """Minimal NSE/BSE holiday awareness — replace with licensed feed later."""

    def __init__(self, holidays: frozenset[date] | None = None) -> None:
        self._holidays = holidays if holidays is not None else _STATIC_HOLIDAYS

    def is_trading_day(self, day: Any, *, exchange: str = "NSE") -> bool:
        _ = exchange
        d = day if isinstance(day, date) else date.fromisoformat(str(day))
        if d.weekday() >= 5:
            return False
        return d not in self._holidays

    def next_trading_day(self, day: Any, *, exchange: str = "NSE") -> date:
        d = day if isinstance(day, date) else date.fromisoformat(str(day))
        cursor = d
        for _ in range(370):
            if self.is_trading_day(cursor, exchange=exchange):
                return cursor
            cursor = cursor + timedelta(days=1)
        raise ProviderError("unable to resolve next trading day")


class NullDigiLockerPort:
    """Future DigiLocker integration — architecture stub."""

    def fetch_document(self, document_id: str) -> bytes:
        raise ProviderError("DigiLockerPort not configured (future India epic)")


class NullPanVerificationPort:
    """Future PAN verification — architecture stub; minimize PII."""

    def verify(self, pan_hash: str) -> dict[str, Any]:
        raise ProviderError("PanVerificationPort not configured (future India epic)")


class NullUpiPort:
    """Future UPI rail — architecture stub."""

    def create_collect_request(self, amount_inr: str, vpa: str) -> dict[str, Any]:
        raise ProviderError("UpiPort not configured (future India epic)")


@dataclass(frozen=True, slots=True)
class IndiaOperationalProfile:
    """Composable India defaults for deploy / diagnostics."""

    settings: IndiaSettings
    market_calendar: MarketCalendarPort
    digilocker: NullDigiLockerPort
    pan_verification: NullPanVerificationPort
    upi: NullUpiPort

    @property
    def timezone(self) -> str:
        return self.settings.timezone

    @property
    def currency(self) -> str:
        return self.settings.currency


def build_india_profile(settings: IndiaSettings | None = None) -> IndiaOperationalProfile:
    cfg = settings or IndiaSettings()
    calendar: MarketCalendarPort
    if cfg.enable_market_calendar:
        calendar = StaticIndiaMarketCalendar()
    else:
        calendar = StaticIndiaMarketCalendar(holidays=frozenset())
    return IndiaOperationalProfile(
        settings=cfg,
        market_calendar=calendar,
        digilocker=NullDigiLockerPort(),
        pan_verification=NullPanVerificationPort(),
        upi=NullUpiPort(),
    )
