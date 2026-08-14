"""In-memory workflow registry (EPIC-A007).

Stores workflow state only — never mutates research artifacts.
"""

from __future__ import annotations

from threading import RLock

from dsp_platform.institutional_workflow.models import WorkflowInstance

__all__ = [
    "WorkflowRegistry",
    "get_workflow_registry",
    "reset_workflow_registry_for_tests",
]


class WorkflowRegistry:
    def __init__(self) -> None:
        self._lock = RLock()
        self._workflows: dict[str, WorkflowInstance] = {}

    def put(self, workflow: WorkflowInstance) -> WorkflowInstance:
        with self._lock:
            self._workflows[workflow.workflow_id] = workflow
            return workflow

    def get(self, workflow_id: str) -> WorkflowInstance | None:
        with self._lock:
            return self._workflows.get(workflow_id)

    def require(self, workflow_id: str) -> WorkflowInstance:
        wf = self.get(workflow_id)
        if wf is None:
            raise KeyError(f"workflow not found: {workflow_id}")
        return wf

    def list_ids(self) -> tuple[str, ...]:
        with self._lock:
            return tuple(sorted(self._workflows.keys()))

    def list_workflows(self) -> tuple[WorkflowInstance, ...]:
        with self._lock:
            return tuple(
                self._workflows[k] for k in sorted(self._workflows.keys())
            )


_REG: WorkflowRegistry | None = None


def get_workflow_registry() -> WorkflowRegistry:
    global _REG
    if _REG is None:
        _REG = WorkflowRegistry()
    return _REG


def reset_workflow_registry_for_tests(reg: WorkflowRegistry | None = None) -> None:
    global _REG
    _REG = reg
