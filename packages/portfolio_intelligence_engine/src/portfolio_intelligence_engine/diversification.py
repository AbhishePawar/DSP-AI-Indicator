"""Diversification Score — combination of already-computed signals only.

Inputs: holding count and sector labels (caller-supplied), the correlation
matrix from ``portfolio_analytics.compute_risk_attribution`` (frozen), and
per-holding risk contribution from the same engine. This module never
computes a new correlation or risk figure — it only derives simple
descriptive statistics (average, Herfindahl index) from numbers already
produced elsewhere, then maps them to an explainable 0-100 score.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from portfolio_intelligence_engine.enums import IntelligenceStatus
from portfolio_intelligence_engine.models import DiversificationScore, HoldingSignal

__all__ = ["compute_diversification_score"]


def _average_pairwise_correlation(
    correlation_matrix: Mapping[str, object] | None,
) -> float | None:
    if not correlation_matrix:
        return None
    symbols = correlation_matrix.get("symbols")
    matrix = correlation_matrix.get("matrix")
    if not isinstance(symbols, Sequence) or not isinstance(matrix, Sequence):
        return None
    n = len(symbols)
    if n < 2:
        return None
    total = 0.0
    count = 0
    for i in range(n):
        row = matrix[i] if i < len(matrix) else ()
        for j in range(i + 1, n):
            value = row[j] if isinstance(row, Sequence) and j < len(row) else None
            if isinstance(value, (int, float)):
                total += float(value)
                count += 1
    if count == 0:
        return None
    return total / count


def compute_diversification_score(
    holdings: Sequence[HoldingSignal],
    *,
    correlation_matrix: Mapping[str, object] | None,
) -> DiversificationScore:
    if not holdings:
        return DiversificationScore(
            status=IntelligenceStatus.UNAVAILABLE,
            score=None,
            holding_count=0,
            sector_count=0,
            average_pairwise_correlation=None,
            largest_position_weight=None,
            position_herfindahl_index=None,
            risk_herfindahl_index=None,
            explanation=(),
            limitations=("no portfolio holdings supplied.",),
        )

    total_weight = sum(h.weight for h in holdings) or 1.0
    sectors = {h.sector for h in holdings if h.sector}
    avg_corr = _average_pairwise_correlation(correlation_matrix)
    largest_weight = max(h.weight for h in holdings) / total_weight
    position_hhi = sum((h.weight / total_weight) ** 2 for h in holdings)

    risk_contributions = [
        h.risk_contribution_pct for h in holdings if h.risk_contribution_pct is not None
    ]
    risk_hhi = (
        sum((rc / 100.0) ** 2 for rc in risk_contributions)
        if risk_contributions
        else None
    )

    limitations: list[str] = []
    if avg_corr is None:
        limitations.append(
            "Data unavailable. No correlation matrix supplied — correlation "
            "component excluded from the score."
        )
    if risk_hhi is None:
        limitations.append(
            "Data unavailable. No per-holding risk attribution supplied — risk "
            "distribution component excluded from the score."
        )

    # Weighted combination of available sub-signals, each mapped to 0-100
    # (higher = more diversified). Undisclosed components are excluded and
    # the remaining weights renormalized — never fabricated.
    components: list[tuple[float, float]] = []  # (score, weight)
    holding_count_score = min(100.0, (len(holdings) / 30.0) * 100.0)
    components.append((holding_count_score, 0.2))
    sector_score = min(100.0, (len(sectors) / 11.0) * 100.0)
    components.append((sector_score, 0.2))
    position_score = max(0.0, (1.0 - position_hhi) * 100.0)
    components.append((position_score, 0.2))
    if avg_corr is not None:
        corr_score = max(0.0, (1.0 - max(0.0, avg_corr)) * 100.0)
        components.append((corr_score, 0.2))
    if risk_hhi is not None:
        risk_score = max(0.0, (1.0 - min(1.0, risk_hhi)) * 100.0)
        components.append((risk_score, 0.2))

    total_weight_used = sum(w for _, w in components)
    score = (
        sum(s * w for s, w in components) / total_weight_used
        if total_weight_used
        else None
    )

    explanation = (
        f"{len(holdings)} holdings across {len(sectors)} of the 11 GICS sectors.",
        f"Largest single position is {largest_weight:.1%} of the portfolio "
        f"(Herfindahl index {position_hhi:.3f}).",
    )
    if avg_corr is not None:
        explanation += (f"Average pairwise return correlation is {avg_corr:.2f}.",)
    if risk_hhi is not None:
        explanation += (f"Risk contribution has a Herfindahl index of {risk_hhi:.3f}.",)

    return DiversificationScore(
        status=IntelligenceStatus.COMPLETE
        if not limitations
        else IntelligenceStatus.PARTIAL,
        score=score,
        holding_count=len(holdings),
        sector_count=len(sectors),
        average_pairwise_correlation=avg_corr,
        largest_position_weight=largest_weight,
        position_herfindahl_index=position_hhi,
        risk_herfindahl_index=risk_hhi,
        explanation=explanation,
        limitations=tuple(limitations),
    )
