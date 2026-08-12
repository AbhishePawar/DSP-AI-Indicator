"""Admin console exceptions (EPIC-A010)."""

from __future__ import annotations

__all__ = ["AdminError", "NotFoundError", "ValidationError"]


class AdminError(ValueError):
    """Base admin console error."""


class NotFoundError(AdminError):
    """Requested admin resource missing."""


class ValidationError(AdminError):
    """Invalid admin query / filter."""
