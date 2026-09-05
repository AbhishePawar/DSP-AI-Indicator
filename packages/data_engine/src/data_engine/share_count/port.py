"""ShareCountPort — authenticated current shares-outstanding acquisition."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from contracts.domain.instrument import Instrument
from data_engine.share_count.models import ShareCountSnapshot

__all__ = ["ShareCountPort", "ShareCountProviderHealth"]


@dataclass(frozen=True, slots=True)
class ShareCountProviderHealth:
    provider_id: str
    healthy: bool
    authenticated: bool
    detail: str
    checked_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "healthy": self.healthy,
            "authenticated": self.authenticated,
            "detail": self.detail,
            "checked_at": self.checked_at.isoformat(),
        }


class ShareCountPort(ABC):
    """Port for current shares outstanding (valuation share-count authority).

    Implementations must never estimate, derive, or fall back to another
    provider. Return ``None`` when the count is unavailable.
    """

    @abstractmethod
    def get_share_count(self, instrument: Instrument) -> ShareCountSnapshot | None:
        """Return an authenticated current-outstanding snapshot, or ``None``."""

    @abstractmethod
    def health(self) -> ShareCountProviderHealth:
        """Provider health for readiness probes."""

    @property
    @abstractmethod
    def provider_id(self) -> str:
        """Stable provider identifier."""
