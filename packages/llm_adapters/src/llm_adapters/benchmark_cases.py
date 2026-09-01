"""DSP benchmark cases — fixed evidence so models are compared fairly.

Each case carries:
- a stable research_case_id
- a fixed DSP research specification (evidence + trusted tool results)
- the question the model must answer
- expected frozen values (ground truth) used by the evaluator
- expected complexity signals (drives routing)

Evidence is intentionally short, deterministic, and provider-neutral so
that no model is favoured by prompt engineering.

The cases follow the brief: simple interpretation, comparison, routine
valuation, complex valuation conflict, conflicting evidence, missing
history, difficult Buffett/BQ case, high-risk/uncertain.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

from llm_adapters.routing import ComplexitySignal


@dataclass(frozen=True, slots=True)
class ResearchSpec:
    """Provider-neutral research specification.

    The same ``ResearchSpec`` is sent to every model. ``evidence`` is the
    authoritative DSP evidence (already validated). ``frozen_values`` is
    the ground truth the evaluator uses to score claims.
    """

    research_case_id: str
    research_spec_version: str
    question: str
    evidence: Mapping[str, str]
    frozen_values: Mapping[str, str]
    notes: str = ""


@dataclass(frozen=True, slots=True)
class BenchmarkCase:
    """A (case, spec, signals) tuple ready for the harness."""

    spec: ResearchSpec
    signals: tuple[ComplexitySignal, ...]
    expected_routing_tier: str  # "cost_efficient" or "premium" — used for report only


# 8 cases — fixed evidence, no live data, fair comparison.


_CASE_01 = ResearchSpec(
    research_case_id="DSP-BMK-01-simple-interpretation",
    research_spec_version="v1",
    question=(
        "Based on the supplied DSP evidence, summarise the company's "
        "current investment posture in plain language."
    ),
    evidence={
        "recommendation": "Hold",
        "intrinsic_value_per_share": "182.50",
        "current_market_price": "175.20",
        "margin_of_safety": "4.0%",
        "business_quality": "Good (score 0.72)",
        "moat": "Narrow",
        "management_quality": "Average",
        "financial_strength": "Strong",
        "risks": "Customer concentration; FX exposure.",
    },
    frozen_values={
        "recommendation": "Hold",
        "intrinsic_value_per_share": "182.50",
        "margin_of_safety": "4.0%",
    },
)


_CASE_02 = ResearchSpec(
    research_case_id="DSP-BMK-02-simple-comparison",
    research_spec_version="v1",
    question=(
        "Compare the two companies on quality, valuation, and risk. "
        "Which is more attractive today and why?"
    ),
    evidence={
        "company_a": {
            "name": "Alpha",
            "recommendation": "Buy",
            "intrinsic_value": "320",
            "current_price": "260",
            "margin_of_safety": "18.8%",
            "business_quality": "Great (0.85)",
            "moat": "Wide",
        },
        "company_b": {
            "name": "Beta",
            "recommendation": "Sell",
            "intrinsic_value": "90",
            "current_price": "120",
            "margin_of_safety": "-33.3%",
            "business_quality": "Weak (0.42)",
            "moat": "None",
        },
    },
    frozen_values={
        "company_a_recommendation": "Buy",
        "company_b_recommendation": "Sell",
    },
)


_CASE_03 = ResearchSpec(
    research_case_id="DSP-BMK-03-routine-valuation",
    research_spec_version="v1",
    question=(
        "Interpret this DCF valuation. Is the current price below or "
        "above intrinsic value, and what is the margin of safety?"
    ),
    evidence={
        "method": "Two-stage DCF (10y explicit + terminal)",
        "intrinsic_value_per_share": "240.00",
        "current_market_price": "210.00",
        "wacc": "9.4%",
        "terminal_growth": "3.0%",
        "fcf_cagr_5y": "11.2%",
    },
    frozen_values={
        "intrinsic_value_per_share": "240.00",
        "current_market_price": "210.00",
        "margin_of_safety": "12.5%",
    },
)


_CASE_04 = ResearchSpec(
    research_case_id="DSP-BMK-04-valuation-conflict",
    research_spec_version="v1",
    question=(
        "DCF and Graham-Number valuations disagree. Reconcile them and "
        "state which one you would weight more for this company."
    ),
    evidence={
        "dcf_intrinsic_value": "210",
        "dcf_assumptions": {"wacc": "9.4%", "terminal_g": "3.0%"},
        "graham_number": "150",
        "graham_assumptions": {"eps_ttm": "8.2", "bvps": "62"},
        "current_market_price": "195",
        "moat": "Narrow",
        "fcf_history_years": 4,
    },
    frozen_values={
        "dcf_intrinsic_value": "210",
        "graham_number": "150",
        "current_market_price": "195",
    },
)


_CASE_05 = ResearchSpec(
    research_case_id="DSP-BMK-05-conflicting-evidence",
    research_spec_version="v1",
    question=(
        "Two evidence sources disagree on business quality. Resolve the "
        "conflict using the provided DSP criteria."
    ),
    evidence={
        "source_a": {"business_quality": "Great", "score": 0.84},
        "source_b": {"business_quality": "Weak", "score": 0.41},
        "moat_inputs": {"gross_margin_stability": "low", "switching_cost": "low"},
        "management_inputs": {"capital_allocation": "poor", "disclosure": "fair"},
        "duration_years": 12,
    },
    frozen_values={
        "source_a_score": "0.84",
        "source_b_score": "0.41",
    },
)


_CASE_06 = ResearchSpec(
    research_case_id="DSP-BMK-06-missing-history",
    research_spec_version="v1",
    question=(
        "Only two years of financial history is available. State what is "
        "knowable and what cannot be determined with confidence."
    ),
    evidence={
        "available_years": 2,
        "fcf_2y": [120, 145],
        "revenue_2y": [980, 1080],
        "missing": "5y history, margin stability, full cycle coverage",
    },
    frozen_values={
        "available_years": "2",
        "knowable": "current margin, current FCF trend",
    },
)


_CASE_07 = ResearchSpec(
    research_case_id="DSP-BMK-07-difficult-buffett-bq",
    research_spec_version="v1",
    question=(
        "Apply the Buffett-style business quality test to this company "
        "given inconsistent evidence."
    ),
    evidence={
        "moat": "unclear",
        "management_consistency": "mixed",
        "industry_structure": "oligopoly with new entrant risk",
        "fcf_history": "volatile",
        "earnings_quality": "moderate",
        "competitive_advantages": ["brand", "scale", "switching cost: low"],
    },
    frozen_values={
        "moat": "unclear",
        "competitive_advantages_count": "3",
    },
)


_CASE_08 = ResearchSpec(
    research_case_id="DSP-BMK-08-high-risk-uncertain",
    research_spec_version="v1",
    question=(
        "Capital is at risk. State the dominant risk, the uncertainty, "
        "and the safest DSP-allowed posture."
    ),
    evidence={
        "primary_risk": "regulatory",
        "secondary_risks": ["FX", "concentration"],
        "uncertainty_level": "high",
        "available_history_years": 1,
        "data_completeness": "0.55",
        "moat": "None",
    },
    frozen_values={
        "primary_risk": "regulatory",
        "data_completeness": "0.55",
    },
)


BENCHMARK_CASES: tuple[BenchmarkCase, ...] = (
    BenchmarkCase(
        spec=_CASE_01,
        signals=(ComplexitySignal.MISSING_DATA,),
        expected_routing_tier="cost_efficient",
    ),
    BenchmarkCase(
        spec=_CASE_02,
        signals=(ComplexitySignal.MISSING_DATA,),
        expected_routing_tier="cost_efficient",
    ),
    BenchmarkCase(
        spec=_CASE_03,
        signals=(ComplexitySignal.MISSING_DATA,),
        expected_routing_tier="cost_efficient",
    ),
    BenchmarkCase(
        spec=_CASE_04,
        signals=(
            ComplexitySignal.VALUATION_DISAGREEMENT,
            ComplexitySignal.INSUFFICIENT_HISTORY,
        ),
        expected_routing_tier="premium",
    ),
    BenchmarkCase(
        spec=_CASE_05,
        signals=(ComplexitySignal.CONFLICTING_EVIDENCE,),
        expected_routing_tier="premium",
    ),
    BenchmarkCase(
        spec=_CASE_06,
        signals=(ComplexitySignal.INSUFFICIENT_HISTORY,),
        expected_routing_tier="cost_efficient",
    ),
    BenchmarkCase(
        spec=_CASE_07,
        signals=(ComplexitySignal.DIFFICULT_BUFFETT_ANALYSIS,),
        expected_routing_tier="premium",
    ),
    BenchmarkCase(
        spec=_CASE_08,
        signals=(
            ComplexitySignal.MATERIAL_RISK,
            ComplexitySignal.HIGH_UNCERTAINTY,
            ComplexitySignal.HIGH_IMPACT_DECISION,
        ),
        expected_routing_tier="premium",
    ),
)


__all__ = [
    "BENCHMARK_CASES",
    "BenchmarkCase",
    "ResearchSpec",
]
