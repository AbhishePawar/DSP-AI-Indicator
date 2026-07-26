"""Platform orchestrator façade for EPIC-001 composition."""

from __future__ import annotations

from dsp_platform.composition.config import PipelineConfiguration
from dsp_platform.composition.context import ExecutionContext
from dsp_platform.composition.models import CompositionRequest, PipelineResult
from dsp_platform.composition.pipeline import run_execution_pipeline
from dsp_platform.composition.resolver import DependencyResolver

__all__ = ["PlatformOrchestrator"]


class PlatformOrchestrator:
    """Orchestrates public package engines into a unified pipeline result."""

    def __init__(
        self,
        *,
        platform_version: str,
        configuration: PipelineConfiguration | None = None,
    ) -> None:
        self._platform_version = platform_version
        self._configuration = configuration or PipelineConfiguration()
        self._resolver = DependencyResolver(self._configuration.stages)

    @property
    def configuration(self) -> PipelineConfiguration:
        return self._configuration

    @property
    def resolver(self) -> DependencyResolver:
        return self._resolver

    def execute(self, request: CompositionRequest) -> PipelineResult:
        """Run the deterministic composition pipeline."""
        ctx = ExecutionContext(request=request)
        stop = (
            request.stop_on_stage_failure or self._configuration.stop_on_stage_failure
        )
        return run_execution_pipeline(
            ctx,
            platform_version=self._platform_version,
            stop_on_stage_failure=stop,
        )
