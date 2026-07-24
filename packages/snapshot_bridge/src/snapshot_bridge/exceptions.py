"""Exceptions for the Snapshot Bridge package."""

from __future__ import annotations

from core.exceptions import DSPAIError

__all__ = ["SnapshotBridgeError"]


class SnapshotBridgeError(DSPAIError):
    """Raised when snapshot construction or derivation fails.

    Wraps structural validation failures from engine snapshot models
    and bridge-local mapping errors so callers catch one hierarchy.
    """
