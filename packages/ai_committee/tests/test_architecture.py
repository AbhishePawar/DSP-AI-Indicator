"""Architecture tests: committee depends only on contracts (+ core)."""

from __future__ import annotations

import ast
import tomllib
from pathlib import Path

_COMMITTEE_SRC = Path(__file__).resolve().parents[1] / "src" / "ai_committee"
_FORBIDDEN_ENGINE_PACKAGES = frozenset(
    {
        "dsp",
        "fundamental",
        "economic",
        "valuation",
        "data_engine",
        "snapshot_bridge",
        "orchestration",
        "recommendation",
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


class TestCommitteeImportBoundary:
    def test_production_src_has_no_engine_imports(self) -> None:
        violations: list[str] = []
        for path in _COMMITTEE_SRC.rglob("*.py"):
            imported = _imported_top_levels(path.read_text(encoding="utf-8"))
            bad = imported & _FORBIDDEN_ENGINE_PACKAGES
            if bad:
                rel = path.relative_to(_COMMITTEE_SRC.parents[2])
                violations.append(f"{rel}: {sorted(bad)}")
        assert violations == [], "\n".join(violations)

    def test_committee_input_annotations_use_contract_dtos(self) -> None:
        from ai_committee.models import CommitteeInput

        hints = {k: str(v) for k, v in CommitteeInput.__annotations__.items()}
        assert "TechnicalContext" in hints["technical"]
        assert "FundamentalContext" in hints["fundamental"]
        assert "EconomicContext" in hints["economic"]
        assert "ValuationContext" in hints["valuation"]

    def test_package_depends_only_on_contracts_and_core(self) -> None:
        pyproject = Path(__file__).resolve().parents[1] / "pyproject.toml"
        data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
        assert data["project"]["dependencies"] == ["contracts", "core"]
