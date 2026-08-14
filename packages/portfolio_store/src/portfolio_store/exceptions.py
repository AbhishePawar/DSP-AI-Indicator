"""portfolio_store domain exceptions (mirrors enterprise.exceptions)."""

from __future__ import annotations

__all__ = [
    "ForbiddenError",
    "NotFoundError",
    "PortfolioStoreError",
    "ValidationError",
]


class PortfolioStoreError(Exception):
    """Base portfolio_store error."""


class ValidationError(PortfolioStoreError):
    """Invalid input or state transition."""


class NotFoundError(PortfolioStoreError):
    """Requested portfolio/holding/transaction/watchlist resource does not exist."""


class ForbiddenError(PortfolioStoreError):
    """The requesting user does not own the requested resource."""
