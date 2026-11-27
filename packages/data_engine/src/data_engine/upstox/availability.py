"""Explicit Upstox availability policy."""

import os


def upstox_enabled() -> bool:
    """Preserve legacy behaviour unless explicitly disabled."""
    value = os.environ.get(
        "DSP_UPSTOX_ENABLED", "true"
    ).strip().lower()

    return value in {"1", "true", "yes", "on"}
