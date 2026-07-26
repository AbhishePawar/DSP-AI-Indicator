"""Composition-stage errors (structured, non-corrupting)."""

from __future__ import annotations

from dsp_platform.platform_exceptions import PlatformError

__all__ = ["CompositionStageError"]


class CompositionStageError(PlatformError):
    """Raised when a composition stage fails and stop-on-failure is enabled."""

    def __init__(self, stage: str, message: str) -> None:
        self.stage = stage
        super().__init__(f"[{stage}] {message}")
