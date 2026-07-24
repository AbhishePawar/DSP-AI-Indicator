"""Architecture boundary tests for industry package."""

from __future__ import annotations

import ast
import tomllib
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1] / "src" / "industry"
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
        "decision_intelligence",
        "universe",
        "dsp_platform",
        "comparison",
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


class TestIndustryArchitecture:
    def test_no_engine_or_downstream_imports(self) -> None:
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
        assert data["project"]["dependencies"] == ["contracts", "core"]

    def test_public_api(self) -> None:
        import industry as ind

        assert ind.IndustryIdentity is not None
        assert ind.IndustryTaxonomy is not None
        assert ind.ClassificationMappingRegistry is not None
        assert ind.InvestmentCharacteristics is not None
        assert ind.InvestmentCharacteristicsRegistry is not None
        assert ind.IndustryMethodology is not None
        assert ind.IndustryMethodologyRegistry is not None
        assert ind.PeerEligibilityEvaluator is not None
        assert ind.IndustryEvidenceRegistry is not None
        assert ind.IndustryEvidenceApplicabilityRegistry is not None
        assert ind.IndustryEvidenceProviderRegistry is not None
        assert ind.IndustryEvidenceInterpreterRegistry is not None
        assert ind.EvidenceBundleAssembler is not None
        assert ind.EvidenceBundleStatus.COMPLETE.value == "complete"
        assert callable(ind.seed_example_evidence_bundle_assembler)
        assert ind.EvidenceAvailability.AVAILABLE.value == "available"
        assert ind.EvidenceObservationSeverity.INFO.value == "info"
        assert callable(ind.seed_example_evidence_provider_context)
        assert callable(ind.seed_example_evidence_interpreter_context)
        assert ind.PeerEligibilityStatus.DIRECT_PEER.value == "direct_peer"
