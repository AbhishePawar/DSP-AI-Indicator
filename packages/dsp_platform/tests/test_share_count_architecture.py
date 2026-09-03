"""Architecture: ShareCountPort is acquired in dsp_platform, not engines."""

from __future__ import annotations

import ast
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
_VALUATION_SRC = _REPO / "packages" / "valuation" / "src" / "valuation"
_RESEARCH_PKG = (
    _REPO / "packages" / "dsp_platform" / "src" / "dsp_platform" / "research_package"
)
_AI_COMMITTEE = _REPO / "packages" / "ai_committee" / "src" / "ai_committee"
_LLM = _REPO / "packages" / "llm_adapters" / "src" / "llm_adapters"
_UPSTOX = _REPO / "packages" / "data_engine" / "src" / "data_engine"
_AUTH_VAL = (
    _REPO
    / "packages"
    / "dsp_platform"
    / "src"
    / "dsp_platform"
    / "composition"
    / "authenticated_valuation.py"
)
_ANALYSE_SCHEMA = (
    _REPO
    / "packages"
    / "api_platform"
    / "src"
    / "api_platform"
    / "api"
    / "composition_schemas.py"
)
_COMPOSITION_MODELS = (
    _REPO
    / "packages"
    / "dsp_platform"
    / "src"
    / "dsp_platform"
    / "composition"
    / "models.py"
)

_FORBIDDEN_SHARE_COUNT_IMPORTS = frozenset(
    {"ShareCountPort", "ShareCountService", "get_share_count"}
)
_FORBIDDEN_SNIPPETS = (
    "ShareCountPort",
    "ShareCountService",
    "build_default_share_count_adapter_from_env",
    "data_engine.share_count",
)


def _imported_names(source: str) -> frozenset[str]:
    tree = ast.parse(source)
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name.split(".", 1)[0])
                names.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            names.add(node.module)
            for alias in node.names:
                names.add(alias.name)
    return frozenset(names)


def _scan_dir(root: Path) -> list[str]:
    hits: list[str] = []
    for path in root.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        imported = _imported_names(text)
        if imported & _FORBIDDEN_SHARE_COUNT_IMPORTS:
            hits.append(
                f"{path}: imported {sorted(imported & _FORBIDDEN_SHARE_COUNT_IMPORTS)}"
            )
        for snippet in _FORBIDDEN_SNIPPETS:
            if snippet in text:
                hits.append(f"{path}: snippet {snippet}")
    return hits


class TestShareCountDependencyDirection:
    def test_valuation_engine_does_not_fetch_share_count_port(self) -> None:
        assert _scan_dir(_VALUATION_SRC) == []

    def test_research_package_does_not_fetch_share_count_port(self) -> None:
        assert _scan_dir(_RESEARCH_PKG) == []

    def test_ai_does_not_generate_or_modify_shares(self) -> None:
        assert _scan_dir(_AI_COMMITTEE) == []
        if _LLM.exists():
            assert _scan_dir(_LLM) == []

    def test_client_request_cannot_provide_shares(self) -> None:
        schema = _ANALYSE_SCHEMA.read_text(encoding="utf-8")
        tree = ast.parse(schema)
        analyse = next(
            node
            for node in tree.body
            if isinstance(node, ast.ClassDef) and node.name == "AnalyseRequest"
        )
        fields = {
            t.id
            for node in analyse.body
            if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name)
            for t in [node.target]
        }
        assert "shares_outstanding" not in fields
        assert "share_count" not in fields
        models = _COMPOSITION_MODELS.read_text(encoding="utf-8")
        tree_m = ast.parse(models)
        req = next(
            node
            for node in tree_m.body
            if isinstance(node, ast.ClassDef) and node.name == "CompositionRequest"
        )
        req_fields = {
            t.id
            for node in req.body
            if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name)
            for t in [node.target]
        }
        assert "shares_outstanding" not in req_fields

    def test_upstox_u2_u4_do_not_invent_shares(self) -> None:
        quote = (_UPSTOX / "upstox_market_quote.py").read_text(encoding="utf-8")
        statements = (_UPSTOX / "upstox_fundamentals.py").read_text(encoding="utf-8")
        assert "ShareCountPort" not in quote
        assert "ShareCountPort" not in statements
        assert "ShareCountSnapshot" not in quote
        assert "ShareCountSnapshot" not in statements

    def test_resolve_shares_does_not_use_quote_or_eps(self) -> None:
        tree = ast.parse(_AUTH_VAL.read_text(encoding="utf-8"))
        fn = next(
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "_resolve_shares"
        )
        source = ast.get_source_segment(_AUTH_VAL.read_text(encoding="utf-8"), fn)
        assert source is not None
        assert "quote.shares_outstanding" not in source
        assert "eps_basic" not in source
        assert "net_income" not in source
        assert "market_cap" not in source
        assert "ShareCountSnapshot" in source or "snapshot" in source

    def test_valuation_does_not_import_data_engine(self) -> None:
        forbidden = {"data_engine"}
        violations: list[str] = []
        for path in _VALUATION_SRC.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name.split(".", 1)[0] in forbidden:
                            violations.append(path.as_posix())
                elif (
                    isinstance(node, ast.ImportFrom)
                    and node.module
                    and node.module.split(".", 1)[0] in forbidden
                ):
                    violations.append(path.as_posix())
        assert violations == []
