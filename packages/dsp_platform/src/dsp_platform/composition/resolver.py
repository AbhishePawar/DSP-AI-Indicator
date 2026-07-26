"""Dependency resolution for composition stages (ordering only)."""

from __future__ import annotations

from dsp_platform.composition.pipeline import EXECUTION_ORDER, PipelineStage

__all__ = ["DependencyResolver"]


class DependencyResolver:
    """Resolves deterministic execution order — no graph cycles introduced."""

    def __init__(self, stages: tuple[PipelineStage, ...] | None = None) -> None:
        self._stages = stages or EXECUTION_ORDER

    @property
    def order(self) -> tuple[PipelineStage, ...]:
        return self._stages

    def prerequisites(self, stage: PipelineStage) -> tuple[PipelineStage, ...]:
        idx = self._stages.index(stage)
        return self._stages[:idx]

    def validate_order(self, stages: tuple[PipelineStage, ...]) -> bool:
        """Return True if ``stages`` respects the canonical prefix order."""
        expected = list(self._stages)
        seen: list[PipelineStage] = []
        for stage in stages:
            if stage not in expected:
                return False
            # Must appear in relative order of EXECUTION_ORDER
            if seen:
                if expected.index(stage) < expected.index(seen[-1]):
                    return False
            seen.append(stage)
        return True
