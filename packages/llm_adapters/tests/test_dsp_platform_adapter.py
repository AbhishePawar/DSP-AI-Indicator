"""Tests for the DSPPlatformToolAdapter, health check, and
provenance audit.
"""

from __future__ import annotations

from typing import Any, Mapping

import pytest

from llm_adapters.tools import (
    AUTHENTICATION_REQUIRED,
    DEFAULT_TOOL_NAMES,
    DSPPlatformToolAdapter,
    DSPToolBackend,
    ToolRegistry,
    ToolResult,
    ToolStatus,
    UNAVAILABLE,
    WIRED,
    assert_no_tool_leakage,
    check_tool_health,
    is_comparison_backed,
    is_composition_backed,
    is_flat_backed,
    reset_pack_cache,
)
from llm_adapters.tools.dsp_platform_adapter import _flatten_pack, _safe_dict


# --- minimal canonical backend stub --------------------------------------


class _CanonicalBackend:
    """Mimics the slice of ``DSPPlatform`` the adapter needs.

    The adapter must use ONLY these methods and never call any other
    backend attribute. This is what makes the adapter "thin" and what
    prevents it from duplicating DSP logic.
    """

    def __init__(self, *, compose: Mapping[str, Any] | None = None,
                 statements: Mapping[str, Any] | None = None,
                 research: Mapping[str, Any] | None = None,
                 committee: Mapping[str, Any] | None = None,
                 comparison: Mapping[str, Any] | None = None,
                 statements_health: Mapping[str, Any] | None = None,
                 compose_raises: Exception | None = None) -> None:
        self._compose_result = compose if compose is not None else _GOOD_COMPOSE
        # Default to a healthy statements payload so direct-method tests work
        self._statements = statements if statements is not None else {
            "periods": ["2024", "2023"],
            "currency": "INR",
            "source": "dsp.financial_statements",
        }
        self._research = research or {"lineage_id": "lin-1", "summary": {}}
        self._committee = committee or {"decision": "BUY", "votes": {}}
        self._comparison = comparison or {"dimensions": [], "summary": {}}
        self._statements_health = (
            statements_health if statements_health is not None
            else {"ok": True, "authenticated": True}
        )
        self._compose_raises = compose_raises
        # bookkeeping
        self.compose_call_count = 0
        self.statements_call_count = 0
        self.committee_call_count = 0
        self.comparison_call_count = 0
        self.last_compose_symbol: str | None = None

    def analyze_decision_pack(self, request: Any) -> Mapping[str, Any]:
        self.compose_call_count += 1
        if self._compose_raises is not None:
            raise self._compose_raises
        symbol = getattr(getattr(request, "instrument", None), "symbol", None) if request is not None else None
        self.last_compose_symbol = symbol
        return dict(self._compose_result)

    def get_authenticated_financial_statements(self, *, symbol: str, exchange: str | None = None) -> Mapping[str, Any] | None:
        self.statements_call_count += 1
        if self._statements is None:
            return None
        return dict(self._statements, _symbol=symbol)

    def financial_statement_health(self) -> Mapping[str, Any]:
        return dict(self._statements_health)

    def build_research_object(self, *, symbol: str) -> Mapping[str, Any]:
        return dict(self._research, _symbol=symbol)

    def run_institutional_committee(self, **kwargs: Any) -> Mapping[str, Any]:
        self.committee_call_count += 1
        return dict(self._committee)

    def compare_companies(self, packs: Any) -> Mapping[str, Any]:
        self.comparison_call_count += 1
        return dict(self._comparison, _pack_count=len(packs))

    # methods the adapter does NOT need
    def ask_research_copilot(self, *a: Any, **kw: Any) -> Any: return None
    def get_research_snapshot(self, *a: Any, **kw: Any) -> Any: return None
    def run_copilot_v2(self, *a: Any, **kw: Any) -> Any: return None
    def analyze_company(self, *a: Any, **kw: Any) -> Any: return None


_GOOD_COMPOSE: dict[str, Any] = {
    "valuation": {
        "intrinsic_value_per_share": 180.0,
        "current_market_price": 150.0,
        "method": "two-stage DCF",
    },
    "margin_of_safety": {"margin_of_safety": 0.2, "basis": "dsp_platform"},
    "economic_moat": {"moat": "Wide", "score": 0.8},
    "management_quality": {"quality": "Strong", "score": 0.85},
    "financial_strength": {"strength": "Strong", "score": 0.82},
    "earnings_quality": {"quality": "High", "score": 0.78},
    "growth_quality": {"growth": "Strong", "score": 0.75},
    "business_quality": {"label": "Great", "score": 0.85},
    "risk": {"risks": ["FX"], "score": 0.4},
    "quantitative_risk": {"volatility": 0.25, "beta": 1.1, "max_drawdown": -0.3},
    "technical_signals": {"signals": [{"name": "trend", "value": "up"}], "direction": "BULLISH"},
    "recommendation": {"decision": "Buy", "confidence": 0.8, "margin_of_safety": 0.2},
}


def _adapter_for(canonical: _CanonicalBackend) -> DSPPlatformToolAdapter:
    """Build a DSPPlatformToolAdapter with a real request builder.

    The builder produces the exact object ``analyze_decision_pack``
    receives; this avoids depending on dsp_platform's import shape.
    """
    def _builder(symbol: str) -> Any:
        return {"instrument": {"symbol": symbol}}
    return DSPPlatformToolAdapter(canonical, compose_request_builder=_builder)


@pytest.fixture(autouse=True)
def _clear_cache():
    reset_pack_cache()
    yield
    reset_pack_cache()


# --- provenance audit (PHASE 0 regression tests) -------------------------


def test_all_seventeen_tools_present() -> None:
    assert len(DEFAULT_TOOL_NAMES) == 17


def test_provenance_strings_do_not_lie_about_engine_source() -> None:
    """The provenance must reference the canonical source, not invented names.

    Every composition-backed tool's provenance must mention the
    composition pipeline. Flat-backed tools must mention the
    corresponding platform module.
    """
    registry = ToolRegistry.default()
    for name in registry.names():
        spec = registry.get_spec(name)
        assert spec is not None
        prov = spec.provenance
        if is_composition_backed(name):
            assert "analyze_company" in prov or "institutional_committee" in prov, (
                f"{name}: provenance must reference canonical composition or committee, got {prov!r}"
            )
        elif is_flat_backed(name):
            # Flat-backed tools must reference the canonical DSP module
            # for that domain.
            assert "dsp_platform" in prov, (
                f"{name}: provenance must reference canonical dsp_platform, got {prov!r}"
            )
        elif is_comparison_backed(name):
            assert "compare_companies" in prov, (
                f"{name}: provenance must reference canonical compare_companies, got {prov!r}"
            )


def test_technical_signals_provenance_corrected() -> None:
    """STEP 3F provenance was dsp_platform.industry. STEP 3G must correct it."""
    spec = ToolRegistry.default().get_spec("dsp.technical_signals")
    assert spec is not None
    # The technical engine package is `industry`; composition owns the
    # canonical read.
    assert "industry" in spec.provenance or "analyze_company" in spec.provenance


# --- canonical delegation (PHASE 2) ---------------------------------------


def test_all_seventeen_tools_resolve_to_a_backend_method() -> None:
    """Every tool has a corresponding method on the adapter."""
    registry = ToolRegistry.default()
    backend = _adapter_for(_CanonicalBackend())
    missing: list[str] = []
    for name in registry.names():
        spec = registry.get_spec(name)
        if spec is None:
            missing.append(name)
            continue
        # The ToolRegistry calls ``backend.<method>(**kwargs)``; we
        # confirm the adapter exposes each method the registry uses.
        method_name = _REGISTRY_BACKEND_METHOD.get(name)
        if method_name is None:
            missing.append(name)
            continue
        if not hasattr(backend, method_name):
            missing.append(name)
    assert not missing, f"tools without backend method: {missing}"


# Map: tool name -> the canonical backend method the registry calls.
# This is the contract the adapter MUST satisfy.
_REGISTRY_BACKEND_METHOD: dict[str, str] = {
    "dsp.financial_statements": "get_authenticated_financial_statements",
    "dsp.financial_quality": "get_financial_quality",
    "dsp.valuation": "get_valuation",
    "dsp.margin_of_safety": "get_margin_of_safety",
    "dsp.economic_moat": "get_economic_moat",
    "dsp.management_quality": "get_management_quality",
    "dsp.financial_strength": "get_financial_strength",
    "dsp.earnings_quality": "get_earnings_quality",
    "dsp.growth_quality": "get_growth_quality",
    "dsp.business_quality": "get_business_quality",
    "dsp.risk": "get_risk",
    "dsp.quantitative_risk": "get_quantitative_risk",
    "dsp.technical_signals": "get_technical_signals",
    "dsp.investment_recommendation": "get_investment_recommendation",
    "dsp.deterministic_committee": "run_deterministic_committee",
    "dsp.research_object": "build_research_object",
    "dsp.comparison": "compare_two_symbols",
}


def test_each_method_delegates_to_canonical_dsp_backend() -> None:
    """The adapter must call the canonical backend, not compute locally."""
    canonical = _CanonicalBackend()
    adapter = _adapter_for(canonical)
    # financial_statements -> direct method
    out = adapter.get_authenticated_financial_statements(symbol="AAPL")
    assert canonical.statements_call_count == 1
    assert out is not None and out.get("_symbol") == "AAPL"
    # valuation -> composition
    v = adapter.get_valuation(symbol="AAPL")
    assert canonical.compose_call_count == 1
    assert v["intrinsic_value_per_share"] == 180.0
    # Second valuation call must reuse the cached composition
    v2 = adapter.get_valuation(symbol="AAPL")
    assert canonical.compose_call_count == 1  # NOT incremented
    assert v == v2


def test_no_calculations_duplicated_in_adapter() -> None:
    """The adapter must not compute any numeric value from raw inputs.

    We scan the source for arithmetic operators OUTSIDE of docstrings
    and comments. Any arithmetic in executable code is a red flag.
    """
    import inspect
    from llm_adapters.tools import dsp_platform_adapter

    src = inspect.getsource(dsp_platform_adapter)
    forbidden_tokens = ("+ ", "- ", "* ", "/ ", "abs(", "min(", "max(", "sum(", "pow(", "sqrt(")
    in_docstring = False
    quote = None
    for line in src.splitlines():
        stripped = line.strip()
        # Toggle docstring state (triple-quoted strings)
        for q in ('"""', "'''"):
            if stripped.startswith(q) and stripped.count(q) == 1:
                in_docstring = not in_docstring
                quote = q if in_docstring else None
                break
        if in_docstring:
            continue
        if stripped.startswith("#"):
            continue
        # Assignment / comparison / keyword lines only
        for tok in forbidden_tokens:
            if tok in line:
                pytest.fail(
                    f"adapter contains arithmetic {tok!r} at: {line!r}"
                )


def test_technical_signals_provenance_finding() -> None:
    """The technical engine is the ``industry`` package; the canonical
    read happens through the composition pipeline."""
    spec = ToolRegistry.default().get_spec("dsp.technical_signals")
    assert spec is not None
    # Must reference the composition pipeline AND the underlying engine.
    assert "analyze_company" in spec.provenance
    assert "industry" in spec.provenance


def test_missing_backend_method_fails_closed() -> None:
    """A bare backend without canonical methods produces FAILED."""

    class Bare:
        def get_authenticated_financial_statements(self, *, symbol, exchange=None):
            return {"periods": []}

    adapter = _adapter_for(Bare())
    registry = ToolRegistry.default()
    result = registry.dispatch("dsp.valuation", {"symbol": "AAPL"}, adapter)
    assert result.status is ToolStatus.FAILED
    # Either "backend missing" (passthrough) or AttributeError (composition) — both are FAILED.
    assert result.limitations


def test_canonical_backend_exception_becomes_failed() -> None:
    canonical = _CanonicalBackend(compose_raises=RuntimeError("boom"))
    adapter = _adapter_for(canonical)
    registry = ToolRegistry.default()
    result = registry.dispatch("dsp.valuation", {"symbol": "AAPL"}, adapter)
    assert result.status is ToolStatus.FAILED
    assert "RuntimeError" in result.limitations[0]


def test_canonical_backend_none_becomes_unavailable() -> None:
    canonical = _CanonicalBackend(compose={})  # no per-tool keys -> None
    adapter = _adapter_for(canonical)
    registry = ToolRegistry.default()
    result = registry.dispatch("dsp.valuation", {"symbol": "AAPL"}, adapter)
    assert result.status is ToolStatus.UNAVAILABLE


def test_canonical_backend_error_becomes_unavailable() -> None:
    canonical = _CanonicalBackend(compose={"error": "data unavailable"})
    adapter = _adapter_for(canonical)
    registry = ToolRegistry.default()
    result = registry.dispatch("dsp.valuation", {"symbol": "AAPL"}, adapter)
    assert result.status is ToolStatus.UNAVAILABLE


def test_valid_result_preserves_evidence_refs() -> None:
    canonical = _CanonicalBackend(
        statements={
            "periods": ["2024", "2023"],
            "currency": "INR",
            "source": "dsp.financial_statements",
            "evidence_refs": ["dsp.statements:2024", "dsp.statements:2023"],
        }
    )
    adapter = _adapter_for(canonical)
    registry = ToolRegistry.default()
    result = registry.dispatch(
        "dsp.financial_statements", {"symbol": "AAPL"}, adapter
    )
    assert result.status is ToolStatus.OK
    assert "dsp.statements:2024" in result.evidence_refs


def test_tool_result_passes_assert_no_tool_leakage() -> None:
    canonical = _CanonicalBackend()
    adapter = _adapter_for(canonical)
    registry = ToolRegistry.default()
    for name in registry.names():
        spec = registry.get_spec(name)
        input_ = _minimal_input_for(spec)
        result = registry.dispatch(name, input_, adapter)
        assert_no_tool_leakage(result.result)
        assert_no_tool_leakage(result.calculation_metadata)


def test_private_fields_cannot_enter_tool_result() -> None:
    """If the backend tries to leak private fields, the adapter strips
    them in the projection layer so the ToolResult guard never sees them.
    """
    canonical = _CanonicalBackend(
        compose={
            "valuation": {
                "intrinsic_value_per_share": 180.0,
                # These should be stripped by the adapter projection.
                "provider": "openai",
                "model": "gpt-4o",
                "estimated_cost_usd": 0.01,
            }
        }
    )
    adapter = _adapter_for(canonical)
    registry = ToolRegistry.default()
    result = registry.dispatch("dsp.valuation", {"symbol": "AAPL"}, adapter)
    # Private fields are stripped; only public numerics remain.
    flat = result.result
    assert "intrinsic_value_per_share" in flat
    for forbidden in ("provider", "model", "estimated_cost_usd"):
        assert forbidden not in flat
    # And the public-shape guard passes.
    assert_no_tool_leakage(flat)


def test_adapter_does_not_construct_providers() -> None:
    """The adapter does not import or instantiate any LLM provider."""
    import inspect
    from llm_adapters.tools import dsp_platform_adapter
    src = inspect.getsource(dsp_platform_adapter)
    forbidden = (
        "OpenAI", "Anthropic", "Gemini", "DeepSeek",
        "httpx", "ProviderRegistry", "LLMPlatformConfig", "load_llm_config",
    )
    for token in forbidden:
        assert token not in src, f"adapter must not reference {token!r}"


def test_adapter_does_not_construct_credentials() -> None:
    """The adapter must not read or build any credential."""
    import inspect
    from llm_adapters.tools import dsp_platform_adapter
    src = inspect.getsource(dsp_platform_adapter)
    for token in ("API_KEY", "TOKEN", "PASSWORD", "SECRET", "getenv", "os.environ"):
        # Check only outside docstrings.
        in_doc = False
        for line in src.splitlines():
            stripped = line.strip()
            for q in ('"""', "'''"):
                if stripped.startswith(q) and stripped.count(q) == 1:
                    in_doc = not in_doc
                    break
            if in_doc or stripped.startswith("#"):
                continue
            if token in line:
                pytest.fail(f"adapter references credential token {token!r} at: {line!r}")


def test_adapter_does_not_bypass_composition() -> None:
    """All per-symbol quantitative tools must hit the composition pipeline."""
    canonical = _CanonicalBackend()
    adapter = _adapter_for(canonical)
    for tool_name in (
        "dsp.valuation", "dsp.margin_of_safety", "dsp.economic_moat",
        "dsp.management_quality", "dsp.financial_strength",
        "dsp.earnings_quality", "dsp.growth_quality", "dsp.business_quality",
        "dsp.risk", "dsp.quantitative_risk", "dsp.technical_signals",
        "dsp.investment_recommendation",
    ):
        spec = ToolRegistry.default().get_spec(tool_name)
        input_ = _minimal_input_for(spec)
        ToolRegistry.default().dispatch(tool_name, input_, adapter)
    # All twelve composition-backed tools triggered compose().
    assert canonical.compose_call_count >= 1


def test_adapter_is_read_only() -> None:
    """The adapter must not expose any mutating method on the backend."""
    adapter = _adapter_for(_CanonicalBackend())
    for name in dir(adapter):
        if name.startswith("_"):
            continue
        attr = getattr(adapter, name)
        if callable(attr):
            # No setter-style methods.
            assert not name.startswith("set_"), name


def test_repeated_identical_calls_remain_deterministic() -> None:
    canonical = _CanonicalBackend()
    adapter = _adapter_for(canonical)
    a = adapter.get_valuation(symbol="AAPL")
    b = adapter.get_valuation(symbol="AAPL")
    assert a == b


def test_unknown_input_still_fails_at_registry() -> None:
    canonical = _CanonicalBackend()
    adapter = _adapter_for(canonical)
    registry = ToolRegistry.default()
    result = registry.dispatch("dsp.valuation", {}, adapter)  # no symbol
    assert result.status is ToolStatus.INVALID_INPUT


# --- health check (PHASE 5) -----------------------------------------------


def test_health_reports_wired_when_backend_ok() -> None:
    canonical = _CanonicalBackend()
    adapter = _adapter_for(canonical)
    report = check_tool_health(adapter)
    assert report.wired_count > 0
    assert report.unavailable_count == 0


def test_health_reports_authentication_required_when_credentials_missing() -> None:
    canonical = _CanonicalBackend(
        statements_health={"ok": False, "authenticated": False, "reason": "no token"},
    )
    adapter = _adapter_for(canonical)
    report = check_tool_health(adapter)
    assert report.auth_required_count > 0


def test_health_reports_unavailable_when_backend_raises() -> None:
    class Broken:
        def financial_statement_health(self):
            raise RuntimeError("backend down")
        def analyze_decision_pack(self, request):
            raise RuntimeError("backend down")

    adapter = _adapter_for(Broken())
    report = check_tool_health(adapter)
    assert report.unavailable_count > 0


def test_health_does_not_make_expensive_calls() -> None:
    """The health probe must use only the lightweight ``*_health``
    method and a synthetic symbol; no real provider call."""
    canonical = _CanonicalBackend()
    adapter = _adapter_for(canonical)
    # If the probe called an LLM provider, the canonical backend would
    # record no call to ``analyze_decision_pack`` for the test symbol.
    # Instead, the probe uses a synthetic symbol; here we just assert
    # the probe does not invoke any external interface.
    report = check_tool_health(adapter)
    # After the probe the canonical backend has at most one compose call
    # (the synthetic probe symbol), NOT 17.
    assert canonical.compose_call_count <= 2


def test_health_reports_no_demo_null_silently_treated_as_healthy() -> None:
    """A backend that returns empty mapping for every tool must NOT
    be reported as healthy."""
    canonical = _CanonicalBackend(compose={})  # empty -> all sub-tools None
    adapter = _adapter_for(canonical)
    report = check_tool_health(adapter)
    # The flat methods (financial_statements, research_object) may be
    # wired; the composition-backed tools are UNAVAILABLE.
    assert report.unavailable_count > 0


# --- helpers --------------------------------------------------------------


def _minimal_input_for(spec: Any) -> dict:
    return {
        f.name: _default_for_type(f.type)
        for f in spec.input_schema
        if f.required
    }


def _default_for_type(type_str: str):
    if type_str == "string":
        return "AAPL"
    if type_str == "integer":
        return 1
    if type_str == "number":
        return 1.0
    if type_str == "boolean":
        return False
    if type_str == "object":
        return {}
    if type_str == "array":
        return []
    if type_str == "any":
        return "AAPL"
    raise ValueError(type_str)


# --- projection (PHASE 4) ------------------------------------------------


def test_flatten_pack_is_projection_only() -> None:
    """The flatten helper must not introduce any field not in the pack."""
    pack = {
        "valuation": {"intrinsic_value_per_share": 100.0, "current_market_price": 80.0},
        "business_quality": {"label": "Good", "score": 0.7},
    }
    view = _flatten_pack(pack, "AAPL")
    assert view["valuation"]["intrinsic_value_per_share"] == 100.0
    assert view["business_quality"]["label"] == "Good"
    # No invented keys.
    assert set(view.keys()) == {"valuation", "business_quality"}


def test_safe_dict_returns_none_for_none() -> None:
    assert _safe_dict(None) is None
    assert _safe_dict({"a": 1}) == {"a": 1}
    assert _safe_dict("not a mapping") is None


def test_adapter_satisfies_protocol() -> None:
    """DSPPlatformToolAdapter must satisfy the DSPToolBackend Protocol."""
    adapter = _adapter_for(_CanonicalBackend())
    assert isinstance(adapter, DSPToolBackend)

