"""Enterprise domain exceptions."""

from __future__ import annotations


class EnterpriseError(Exception):
    """Base enterprise error."""


class ValidationError(EnterpriseError):
    """Invalid input or state transition."""


class NotFoundError(EnterpriseError):
    """Requested enterprise resource does not exist."""


class ForbiddenError(EnterpriseError):
    """Permission denied for the requested enterprise action."""
