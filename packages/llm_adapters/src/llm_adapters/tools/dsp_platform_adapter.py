"""Thin server-side adapter from ``DSPToolBackend`` to the canonical
``DSPPlatform`` façade.

This module is the ONLY place where ``llm_adapters`` is permitted to call
into the canonical DSP surface. It does not import DSP engines directly;
it delegates every operation to an injected ``DSPPlatform``-like backend.

Design rules
------------

1. **No calculation in the adapter.** Every numeric value, score, label,
   or signal is read from the platform's existing return value. If a
   field is missing or ``None``, the adapter returns ``None`` and the
   ``ToolRegistry`` normalizes that to ``UNAVAILABLE``. We never invent.

2. **Single composition per symbol.** Sub-tools that need a per-symbol
   quantitative result (``dsp.valuation``, ``dsp.economic_moat``,
   ``dsp.management_quality``, ``dsp.financial_strength``,
   ``dsp.earnings_quality``, ``dsp.growth_quality``,
   ``dsp.business_quality``, ``dsp.risk``, ``dsp.quantitative_risk``,
   ``dsp.technical_signals``, ``dsp.investment_recommendation``,
   ``dsp.margin_of_safety``) all read from a single
   ``analyze_company(AnalysisRequest(symbol=...))`` call. The adapter
   caches that result in a thread-local so the composition pipeline is
   not re-run on every per-tool dispatch.

3. **Direct delegation for flat methods.** Tools that map cleanly to a
   flat platform method (``dsp.financial_statements``,
   ``dsp.research_object``, ``dsp.deterministic_committee``,
   ``dsp.comparison``) call that method directly.

4. **No credential, provider, or network construction inside the
   adapter.** The injected backend is fully responsible for auth, data,
   and I/O. The adapter is read-only over its return values.

5. **Fail-closed.** Any backend exception is re-raised (the
   ``ToolRegistry`` catches it and returns ``FAILED``). Any ``None`` or
   ``{"error": ...}`` from the backend is propagated as ``None`` so the
   ``ToolRegistry`` normalizes it to ``UNAVAILABLE``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from llm_adapters.tools.contract import DSPToolBackend


@dataclass(frozen=True, slots=True)
class ToolHealthState:
    """One tool's wiring/auth/availability snapshot."""

    tool_name: str
    state: str  # "wired" | "authentication_required" | "unavailable"
    detail: str = ""


class DSPPlatformToolAdapter(DSPToolBackend):
    """Adapter that turns ``DSPPlatform`` into a ``DSPToolBackend``.

    The constructor receives a fully-constructed backend. It does NOT
    construct providers, credentials, or network clients.
    """

    def __init__(
        self,
        platform: Any,
        *,
        compose_request_builder: Any | None = None,
    ) -> None:
        """Adapter over an already-constructed ``DSPPlatform``-like backend.

        ``compose_request_builder`` is an optional callable
        ``(symbol: str) -> Any`` that returns the canonical request
        object expected by ``platform.analyze_decision_pack``. When
        ``None``, the adapter uses a best-effort default that tries to
        import ``dsp_platform.AnalysisRequest`` and constructs an
        ``Instrument(symbol=...)`` request. Wiring code should pass a
        real builder in production; the default exists so the adapter
        remains usable in unit tests and environments where the
        platform request shape is not importable.
        """
        self._platform = platform
        self._compose_request_builder = compose_request_builder or self._default_request_builder

    @staticmethod
    def _default_request_builder(symbol: str) -> Any | None:
        """Try to build a canonical analysis request; return ``None`` if
        the platform does not expose the expected types in this env.
        """
        try:
            from dsp_platform import AnalysisRequest  # type: ignore
        except Exception:
            return None
        instrument: Any = None
        try:
            from dsp_platform import Instrument  # type: ignore
            instrument = Instrument(symbol=symbol)
        except Exception:
            try:
                from contracts.domain.instrument import Instrument  # type: ignore
                instrument = Instrument(symbol=symbol)
            except Exception:
                return None
        try:
            return AnalysisRequest(instrument=instrument)
        except Exception:
            return None

    # --- direct methods (flat platform API) -------------------------------

    def get_authenticated_financial_statements(
        self, symbol: str, *, exchange: str | None = None, **kwargs: Any
    ) -> Any:
        return self._platform.get_authenticated_financial_statements(
            symbol=symbol, exchange=exchange
        )

    def financial_statement_health(self) -> Mapping[str, Any]:
        return self._platform.financial_statement_health()

    def build_research_object(self, symbol: str, **kwargs: Any) -> Any:
        return self._platform.build_research_object(symbol=symbol)

    def get_research_snapshot(self, snapshot_id: str) -> Any:
        return self._platform.get_research_snapshot(snapshot_id)

    def run_copilot_v2(self, **kwargs: Any) -> Any:
        return self._platform.run_copilot_v2(**kwargs)

    def ask_research_copilot(self, question: str, **kwargs: Any) -> Any:
        return self._platform.ask_research_copilot(question=question, **kwargs)

    def analyze_company(self, request: Any) -> Any:
        return self._platform.analyze_company(request)

    def compare_companies(self, packs: Any) -> Any:
        return self._platform.compare_companies(packs)

    # --- composition-backed sub-reads -------------------------------------

    def get_financial_quality(self, *, symbol: str) -> Mapping[str, Any] | None:
        return _safe_dict(self._composition_view(symbol).get("financial_quality"))

    def get_valuation(self, *, symbol: str) -> Mapping[str, Any] | None:
        return _safe_dict(self._composition_view(symbol).get("valuation"))

    def get_margin_of_safety(self, *, symbol: str) -> Mapping[str, Any] | None:
        return _safe_dict(self._composition_view(symbol).get("margin_of_safety"))

    def get_economic_moat(self, *, symbol: str) -> Mapping[str, Any] | None:
        return _safe_dict(self._composition_view(symbol).get("economic_moat"))

    def get_management_quality(self, *, symbol: str) -> Mapping[str, Any] | None:
        return _safe_dict(self._composition_view(symbol).get("management_quality"))

    def get_financial_strength(self, *, symbol: str) -> Mapping[str, Any] | None:
        return _safe_dict(self._composition_view(symbol).get("financial_strength"))

    def get_earnings_quality(self, *, symbol: str) -> Mapping[str, Any] | None:
        return _safe_dict(self._composition_view(symbol).get("earnings_quality"))

    def get_growth_quality(self, *, symbol: str) -> Mapping[str, Any] | None:
        return _safe_dict(self._composition_view(symbol).get("growth_quality"))

    def get_business_quality(self, *, symbol: str) -> Mapping[str, Any] | None:
        return _safe_dict(self._composition_view(symbol).get("business_quality"))

    def get_risk(self, *, symbol: str) -> Mapping[str, Any] | None:
        return _safe_dict(self._composition_view(symbol).get("risk"))

    def get_quantitative_risk(self, *, symbol: str) -> Mapping[str, Any] | None:
        return _safe_dict(self._composition_view(symbol).get("quantitative_risk"))

    def get_technical_signals(self, *, symbol: str) -> Mapping[str, Any] | None:
        return _safe_dict(self._composition_view(symbol).get("technical_signals"))

    def get_investment_recommendation(self, *, symbol: str) -> Mapping[str, Any] | None:
        return _safe_dict(self._composition_view(symbol).get("recommendation"))

    def run_deterministic_committee(self, *, symbol: str) -> Mapping[str, Any] | None:
        """Run the institutional multi-agent review on the symbol's DecisionPack.

        If the symbol has not been analyzed yet, this returns ``None`` so
        the ToolRegistry normalizes it to UNAVAILABLE.
        """
        pack = self._decision_pack(symbol)
        if pack is None:
            return None
        try:
            result = self._platform.run_institutional_committee(
                subject=f"tool:{symbol}",
                research_object={"symbol": symbol},
                report=pack,
            )
        except Exception:  # noqa: BLE001 — re-raise, let registry map to FAILED
            raise
        return _safe_dict(result)

    # --- comparison: per-symbol (composes two DecisionsPacks) -------------

    def compare_two_symbols(
        self, *, symbol_a: str, symbol_b: str
    ) -> Mapping[str, Any] | None:
        pack_a = self._decision_pack(symbol_a)
        pack_b = self._decision_pack(symbol_b)
        if pack_a is None or pack_b is None:
            return None
        try:
            return self._platform.compare_companies((pack_a, pack_b))
        except Exception:
            raise

    # --- helpers ----------------------------------------------------------

    def _decision_pack(self, symbol: str) -> Any | None:
        """Return the cached DecisionPack for ``symbol`` or compose one."""
        from llm_adapters.tools.dsp_platform_adapter import _get_cached_pack
        cached = _get_cached_pack(self, symbol)
        if cached is not None:
            return cached
        pack = self._compose(symbol)
        if pack is not None:
            _set_cached_pack(self, symbol, pack)
        return pack

    def _compose(self, symbol: str) -> Any | None:
        """Run the canonical composition pipeline once for ``symbol``.

        The composition-pipeline request is built by the injected
        ``compose_request_builder`` so this adapter stays decoupled from
        the ``dsp_platform.AnalysisRequest`` / ``Instrument`` types. A
        return of ``None`` means the platform could not produce a
        DecisionPack; the ``ToolRegistry`` normalizes that to
        ``UNAVAILABLE``.
        """
        request = self._compose_request_builder(symbol)
        if request is None:
            return None
        try:
            pack = self._platform.analyze_decision_pack(request)
        except Exception:
            raise
        if isinstance(pack, Mapping) and pack.get("error"):
            return None
        return pack

    def _composition_view(self, symbol: str) -> Mapping[str, Any]:
        """Return a flat dict view of the per-symbol composition.

        Each key is a tool name; each value is a dict with the
        canonical, pre-computed result. If the symbol has not been
        analyzed, the value is an empty dict (ToolRegistry turns that
        into UNAVAILABLE).
        """
        pack = self._decision_pack(symbol)
        if pack is None or not isinstance(pack, Mapping):
            return {}
        return _flatten_pack(pack, symbol)


# --- module-level pack cache (per-adapter) --------------------------------


_PACK_CACHE: dict[int, dict[str, Any]] = {}


def _get_cached_pack(adapter: DSPPlatformToolAdapter, symbol: str) -> Any:
    cache = _PACK_CACHE.get(id(adapter), {})
    return cache.get(symbol)


def _set_cached_pack(adapter: DSPPlatformToolAdapter, symbol: str, pack: Any) -> None:
    _PACK_CACHE.setdefault(id(adapter), {})[symbol] = pack


def reset_pack_cache(adapter: DSPPlatformToolAdapter | None = None) -> None:
    """Reset the per-adapter pack cache. Useful for tests."""
    if adapter is None:
        _PACK_CACHE.clear()
    else:
        _PACK_CACHE.pop(id(adapter), None)


# --- pack-flattening helpers ----------------------------------------------


def _safe_dict(value: Any) -> Mapping[str, Any] | None:
    """Return a Mapping or None. ``None`` -> ``None``. Non-mapping -> ``None``."""
    if value is None:
        return None
    if isinstance(value, Mapping):
        return value
    return None


def _strip_private(value: Any) -> Any:
    """Recursively drop any private field name from mappings."""
    from llm_adapters.tools.contract import _PRIVATE_FIELDS
    if isinstance(value, Mapping):
        return {k: _strip_private(v) for k, v in value.items() if k not in _PRIVATE_FIELDS}
    if isinstance(value, (list, tuple)):
        return [_strip_private(v) for v in value]
    return value


def _flatten_pack(pack: Mapping[str, Any], symbol: str) -> dict[str, dict[str, Any]]:
    """Project a DecisionPack-shaped dict to a per-tool flat view.

    The canonical ``analyze_company`` returns a DecisionPack with a
    nested structure. This helper reads known fields by name and emits
    one dict per tool. The shape of each dict is the contract for the
    corresponding ``ToolResult.result``.

    NOTE: This is *projection*, not calculation. Every value comes from
    the DecisionPack. Private fields (provider, model, cost, tokens,
    internal_prompt, raw_ai_response, chain_of-thought) are stripped
    before projection so they can never enter a ToolResult.
    """
    pack = _strip_private(pack)
    out: dict[str, dict[str, Any]] = {}
    valuation = _read_valuation(pack)
    if valuation is not None:
        out["valuation"] = valuation
    mos = _read_margin_of_safety(pack)
    if mos is not None:
        out["margin_of_safety"] = mos
    for tool_key, pack_key in (
        ("economic_moat", "economic_moat"),
        ("management_quality", "management_quality"),
        ("financial_strength", "financial_strength"),
        ("earnings_quality", "earnings_quality"),
        ("growth_quality", "growth_quality"),
        ("business_quality", "business_quality"),
        ("financial_quality", "financial_quality"),
    ):
        sub = _read_sub(pack, pack_key)
        if sub is not None:
            out[tool_key] = sub
    risk = _read_sub(pack, "risk")
    if risk is not None:
        out["risk"] = risk
    qrisk = _read_sub(pack, "quantitative_risk")
    if qrisk is not None:
        out["quantitative_risk"] = qrisk
    tech = _read_sub(pack, "technical_signals")
    if tech is not None:
        out["technical_signals"] = tech
    rec = _read_recommendation(pack)
    if rec is not None:
        out["recommendation"] = rec
    return out


def _read_valuation(pack: Mapping[str, Any]) -> dict[str, Any] | None:
    """Project the valuation section. May be at pack top or nested."""
    candidates = (
        pack.get("valuation"),
        pack.get("valuation_summary"),
        (pack.get("valuation") or {}).get("summary") if isinstance(pack.get("valuation"), Mapping) else None,
    )
    for cand in candidates:
        if isinstance(cand, Mapping):
            iv = cand.get("intrinsic_value_per_share")
            cmp_ = cand.get("current_market_price")
            method = cand.get("method") or cand.get("valuation_method")
            if iv is not None or cmp_ is not None:
                return {
                    "intrinsic_value_per_share": iv,
                    "current_market_price": cmp_,
                    "method": method,
                }
    return None


def _read_margin_of_safety(pack: Mapping[str, Any]) -> dict[str, Any] | None:
    candidates = (
        pack.get("margin_of_safety"),
        pack.get("valuation_margin_of_safety"),
    )
    for cand in candidates:
        if isinstance(cand, Mapping):
            mos = cand.get("margin_of_safety") or cand.get("value")
            basis = cand.get("basis") or "dsp_platform.analyze_company"
            if mos is not None:
                return {"margin_of_safety": mos, "basis": basis}
    return None


def _read_sub(pack: Mapping[str, Any], key: str) -> dict[str, Any] | None:
    sub = pack.get(key)
    if isinstance(sub, Mapping):
        return dict(sub)
    return None


def _read_recommendation(pack: Mapping[str, Any]) -> dict[str, Any] | None:
    rec = pack.get("recommendation")
    if not isinstance(rec, Mapping):
        rec = pack.get("investment_recommendation")
    if isinstance(rec, Mapping):
        return {
            "decision": rec.get("decision") or rec.get("action"),
            "confidence": rec.get("confidence"),
            "margin_of_safety": rec.get("margin_of_safety"),
        }
    return None


__all__ = [
    "DSPPlatformToolAdapter",
    "ToolHealthState",
    "reset_pack_cache",
]
