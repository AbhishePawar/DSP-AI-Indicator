"""Architecture boundary tests for portfolio package."""

from __future__ import annotations

import ast
import tomllib
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1] / "src" / "portfolio"
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


class TestPortfolioArchitecture:
    def test_no_engine_or_platform_imports(self) -> None:
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
            "contracts",
            "core",
            "decision_intelligence",
            "industry",
            "comparison",
            "universe",
        ]

    def test_public_api(self) -> None:
        import portfolio as pf

        assert pf.Portfolio is not None
        assert pf.PortfolioIdentity is not None
        assert pf.PortfolioHolding is not None
        assert pf.PortfolioSnapshot is not None
        assert pf.PortfolioReport is not None
        assert pf.PortfolioAssembler is not None
        assert pf.PortfolioAnalyzer is not None
        assert pf.PortfolioCitationAssembler is not None
        assert pf.PortfolioMonitor is not None
        assert pf.PortfolioMonitoringStatus.INITIAL.value == "initial"
        assert pf.PortfolioChangeType.HOLDING_ADDED.value == "holding_added"
        assert pf.PortfolioTimeline is not None
        assert pf.PortfolioCitationStatus.ABSENT.value == "absent"
        assert pf.PortfolioCitationSummary is not None
        assert pf.CoverageSummary is not None
        assert pf.PortfolioAnalysisStatus.COMPLETE.value == "complete"
        assert pf.PortfolioDescriptor is not None
        assert pf.PortfolioAssemblyStatus.COMPLETE.value == "complete"
        assert pf.PortfolioType.MODEL.value == "model"
        assert pf.DecisionPackReference is not None
