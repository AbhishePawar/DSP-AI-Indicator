"""Application import-boundary enforcement tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from dsp_platform import (
    ALLOWED_APPLICATION_PACKAGES,
    FORBIDDEN_APPLICATION_PACKAGES,
    PLATFORM_PACKAGES,
    PlatformError,
    assert_application_imports,
    assert_public_sibling_imports,
    scan_cross_package_deep_imports,
    scan_module_imports,
)

_SAMPLES = Path(__file__).resolve().parent / "samples"
_REPO_ROOT = Path(__file__).resolve().parents[3]


class TestImportBoundaries:
    def test_allowed_and_forbidden_sets(self) -> None:
        assert "dsp_platform" in ALLOWED_APPLICATION_PACKAGES
        assert "contracts" in ALLOWED_APPLICATION_PACKAGES
        for name in (
            "data_engine",
            "snapshot_bridge",
            "dsp",
            "fundamental",
            "economic",
            "valuation",
            "ai_committee",
            "orchestration",
            "recommendation",
            "decision_intelligence",
            "universe",
            "industry",
            "core",
        ):
            assert name in FORBIDDEN_APPLICATION_PACKAGES
        assert "valuation" in PLATFORM_PACKAGES
        assert "decision_intelligence" in PLATFORM_PACKAGES
        assert "universe" in PLATFORM_PACKAGES
        assert "industry" in PLATFORM_PACKAGES
        assert "workflow" in PLATFORM_PACKAGES
        assert "workflow" in FORBIDDEN_APPLICATION_PACKAGES
        assert "knowledge_graph" in PLATFORM_PACKAGES
        assert "knowledge_graph" in FORBIDDEN_APPLICATION_PACKAGES
        assert "copilot" in PLATFORM_PACKAGES
        assert "copilot" in FORBIDDEN_APPLICATION_PACKAGES
        for name in (
            "financial",
            "business_quality",
            "economic_moat",
            "management_quality",
            "financial_strength",
            "earnings_quality",
            "growth_quality",
            "business_quality_aggregator",
            "investment_recommendation",
            "investment_committee",
            "llm_adapters",
            "compliance",
        ):
            assert name in FORBIDDEN_APPLICATION_PACKAGES
            assert name in PLATFORM_PACKAGES

    def test_financial_and_committee_forbidden_for_apps(self) -> None:
        with pytest.raises(PlatformError, match="financial"):
            assert_application_imports("from financial import FinancialEngine\n")
        with pytest.raises(PlatformError, match="investment_committee"):
            assert_application_imports(
                "from investment_committee import InvestmentCommittee\n"
            )
        source = (_SAMPLES / "compliant_app.py").read_text(encoding="utf-8")
        imported = assert_application_imports(source, path="compliant_app.py")
        assert "dsp_platform" in imported
        assert "contracts" in imported

    def test_violating_sample_app(self) -> None:
        source = (_SAMPLES / "violating_app.py").read_text(encoding="utf-8")
        with pytest.raises(PlatformError, match="forbidden packages"):
            assert_application_imports(source, path="violating_app.py")

    def test_valuation_is_forbidden_for_apps(self) -> None:
        source = "from valuation import ValuationEngine\n"
        with pytest.raises(PlatformError, match="valuation"):
            assert_application_imports(source)

    def test_scan_detects_from_import(self) -> None:
        source = "from data_engine.services import MarketDataService\n"
        assert "data_engine" in scan_module_imports(source)

    def test_stdlib_and_third_party_ignored(self) -> None:
        source = "import os\nfrom datetime import date\nimport numpy\n"
        # Not in forbidden set — applications may use stdlib / third-party.
        assert_application_imports(source)


class TestPackageFacadeParity:
    def test_deep_sibling_import_detected(self) -> None:
        source = "from valuation.engine.service import ValuationEngine\n"
        deep = scan_cross_package_deep_imports(
            source, current_package="orchestration"
        )
        assert "valuation.engine.service" in deep
        with pytest.raises(PlatformError, match="façade boundary"):
            assert_public_sibling_imports(
                source,
                current_package="orchestration",
                path="example.py",
            )

    def test_public_sibling_import_allowed(self) -> None:
        source = "from valuation import ValuationEngine\n"
        assert (
            scan_cross_package_deep_imports(
                source, current_package="orchestration"
            )
            == frozenset()
        )
        assert_public_sibling_imports(
            source, current_package="orchestration"
        )

    def test_all_platform_packages_use_public_sibling_imports(self) -> None:
        """Production src must not deep-import sibling packages."""
        failures: list[str] = []
        for package in sorted(PLATFORM_PACKAGES):
            root = _REPO_ROOT / "packages" / package / "src" / package
            if not root.is_dir():
                continue
            for path in root.rglob("*.py"):
                # utf-8-sig strips accidental BOM without touching package sources
                source = path.read_text(encoding="utf-8-sig")
                deep = scan_cross_package_deep_imports(
                    source, current_package=package
                )
                if deep:
                    rel = path.relative_to(_REPO_ROOT)
                    failures.append(f"{rel}: {sorted(deep)}")
        assert failures == [], "\n".join(failures)
