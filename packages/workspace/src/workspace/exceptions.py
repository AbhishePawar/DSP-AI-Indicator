"""Workspace package exceptions (EPIC-A010)."""

from __future__ import annotations

__all__ = [
    "WorkspaceError",
    "WorkspaceNotFoundError",
    "WorkspaceValidationError",
    "WorkspacePermissionError",
    "DuplicateNameError",
    "InvalidReferenceError",
]


class WorkspaceError(ValueError):
    """Base workspace error."""


class WorkspaceNotFoundError(WorkspaceError):
    """Missing workspace / project / entity."""


class WorkspaceValidationError(WorkspaceError):
    """Validation failure."""


class WorkspacePermissionError(WorkspaceError):
    """Actor lacks required workspace role / permission."""


class DuplicateNameError(WorkspaceValidationError):
    """Duplicate workspace or project name."""


class InvalidReferenceError(WorkspaceValidationError):
    """Invalid or missing artifact reference."""
