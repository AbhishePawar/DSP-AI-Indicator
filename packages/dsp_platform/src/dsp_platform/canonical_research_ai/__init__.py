"""Canonical research AI interpret seam (production blocked).

The deterministic test implementation lives in ``testing.py`` and must
not be imported by production HTTP, assembly, or provider packages.
"""

from __future__ import annotations

from dsp_platform.canonical_research_ai.models import CanonicalAIDraft
from dsp_platform.canonical_research_ai.port import (
    CanonicalResearchAiBlockedError,
    CanonicalResearchAiPort,
    ProductionBlockedCanonicalResearchAiPort,
)

__all__ = [
    "CanonicalAIDraft",
    "CanonicalResearchAiBlockedError",
    "CanonicalResearchAiPort",
    "ProductionBlockedCanonicalResearchAiPort",
]
