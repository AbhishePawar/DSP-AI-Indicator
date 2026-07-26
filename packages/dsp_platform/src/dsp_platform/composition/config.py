"""Pipeline configuration for EPIC-001 composition."""

from __future__ import annotations

from dataclasses import dataclass

from dsp_platform.composition.pipeline import EXECUTION_ORDER, PipelineStage

__all__ = ["PipelineConfiguration"]


@dataclass(frozen=True, slots=True)
class PipelineConfiguration:
    """Strongly typed pipeline settings — no scoring parameters."""

    stages: tuple[PipelineStage, ...] = EXECUTION_ORDER
    stop_on_stage_failure: bool = False
    collect_timing: bool = True
    collect_evidence: bool = True

    def to_dict(self) -> dict[str, object]:
        return {
            "stages": [s.value for s in self.stages],
            "stop_on_stage_failure": self.stop_on_stage_failure,
            "collect_timing": self.collect_timing,
            "collect_evidence": self.collect_evidence,
        }
