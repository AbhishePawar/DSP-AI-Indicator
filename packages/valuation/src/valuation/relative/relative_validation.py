"""Input validation for Relative Valuation."""

from __future__ import annotations

import math

from valuation.core.result_models import ValidationSummary
from valuation.core.validation_engine import ValidationEngine
from valuation.exceptions import ValuationError
from valuation.relative.relative_models import (
    BenchmarkMultiples,
    BenchmarkScope,
    RelativeInputs,
    RelativeMultiple,
)

__all__ = ["validate_relative_inputs"]


def _finite(value: float, name: str, errors: list[str]) -> None:
    if math.isnan(value):
        errors.append(f"{name} is NaN")
    if math.isinf(value):
        errors.append(f"{name} is infinite")


def _bench_ok(b: BenchmarkMultiples | None) -> bool:
    if b is None:
        return False
    return (b.median is not None and b.median > 0) or (
        b.mean is not None and b.mean > 0
    )


def validate_relative_inputs(inputs: RelativeInputs) -> ValidationSummary:
    """Validate relative inputs; raise ValuationError on hard failures."""
    errors: list[str] = []
    checks: list[str] = []
    warnings: list[str] = []

    required: list[tuple[str, float]] = [
        ("current_market_price", inputs.current_market_price),
        ("shares_outstanding", inputs.shares_outstanding),
        ("industry_weight", inputs.industry_weight),
        ("sector_weight", inputs.sector_weight),
        ("peer_weight", inputs.peer_weight),
        ("bear_multiple_delta", inputs.bear_multiple_delta),
        ("bull_multiple_delta", inputs.bull_multiple_delta),
        ("bear_growth_delta", inputs.bear_growth_delta),
        ("bull_growth_delta", inputs.bull_growth_delta),
    ]
    optionals: list[tuple[str, float | None]] = [
        ("enterprise_value", inputs.enterprise_value),
        ("revenue", inputs.revenue),
        ("ebit", inputs.ebit),
        ("ebitda", inputs.ebitda),
        ("net_income", inputs.net_income),
        ("eps", inputs.eps),
        ("forward_eps", inputs.forward_eps),
        ("book_value", inputs.book_value),
        ("tangible_book_value", inputs.tangible_book_value),
        ("operating_cash_flow", inputs.operating_cash_flow),
        ("free_cash_flow", inputs.free_cash_flow),
        ("dividend_per_share", inputs.dividend_per_share),
        ("dividend_yield", inputs.dividend_yield),
        ("growth_rate", inputs.growth_rate),
        ("expected_growth", inputs.expected_growth),
        ("historical_average", inputs.historical_average),
        ("average_5y", inputs.average_5y),
        ("average_10y", inputs.average_10y),
        ("risk_free_rate", inputs.risk_free_rate),
        ("market_premium", inputs.market_premium),
        ("accounting_quality_score", inputs.accounting_quality_score),
    ]
    for name, value in required:
        _finite(value, name, errors)
    for name, value in optionals:
        if value is not None:
            _finite(value, name, errors)

    for scope_name, bench in (
        ("industry", inputs.industry),
        ("sector", inputs.sector),
        ("peer", inputs.peer),
    ):
        if bench is None:
            continue
        for attr in ("median", "mean", "percentile_25", "percentile_75"):
            v = getattr(bench, attr)
            if v is not None:
                _finite(v, f"{scope_name}.{attr}", errors)
                if v <= 0 and inputs.method is not RelativeMultiple.DIVIDEND_YIELD:
                    errors.append(f"impossible multiple {scope_name}.{attr}={v}")
                if (
                    inputs.method is RelativeMultiple.DIVIDEND_YIELD
                    and v < 0
                ):
                    errors.append(f"impossible yield {scope_name}.{attr}={v}")

    shared = ValidationEngine().summarize(
        {
            "shares_outstanding": inputs.shares_outstanding,
            "revenue": inputs.revenue if inputs.revenue and inputs.revenue > 0 else None,
        }
    )
    errors.extend(shared.errors)
    checks.extend(shared.checks)
    warnings.extend(shared.warnings)

    if inputs.shares_outstanding <= 0:
        errors.append(
            f"shares_outstanding must be positive, got {inputs.shares_outstanding}"
        )
    else:
        checks.append("shares > 0")

    if inputs.current_market_price < 0:
        errors.append(
            f"current_market_price must be non-negative, "
            f"got {inputs.current_market_price}"
        )
    else:
        checks.append("price >= 0")

    if inputs.enterprise_value is not None and inputs.enterprise_value < 0:
        errors.append(
            f"enterprise_value must be non-negative, got {inputs.enterprise_value}"
        )

    if inputs.revenue is not None and inputs.revenue < 0:
        errors.append(f"revenue must be non-negative, got {inputs.revenue}")

    method = inputs.method
    # Method-specific fundamental requirements
    need_map: dict[RelativeMultiple, tuple[str, ...]] = {
        RelativeMultiple.PE: ("eps",),
        RelativeMultiple.FORWARD_PE: ("forward_eps",),
        RelativeMultiple.PEG: ("eps", "expected_growth"),
        RelativeMultiple.PB: ("book_value",),
        RelativeMultiple.PTBV: ("tangible_book_value",),
        RelativeMultiple.PRICE_SALES: ("revenue",),
        RelativeMultiple.PRICE_CASH_FLOW: ("operating_cash_flow",),
        RelativeMultiple.PRICE_FCF: ("free_cash_flow",),
        RelativeMultiple.EV_SALES: ("enterprise_value", "revenue"),
        RelativeMultiple.EV_EBIT: ("enterprise_value", "ebit"),
        RelativeMultiple.EV_EBITDA: ("enterprise_value", "ebitda"),
        RelativeMultiple.DIVIDEND_YIELD: (),
    }
    for field_name in need_map.get(method, ()):
        if getattr(inputs, field_name) is None:
            errors.append(f"{method.value} requires {field_name}")
        elif field_name == "eps" and inputs.eps == 0:
            errors.append("eps must be non-zero for P/E")
        elif field_name == "forward_eps" and inputs.forward_eps == 0:
            errors.append("forward_eps must be non-zero for Forward P/E")
        elif field_name == "expected_growth" and (
            inputs.expected_growth is None or inputs.expected_growth == 0
        ):
            errors.append("expected_growth must be non-zero for PEG")

    # Peer / benchmark data required for primary scope
    # Prefer top-level benches; fall back to per-multiple maps for primary method.
    industry = inputs.industry
    sector = inputs.sector
    peer = inputs.peer
    if not _bench_ok(industry):
        industry = inputs.industry_by_multiple.get(inputs.method, industry)
    if not _bench_ok(sector):
        sector = inputs.sector_by_multiple.get(inputs.method, sector)
    if not _bench_ok(peer):
        peer = inputs.peer_by_multiple.get(inputs.method, peer)

    scope = inputs.benchmark_scope
    if scope is BenchmarkScope.INDUSTRY and not _bench_ok(industry):
        errors.append("missing industry peer data (median/mean)")
    elif scope is BenchmarkScope.SECTOR and not _bench_ok(sector):
        errors.append("missing sector peer data (median/mean)")
    elif scope is BenchmarkScope.PEER and not _bench_ok(peer):
        errors.append("missing peer group data (median/mean)")
    elif scope is BenchmarkScope.HISTORICAL:
        hist = (
            inputs.historical_average
            or inputs.average_5y
            or inputs.average_10y
            or inputs.historical_by_multiple.get(inputs.method)
        )
        if hist is None or hist <= 0:
            errors.append("missing historical multiples")
        else:
            checks.append("historical multiples present")
    elif scope is BenchmarkScope.WEIGHTED:
        if not (_bench_ok(industry) or _bench_ok(sector) or _bench_ok(peer)):
            errors.append("weighted scope requires at least one benchmark set")
        wsum = inputs.industry_weight + inputs.sector_weight + inputs.peer_weight
        if abs(wsum - 1.0) > 1e-6:
            warnings.append(f"benchmark weights sum to {wsum}, not 1.0")
        else:
            checks.append("weights sum to 1")

    if inputs.peer is not None and inputs.peer.count > 0 and inputs.peer.count < 3:
        warnings.append("weak peer set (count < 3)")

    if inputs.eps is not None and inputs.eps < 0:
        warnings.append("negative EPS — P/E interpretation is limited")

    errors = list(dict.fromkeys(errors))
    checks = list(dict.fromkeys(checks))
    warnings = list(dict.fromkeys(warnings))

    if errors:
        raise ValuationError(
            "Relative valuation validation failed: " + "; ".join(errors)
        )

    return ValidationSummary(
        ok=True,
        checks=tuple(checks),
        errors=(),
        warnings=tuple(warnings),
    )
