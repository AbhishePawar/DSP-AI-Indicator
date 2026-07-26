"""Monorepo public-API smoke + determinism guards (ASI-006).

Protects package registration / import / export stability without exercising
domain calculations. Does not require network or wall-clock time.
"""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[3]
_REGISTERED = (
    "ai_committee",
    "api_platform",
    "business_quality",
    "comparison",
    "compliance",
    "contracts",
    "copilot",
    "core",
    "data_engine",
    "decision_intelligence",
    "dsp",
    "dsp_platform",
    "economic",
    "economic_moat",
    "management_quality",
    "financial_strength",
    "earnings_quality",
    "growth_quality",
    "business_quality_aggregator",
    "investment_recommendation",
    "investment_committee",
    "financial",
    "fundamental",
    "industry",
    "knowledge_graph",
    "orchestration",
    "portfolio",
    "production_platform",
    "quantitative_risk",
    "recommendation",
    "research",
    "risk",
    "security_platform",
    "snapshot_bridge",
    "universe",
    "valuation",
    "workflow",
)


def _snapshot() -> list[tuple[str, str, int]]:
    rows: list[tuple[str, str, int]] = []
    for name in _REGISTERED:
        mod = importlib.import_module(name)
        version = getattr(mod, "__version__", None)
        assert isinstance(version, str) and version, name
        all_names = getattr(mod, "__all__", None)
        assert isinstance(all_names, (list, tuple)), name
        missing = [item for item in all_names if not hasattr(mod, item)]
        assert missing == [], (name, missing)
        rows.append((name, version, len(all_names)))
    return rows


class TestAsiMonorepoPublicApiSmoke:
    def test_all_registered_packages_import_and_export(self) -> None:
        rows = _snapshot()
        assert len(rows) == len(_REGISTERED)
        # Orphan data-ingestion must remain unregistered.
        assert not (_REPO / "packages" / "data-ingestion" / "pyproject.toml").exists()

    def test_public_api_snapshot_is_deterministic(self) -> None:
        first = _snapshot()
        second = _snapshot()
        assert first == second


class TestAsiMonorepoFaçadeSpotChecks:
    @pytest.mark.parametrize(
        ("module_name", "attr"),
        [
            ("valuation", "ValuationEngine"),
            ("financial", "FinancialEngine"),
            ("business_quality", "BusinessQualityEngine"),
            ("business_quality", "BusinessQualityAggregator"),
            ("economic_moat", "EconomicEngine"),
            ("management_quality", "ManagementEngine"),
            ("financial_strength", "FinancialStrengthEngine"),
            ("earnings_quality", "EarningsQualityEngine"),
            ("growth_quality", "GrowthQualityEngine"),
            ("business_quality_aggregator", "BusinessQualityAggregatorEngine"),
            ("investment_recommendation", "InvestmentRecommendationEngine"),
            ("investment_committee", "InvestmentCommitteeEngine"),
            ("orchestration", "InvestmentAnalysisService"),
            ("dsp_platform", "DSPPlatform"),
            ("api_platform", "create_app"),
            ("core", "Registry"),
            ("contracts", "Instrument"),
        ],
    )
    def test_critical_façade_symbols(self, module_name: str, attr: str) -> None:
        mod = importlib.import_module(module_name)
        assert hasattr(mod, attr)
