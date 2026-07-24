"""Public façade service for the DSP AI Indicator platform.

K1.0 — ``DSPPlatform`` lives in ``platform.py``. This module re-exports
for backward-compatible imports (``dsp_platform.facade`` / health).
"""

from __future__ import annotations

from dsp_platform.platform import DSPPlatform

__all__ = ["DSPPlatform"]
