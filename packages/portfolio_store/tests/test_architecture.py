"""Architecture boundary tests for portfolio_store package."""

from __future__ import annotations

import ast
import tomllib
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1] / "src" / "portfolio_store"
_EXPECTED_VERSION = "1.0.0"
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
        "api_platform",
        "decision_intelligence",
        "comparison",
        "universe",
        "contracts",
        "portfolio",
        "portfolio_analytics",
        "risk",
        "research",
        "industry",
        "quantitative_risk",
        "enterprise",
        "auth",
        "security_platform",
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


class TestPortfolioStoreArchitecture:
    def test_no_forbidden_imports(self) -> None:
        violations: list[str] = []
        for path in _SRC.rglob("*.py"):
            bad = _imported_top_levels(path.read_text(encoding="utf-8")) & _FORBIDDEN
            if bad:
                violations.append(f"{path.name}: {sorted(bad)}")
        assert violations == []

    def test_zero_package_dependencies(self) -> None:
        """Matches enterprise's convention: duck-type DatabasePort, no import."""
        data = tomllib.loads(
            (Path(__file__).resolve().parents[1] / "pyproject.toml").read_text(
                encoding="utf-8"
            )
        )
        assert data["project"]["dependencies"] == []
        assert data["project"]["version"] == _EXPECTED_VERSION

    def test_public_api_version(self) -> None:
        import portfolio_store as ps

        assert ps.__version__ == _EXPECTED_VERSION
        assert ps.PortfolioService is not None
        assert ps.DatabasePortfolioStore is not None
