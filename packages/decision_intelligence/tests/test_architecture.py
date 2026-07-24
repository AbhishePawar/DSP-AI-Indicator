"""Architecture boundary tests for Decision Intelligence."""

from __future__ import annotations

import ast
import tomllib
from pathlib import Path

_DI_SRC = Path(__file__).resolve().parents[1] / "src" / "decision_intelligence"
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


class TestDecisionIntelligenceBoundaries:
    def test_production_src_has_no_engine_imports(self) -> None:
        violations: list[str] = []
        for path in _DI_SRC.rglob("*.py"):
            imported = _imported_top_levels(path.read_text(encoding="utf-8"))
            bad = imported & _FORBIDDEN_ENGINE_PACKAGES
            if bad:
                rel = path.relative_to(_DI_SRC.parents[2])
                violations.append(f"{rel}: {sorted(bad)}")
        assert violations == [], "\n".join(violations)

    def test_package_depends_only_on_contracts_core_committee_industry(self) -> None:
        pyproject = Path(__file__).resolve().parents[1] / "pyproject.toml"
        data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
        assert data["project"]["dependencies"] == [
            "contracts",
            "core",
            "ai_committee",
            "industry",
        ]

    def test_public_api_exports(self) -> None:
        import decision_intelligence as di

        assert di.DecisionPack is not None
        assert di.DecisionBrief is not None
        assert di.AssuranceAssessment is not None
        assert di.DecisionIntelligenceService is not None
        assert di.GuidanceStance.STAND_ASIDE.value == "stand_aside"
        assert di.AssuranceLevel.HIGH.value == "high"
        assert callable(di.present_decision_pack)
        assert di.DecisionPackView is not None
        assert di.DecisionPackEvidenceSummary is not None
        assert callable(di.attach_evidence_bundle_ref)
