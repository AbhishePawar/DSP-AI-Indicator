"""PR1.0 compliance architecture tests — flags & terminology only."""

from __future__ import annotations

import ast
from pathlib import Path

from compliance.analysis_sections import ANALYSIS_PAGE_ORDER, AnalysisSection
from compliance.disclaimer_engine import default_research_disclaimer
from compliance.feature_flags import FeatureFlags, load_feature_flags
from compliance.metric_presentation import MetricPresentation, metric_card_fields
from compliance.terminology import present_action, present_field_label


class TestFeatureFlags:
    def test_phase1_defaults(self) -> None:
        flags = FeatureFlags()
        assert flags.research_mode is True
        assert flags.recommendation_mode is False
        assert flags.sebi_mode is False
        assert flags.allow_action_labels() is False
        assert flags.allow_official_target_price() is False
        assert flags.is_research_only() is True

    def test_sebi_activation_requires_all_gates(self) -> None:
        flags = FeatureFlags(
            research_mode=True,
            recommendation_mode=True,
            sebi_mode=True,
            show_buy_sell=True,
            show_target_price=True,
        )
        assert flags.allow_action_labels() is True
        assert flags.allow_official_target_price() is True

    def test_load_from_env(self, monkeypatch) -> None:
        monkeypatch.setenv("RESEARCH_MODE", "true")
        monkeypatch.setenv("RECOMMENDATION_MODE", "false")
        monkeypatch.setenv("SEBI_MODE", "false")
        flags = load_feature_flags()
        assert flags.research_mode is True
        assert flags.sebi_mode is False

    def test_validate_warns_on_inconsistent_sebi(self) -> None:
        warnings = FeatureFlags(sebi_mode=True, recommendation_mode=False).validate()
        assert any("RECOMMENDATION_MODE" in w for w in warnings)


class TestTerminology:
    def test_research_mode_maps_buy_sell_hold(self) -> None:
        flags = FeatureFlags()
        assert present_action("BUY", flags) == "Attractive"
        assert present_action("sell", flags) == "Caution"
        assert present_action("HOLD", flags) == "Fairly Valued"
        assert present_action("strong_buy", flags) == "Attractive"

    def test_field_labels_research(self) -> None:
        flags = FeatureFlags()
        assert present_field_label("target_price", flags) == (
            "Estimated Intrinsic Value Range"
        )
        assert present_field_label("recommendation", flags) == "Research Conclusion"
        assert present_field_label("stock_recommendation", flags) == (
            "Investment Assessment"
        )
        assert present_field_label("action", flags) == "DSP View"

    def test_sebi_mode_labels_when_gated(self) -> None:
        flags = FeatureFlags(
            recommendation_mode=True,
            sebi_mode=True,
            show_buy_sell=True,
            show_target_price=True,
        )
        assert present_action("buy", flags) == "Buy"
        assert present_field_label("target_price", flags) == "Official Target Price"


class TestAnalysisOrder:
    def test_canonical_order_starts_with_snapshot(self) -> None:
        assert ANALYSIS_PAGE_ORDER[0] is AnalysisSection.COMPANY_SNAPSHOT
        assert AnalysisSection.RESEARCH_CONCLUSION in ANALYSIS_PAGE_ORDER
        assert AnalysisSection.AI_CHALLENGE in ANALYSIS_PAGE_ORDER
        assert ANALYSIS_PAGE_ORDER[-1] is AnalysisSection.EXPORT


class TestMetricPresentation:
    def test_required_fields(self) -> None:
        assert metric_card_fields() == (
            "title",
            "rating",
            "actual_value",
            "plain_english_explanation",
            "why_it_matters",
            "investor_takeaway",
        )
        card = MetricPresentation(
            title="Debt Level",
            rating="HIGH",
            actual_value="Debt to Equity 1.87",
            plain_english_explanation="Company relies more on debt than many peers.",
            why_it_matters="Higher debt increases financial risk during downturns.",
            investor_takeaway="Monitor cash flow and debt servicing.",
        )
        assert card.rating == "HIGH"


class TestDisclaimer:
    def test_research_disclaimer_avoids_tip_language(self) -> None:
        text = default_research_disclaimer().text.lower()
        assert "buy, sell, or hold" in text
        assert "research" in text


class TestArchitectureBoundaries:
    def test_package_does_not_import_engines(self) -> None:
        root = Path(__file__).resolve().parents[1] / "src" / "compliance"
        forbidden_roots = {
            "recommendation",
            "valuation",
            "dsp_platform",
            "api_platform",
            "workflow",
            "knowledge_graph",
        }
        for path in root.glob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        top = alias.name.split(".", 1)[0]
                        assert top not in forbidden_roots, path.name
                elif isinstance(node, ast.ImportFrom) and node.module:
                    top = node.module.split(".", 1)[0]
                    assert top not in forbidden_roots, path.name
