"""Composition-root factory for the platform's default comparison engine.

Wires ``comparison.QualitativeComparisonEngine`` together with
``industry.PeerEligibilityEvaluator`` and ``industry.IndustryMethodologyRegistry``
so ``DSPPlatform.compare_companies`` has a real, working default without every
caller having to hand-assemble the industry taxonomy stack themselves.

No new comparison, scoring, or peer-eligibility algorithm is introduced here:
every class instantiated below already exists and is fully covered by tests
in ``packages/comparison`` and ``packages/industry``. This module only wires
those existing pieces together (composition-root responsibility), following
the exact construction sequence already used by
``packages/comparison/tests/test_comparison.py::_engine``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from comparison import QualitativeComparisonEngine

__all__ = ["build_default_comparison_engine"]


def build_default_comparison_engine() -> QualitativeComparisonEngine:
    """Build the platform's default ``QualitativeComparisonEngine``.

    The engine is seeded with the platform's illustrative industry taxonomy,
    peer-eligibility policies, and instrument-industry bindings via
    ``industry.seed_peer_eligibility_context`` — the same reference dataset
    shipped with the ``industry`` package (commercial banking, electric
    utilities, premium consumer franchise, software, and NBFC industries).

    Instruments outside that seeded universe are not silently compared: the
    ``PeerEligibilityEvaluator`` reports them as excluded/not-comparable
    rather than fabricating an eligibility decision, exactly as it does for
    unassigned symbols in the existing test suite.

    Returns:
        A fully wired, ready-to-use ``QualitativeComparisonEngine``.
    """
    from comparison import QualitativeComparisonEngine
    from industry import (
        IndustryMethodologyRegistry,
        IndustryTaxonomy,
        InstrumentIndustryRegistry,
        InvestmentCharacteristicsRegistry,
        PeerEligibilityEvaluator,
        PeerEligibilityPolicyRegistry,
        seed_peer_eligibility_context,
    )

    taxonomy = IndustryTaxonomy()
    characteristics = InvestmentCharacteristicsRegistry()
    methodologies = IndustryMethodologyRegistry(taxonomy, characteristics)
    policies = PeerEligibilityPolicyRegistry(taxonomy)
    assignments = InstrumentIndustryRegistry(taxonomy)
    seed_peer_eligibility_context(
        taxonomy, characteristics, methodologies, policies, assignments
    )
    evaluator = PeerEligibilityEvaluator(
        assignments=assignments,
        methodologies=methodologies,
        policies=policies,
    )
    return QualitativeComparisonEngine(evaluator=evaluator, methodologies=methodologies)
