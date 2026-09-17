"""Executable guards for the canonical DSP research architecture."""

from __future__ import annotations

import ast
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
_WEB = _REPO / "apps" / "web" / "src"
_COMPOSITION = (
    _REPO
    / "packages"
    / "api_platform"
    / "src"
    / "api_platform"
    / "api"
    / "routers"
    / "composition.py"
)


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


class TestCanonicalArchitecture:
    def test_public_dashboard_is_search_first(self) -> None:
        page = (_WEB / "app" / "dashboard" / "page.tsx").read_text(encoding="utf-8")
        assert "SearchFirstDashboard" in page
        assert "DashboardGrid" not in page
        assert "InstitutionalDashboard" not in page

    def test_dashboard_search_preserves_dsp_intent(self) -> None:
        dashboard = (
            _WEB / "components" / "dashboard" / "SearchFirstDashboard.tsx"
        ).read_text(encoding="utf-8")
        assert "/analysis?symbol=" in dashboard
        assert "intent=dsp_indicator" in dashboard

    def test_http_composition_delegates_to_platform(self) -> None:
        source = _COMPOSITION.read_text(encoding="utf-8")
        assert "state.platform.compose_intelligence(composition_request)" in source
        assert "build_composition_request" in source
        assert "build_research_team_metadata" in source
        assert "ResearchOrchestrator" not in source
        assert "analyze_decision_pack" not in source

    def test_composition_has_no_provider_sdk_authority(self) -> None:
        imports = _imports(_COMPOSITION)
        forbidden = {
            "openai",
            "anthropic",
            "google.generativeai",
            "deepseek",
            "llm_adapters.orchestrator",
        }
        assert imports.isdisjoint(forbidden)

    def test_canonical_frontend_analysis_client_is_single_api_contract(self) -> None:
        client = (_WEB / "lib" / "api" / "client.ts").read_text(encoding="utf-8")
        assert "request<AnalyseResponse>(" in client
        assert '"/analyse"' in client
        assert "request<ApiResponse<AnalyzeCompanyPayload>>(" in client
        assert '"/analyze/company"' in client
