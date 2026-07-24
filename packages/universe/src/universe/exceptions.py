"""Investment universe and multi-stock Decision Pack foundation."""

from __future__ import annotations

from core.exceptions import DSPAIError

__all__ = ["UniverseError"]


class UniverseError(DSPAIError):
    """Raised for invalid universe membership or batch configuration."""
