"""Architecture boundary tests for research package."""

from __future__ import annotations

import ast
import tomllib
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1] / "src" / "research"
_FORBIDDEN = frozenset(
    {
        "dsp",
        "fundamental",
        "economic",
        "valuation",
        "data_engine",
        "snapshot_bridge",
        "orchestration",
        "recommendation",
        "ai_committee",
        "dsp_platform",
        "decision_intelligence",
        "comparison",
        "universe",
        "contracts",
        "portfolio",
        "risk",
        "industry",
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


class TestResearchArchitecture:
    def test_no_engine_or_forbidden_imports(self) -> None:
        violations: list[str] = []
        for path in _SRC.rglob("*.py"):
            bad = _imported_top_levels(path.read_text(encoding="utf-8")) & _FORBIDDEN
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

    def test_public_api_models_only(self) -> None:
        import research as rs

        assert rs.ResearchIdentity is not None
        assert rs.ResearchProfile is not None
        assert rs.ResearchObservation is not None
        assert rs.ResearchInsight is not None
        assert rs.ResearchConflict is not None
        assert rs.ResearchGap is not None
        assert rs.ResearchAgenda is not None
        assert rs.ResearchPriority is not None
        assert rs.ResearchCoverage is not None
        assert rs.ResearchSummary is not None
        assert rs.ResearchReport is not None
        assert rs.ResearchAssembler is not None
        assert rs.ResearchSynthesizer is not None
        assert rs.ResearchReporter is not None
        assert rs.ResearchAssemblyStatus.COMPLETE.value == "complete"
        assert rs.ResearchSynthesisStatus.COMPLETE.value == "complete"
        assert rs.ResearchReportingStatus.COMPLETE.value == "complete"
        assert rs.DecisionReference is not None
        assert rs.EvidenceReference is not None
        assert rs.ResearchPriorityLevel.CRITICAL.value == "critical"
        assert rs.__version__ == "0.4.0"
