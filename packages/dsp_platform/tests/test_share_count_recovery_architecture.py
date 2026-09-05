"""Architecture: recovered ShareCountPort stays off the analyse path."""

from __future__ import annotations

from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
_AUTH_VAL = (
    _REPO
    / "packages"
    / "dsp_platform"
    / "src"
    / "dsp_platform"
    / "composition"
    / "authenticated_valuation.py"
)
_PIPELINE = (
    _REPO
    / "packages"
    / "dsp_platform"
    / "src"
    / "dsp_platform"
    / "composition"
    / "pipeline.py"
)
_SHARE_COUNTS = (
    _REPO / "packages" / "dsp_platform" / "src" / "dsp_platform" / "share_counts.py"
)
_VALUATION_SRC = _REPO / "packages" / "valuation" / "src" / "valuation"
_LLM = _REPO / "packages" / "llm_adapters" / "src" / "llm_adapters"
_API_ROUTERS = (
    _REPO
    / "packages"
    / "api_platform"
    / "src"
    / "api_platform"
    / "api"
    / "routers"
)


class TestShareCountRecoveryBoundaries:
    def test_analyse_path_does_not_import_protocol_or_gemini_retrieval(self) -> None:
        auth = _AUTH_VAL.read_text(encoding="utf-8")
        pipeline = _PIPELINE.read_text(encoding="utf-8")
        for text in (auth, pipeline):
            assert "current_outstanding_protocol" not in text
            assert "canonical_research_ai_runtime" not in text
            assert "controlled_document_retrieval" not in text
            assert "GeminiAdapter" not in text

    def test_share_count_facade_does_not_auto_run_protocol(self) -> None:
        text = _SHARE_COUNTS.read_text(encoding="utf-8")
        assert "current_outstanding_protocol" not in text
        assert "canonical_research_ai_runtime" not in text

    def test_valuation_engine_does_not_import_share_count_port(self) -> None:
        for path in _VALUATION_SRC.rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            assert "ShareCountPort" not in text
            assert "data_engine.share_count" not in text

    def test_http_analyse_router_does_not_import_protocol(self) -> None:
        for name in ("composition.py", "analysis.py"):
            path = _API_ROUTERS / name
            if not path.exists():
                continue
            text = path.read_text(encoding="utf-8")
            assert "current_outstanding_protocol" not in text
            assert "ControlledHttpsDocumentRetrieval" not in text

    def test_llm_adapters_do_not_construct_snapshots(self) -> None:
        if not _LLM.exists():
            return
        for path in _LLM.rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            assert "ShareCountSnapshot(" not in text
            assert "accept_current_outstanding_claims" not in text
