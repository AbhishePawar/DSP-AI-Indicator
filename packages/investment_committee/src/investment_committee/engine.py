"""Public Investment Committee engine (FEATURE-008 Phase 1).

Distinct from frozen G-era ``ai_committee.InvestmentCommittee``.
"""

from __future__ import annotations

from business_quality_aggregator import BusinessQualityAggregation
from earnings_quality import EarningsQualityAnalysis
from economic_moat import EconomicAnalysis
from financial_strength import FinancialStrengthAnalysis
from growth_quality import GrowthQualityAnalysis
from investment_recommendation import InvestmentRecommendation, ValuationSignals
from management_quality import ManagementAnalysis
from valuation import OverallValuationResult

from investment_committee.consensus import build_consensus
from investment_committee.exceptions import InvestmentCommitteeValidationError
from investment_committee.explainability import (
    RESEARCH_DISCLAIMER,
    build_explainability,
    build_summary,
    build_thesis,
)
from investment_committee.metadata import (
    COMMITTEE_VERSION,
    FRAMEWORK_VERSION,
    InvestmentCommitteeMetadata,
)
from investment_committee.models import (
    CommitteeExplainability,
    CommitteeScore,
    CommitteeValidationSummary,
    InvestmentCommitteeResult,
)
from investment_committee.reviewers import evaluate_all_reviewers
from investment_committee.signals import build_signals
from investment_committee.validation import validate_framework_inputs

__all__ = ["InvestmentCommitteeEngine"]


class InvestmentCommitteeEngine:
    """Deterministic multi-reviewer consensus over public domain outputs."""

    @property
    def version(self) -> str:
        return COMMITTEE_VERSION

    @property
    def framework_version(self) -> str:
        return FRAMEWORK_VERSION

    def validate(
        self,
        *,
        recommendation: object | None = None,
        business_quality: object | None = None,
        economic_moat: object | None = None,
        management_quality: object | None = None,
        financial_strength: object | None = None,
        earnings_quality: object | None = None,
        growth_quality: object | None = None,
        valuation: object | None = None,
        metadata: object | None = None,
    ) -> CommitteeValidationSummary:
        effective_metadata = metadata if metadata is not None else self._metadata()
        return validate_framework_inputs(
            recommendation=recommendation,
            business_quality=business_quality,
            economic_moat=economic_moat,
            management_quality=management_quality,
            financial_strength=financial_strength,
            earnings_quality=earnings_quality,
            growth_quality=growth_quality,
            valuation=valuation,
            metadata=effective_metadata,
        )

    def analyze(
        self,
        *,
        recommendation: InvestmentRecommendation,
        business_quality: BusinessQualityAggregation,
        economic_moat: EconomicAnalysis,
        management_quality: ManagementAnalysis,
        financial_strength: FinancialStrengthAnalysis,
        earnings_quality: EarningsQualityAnalysis,
        growth_quality: GrowthQualityAnalysis,
        valuation: OverallValuationResult | ValuationSignals,
        metadata: InvestmentCommitteeMetadata | None = None,
    ) -> InvestmentCommitteeResult:
        effective_metadata = metadata if metadata is not None else self._metadata()
        validation = self.validate(
            recommendation=recommendation,
            business_quality=business_quality,
            economic_moat=economic_moat,
            management_quality=management_quality,
            financial_strength=financial_strength,
            earnings_quality=earnings_quality,
            growth_quality=growth_quality,
            valuation=valuation,
            metadata=effective_metadata,
        )
        if not validation.ok:
            raise InvestmentCommitteeValidationError("; ".join(validation.errors))

        signals = build_signals(
            recommendation=recommendation,
            business_quality=business_quality,
            economic_moat=economic_moat,
            management_quality=management_quality,
            financial_strength=financial_strength,
            earnings_quality=earnings_quality,
            growth_quality=growth_quality,
            valuation=valuation,
        )
        reviewers = evaluate_all_reviewers(signals)
        consensus = build_consensus(reviewers, signals)
        decision = consensus.decision
        explainability = build_explainability(
            effective_metadata, reviewers, consensus, decision
        )
        scored = [r.score.value for r in reviewers if r.score.value is not None]
        overall = None if not scored else round(sum(scored) / len(scored), 4)
        score = (
            CommitteeScore(value=None, status="insufficient_data")
            if overall is None
            else CommitteeScore(value=overall, status="assessed")
        )
        return InvestmentCommitteeResult(
            metadata=effective_metadata,
            validation=validation,
            reviewers=reviewers,
            consensus=consensus,
            score=score,
            decision=decision,
            confidence=consensus.consensus_confidence,
            evidence=explainability.evidence,
            explainability=explainability,
            final_investment_thesis=build_thesis(decision, consensus, reviewers),
            decision_summary=build_summary(decision, consensus, reviewers),
            research_disclaimer=RESEARCH_DISCLAIMER,
        )

    def explain(
        self, result: InvestmentCommitteeResult
    ) -> CommitteeExplainability:
        if not isinstance(result, InvestmentCommitteeResult):
            raise InvestmentCommitteeValidationError(
                "Accept ONLY InvestmentCommitteeResult, "
                f"got {type(result).__name__}"
            )
        return result.explainability

    def _metadata(self) -> InvestmentCommitteeMetadata:
        return InvestmentCommitteeMetadata(engine_version=self.version)
