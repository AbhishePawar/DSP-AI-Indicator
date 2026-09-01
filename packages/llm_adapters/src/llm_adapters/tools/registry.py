"""DSP trusted tool registry and dispatcher.

The registry holds a fixed, approved set of tools. Each tool:

- is registered with a stable name + version
- declares its input/output schema
- implements ``invoke(backend, input) -> ToolResult``
- returns typed results only
- never fabricates values
- fails closed on any error

The dispatcher:

- accepts tool calls by name only (string)
- validates input against the declared schema
- returns a typed ``ToolResult``
- wraps any exception in a FAILED ToolResult
- never returns Python internals, raw provider data, or models

The list of approved tools lives in :data:`DEFAULT_TOOL_NAMES`. Only
those names are honoured; an unknown name returns INVALID_INPUT.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Mapping

from llm_adapters.tools.contract import (
    DSPToolBackend,
    ToolInputField,
    ToolOutputField,
    ToolResult,
    ToolSpec,
    ToolStatus,
    assert_no_tool_leakage,
)


# --- helper builders ------------------------------------------------------


def _ok(
    tool_name: str,
    tool_version: str,
    result: Mapping[str, Any],
    *,
    evidence_refs: Iterable[str] = (),
    calculation_metadata: Mapping[str, Any] | None = None,
    limitations: Iterable[str] = (),
) -> ToolResult:
    payload = {
        "tool_name": tool_name,
        "tool_version": tool_version,
        "status": ToolStatus.OK,
        "result": dict(result),
        "evidence_refs": tuple(evidence_refs),
        "calculation_metadata": dict(calculation_metadata or {}),
        "limitations": tuple(limitations),
    }
    assert_no_tool_leakage(payload["result"])
    return ToolResult(**payload)


def _unavailable(
    tool_name: str,
    tool_version: str,
    reason: str,
    *,
    evidence_refs: Iterable[str] = (),
) -> ToolResult:
    return ToolResult(
        tool_name=tool_name,
        tool_version=tool_version,
        status=ToolStatus.UNAVAILABLE,
        result={"reason": reason},
        evidence_refs=tuple(evidence_refs),
        calculation_metadata={},
        limitations=(reason,),
    )


def _failed(
    tool_name: str,
    tool_version: str,
    reason: str,
) -> ToolResult:
    return ToolResult(
        tool_name=tool_name,
        tool_version=tool_version,
        status=ToolStatus.FAILED,
        result={"reason": reason},
        evidence_refs=(),
        calculation_metadata={},
        limitations=(reason,),
    )


def _invalid(
    tool_name: str,
    tool_version: str,
    reason: str,
) -> ToolResult:
    return ToolResult(
        tool_name=tool_name,
        tool_version=tool_version,
        status=ToolStatus.INVALID_INPUT,
        result={"reason": reason},
        evidence_refs=(),
        calculation_metadata={},
        limitations=(reason,),
    )


def _validate_input(
    tool_name: str,
    tool_version: str,
    schema: tuple[ToolInputField, ...],
    input_: Mapping[str, Any],
) -> ToolResult | None:
    """Return an INVALID_INPUT ToolResult if validation fails, else None."""
    for fld in schema:
        if fld.required and fld.name not in input_:
            return _invalid(
                tool_name,
                tool_version,
                f"missing required input field: {fld.name}",
            )
        if fld.name in input_:
            value = input_[fld.name]
            if not _matches_type(value, fld.type):
                return _invalid(
                    tool_name,
                    tool_version,
                    f"input field {fld.name!r} has wrong type; expected {fld.type}",
                )
    return None


def _matches_type(value: Any, type_str: str) -> bool:
    if type_str == "string":
        return isinstance(value, str)
    if type_str == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if type_str == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if type_str == "boolean":
        return isinstance(value, bool)
    if type_str == "object":
        return isinstance(value, Mapping)
    if type_str == "array":
        return isinstance(value, (list, tuple))
    if type_str == "any":
        return True
    return False  # unknown type -> never match


# --- individual tool definitions ------------------------------------------


_COMMON_PROVENANCE = "dsp_platform"


def _spec_financial_statements() -> ToolSpec:
    return ToolSpec(
        name="dsp.financial_statements",
        version="1.0.0",
        description="Authenticated financial statements (income / balance / cashflow) for a symbol.",
        provenance=f"{_COMMON_PROVENANCE}.financial_statements",
        input_schema=(
            ToolInputField("symbol", "string", True, "Ticker symbol"),
            ToolInputField("exchange", "string", False, "Optional exchange code"),
        ),
        output_schema=(
            ToolOutputField("periods", "array", True, "Available reporting periods"),
            ToolOutputField("currency", "string", False, "Reporting currency"),
            ToolOutputField("source", "string", True, "Provenance of the data"),
        ),
    )


def _spec_financial_quality() -> ToolSpec:
    return ToolSpec(
        name="dsp.financial_quality",
        version="1.0.0",
        description="Authoritative financial-quality signals derived from authenticated statements.",
        provenance=f"{_COMMON_PROVENANCE}.analyze_company (composition)",
        input_schema=(ToolInputField("symbol", "string", True, "Ticker symbol"),),
        output_schema=(
            ToolOutputField("metrics", "object", True, "Named financial-quality metrics"),
            ToolOutputField("as_of", "string", True, "Effective timestamp (ISO-8601)"),
        ),
    )


def _spec_valuation() -> ToolSpec:
    return ToolSpec(
        name="dsp.valuation",
        version="1.0.0",
        description="Authoritative valuation result: intrinsic value per share and current market price.",
        provenance=f"{_COMMON_PROVENANCE}.analyze_company.valuation_summary",
        input_schema=(ToolInputField("symbol", "string", True, "Ticker symbol"),),
        output_schema=(
            ToolOutputField("intrinsic_value_per_share", "number", True, "Authoritative intrinsic value"),
            ToolOutputField("current_market_price", "number", False, "Current authenticated market price"),
            ToolOutputField("method", "string", True, "Valuation method used"),
        ),
    )


def _spec_margin_of_safety() -> ToolSpec:
    return ToolSpec(
        name="dsp.margin_of_safety",
        version="1.0.0",
        description="Authoritative margin of safety derived from intrinsic value vs. current price.",
        provenance=f"{_COMMON_PROVENANCE}.analyze_company.margin_of_safety",
        input_schema=(ToolInputField("symbol", "string", True, "Ticker symbol"),),
        output_schema=(
            ToolOutputField("margin_of_safety", "number", True, "Decimal (0.2 = 20%)"),
            ToolOutputField("basis", "string", True, "Computation basis"),
        ),
    )


def _spec_economic_moat() -> ToolSpec:
    return ToolSpec(
        name="dsp.economic_moat",
        version="1.0.0",
        description="Authoritative economic moat assessment (Wide / Narrow / None).",
        provenance=f"{_COMMON_PROVENANCE}.analyze_company.economic_moat",
        input_schema=(ToolInputField("symbol", "string", True, "Ticker symbol"),),
        output_schema=(
            ToolOutputField("moat", "string", True, "Wide / Narrow / None"),
            ToolOutputField("score", "number", False, "Optional numeric score"),
        ),
    )


def _spec_management_quality() -> ToolSpec:
    return ToolSpec(
        name="dsp.management_quality",
        version="1.0.0",
        description="Authoritative management-quality assessment.",
        provenance=f"{_COMMON_PROVENANCE}.analyze_company.management_quality",
        input_schema=(ToolInputField("symbol", "string", True, "Ticker symbol"),),
        output_schema=(
            ToolOutputField("quality", "string", True, "Strong / Average / Weak"),
            ToolOutputField("score", "number", False, "Optional numeric score"),
        ),
    )


def _spec_financial_strength() -> ToolSpec:
    return ToolSpec(
        name="dsp.financial_strength",
        version="1.0.0",
        description="Authoritative financial-strength assessment (balance sheet health).",
        provenance=f"{_COMMON_PROVENANCE}.analyze_company.financial_strength",
        input_schema=(ToolInputField("symbol", "string", True, "Ticker symbol"),),
        output_schema=(
            ToolOutputField("strength", "string", True, "Strong / Average / Weak"),
            ToolOutputField("score", "number", False, "Optional numeric score"),
        ),
    )


def _spec_earnings_quality() -> ToolSpec:
    return ToolSpec(
        name="dsp.earnings_quality",
        version="1.0.0",
        description="Authoritative earnings-quality signals (accruals, cash conversion, stability).",
        provenance=f"{_COMMON_PROVENANCE}.analyze_company.earnings_quality",
        input_schema=(ToolInputField("symbol", "string", True, "Ticker symbol"),),
        output_schema=(
            ToolOutputField("quality", "string", True, "High / Average / Low"),
            ToolOutputField("score", "number", False, "Optional numeric score"),
        ),
    )


def _spec_growth_quality() -> ToolSpec:
    return ToolSpec(
        name="dsp.growth_quality",
        version="1.0.0",
        description="Authoritative growth-quality signals (sustainability + consistency).",
        provenance=f"{_COMMON_PROVENANCE}.analyze_company.growth_quality",
        input_schema=(ToolInputField("symbol", "string", True, "Ticker symbol"),),
        output_schema=(
            ToolOutputField("growth", "string", True, "Strong / Average / Weak"),
            ToolOutputField("score", "number", False, "Optional numeric score"),
        ),
    )


def _spec_business_quality() -> ToolSpec:
    return ToolSpec(
        name="dsp.business_quality",
        version="1.0.0",
        description="Authoritative aggregated business-quality label and score.",
        provenance=f"{_COMMON_PROVENANCE}.analyze_company.business_quality",
        input_schema=(ToolInputField("symbol", "string", True, "Ticker symbol"),),
        output_schema=(
            ToolOutputField("label", "string", True, "Great / Good / Average / Weak / Poor"),
            ToolOutputField("score", "number", True, "0-1 normalized score"),
        ),
    )


def _spec_risk() -> ToolSpec:
    return ToolSpec(
        name="dsp.risk",
        version="1.0.0",
        description="Authoritative qualitative + quantitative risk signals.",
        provenance=f"{_COMMON_PROVENANCE}.analyze_company.risk",
        input_schema=(ToolInputField("symbol", "string", True, "Ticker symbol"),),
        output_schema=(
            ToolOutputField("risks", "array", True, "List of named risk items"),
            ToolOutputField("score", "number", False, "Optional numeric risk score"),
        ),
    )


def _spec_quantitative_risk() -> ToolSpec:
    return ToolSpec(
        name="dsp.quantitative_risk",
        version="1.0.0",
        description="Authoritative quantitative risk metrics (volatility, drawdown, beta).",
        provenance=f"{_COMMON_PROVENANCE}.analyze_company.quantitative_risk",
        input_schema=(ToolInputField("symbol", "string", True, "Ticker symbol"),),
        output_schema=(
            ToolOutputField("volatility", "number", False, "Annualized volatility"),
            ToolOutputField("beta", "number", False, "Market beta"),
            ToolOutputField("max_drawdown", "number", False, "Maximum drawdown"),
        ),
    )


def _spec_technical_signals() -> ToolSpec:
    return ToolSpec(
        name="dsp.technical_signals",
        version="1.0.0",
        description="Authoritative technical indicators/signals (trend, momentum, mean-reversion).",
        provenance=f"{_COMMON_PROVENANCE}.analyze_company.technical_signals (industry package)",
        input_schema=(ToolInputField("symbol", "string", True, "Ticker symbol"),),
        output_schema=(
            ToolOutputField("signals", "array", True, "Named signal items"),
            ToolOutputField("direction", "string", False, "BULLISH / BEARISH / NEUTRAL"),
        ),
    )


def _spec_investment_recommendation() -> ToolSpec:
    return ToolSpec(
        name="dsp.investment_recommendation",
        version="1.0.0",
        description="Authoritative investment recommendation derived from frozen DSP engines.",
        provenance=f"{_COMMON_PROVENANCE}.analyze_company.recommendation",
        input_schema=(ToolInputField("symbol", "string", True, "Ticker symbol"),),
        output_schema=(
            ToolOutputField("decision", "string", True, "Buy / Hold / Sell"),
            ToolOutputField("confidence", "number", True, "0-1 confidence"),
            ToolOutputField("margin_of_safety", "number", False, "Decimal margin of safety"),
        ),
    )


def _spec_deterministic_committee() -> ToolSpec:
    return ToolSpec(
        name="dsp.deterministic_committee",
        version="1.0.0",
        description="Deterministic investment-committee vote over already-computed engine signals.",
        provenance=f"{_COMMON_PROVENANCE}.institutional_committee",
        input_schema=(ToolInputField("symbol", "string", True, "Ticker symbol"),),
        output_schema=(
            ToolOutputField("decision", "string", True, "BUY / HOLD / SELL"),
            ToolOutputField("votes", "object", True, "Per-member votes"),
            ToolOutputField("confidence", "number", False, "0-1 confidence"),
        ),
    )


def _spec_research_object() -> ToolSpec:
    return ToolSpec(
        name="dsp.research_object",
        version="1.0.0",
        description="Authoritative research object for a symbol (frozen, evidence-linked).",
        provenance=f"{_COMMON_PROVENANCE}.research_object_facade",
        input_schema=(ToolInputField("symbol", "string", True, "Ticker symbol"),),
        output_schema=(
            ToolOutputField("lineage_id", "string", True, "Stable lineage identifier"),
            ToolOutputField("evidence_refs", "array", True, "Evidence section references"),
            ToolOutputField("summary", "object", True, "Top-level research summary"),
        ),
    )


def _spec_comparison() -> ToolSpec:
    return ToolSpec(
        name="dsp.comparison",
        version="1.0.0",
        description="Authoritative side-by-side comparison of two symbols (qualitative, evidence-linked).",
        provenance=f"{_COMMON_PROVENANCE}.compare_companies (composition-fed)",
        input_schema=(
            ToolInputField("symbol_a", "string", True, "First ticker"),
            ToolInputField("symbol_b", "string", True, "Second ticker"),
        ),
        output_schema=(
            ToolOutputField("dimensions", "array", True, "Per-dimension comparison results"),
            ToolOutputField("summary", "object", True, "Aggregate comparison summary"),
        ),
    )


# --- tool implementations -------------------------------------------------


def _impl_financial_statements(backend: DSPToolBackend, input_: Mapping[str, Any]) -> ToolResult:
    name, version = "dsp.financial_statements", "1.0.0"
    err = _validate_input(name, version, _spec_financial_statements().input_schema, input_)
    if err is not None:
        return err
    try:
        out = backend.get_authenticated_financial_statements(
            symbol=input_["symbol"],
            exchange=input_.get("exchange"),
        )
    except Exception as exc:  # noqa: BLE001 — fail-closed
        return _failed(name, version, f"{exc.__class__.__name__}: {exc}")
    if out is None:
        return _unavailable(name, version, "no financial statements available")
    if isinstance(out, Mapping) and out.get("error"):
        return _unavailable(name, version, str(out.get("error")))
    if not isinstance(out, Mapping):
        return _failed(name, version, "backend returned non-mapping result")
    periods = out.get("periods") or out.get("statements") or []
    return _ok(
        name,
        version,
        {
            "periods": list(periods) if isinstance(periods, (list, tuple)) else [],
            "currency": out.get("currency"),
            "source": out.get("source") or "dsp.financial_statements",
        },
        evidence_refs=tuple(out.get("evidence_refs", ())),
        calculation_metadata={"as_of": out.get("as_of")},
    )


def _impl_passthrough(
    backend_method: str,
    spec: ToolSpec,
    *,
    ok_transform: Callable[[Any], Mapping[str, Any]],
) -> Callable[[DSPToolBackend, Mapping[str, Any]], ToolResult]:
    def invoke(backend: DSPToolBackend, input_: Mapping[str, Any]) -> ToolResult:
        err = _validate_input(spec.name, spec.version, spec.input_schema, input_)
        if err is not None:
            return err
        method = getattr(backend, backend_method, None)
        if method is None:
            return _failed(spec.name, spec.version, f"backend missing {backend_method!r}")
        try:
            kwargs: dict[str, Any] = {"symbol": input_["symbol"]}
            if "exchange" in input_:
                kwargs["exchange"] = input_["exchange"]
            out = method(**kwargs)
        except Exception as exc:  # noqa: BLE001 — fail-closed
            return _failed(spec.name, spec.version, f"{exc.__class__.__name__}: {exc}")
        if out is None:
            return _unavailable(spec.name, spec.version, "engine returned no result")
        if isinstance(out, Mapping) and out.get("error"):
            return _unavailable(spec.name, spec.version, str(out.get("error")))
        return _ok(
            spec.name,
            spec.version,
            ok_transform(out),
            evidence_refs=tuple(out.get("evidence_refs", ())) if isinstance(out, Mapping) else (),
            calculation_metadata={
                "as_of": out.get("as_of") if isinstance(out, Mapping) else None,
            },
        )
    return invoke


def _impl_comparison(backend: DSPToolBackend, input_: Mapping[str, Any]) -> ToolResult:
    name, version = "dsp.comparison", "1.0.0"
    err = _validate_input(name, version, _spec_comparison().input_schema, input_)
    if err is not None:
        return err
    method = getattr(backend, "compare_two_symbols", None)
    if method is None:
        return _failed(name, version, "backend missing compare_two_symbols")
    try:
        out = method(symbol_a=input_["symbol_a"], symbol_b=input_["symbol_b"])
    except Exception as exc:  # noqa: BLE001
        return _failed(name, version, f"{exc.__class__.__name__}: {exc}")
    if out is None:
        return _unavailable(name, version, "engine returned no result")
    if isinstance(out, Mapping) and out.get("error"):
        return _unavailable(name, version, str(out.get("error")))
    return _ok(
        name,
        version,
        {
            "dimensions": list(out.get("dimensions", [])) if isinstance(out, Mapping) else [],
            "summary": dict(out.get("summary", {})) if isinstance(out, Mapping) else {},
        },
        evidence_refs=tuple(out.get("evidence_refs", ())) if isinstance(out, Mapping) else (),
    )


def _build_default_tools() -> dict[str, tuple[ToolSpec, Callable[[DSPToolBackend, Mapping[str, Any]], ToolResult]]]:
    tools: dict[str, tuple[ToolSpec, Callable[[DSPToolBackend, Mapping[str, Any]], ToolResult]]] = {}

    def add(
        spec: ToolSpec,
        impl: Callable[[DSPToolBackend, Mapping[str, Any]], ToolResult],
    ) -> None:
        tools[spec.name] = (spec, impl)

    add(_spec_financial_statements(), _impl_financial_statements)
    add(
        _spec_financial_quality(),
        _impl_passthrough(
            "get_financial_quality",
            _spec_financial_quality(),
            ok_transform=lambda out: {
                "metrics": dict(out.get("metrics", {})) if isinstance(out, Mapping) else {},
                "as_of": out.get("as_of") if isinstance(out, Mapping) else None,
            },
        ),
    )
    add(
        _spec_valuation(),
        _impl_passthrough(
            "get_valuation",
            _spec_valuation(),
            ok_transform=lambda out: {
                "intrinsic_value_per_share": out.get("intrinsic_value_per_share"),
                "current_market_price": out.get("current_market_price"),
                "method": out.get("method", "dsp.valuation"),
            },
        ),
    )
    add(
        _spec_margin_of_safety(),
        _impl_passthrough(
            "get_margin_of_safety",
            _spec_margin_of_safety(),
            ok_transform=lambda out: {
                "margin_of_safety": out.get("margin_of_safety"),
                "basis": out.get("basis", "dsp.valuation"),
            },
        ),
    )
    add(
        _spec_economic_moat(),
        _impl_passthrough(
            "get_economic_moat",
            _spec_economic_moat(),
            ok_transform=lambda out: {
                "moat": out.get("moat", out.get("label")),
                "score": out.get("score"),
            },
        ),
    )
    add(
        _spec_management_quality(),
        _impl_passthrough(
            "get_management_quality",
            _spec_management_quality(),
            ok_transform=lambda out: {
                "quality": out.get("quality", out.get("label")),
                "score": out.get("score"),
            },
        ),
    )
    add(
        _spec_financial_strength(),
        _impl_passthrough(
            "get_financial_strength",
            _spec_financial_strength(),
            ok_transform=lambda out: {
                "strength": out.get("strength", out.get("label")),
                "score": out.get("score"),
            },
        ),
    )
    add(
        _spec_earnings_quality(),
        _impl_passthrough(
            "get_earnings_quality",
            _spec_earnings_quality(),
            ok_transform=lambda out: {
                "quality": out.get("quality", out.get("label")),
                "score": out.get("score"),
            },
        ),
    )
    add(
        _spec_growth_quality(),
        _impl_passthrough(
            "get_growth_quality",
            _spec_growth_quality(),
            ok_transform=lambda out: {
                "growth": out.get("growth", out.get("label")),
                "score": out.get("score"),
            },
        ),
    )
    add(
        _spec_business_quality(),
        _impl_passthrough(
            "get_business_quality",
            _spec_business_quality(),
            ok_transform=lambda out: {
                "label": out.get("label"),
                "score": out.get("score"),
            },
        ),
    )
    add(
        _spec_risk(),
        _impl_passthrough(
            "get_risk",
            _spec_risk(),
            ok_transform=lambda out: {
                "risks": list(out.get("risks", [])) if isinstance(out, Mapping) else [],
                "score": out.get("score"),
            },
        ),
    )
    add(
        _spec_quantitative_risk(),
        _impl_passthrough(
            "get_quantitative_risk",
            _spec_quantitative_risk(),
            ok_transform=lambda out: {
                "volatility": out.get("volatility"),
                "beta": out.get("beta"),
                "max_drawdown": out.get("max_drawdown"),
            },
        ),
    )
    add(
        _spec_technical_signals(),
        _impl_passthrough(
            "get_technical_signals",
            _spec_technical_signals(),
            ok_transform=lambda out: {
                "signals": list(out.get("signals", [])) if isinstance(out, Mapping) else [],
                "direction": out.get("direction"),
            },
        ),
    )
    add(
        _spec_investment_recommendation(),
        _impl_passthrough(
            "get_investment_recommendation",
            _spec_investment_recommendation(),
            ok_transform=lambda out: {
                "decision": out.get("decision"),
                "confidence": out.get("confidence"),
                "margin_of_safety": out.get("margin_of_safety"),
            },
        ),
    )
    add(
        _spec_deterministic_committee(),
        _impl_passthrough(
            "run_deterministic_committee",
            _spec_deterministic_committee(),
            ok_transform=lambda out: {
                "decision": out.get("decision"),
                "votes": dict(out.get("votes", {})) if isinstance(out, Mapping) else {},
                "confidence": out.get("confidence"),
            },
        ),
    )
    add(
        _spec_research_object(),
        _impl_passthrough(
            "build_research_object",
            _spec_research_object(),
            ok_transform=lambda out: {
                "lineage_id": out.get("lineage_id"),
                "evidence_refs": list(out.get("evidence_refs", [])) if isinstance(out, Mapping) else [],
                "summary": dict(out.get("summary", {})) if isinstance(out, Mapping) else {},
            },
        ),
    )
    add(_spec_comparison(), _impl_comparison)
    return tools


# --- registry -------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ToolRegistry:
    """Immutable registry of approved tools."""

    _tools: Mapping[str, tuple[ToolSpec, Callable[[DSPToolBackend, Mapping[str, Any]], ToolResult]]] = field(
        default_factory=dict
    )

    @classmethod
    def default(cls) -> "ToolRegistry":
        return cls(_build_default_tools())

    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._tools.keys()))

    def get_spec(self, name: str) -> ToolSpec | None:
        item = self._tools.get(name)
        return item[0] if item is not None else None

    def dispatch(
        self,
        name: str,
        input_: Mapping[str, Any],
        backend: DSPToolBackend,
    ) -> ToolResult:
        item = self._tools.get(name)
        if item is None:
            return _invalid(
                name,
                "0.0.0",
                f"unknown tool {name!r}; approved: {sorted(self._tools.keys())}",
            )
        spec, impl = item
        return impl(backend, dict(input_))

    def public_manifest(self) -> list[dict[str, Any]]:
        """Public manifest — what the LLM is allowed to know about.

        Contains: name, version, description, input_schema, output_schema.
        Does NOT contain: provenance, validation_status, implementation refs.
        """
        out: list[dict[str, Any]] = []
        for name in self.names():
            spec = self.get_spec(name)
            if spec is None:
                continue
            out.append(
                {
                    "name": spec.name,
                    "version": spec.version,
                    "description": spec.description,
                    "input_schema": [
                        {"name": f.name, "type": f.type, "required": f.required}
                        for f in spec.input_schema
                    ],
                    "output_schema": [
                        {"name": f.name, "type": f.type, "required": f.required}
                        for f in spec.output_schema
                    ],
                }
            )
        return out


DEFAULT_TOOL_NAMES: tuple[str, ...] = (
    "dsp.business_quality",
    "dsp.comparison",
    "dsp.deterministic_committee",
    "dsp.earnings_quality",
    "dsp.economic_moat",
    "dsp.financial_quality",
    "dsp.financial_statements",
    "dsp.financial_strength",
    "dsp.growth_quality",
    "dsp.investment_recommendation",
    "dsp.management_quality",
    "dsp.margin_of_safety",
    "dsp.quantitative_risk",
    "dsp.research_object",
    "dsp.risk",
    "dsp.technical_signals",
    "dsp.valuation",
)


__all__ = [
    "DEFAULT_TOOL_NAMES",
    "ToolRegistry",
]
