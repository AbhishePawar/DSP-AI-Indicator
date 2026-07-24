"""Thin application service composing the official analysis pipeline."""

from __future__ import annotations

from ai_committee import (
    CommitteeError,
    CommitteeInput,
    CommitteeMember,
    CommitteeReport,
    EconomicMember,
    FundamentalMember,
    InvestmentCommittee,
    TechnicalMember,
    ValuationMember,
)
from contracts import Recommendation
from data_engine import (
    DataEngineError,
    FundamentalsRequest,
    MarketDataService,
    PriceSeriesRequest,
)
from dsp import AnalysisResult, IndicatorEngine, IndicatorError
from economic import EconomicAssessment, EconomicEngine, EconomicError
from fundamental import CompanyAnalysis, FinancialSnapshot, FundamentalEngine, FundamentalError
from orchestration.committee_mapping import (
    to_economic_context,
    to_fundamental_context,
    to_technical_context,
    to_valuation_context,
)
from orchestration.exceptions import OrchestrationError
from orchestration.market import resolve_market_snapshot
from orchestration.models import AnalysisRequest
from recommendation import RecommendationMapper, RecommendationMappingError
from snapshot_bridge import (
    EconomicBridgeService,
    FinancialBridgeService,
    SnapshotBridgeError,
)
from valuation import ValuationAssessment, ValuationEngine, ValuationError

__all__ = ["InvestmentAnalysisService"]


class InvestmentAnalysisService:
    """Official end-to-end investment analysis orchestrator.

    Coordinates Data Engine services, snapshot bridges, analytical
    engines, and the Investment Committee. Contains no indicator math,
    financial scoring, economic classification, valuation formulas,
    voting logic, or provider parsing — only sequencing and error
    translation.
    """

    def __init__(
        self,
        *,
        market_data: MarketDataService,
        financial_bridge: FinancialBridgeService,
        economic_bridge: EconomicBridgeService,
        indicator_engine: IndicatorEngine | None = None,
        fundamental_engine: FundamentalEngine | None = None,
        economic_engine: EconomicEngine | None = None,
        valuation_engine: ValuationEngine | None = None,
        committee: InvestmentCommittee | None = None,
    ) -> None:
        """Wire collaborators for the pipeline.

        Args:
            market_data: Price-series Data Engine service.
            financial_bridge: Fundamentals fetch + ``FinancialSnapshot``.
            economic_bridge: Economic fetch + ``EconomicSnapshot``.
            indicator_engine: DSP engine (default: new ``IndicatorEngine``).
            fundamental_engine: Fundamental engine (default: new instance).
            economic_engine: Economic engine (default: new instance).
            valuation_engine: Valuation engine (default: new instance).
            committee: Optional fixed committee. When omitted, members are
                composed from successfully produced analyses (Technical
                always; Fundamental/Economic/Valuation when available).
        """
        self._market_data = market_data
        self._financial_bridge = financial_bridge
        self._economic_bridge = economic_bridge
        self._indicator_engine = indicator_engine or IndicatorEngine()
        self._fundamental_engine = fundamental_engine or FundamentalEngine()
        self._economic_engine = economic_engine or EconomicEngine()
        self._valuation_engine = valuation_engine or ValuationEngine()
        self._committee = committee

    def analyze(self, request: AnalysisRequest) -> CommitteeReport:
        """Run the official pipeline and return a committee report.

        Args:
            request: Analysis parameters for one instrument.

        Returns:
            ``CommitteeReport`` from the Investment Committee.

        Raises:
            OrchestrationError: On mandatory-stage failure, or optional
                stage failure when ``allow_partial`` is ``False``.
        """
        technical = self._run_technical(request)
        financial_snapshot = self._fetch_financial_snapshot(request)
        fundamental = self._run_fundamental(request, financial_snapshot)
        economic = self._run_economic(request)
        valuation = self._run_valuation(request, financial_snapshot)

        context = CommitteeInput(
            instrument=request.instrument,
            technical=to_technical_context(technical),
            fundamental=(
                to_fundamental_context(fundamental)
                if fundamental is not None
                else None
            ),
            economic=(
                to_economic_context(economic) if economic is not None else None
            ),
            valuation=(
                to_valuation_context(valuation)
                if valuation is not None
                else None
            ),
        )
        committee = self._resolve_committee(context)
        try:
            return committee.deliberate(context)
        except CommitteeError as exc:
            msg = f"committee deliberation failed: {exc}"
            raise OrchestrationError(msg) from exc
        except Exception as exc:
            msg = f"unexpected committee failure: {exc}"
            raise OrchestrationError(msg) from exc

    def analyze_recommendation(self, request: AnalysisRequest) -> Recommendation:
        """Run the pipeline and map the report to ``contracts.Recommendation``.

        Thin convenience over :meth:`analyze` +
        :class:`~recommendation.RecommendationMapper` — no extra analysis.
        """
        report = self.analyze(request)
        try:
            return RecommendationMapper.map(report)
        except RecommendationMappingError as exc:
            msg = f"recommendation mapping failed: {exc}"
            raise OrchestrationError(msg) from exc

    def _run_technical(self, request: AnalysisRequest) -> AnalysisResult:
        try:
            price_series = self._market_data.get_price_series(
                PriceSeriesRequest(
                    instrument=request.instrument,
                    start=request.start,
                    end=request.end,
                    frequency=request.market_frequency,
                    provider_name=request.market_provider,
                )
            )
            return self._indicator_engine.analyze(price_series)
        except (DataEngineError, IndicatorError, OrchestrationError) as exc:
            msg = (
                f"technical analysis failed for "
                f"'{request.instrument.symbol}': {exc}"
            )
            raise OrchestrationError(msg) from exc
        except Exception as exc:
            msg = (
                f"unexpected technical failure for "
                f"'{request.instrument.symbol}': {exc}"
            )
            raise OrchestrationError(msg) from exc

    def _fetch_financial_snapshot(
        self, request: AnalysisRequest
    ) -> FinancialSnapshot | None:
        """Fetch once for fundamental and/or valuation stages."""
        if not request.include_fundamentals and not request.include_valuation:
            return None
        try:
            return self._financial_bridge.get_snapshot(
                FundamentalsRequest(
                    instrument=request.instrument,
                    period_type=request.statement_period,
                    limit=request.fundamentals_limit,
                    provider_name=request.fundamentals_provider,
                )
            )
        except (
            DataEngineError,
            SnapshotBridgeError,
            OrchestrationError,
        ) as exc:
            if request.allow_partial:
                return None
            msg = (
                f"financial snapshot failed for "
                f"'{request.instrument.symbol}': {exc}"
            )
            raise OrchestrationError(msg) from exc
        except Exception as exc:
            if request.allow_partial:
                return None
            msg = (
                f"unexpected financial snapshot failure for "
                f"'{request.instrument.symbol}': {exc}"
            )
            raise OrchestrationError(msg) from exc

    def _run_fundamental(
        self,
        request: AnalysisRequest,
        snapshot: FinancialSnapshot | None,
    ) -> CompanyAnalysis | None:
        if not request.include_fundamentals:
            return None
        if snapshot is None:
            return None
        try:
            return self._fundamental_engine.analyze(snapshot)
        except (FundamentalError, OrchestrationError) as exc:
            if request.allow_partial:
                return None
            msg = (
                f"fundamental analysis failed for "
                f"'{request.instrument.symbol}': {exc}"
            )
            raise OrchestrationError(msg) from exc
        except Exception as exc:
            if request.allow_partial:
                return None
            msg = (
                f"unexpected fundamental failure for "
                f"'{request.instrument.symbol}': {exc}"
            )
            raise OrchestrationError(msg) from exc

    def _run_economic(
        self, request: AnalysisRequest
    ) -> EconomicAssessment | None:
        if not request.include_economic:
            return None
        try:
            snapshot = self._economic_bridge.get_snapshot(
                country=request.economic_country,
                as_of=request.end,
                provider_name=request.economic_provider,
            )
            return self._economic_engine.analyze(snapshot)
        except (
            DataEngineError,
            SnapshotBridgeError,
            EconomicError,
            OrchestrationError,
        ) as exc:
            if request.allow_partial:
                return None
            msg = (
                f"economic analysis failed for "
                f"'{request.instrument.symbol}': {exc}"
            )
            raise OrchestrationError(msg) from exc
        except Exception as exc:
            if request.allow_partial:
                return None
            msg = (
                f"unexpected economic failure for "
                f"'{request.instrument.symbol}': {exc}"
            )
            raise OrchestrationError(msg) from exc

    def _run_valuation(
        self,
        request: AnalysisRequest,
        snapshot: FinancialSnapshot | None,
    ) -> ValuationAssessment | None:
        if not request.include_valuation:
            return None
        if snapshot is None:
            return None
        try:
            market = resolve_market_snapshot(request, snapshot)
            return self._valuation_engine.analyze(snapshot, market)
        except (ValuationError, OrchestrationError) as exc:
            if request.allow_partial:
                return None
            msg = (
                f"valuation analysis failed for "
                f"'{request.instrument.symbol}': {exc}"
            )
            raise OrchestrationError(msg) from exc
        except Exception as exc:
            if request.allow_partial:
                return None
            msg = (
                f"unexpected valuation failure for "
                f"'{request.instrument.symbol}': {exc}"
            )
            raise OrchestrationError(msg) from exc

    def _resolve_committee(self, context: CommitteeInput) -> InvestmentCommittee:
        if self._committee is not None:
            return self._committee

        members: list[CommitteeMember] = [TechnicalMember()]
        if context.fundamental is not None:
            members.append(FundamentalMember())
        if context.economic is not None:
            members.append(EconomicMember())
        if context.valuation is not None:
            members.append(ValuationMember())
        return InvestmentCommittee(members=tuple(members))
