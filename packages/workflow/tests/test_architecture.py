"""Architecture boundary tests for workflow domain modules (H1.3)."""

from __future__ import annotations

import ast
import tomllib
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1] / "src" / "workflow"
_DOMAIN_FILES = frozenset(
    {
        "models.py",
        "refs.py",
        "enums.py",
        "exceptions.py",
        "validation.py",
        "assembler.py",
        "engine.py",
        "reporter.py",
        "__init__.py",
    }
)
_FORBIDDEN_IN_DOMAIN = frozenset(
    {
        "dsp",
        "fundamental",
        "economic",
        "valuation",
        "data_engine",
        "snapshot_bridge",
        "orchestration",
        "ai_committee",
        "dsp_platform",
        "decision_intelligence",
        "comparison",
        "universe",
        "contracts",
        "portfolio",
        "risk",
        "research",
        "industry",
        "quantitative_risk",
        "recommendation",
    }
)


def _imported_top_levels(source: str) -> frozenset[str]:
    tree = ast.parse(source)
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name.split(".", 1)[0])
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            names.add(node.module.split(".", 1)[0])
    return frozenset(names)


class TestWorkflowArchitecture:
    def test_domain_modules_forbid_upstream_imports(self) -> None:
        violations: list[str] = []
        for path in _SRC.rglob("*.py"):
            if path.name not in _DOMAIN_FILES:
                continue
            bad = (
                _imported_top_levels(path.read_text(encoding="utf-8"))
                & _FORBIDDEN_IN_DOMAIN
            )
            if bad:
                violations.append(f"{path.name}: {sorted(bad)}")
        assert violations == []

    def test_dependencies(self) -> None:
        data = tomllib.loads(
            (Path(__file__).resolve().parents[1] / "pyproject.toml").read_text(
                encoding="utf-8"
            )
        )
        assert data["project"]["dependencies"] == ["core"]
        assert data["project"]["version"] == "0.4.0"

    def test_public_api_includes_full_pipeline(self) -> None:
        import workflow as wf

        assert wf.WorkflowAssembler is not None
        assert wf.WorkflowEngine is not None
        assert wf.WorkflowReporter is not None
        assert wf.ReportingStatus.COMPLETE.value == "complete"
        assert wf.ExecutionSection is not None
        assert wf.ReportMetadata is not None
        assert wf.__version__ == "0.4.0"
