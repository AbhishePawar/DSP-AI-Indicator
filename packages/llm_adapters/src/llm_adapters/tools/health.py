"""Health check for the DSP trusted-tool wiring.

Reports one of three states per tool:

- ``wired``                  — the adapter has a backend method, the
                              backend is reachable, and the method can
                              be invoked (possibly with a HEALTH probe)
- ``authentication_required``— the backend method exists but the
                              canonical engine reports an authentication
                              gap (e.g. no Upstox token, missing API
                              credential)
- ``unavailable``            — the backend method is missing or the
                              canonical engine reports the data
                              unavailable

The health check does NOT make expensive LLM calls. It probes the
backend's lightweight ``*_health()`` methods when available, and only
exercises the composition pipeline with a non-existent symbol so the
failure is fast and observable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Sequence

from llm_adapters.tools.contract import DSPToolBackend, ToolSpec
from llm_adapters.tools.dsp_platform_adapter import DSPPlatformToolAdapter
from llm_adapters.tools.registry import ToolRegistry


WIRED = "wired"
AUTHENTICATION_REQUIRED = "authentication_required"
UNAVAILABLE = "unavailable"


@dataclass(frozen=True, slots=True)
class ToolHealthReport:
    """Aggregate health report for the DSP tool surface."""

    tools: tuple[tuple[str, str, str], ...]  # (tool_name, state, detail)
    wired_count: int
    auth_required_count: int
    unavailable_count: int

    def all_wired(self) -> bool:
        return self.unavailable_count == 0 and self.auth_required_count == 0


def _probe_flat_health(backend: DSPToolBackend) -> str:
    """Probe the financial_statements health (lightweight, no I/O)."""
    try:
        health = backend.financial_statement_health()
    except Exception:
        return UNAVAILABLE
    if not isinstance(health, Mapping):
        return WIRED  # unknown shape -> don't claim broken
    if health.get("ok") is False or health.get("error"):
        if "credential" in str(health).lower() or "token" in str(health).lower():
            return AUTHENTICATION_REQUIRED
        return UNAVAILABLE
    if health.get("authenticated") is False:
        return AUTHENTICATION_REQUIRED
    return WIRED


def _probe_composition(backend: DSPPlatformToolAdapter) -> str:
    """Run the composition pipeline with a benign symbol and read the
    result. Authentication-required upstream surfaces will surface here.
    A successful composition that contains no per-tool sub-results is
    treated as UNAVAILABLE (an empty mapping is not a healthy result).
    """
    try:
        # A no-op symbol that we never intend to use elsewhere. Compose
        # the pipeline; if it raises, the engine isn't reachable.
        result = backend._compose("__TOOL_HEALTH_PROBE__")
    except Exception as exc:  # noqa: BLE001
        text = str(exc).lower()
        if any(t in text for t in ("credential", "token", "auth", "key")):
            return AUTHENTICATION_REQUIRED
        return UNAVAILABLE
    if result is None:
        return UNAVAILABLE
    if not isinstance(result, Mapping):
        return UNAVAILABLE
    if result.get("error"):
        text = str(result.get("error", "")).lower()
        if any(t in text for t in ("credential", "token", "auth", "key")):
            return AUTHENTICATION_REQUIRED
        return UNAVAILABLE
    # The probe must produce at least one known per-tool sub-result.
    from llm_adapters.tools.dsp_platform_adapter import _flatten_pack
    view = _flatten_pack(result, "__TOOL_HEALTH_PROBE__")
    if not view:
        return UNAVAILABLE
    return WIRED


def check_tool_health(
    backend: DSPToolBackend,
    registry: ToolRegistry | None = None,
) -> ToolHealthReport:
    """Compute the per-tool health state.

    The flat methods are probed via ``*_health()`` when available. The
    composition-backed sub-tools inherit the composition probe result.
    """
    registry = registry or ToolRegistry.default()
    flat_health = _probe_flat_health(backend)
    comp_health = (
        _probe_composition(backend)
        if isinstance(backend, DSPPlatformToolAdapter)
        else UNAVAILABLE
    )

    tools: list[tuple[str, str, str]] = []
    wired = auth = unav = 0
    for name in registry.names():
        spec = registry.get_spec(name)
        if spec is None:
            tools.append((name, UNAVAILABLE, "no spec"))
            unav += 1
            continue
        # Tools that delegate to the composition pipeline inherit
        # comp_health; tools that delegate to a flat method inherit
        # flat_health; tools that need both (e.g. committee) need both
        # to be wired.
        needs_composition = name in _COMPOSITION_BACKED_TOOLS
        needs_flat = name in _FLAT_BACKED_TOOLS
        if needs_composition and needs_flat:
            state = flat_health if flat_health == comp_health else (
                WIRED if flat_health == WIRED and comp_health == WIRED
                else (UNAVAILABLE if UNAVAILABLE in (flat_health, comp_health) else AUTHENTICATION_REQUIRED)
            )
        elif needs_composition:
            state = comp_health
        else:
            state = flat_health
        if state == WIRED:
            wired += 1
        elif state == AUTHENTICATION_REQUIRED:
            auth += 1
        else:
            unav += 1
        tools.append((name, state, ""))

    # Reset the health-probe cache entry so a real subsequent call
    # recomposes for the actual symbol.
    if isinstance(backend, DSPPlatformToolAdapter):
        from llm_adapters.tools.dsp_platform_adapter import reset_pack_cache
        reset_pack_cache(backend)

    return ToolHealthReport(
        tools=tuple(tools),
        wired_count=wired,
        auth_required_count=auth,
        unavailable_count=unav,
    )


# --- tool classification --------------------------------------------------


_FLAT_BACKED_TOOLS: frozenset[str] = frozenset(
    {
        "dsp.financial_statements",
        "dsp.research_object",
    }
)


_COMPOSITION_BACKED_TOOLS: frozenset[str] = frozenset(
    {
        "dsp.business_quality",
        "dsp.deterministic_committee",
        "dsp.earnings_quality",
        "dsp.economic_moat",
        "dsp.financial_quality",
        "dsp.financial_strength",
        "dsp.growth_quality",
        "dsp.investment_recommendation",
        "dsp.management_quality",
        "dsp.margin_of_safety",
        "dsp.quantitative_risk",
        "dsp.risk",
        "dsp.technical_signals",
        "dsp.valuation",
    }
)


# dsp.comparison needs BOTH packs (composition) AND compare_companies (flat-ish)
_COMPARISON_TOOLS: frozenset[str] = frozenset({"dsp.comparison"})


def is_flat_backed(name: str) -> bool:
    return name in _FLAT_BACKED_TOOLS


def is_composition_backed(name: str) -> bool:
    return name in _COMPOSITION_BACKED_TOOLS


def is_comparison_backed(name: str) -> bool:
    return name in _COMPARISON_TOOLS


__all__ = [
    "AUTHENTICATION_REQUIRED",
    "ToolHealthReport",
    "UNAVAILABLE",
    "WIRED",
    "check_tool_health",
    "is_comparison_backed",
    "is_composition_backed",
    "is_flat_backed",
]
