"""Architecture boundary tests for risk package."""

from __future__ import annotations

import ast
import tomllib
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1] / "src" / "risk"
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


class TestRiskArchitecture:
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
        assert data["project"]["dependencies"] == [
            "core",
            "portfolio",
            "industry",
        ]

    def test_public_api(self) -> None:
        import risk as rk

        assert rk.RiskIdentity is not None
        assert rk.RiskProfile is not None
        assert rk.RiskAssessment is not None
        assert rk.RiskObservation is not None
        assert rk.RiskDescriptor is not None
        assert rk.RiskCoverage is not None
        assert rk.RiskConstraint is not None
        assert rk.RiskSummary is not None
        assert rk.RiskReport is not None
        assert rk.RiskAssembler is not None
        assert rk.RiskAnalyzer is not None
        assert rk.RiskReporter is not None
        assert rk.RiskIntegrator is not None
        assert rk.RiskIntegrationStatus.COMPLETE.value == "complete"
        assert rk.RiskReportingStatus.COMPLETE.value == "complete"
        assert rk.RiskAnalysisStatus.COMPLETE.value == "complete"
        assert rk.RiskAssemblyStatus.COMPLETE.value == "complete"
        assert rk.RiskLevel.UNKNOWN.value == "unknown"
        assert rk.__version__ == "0.5.0"
