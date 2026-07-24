"""Universe integration — eligibility-gated qualitative comparison."""

from __future__ import annotations

from industry import EligibilityOptions, EvidenceBundle
from universe import MultiStockDecisionResult

from comparison.engine import QualitativeComparisonEngine
from comparison.exceptions import ComparisonError
from comparison.models import ComparisonRequest, ComparisonResult

__all__ = ["compare_universe_result"]


def compare_universe_result(
    engine: QualitativeComparisonEngine,
    result: MultiStockDecisionResult,
    *,
    eligibility_options: EligibilityOptions | None = None,
    evidence_bundles: tuple[EvidenceBundle, ...] = (),
) -> ComparisonResult:
    """Compare successful DecisionPacks from a multi-stock universe run.

    Refuses when fewer than two packs succeeded. Does not invent packs for
    failures. Peer eligibility is applied inside the engine.

    Optional ``evidence_bundles`` enrich qualitative notes when supplied.
    """
    packs = result.packs
    if len(packs) < 2:
        msg = (
            "universe comparison requires at least two successful DecisionPacks; "
            f"got {len(packs)}"
        )
        raise ComparisonError(msg)
    return engine.compare(
        ComparisonRequest(
            packs=packs,
            eligibility_options=eligibility_options or EligibilityOptions(),
            evidence_bundles=evidence_bundles,
        )
    )
