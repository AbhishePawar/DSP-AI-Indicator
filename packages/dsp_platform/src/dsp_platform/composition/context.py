"""Execution context for composition pipeline."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from data_engine import ShareCount

from dsp_platform.composition.models import CompositionRequest, ExecutionTraceEntry

__all__ = ["ExecutionContext"]


@dataclass
class ExecutionContext:
    """Mutable working state during a single pipeline run."""

    request: CompositionRequest
    results: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    trace: list[ExecutionTraceEntry] = field(default_factory=list)
    package_versions: dict[str, str] = field(default_factory=dict)
    evidence_counts: dict[str, int] = field(default_factory=dict)
    confidence_summary: dict[str, float | None] = field(default_factory=dict)
    failed_stage: str | None = None
    # Optional server-side AI research hook used only when authoritative share count is missing.
    share_count_researcher: Callable[[str], ShareCount | None] | None = None
