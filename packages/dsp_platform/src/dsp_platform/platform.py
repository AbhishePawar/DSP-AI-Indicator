"""DSP Platform integration entry point (K1.0).

Orchestrates frozen public bounded-context APIs without containing business
logic, financial calculations, persistence, REST, or authentication.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any, Callable

from comparison import ComparisonResult, QualitativeComparisonEngine
from contracts import (
    BarFrequency,
    Instrument,
    Recommendation,
    StatementPeriodType,
)
from data_engine import InMemoryCache
from decision_intelligence import DecisionPack
from dsp_platform.config import FeatureFlags, PlatformConfig
from dsp_platform.configuration import PlatformConfiguration
from dsp_platform.lifecycle import PlatformLifecycle, PlatformStatus
from dsp_platform.platform_exceptions import (
    PlatformConfigurationError,
    PlatformError,
    PlatformLifecycleError,
    ServiceRegistryError,
)
from dsp_platform.service_registry import ServiceRegistry
from industry import EligibilityOptions, EvidenceBundle, EvidenceBundleReference
from orchestration import AnalysisRequest, InvestmentAnalysisService, OrchestrationError
from universe import MultiStockAnalysisRequest, MultiStockDecisionResult

__all__ = [
    "DSPPlatform",
    "PlatformBuilder",
    "PlatformMetadata",
    "PlatformResult",
]

# Peer comparisons fan out across multiple instruments' Decision Packs; a
# short-TTL cache avoids re-running eligibility + comparison for repeat
# requests (e.g. a Peers tab re-render) without risking stale results once
# any of the referenced Decision Pack reports are refreshed.
_COMPARISON_CACHE_TTL_SECONDS = 300.0

_PLATFORM_VERSION = "0.7.1"


@dataclass(frozen=True, slots=True)
class PlatformMetadata:
    """Immutable platform identity / capability metadata."""

    name: str
    version: str
    status: PlatformStatus
    environment: str
    capabilities: tuple[str, ...]
    registered_services: tuple[str, ...]
    generated_at: datetime
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "capabilities", tuple(self.capabilities))
        object.__setattr__(
            self, "registered_services", tuple(self.registered_services)
        )
        object.__setattr__(
            self,
            "notes",
            tuple(n.strip() for n in self.notes if n.strip()),
        )


@dataclass(frozen=True, slots=True)
class PlatformResult:
    """Immutable orchestration result envelope â€” no business conclusions."""

    ok: bool
    capability: str
    payload: Any
    metadata: PlatformMetadata
    limitations: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.capability.strip():
            msg = "capability must not be empty"
            raise PlatformError(msg)
        object.__setattr__(
            self,
            "limitations",
            tuple(n.strip() for n in self.limitations if n.strip()),
        )
        object.__setattr__(
            self,
            "errors",
            tuple(n.strip() for n in self.errors if n.strip()),
        )


class PlatformBuilder:
    """Composition helper for ``DSPPlatform`` â€” registration only."""

    def __init__(self) -> None:
        self._configuration: PlatformConfiguration | None = None
        self._analysis_service: InvestmentAnalysisService | None = None
        self._features: FeatureFlags | None = None
        self._registry = ServiceRegistry()
        self._lifecycle = PlatformLifecycle()
        self._auto_ready = True

    def with_configuration(
        self, configuration: PlatformConfiguration
    ) -> PlatformBuilder:
        """Bind immutable platform configuration."""
        self._configuration = configuration
        return self

    def with_platform_config(self, config: PlatformConfig) -> PlatformBuilder:
        """Bind legacy ``PlatformConfig`` projected into ``PlatformConfiguration``."""
        self._configuration = PlatformConfiguration.from_platform_config(config)
        return self

    def with_analysis_service(
        self, analysis_service: InvestmentAnalysisService
    ) -> PlatformBuilder:
        """Inject the frozen orchestration faÃ§ade."""
        self._analysis_service = analysis_service
        return self

    def with_features(self, features: FeatureFlags) -> PlatformBuilder:
        """Override default feature flags."""
        self._features = features
        return self

    def with_lifecycle(self, lifecycle: PlatformLifecycle) -> PlatformBuilder:
        """Inject a pre-built lifecycle controller."""
        self._lifecycle = lifecycle
        return self

    def with_registry(self, registry: ServiceRegistry) -> PlatformBuilder:
        """Inject a pre-built service registry."""
        self._registry = registry
        return self

    def register_service(
        self,
        name: str,
        service: Any,
        *,
        capability: str,
        version: str = "1.0.0",
        replace: bool = False,
    ) -> PlatformBuilder:
        """Register a dependency for capability discovery."""
        self._registry.register(
            name,
            service,
            capability=capability,
            version=version,
            replace=replace,
        )
        return self

    def auto_ready(self, enabled: bool = True) -> PlatformBuilder:
        """When True (default), ``build`` marks lifecycle READY."""
        self._auto_ready = enabled
        return self

    def build(self) -> DSPPlatform:
        """Construct an immutable-facing ``DSPPlatform`` orchestration root."""
        configuration = self._configuration or PlatformConfiguration()
        features = self._features or configuration.features
        if (
            configuration.require_analysis_service
            and self._analysis_service is None
        ):
            msg = "analysis_service is required when require_analysis_service=True"
            raise PlatformConfigurationError(msg)

        self._lifecycle.begin_initialize()
        if self._analysis_service is not None and not self._registry.has(
            "analysis_service"
        ):
            self._registry.register(
                "analysis_service",
                self._analysis_service,
                capability="analyze_company",
                version=_PLATFORM_VERSION,
            )

        platform = DSPPlatform(
            analysis_service=self._analysis_service,
            features=features,
            configuration=configuration,
            registry=self._registry,
            lifecycle=self._lifecycle,
        )
        if self._auto_ready:
            self._lifecycle.mark_ready(note="PlatformBuilder.build")
        return platform


class DSPPlatform:
    """Stable public entry point for all DSP bounded contexts.

    Orchestrates frozen public APIs only. Never performs financial analysis,
    valuation, recommendation synthesis, workflow implementation, persistence,
    authentication, or frontend concerns inside this type.
    """

    def __init__(
        self,
        *,
        analysis_service: InvestmentAnalysisService | None = None,
        features: FeatureFlags | None = None,
        configuration: PlatformConfiguration | None = None,
        registry: ServiceRegistry | None = None,
        lifecycle: PlatformLifecycle | None = None,
    ) -> None:
        """Create a platform faÃ§ade.

        Legacy callers may pass only ``analysis_service`` (and optional
        ``features``). K1.0 callers typically use :class:`PlatformBuilder`.
        """
        self._configuration = configuration or PlatformConfiguration(
            require_analysis_service=analysis_service is not None
        )
        self._features = features or self._configuration.features
        self._analysis = analysis_service
        self._registry = registry or ServiceRegistry()
        self._lifecycle = lifecycle or PlatformLifecycle(
            status=PlatformStatus.READY
            if analysis_service is not None
            else PlatformStatus.CREATED
        )
        if (
            analysis_service is not None
            and not self._registry.has("analysis_service")
        ):
            self._registry.register(
                "analysis_service",
                analysis_service,
                capability="analyze_company",
                version=_PLATFORM_VERSION,
            )

    @classmethod
    def from_config(cls, config: PlatformConfig) -> DSPPlatform:
        """Composition-root constructor from immutable configuration.

        Args:
            config: Provider, cache, timeout, feature, and secret settings.

        Returns:
            A ready-to-use ``DSPPlatform``.

        Raises:
            PlatformError: If wiring fails (e.g. missing required secrets).
        """
        from dsp_platform.wiring import build_analysis_service

        service = build_analysis_service(config)
        configuration = PlatformConfiguration.from_platform_config(config)
        return (
            PlatformBuilder()
            .with_configuration(configuration)
            .with_analysis_service(service)
            .with_features(config.features)
            .build()
        )

    @classmethod
    def builder(cls) -> PlatformBuilder:
        """Return a fresh :class:`PlatformBuilder`."""
        return PlatformBuilder()

    @property
    def features(self) -> FeatureFlags:
        """Return the immutable default feature flags."""
        return self._features

    @property
    def configuration(self) -> PlatformConfiguration:
        """Return immutable platform configuration."""
        return self._configuration

    @property
    def registry(self) -> ServiceRegistry:
        """Return the service registry."""
        return self._registry

    @property
    def lifecycle(self) -> PlatformLifecycle:
        """Return the lifecycle controller."""
        return self._lifecycle

    @property
    def analysis_service(self) -> InvestmentAnalysisService:
        """Return the injected orchestrator (for health / readiness)."""
        if self._analysis is None:
            msg = "analysis service is not wired"
            raise PlatformError(msg)
        return self._analysis

    def make_request(
        self,
        instrument: Instrument,
        start: date,
        end: date,
        *,
        market_frequency: BarFrequency = BarFrequency.DAILY,
        statement_period: StatementPeriodType = StatementPeriodType.ANNUAL,
        fundamentals_limit: int | None = 4,
        economic_country: str = "US",
        include_fundamentals: bool | None = None,
        include_economic: bool | None = None,
        include_valuation: bool | None = None,
        allow_partial: bool | None = None,
        market_provider: str | None = None,
        fundamentals_provider: str | None = None,
        economic_provider: str | None = None,
    ) -> AnalysisRequest:
        """Build an ``AnalysisRequest`` applying platform feature defaults."""
        return AnalysisRequest(
            instrument=instrument,
            start=start,
            end=end,
            market_frequency=market_frequency,
            statement_period=statement_period,
            fundamentals_limit=fundamentals_limit,
            economic_country=economic_country,
            include_fundamentals=(
                self._features.include_fundamentals
                if include_fundamentals is None
                else include_fundamentals
            ),
            include_economic=(
                self._features.include_economic
                if include_economic is None
                else include_economic
            ),
            include_valuation=(
                self._features.include_valuation
                if include_valuation is None
                else include_valuation
            ),
            allow_partial=(
                self._features.allow_partial
                if allow_partial is None
                else allow_partial
            ),
            market_provider=market_provider,
            fundamentals_provider=fundamentals_provider,
            economic_provider=economic_provider,
        )

    def analyze(self, request: AnalysisRequest) -> Recommendation:
        """Run the official pipeline and return ``contracts.Recommendation``."""
        try:
            return self.analysis_service.analyze_recommendation(request)
        except OrchestrationError as exc:
            msg = f"platform analysis failed: {exc}"
            raise PlatformError(msg) from exc
        except Exception as exc:
            msg = f"unexpected platform failure: {exc}"
            raise PlatformError(msg) from exc

    def analyze_decision_pack(
        self,
        request: AnalysisRequest,
        *,
        evidence_bundle_ref: EvidenceBundleReference | None = None,
    ) -> DecisionPack:
        """Run the pipeline and return the investor-facing Decision Pack."""
        try:
            from decision_intelligence import DecisionIntelligenceService
            from recommendation import RecommendationMapper

            report = self.analysis_service.analyze(request)
            recommendation = RecommendationMapper.map(report)
            return DecisionIntelligenceService().build_pack(
                report,
                recommendation,
                evidence_bundle_ref=evidence_bundle_ref,
            )
        except OrchestrationError as exc:
            msg = f"platform decision pack failed: {exc}"
            raise PlatformError(msg) from exc
        except Exception as exc:
            msg = f"unexpected decision pack failure: {exc}"
            raise PlatformError(msg) from exc

    def analyze_universe(
        self, request: MultiStockAnalysisRequest
    ) -> MultiStockDecisionResult:
        """Analyze every instrument in a universe via Decision Packs."""
        from universe import MultiStockAnalysisService

        def _analyze_one(instrument: Instrument) -> DecisionPack:
            single = self.make_request(
                instrument,
                request.start,
                request.end,
            )
            return self.analyze_decision_pack(single)

        try:
            return MultiStockAnalysisService(_analyze_one).analyze(request)
        except Exception as exc:
            msg = f"universe analysis failed: {exc}"
            raise PlatformError(msg) from exc

    def compare_universe(
        self,
        result: MultiStockDecisionResult,
        *,
        engine: QualitativeComparisonEngine | None = None,
        eligibility_options: EligibilityOptions | None = None,
        evidence_bundles: tuple[EvidenceBundle, ...] = (),
    ) -> ComparisonResult:
        """Qualitative comparison of universe DecisionPacks.

        ``engine`` defaults to the platform's shared comparison engine (see
        :meth:`_default_comparison_engine`) when not supplied.
        """
        from comparison import compare_universe_result

        try:
            return compare_universe_result(
                engine or self._default_comparison_engine(),
                result,
                eligibility_options=eligibility_options,
                evidence_bundles=evidence_bundles,
            )
        except Exception as exc:
            msg = f"universe comparison failed: {exc}"
            raise PlatformError(msg) from exc

    # --- K1.0 public orchestration methods ---------------------------------

    def analyze_company(
        self,
        request: AnalysisRequest,
        *,
        as_decision_pack: bool = True,
        evidence_bundle_ref: EvidenceBundleReference | None = None,
    ) -> PlatformResult:
        """Orchestrate single-company analysis via frozen public APIs."""
        self._require_capability("analyze_company")
        try:
            payload: Any
            if as_decision_pack:
                payload = self.analyze_decision_pack(
                    request, evidence_bundle_ref=evidence_bundle_ref
                )
            else:
                payload = self.analyze(request)
            return self._ok_result("analyze_company", payload)
        except PlatformError as exc:
            return self._err_result("analyze_company", exc)

    def compare_companies(
        self,
        packs: tuple[DecisionPack, ...] | list[DecisionPack],
        *,
        engine: QualitativeComparisonEngine | None = None,
        eligibility_options: EligibilityOptions | None = None,
        evidence_bundles: tuple[EvidenceBundle, ...] = (),
    ) -> PlatformResult:
        """Orchestrate multi-company comparison via frozen comparison APIs.

        When ``engine`` is not supplied, resolves (and caches on this
        platform instance) the default ``QualitativeComparisonEngine`` built
        by :meth:`_default_comparison_engine` — no caller has to hand-wire
        ``comparison``/``industry`` themselves for the common case. Pass a
        custom ``engine`` to compare against a different industry taxonomy.

        Results for the default engine (no ``evidence_bundles``, which are
        not part of the cache key) are cached for a short TTL — see
        :data:`_COMPARISON_CACHE_TTL_SECONDS` — using the existing
        ``data_engine.cache.InMemoryCache`` port, keyed by the compared
        symbols and eligibility options. No new cache mechanism is introduced.
        """
        self._require_capability("compare_companies")
        cache_key = None
        if engine is None and not evidence_bundles:
            cache_key = self._comparison_cache_key(packs, eligibility_options)

        cache = self._comparison_cache() if cache_key is not None else None
        if cache is not None:
            cached = cache.get(cache_key)
            if cached is not None:
                return self._ok_result(
                    "compare_companies",
                    cached,
                    limitations=(
                        "comparison served from short-TTL cache "
                        f"(<= {int(_COMPARISON_CACHE_TTL_SECONDS)}s old)",
                    ),
                )

        try:
            payload = (engine or self._default_comparison_engine()).compare_packs(
                packs,
                eligibility_options=eligibility_options,
                evidence_bundles=evidence_bundles,
            )
            if cache is not None:
                cache.set(cache_key, payload, ttl_seconds=_COMPARISON_CACHE_TTL_SECONDS)
            return self._ok_result("compare_companies", payload)
        except Exception as exc:
            return self._err_result(
                "compare_companies",
                PlatformError(f"compare_companies failed: {exc}"),
            )

    @staticmethod
    def _comparison_cache_key(
        packs: tuple[DecisionPack, ...] | list[DecisionPack],
        eligibility_options: EligibilityOptions | None,
    ) -> tuple[Any, ...] | None:
        """Build a deterministic cache key, or ``None`` when uncacheable."""
        try:
            symbols = tuple(sorted(p.recommendation.instrument.symbol for p in packs))
        except Exception:  # noqa: BLE001 — malformed packs fail the real call, not caching
            return None
        options = eligibility_options or EligibilityOptions()
        return (symbols, options.allow_related, options.allow_limited)

    def _comparison_cache(self) -> InMemoryCache:
        """Resolve the platform's shared short-TTL comparison cache."""
        return self._resolve_service(
            "comparison_cache",
            InMemoryCache,
            capability="compare_companies",
        )

    def _default_comparison_engine(self) -> QualitativeComparisonEngine:
        """Resolve the platform's shared default comparison engine (cached)."""
        from dsp_platform.comparison_engine import build_default_comparison_engine

        return self._resolve_service(
            "comparison_engine",
            build_default_comparison_engine,
            capability="compare_companies",
        )

    def run_workflow(self, context: Any) -> PlatformResult:
        """Orchestrate workflow execution via frozen WorkflowEngine API.

        ``context`` must be a workflow ``EngineContext`` (with faÃ§ade port).
        """
        self._require_capability("run_workflow")
        try:
            from workflow import WorkflowEngine, WorkflowError

            engine = self._resolve_service(
                "workflow_engine", WorkflowEngine, capability="run_workflow"
            )
            payload = engine.run(context)
            return self._ok_result("run_workflow", payload)
        except PlatformError as exc:
            return self._err_result("run_workflow", exc)
        except Exception as exc:
            from workflow import WorkflowError

            if isinstance(exc, WorkflowError):
                return self._err_result(
                    "run_workflow", PlatformError(f"run_workflow failed: {exc}")
                )
            return self._err_result(
                "run_workflow",
                PlatformError(f"run_workflow failed: {exc}"),
            )

    def build_knowledge_graph(self, context: Any) -> PlatformResult:
        """Orchestrate Knowledge Graph synthesis via frozen public APIs."""
        self._require_capability("build_knowledge_graph")
        try:
            from knowledge_graph import (
                KnowledgeGraphAssembler,
                KnowledgeGraphEngine,
                KnowledgeGraphError,
            )

            if hasattr(context, "recommendation_refs") and hasattr(
                context, "workflow_refs"
            ):
                assembler = self._resolve_service(
                    "knowledge_graph_assembler",
                    KnowledgeGraphAssembler,
                    capability="build_knowledge_graph",
                )
                assembly = assembler.assemble(context)
                engine = self._resolve_service(
                    "knowledge_graph_engine",
                    KnowledgeGraphEngine,
                    capability="build_knowledge_graph",
                )
                payload = engine.synthesize(assembly)
            else:
                engine = self._resolve_service(
                    "knowledge_graph_engine",
                    KnowledgeGraphEngine,
                    capability="build_knowledge_graph",
                )
                payload = engine.synthesize(context)
            return self._ok_result("build_knowledge_graph", payload)
        except PlatformError as exc:
            return self._err_result("build_knowledge_graph", exc)
        except Exception as exc:
            return self._err_result(
                "build_knowledge_graph",
                PlatformError(f"build_knowledge_graph failed: {exc}"),
            )

    def ask_copilot(
        self,
        conversation_context: Any,
        *,
        language_model: Any | None = None,
        metadata: Any | None = None,
    ) -> PlatformResult:
        """Orchestrate Conversation â†’ Explanation â†’ Reporter via frozen APIs."""
        self._require_capability("ask_copilot")
        try:
            from copilot import (
                ConversationEngine,
                CopilotReporter,
                ExplanationEngine,
                ReportingContext,
            )

            conversation = self._resolve_service(
                "conversation_engine",
                ConversationEngine,
                capability="ask_copilot",
            )
            conversation_result = conversation.run(conversation_context)
            explanation = ExplanationEngine(language_model=language_model)
            explanation_result = explanation.explain(
                conversation_result.explanation_input
            )
            reporter = self._resolve_service(
                "copilot_reporter",
                CopilotReporter,
                capability="ask_copilot",
            )
            payload = reporter.report(
                ReportingContext(
                    explanation_result=explanation_result,
                    explanation_input=conversation_result.explanation_input,
                    metadata=metadata,
                )
            )
            return self._ok_result("ask_copilot", payload)
        except PlatformError as exc:
            return self._err_result("ask_copilot", exc)
        except Exception as exc:
            return self._err_result(
                "ask_copilot",
                PlatformError(f"ask_copilot failed: {exc}"),
            )

    def export_report(
        self,
        report: Any,
        *,
        format_name: str = "native",
        limitations: tuple[str, ...] = (),
    ) -> PlatformResult:
        """Export an immutable report envelope â€” presentation only.

        Does not mutate ``report``. ``format_name`` is descriptive metadata
        for channel adapters (REST / UI / CLI); no serialization engine lives
        in the domain platform core.
        """
        self._require_capability("export_report")
        if report is None:
            return self._err_result(
                "export_report",
                PlatformError("export_report requires a report payload"),
            )
        note = f"format={format_name.strip() or 'native'}"
        return self._ok_result(
            "export_report",
            {
                "format": format_name.strip() or "native",
                "report": report,
            },
            limitations=(note, *limitations),
        )

    def compose_intelligence(
        self,
        request: Any,
    ) -> PlatformResult:
        """EPIC-001: run the internal FEATURE composition pipeline.

        Orchestrates public package engines only â€” no score/recommendation
        overrides. Does not modify ``/api/v1``.
        """
        from dsp_platform.composition import (
            CompositionRequest,
            PlatformOrchestrator,
        )

        if not isinstance(request, CompositionRequest):
            return self._err_result(
                "compose_intelligence",
                PlatformError(
                    "compose_intelligence requires CompositionRequest, "
                    f"got {type(request).__name__}"
                ),
            )
        try:
            if self._lifecycle.status == PlatformStatus.CREATED:
                self._lifecycle.begin_initialize()
                self._lifecycle.mark_ready(note="compose_intelligence")
            orchestrator = PlatformOrchestrator(
                platform_version=_PLATFORM_VERSION
            )
            pipeline_result = orchestrator.execute(request)
            return PlatformResult(
                ok=pipeline_result.ok,
                capability="compose_intelligence",
                payload=pipeline_result,
                metadata=self._metadata(),
                limitations=pipeline_result.limitations,
                errors=pipeline_result.errors,
            )
        except Exception as exc:  # noqa: BLE001
            return self._err_result("compose_intelligence", PlatformError(str(exc)))

    def research_intelligence_schema(self) -> dict[str, object]:
        """Research Intelligence schema descriptor (EPIC-011B)."""
        from dsp_platform.research_intelligence_facade import research_intelligence_schema

        return research_intelligence_schema()

    def capture_research_intelligence_snapshot(
        self,
        payload: dict[str, object],
        *,
        research_id: str | None = None,
        timestamp: str | None = None,
        ticker: str | None = None,
        company: str | None = None,
        exchange: str | None = None,
        research_version: str | None = None,
        model_version: str | None = None,
        allow_duplicate: bool = False,
    ) -> dict[str, object]:
        """Capture immutable research snapshot after analysis (EPIC-011B)."""
        from dsp_platform.research_intelligence_facade import (
            capture_canonical_research_snapshot,
        )

        return capture_canonical_research_snapshot(
            payload,
            research_id=research_id,
            timestamp=timestamp,
            ticker=ticker,
            company=company,
            exchange=exchange,
            research_version=research_version,
            model_version=model_version,
            allow_duplicate=allow_duplicate,
        )

    def research_intelligence_list_snapshots(
        self,
        *,
        symbol: str | None = None,
        company: str | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> dict[str, object]:
        from dsp_platform.research_intelligence_facade import (
            research_intelligence_list_snapshots,
        )

        return research_intelligence_list_snapshots(
            symbol=symbol, company=company, limit=limit, offset=offset
        )

    def research_intelligence_timeline(
        self,
        *,
        symbol: str | None = None,
        company: str | None = None,
        limit: int | None = 100,
        offset: int = 0,
    ) -> dict[str, object]:
        from dsp_platform.research_intelligence_facade import (
            research_intelligence_timeline,
        )

        return research_intelligence_timeline(
            symbol=symbol, company=company, limit=limit, offset=offset
        )

    def research_intelligence_measure(
        self,
        *,
        research_id: str,
        window_months: int,
        price_at_horizon: float | None = None,
        iv_at_horizon: float | None = None,
        measured_at: str | None = None,
    ) -> dict[str, object]:
        from dsp_platform.research_intelligence_facade import (
            research_intelligence_measure,
        )

        return research_intelligence_measure(
            research_id=research_id,
            window_months=window_months,
            price_at_horizon=price_at_horizon,
            iv_at_horizon=iv_at_horizon,
            measured_at=measured_at,
        )

    def research_intelligence_measure_batch(
        self,
        *,
        window_months: int,
        horizon_prices: dict[str, float | None] | None = None,
        measured_at: str | None = None,
    ) -> dict[str, object]:
        from dsp_platform.research_intelligence_facade import (
            research_intelligence_measure_batch,
        )

        return research_intelligence_measure_batch(
            window_months=window_months,
            horizon_prices=horizon_prices,
            measured_at=measured_at,
        )

    def research_intelligence_calibration(
        self,
        *,
        window_months: int,
        horizon_prices: dict[str, float | None] | None = None,
        result_id: str | None = None,
        created_at: str | None = None,
        measured_at: str | None = None,
    ) -> dict[str, object]:
        from dsp_platform.research_intelligence_facade import (
            research_intelligence_calibration,
        )

        return research_intelligence_calibration(
            window_months=window_months,
            horizon_prices=horizon_prices,
            result_id=result_id,
            created_at=created_at,
            measured_at=measured_at,
        )

    def research_intelligence_performance(
        self,
        *,
        window_months: int,
        horizon_prices: dict[str, float | None] | None = None,
        result_id: str | None = None,
        created_at: str | None = None,
        measured_at: str | None = None,
    ) -> dict[str, object]:
        from dsp_platform.research_intelligence_facade import (
            research_intelligence_performance,
        )

        return research_intelligence_performance(
            window_months=window_months,
            horizon_prices=horizon_prices,
            result_id=result_id,
            created_at=created_at,
            measured_at=measured_at,
        )

    def research_intelligence_insights(
        self,
        *,
        window_months: int,
        horizon_prices: dict[str, float | None] | None = None,
        result_id: str | None = None,
        created_at: str | None = None,
        measured_at: str | None = None,
        top_n: int = 5,
    ) -> dict[str, object]:
        from dsp_platform.research_intelligence_facade import (
            research_intelligence_insights,
        )

        return research_intelligence_insights(
            window_months=window_months,
            horizon_prices=horizon_prices,
            result_id=result_id,
            created_at=created_at,
            measured_at=measured_at,
            top_n=top_n,
        )

    # -- Authenticated data gateways (EPIC-D001..D005) -----------------
    # Thin delegations to process-local façade services. Additive only —
    # never alter ``/analyse`` composition or perform calculations here.

    def get_authenticated_market_quote(
        self,
        symbol: str,
        *,
        exchange: str | None = None,
        currency: str = "USD",
    ) -> dict[str, object] | None:
        from dsp_platform.market_quotes import get_authenticated_market_quote

        return get_authenticated_market_quote(
            symbol, exchange=exchange, currency=currency
        )

    def market_quote_health(self) -> dict[str, object]:
        from dsp_platform.market_quotes import market_quote_health

        return market_quote_health()

    def get_authenticated_financial_statements(
        self,
        symbol: str,
        *,
        exchange: str | None = None,
        currency: str = "USD",
        period_type: str | None = None,
        limit: int = 8,
        include_restated: bool = True,
    ) -> dict[str, object] | None:
        from dsp_platform.financial_statements import (
            get_authenticated_financial_statements,
        )

        return get_authenticated_financial_statements(
            symbol,
            exchange=exchange,
            currency=currency,
            period_type=period_type,
            limit=limit,
            include_restated=include_restated,
        )

    def resolve_company_identity(
        self,
        symbol: str,
        *,
        exchange: str | None = None,
        currency: str = "USD",
    ) -> dict[str, object] | None:
        from dsp_platform.financial_statements import resolve_company_identity

        return resolve_company_identity(symbol, exchange=exchange, currency=currency)

    def financial_statement_health(self) -> dict[str, object]:
        from dsp_platform.financial_statements import financial_statement_health

        return financial_statement_health()

    def get_authenticated_historical_series(
        self,
        symbol: str,
        *,
        series_kind: str,
        exchange: str | None = None,
        currency: str = "USD",
        frequency: str | None = "daily",
        start_date: object | None = None,
        end_date: object | None = None,
        limit: int = 500,
    ) -> dict[str, object] | None:
        from dsp_platform.historical_series import get_authenticated_historical_series

        return get_authenticated_historical_series(
            symbol,
            series_kind=series_kind,
            exchange=exchange,
            currency=currency,
            frequency=frequency,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
        )

    def historical_series_health(self) -> dict[str, object]:
        from dsp_platform.historical_series import historical_series_health

        return historical_series_health()

    def get_authenticated_corporate_actions(
        self,
        symbol: str,
        *,
        exchange: str | None = None,
        currency: str = "USD",
        action_type: str | None = None,
        start_date: object | None = None,
        end_date: object | None = None,
        limit: int = 50,
    ) -> dict[str, object] | None:
        from dsp_platform.corporate_actions import get_authenticated_corporate_actions

        return get_authenticated_corporate_actions(
            symbol,
            exchange=exchange,
            currency=currency,
            action_type=action_type,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
        )

    def corporate_actions_health(self) -> dict[str, object]:
        from dsp_platform.corporate_actions import corporate_actions_health

        return corporate_actions_health()

    # -- Data Connector Framework: News/Filings/Ownership/Insider/ESG/
    # Transcripts. Thin delegations to process-local façade services, each
    # backed by a multi-provider priority registry with automatic failover
    # (see ``data_engine.connector_framework``). Additive only.

    def get_authenticated_news(
        self,
        symbol: str,
        *,
        exchange: str | None = None,
        currency: str = "USD",
        limit: int = 20,
        since: object | None = None,
    ) -> dict[str, object] | None:
        from dsp_platform.news import get_authenticated_news

        return get_authenticated_news(
            symbol, exchange=exchange, currency=currency, limit=limit, since=since
        )

    def news_health(self) -> dict[str, object]:
        from dsp_platform.news import news_health

        return news_health()

    def get_authenticated_filings(
        self,
        symbol: str,
        *,
        exchange: str | None = None,
        currency: str = "USD",
        filing_types: tuple[str, ...] = (),
        start_date: object | None = None,
        end_date: object | None = None,
        limit: int = 50,
    ) -> dict[str, object] | None:
        from dsp_platform.filings import get_authenticated_filings

        return get_authenticated_filings(
            symbol,
            exchange=exchange,
            currency=currency,
            filing_types=filing_types,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
        )

    def filings_health(self) -> dict[str, object]:
        from dsp_platform.filings import filings_health

        return filings_health()

    def get_authenticated_ownership(
        self,
        symbol: str,
        *,
        exchange: str | None = None,
        currency: str = "USD",
        as_of: object | None = None,
    ) -> dict[str, object] | None:
        from dsp_platform.ownership import get_authenticated_ownership

        return get_authenticated_ownership(
            symbol, exchange=exchange, currency=currency, as_of=as_of
        )

    def ownership_health(self) -> dict[str, object]:
        from dsp_platform.ownership import ownership_health

        return ownership_health()

    def get_authenticated_insider_activity(
        self,
        symbol: str,
        *,
        exchange: str | None = None,
        currency: str = "USD",
        start_date: object | None = None,
        end_date: object | None = None,
        limit: int = 50,
    ) -> dict[str, object] | None:
        from dsp_platform.insider_trading import get_authenticated_insider_activity

        return get_authenticated_insider_activity(
            symbol,
            exchange=exchange,
            currency=currency,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
        )

    def insider_trading_health(self) -> dict[str, object]:
        from dsp_platform.insider_trading import insider_trading_health

        return insider_trading_health()

    def get_authenticated_esg_score(
        self,
        symbol: str,
        *,
        exchange: str | None = None,
        currency: str = "USD",
    ) -> dict[str, object] | None:
        from dsp_platform.esg import get_authenticated_esg_score

        return get_authenticated_esg_score(symbol, exchange=exchange, currency=currency)

    def esg_health(self) -> dict[str, object]:
        from dsp_platform.esg import esg_health

        return esg_health()

    def get_authenticated_transcripts(
        self,
        symbol: str,
        *,
        exchange: str | None = None,
        currency: str = "USD",
        year: int | None = None,
        quarter: int | None = None,
        limit: int = 8,
    ) -> dict[str, object] | None:
        from dsp_platform.transcripts import get_authenticated_transcripts

        return get_authenticated_transcripts(
            symbol,
            exchange=exchange,
            currency=currency,
            year=year,
            quarter=quarter,
            limit=limit,
        )

    def transcripts_health(self) -> dict[str, object]:
        from dsp_platform.transcripts import transcripts_health

        return transcripts_health()

    def get_unified_data_bundle(
        self,
        symbol: str,
        *,
        exchange: str | None = None,
        currency: str = "USD",
        include_market_quote: bool = True,
        include_financial_statements: bool = True,
        include_corporate_actions: bool = True,
        include_historical_series: bool = True,
        historical_series_kind: str = "ohlcv",
        historical_frequency: str | None = "daily",
        historical_limit: int = 30,
        statement_limit: int = 8,
        corporate_actions_limit: int = 50,
    ) -> dict[str, object]:
        from dsp_platform.data_orchestrator import get_unified_data_bundle

        return get_unified_data_bundle(
            symbol,
            exchange=exchange,
            currency=currency,
            include_market_quote=include_market_quote,
            include_financial_statements=include_financial_statements,
            include_corporate_actions=include_corporate_actions,
            include_historical_series=include_historical_series,
            historical_series_kind=historical_series_kind,
            historical_frequency=historical_frequency,
            historical_limit=historical_limit,
            statement_limit=statement_limit,
            corporate_actions_limit=corporate_actions_limit,
        )

    def unified_data_health(self) -> dict[str, object]:
        from dsp_platform.data_orchestrator import unified_data_health

        return unified_data_health()

    # -- Research Object / Report / Export / Archive / Diff / Copilot --
    # (EPIC-R001..R005, EPIC-A001, EPIC-A004). Thin delegations to
    # process-local façade services — never recompute or re-score.

    def research_object_schema(self) -> dict[str, object]:
        from dsp_platform.research_object_facade import research_object_schema

        return research_object_schema()

    def build_research_object(
        self,
        symbol: str,
        *,
        data_bundle: dict[str, object] | None = None,
        analysis_payload: dict[str, object] | None = None,
        valuation_signals: dict[str, object] | None = None,
        company: str | None = None,
        exchange: str | None = None,
        correlation_id: str | None = None,
        fetch_data_bundle: bool = False,
    ) -> dict[str, object]:
        from dsp_platform.research_object_facade import build_canonical_research_object

        return build_canonical_research_object(
            symbol,
            data_bundle=data_bundle,
            analysis_payload=analysis_payload,
            valuation_signals=valuation_signals,
            company=company,
            exchange=exchange,
            correlation_id=correlation_id,
            fetch_data_bundle=fetch_data_bundle,
        )

    def institutional_report_schema(self) -> dict[str, object]:
        from dsp_platform.institutional_report_facade import institutional_report_schema

        return institutional_report_schema()

    def generate_institutional_report(
        self,
        research_object: dict[str, object],
        *,
        report_id: str | None = None,
        generated_at: str | None = None,
    ) -> dict[str, object]:
        from dsp_platform.institutional_report_facade import (
            generate_canonical_institutional_report,
        )

        return generate_canonical_institutional_report(
            research_object, report_id=report_id, generated_at=generated_at
        )

    def institutional_export_schema(self) -> dict[str, object]:
        from dsp_platform.institutional_export_facade import institutional_export_schema

        return institutional_export_schema()

    def export_institutional_report(
        self,
        report: dict[str, object],
        *,
        format: str = "json",
        export_id: str | None = None,
        exported_at: str | None = None,
    ) -> dict[str, object]:
        from dsp_platform.institutional_export_facade import (
            export_canonical_institutional_report,
        )

        return export_canonical_institutional_report(
            report, format=format, export_id=export_id, exported_at=exported_at
        )

    def research_archive_schema(self) -> dict[str, object]:
        from dsp_platform.research_archive_facade import research_archive_schema

        return research_archive_schema()

    def archive_research_snapshot(
        self,
        kind: str,
        payload: dict[str, object],
        *,
        lineage_id: str | None = None,
        parent_snapshot_id: str | None = None,
        snapshot_id: str | None = None,
        archived_at: str | None = None,
        provenance: dict[str, object] | None = None,
    ) -> dict[str, object]:
        from dsp_platform.research_archive_facade import archive_research_snapshot

        return archive_research_snapshot(
            kind,
            payload,
            lineage_id=lineage_id,
            parent_snapshot_id=parent_snapshot_id,
            snapshot_id=snapshot_id,
            archived_at=archived_at,
            provenance=provenance,
        )

    def get_research_snapshot(self, snapshot_id: str) -> dict[str, object]:
        from dsp_platform.research_archive_facade import get_research_snapshot

        return get_research_snapshot(snapshot_id)

    def list_research_version_history(self, lineage_id: str) -> list[dict[str, object]]:
        from dsp_platform.research_archive_facade import list_research_version_history

        return list_research_version_history(lineage_id)

    def compare_research_snapshots(
        self, left_snapshot_id: str, right_snapshot_id: str
    ) -> dict[str, object]:
        from dsp_platform.research_archive_facade import compare_research_snapshots

        return compare_research_snapshots(left_snapshot_id, right_snapshot_id)

    def evaluate_research_retention(self, snapshot_id: str) -> dict[str, object]:
        from dsp_platform.research_archive_facade import evaluate_research_retention

        return evaluate_research_retention(snapshot_id)

    def research_diff_schema(self) -> dict[str, object]:
        from dsp_platform.research_diff_facade import research_diff_schema

        return research_diff_schema()

    def diff_research_snapshots(
        self,
        left_snapshot_id: str,
        right_snapshot_id: str,
        *,
        diff_id: str | None = None,
        created_at: str | None = None,
    ) -> dict[str, object]:
        from dsp_platform.research_diff_facade import diff_canonical_research_snapshots

        return diff_canonical_research_snapshots(
            left_snapshot_id,
            right_snapshot_id,
            diff_id=diff_id,
            created_at=created_at,
        )

    def research_copilot_schema(self) -> dict[str, object]:
        from dsp_platform.research_copilot_facade import research_copilot_schema

        return research_copilot_schema()

    def ask_research_copilot(
        self,
        question: str,
        *,
        research_object: dict[str, object] | None = None,
        report: dict[str, object] | None = None,
        archive_snapshot: dict[str, object] | None = None,
        research_diff: dict[str, object] | None = None,
        snapshot_id: str | None = None,
        conversation_id: str | None = None,
        response_id: str | None = None,
        created_at: str | None = None,
    ) -> dict[str, object]:
        from dsp_platform.research_copilot_facade import ask_canonical_research_copilot

        return ask_canonical_research_copilot(
            question,
            research_object=research_object,
            report=report,
            archive_snapshot=archive_snapshot,
            research_diff=research_diff,
            snapshot_id=snapshot_id,
            conversation_id=conversation_id,
            response_id=response_id,
            created_at=created_at,
        )


    # -- Super Admin Control Center (RC1 Milestone 11) ------------------

    def control_center_schema(self) -> dict[str, object]:
        from dsp_platform.control_center import control_center_schema

        return control_center_schema()

    def run_control_center(
        self,
        action: str,
        *,
        api_state: object | None = None,
        payload: dict[str, object] | None = None,
    ) -> dict[str, object]:
        """Orchestrate configuration registry + façades — never execute engines."""
        from dsp_platform.control_center import run_control_center

        return run_control_center(
            action, platform=self, api_state=api_state, payload=payload
        )

    # -- Decision Workspace (EPIC-A004) ---------------------------------

    def decision_workspace_schema(self) -> dict[str, object]:
        from dsp_platform.decision_workspace_facade import decision_workspace_schema

        return decision_workspace_schema()

    def build_decision_workspace(
        self,
        *,
        kind: str,
        subject: str,
        research_object: dict[str, object] | None = None,
        report: dict[str, object] | None = None,
        reports: dict[str, object] | list[object] | None = None,
        snapshots: dict[str, object] | list[object] | None = None,
        diffs: dict[str, object] | list[object] | None = None,
        copilot_response: dict[str, object] | None = None,
        portfolio_intelligence: dict[str, object] | None = None,
        monitoring_result: dict[str, object] | None = None,
        workspace_id: str | None = None,
        created_at: str | None = None,
    ) -> dict[str, object]:
        from dsp_platform.decision_workspace_facade import (
            build_canonical_decision_workspace,
        )

        return build_canonical_decision_workspace(
            kind=kind,
            subject=subject,
            research_object=research_object,
            report=report,
            reports=reports,
            snapshots=snapshots,
            diffs=diffs,
            copilot_response=copilot_response,
            portfolio_intelligence=portfolio_intelligence,
            monitoring_result=monitoring_result,
            workspace_id=workspace_id,
            created_at=created_at,
        )

    # -- Research Monitoring (EPIC-A003) --------------------------------

    def research_monitoring_schema(self) -> dict[str, object]:
        from dsp_platform.research_monitoring_facade import research_monitoring_schema

        return research_monitoring_schema()

    def register_monitoring_watchlist(self, symbols: list[str]) -> list[str]:
        from dsp_platform.research_monitoring_facade import (
            register_monitoring_watchlist,
        )

        return register_monitoring_watchlist(symbols)

    def register_monitoring_portfolio(
        self, portfolio_id: str, *, metadata: dict[str, object] | None = None
    ) -> dict[str, object]:
        from dsp_platform.research_monitoring_facade import (
            register_monitoring_portfolio,
        )

        return register_monitoring_portfolio(portfolio_id, metadata=metadata)

    def track_monitoring_snapshot(
        self,
        subject: str,
        *,
        subject_kind: str = "symbol",
        baseline_snapshot_id: str | None = None,
        current_snapshot_id: str | None = None,
        tracked_at: str | None = None,
    ) -> dict[str, object]:
        from dsp_platform.research_monitoring_facade import track_monitoring_snapshot

        return track_monitoring_snapshot(
            subject,
            subject_kind=subject_kind,
            baseline_snapshot_id=baseline_snapshot_id,
            current_snapshot_id=current_snapshot_id,
            tracked_at=tracked_at,
        )

    def evaluate_research_monitoring(
        self,
        *,
        snapshot_pairs: dict[str, dict[str, str]] | None = None,
        portfolio_intelligence_baseline: dict[str, object] | None = None,
        portfolio_intelligence_current: dict[str, object] | None = None,
        portfolio_id: str | None = None,
        result_id: str | None = None,
        created_at: str | None = None,
        register_watchlist_symbols: list[str] | None = None,
    ) -> dict[str, object]:
        from dsp_platform.research_monitoring_facade import (
            evaluate_canonical_research_monitoring,
        )

        return evaluate_canonical_research_monitoring(
            snapshot_pairs=snapshot_pairs,
            portfolio_intelligence_baseline=portfolio_intelligence_baseline,
            portfolio_intelligence_current=portfolio_intelligence_current,
            portfolio_id=portfolio_id,
            result_id=result_id,
            created_at=created_at,
            register_watchlist_symbols=register_watchlist_symbols,
        )

    # -- Portfolio Intelligence (EPIC-A002) ------------------------------

    def portfolio_intelligence_schema(self) -> dict[str, object]:
        from dsp_platform.portfolio_intelligence_facade import (
            portfolio_intelligence_schema,
        )

        return portfolio_intelligence_schema()

    def evaluate_portfolio_intelligence(
        self,
        *,
        portfolio: dict[str, object] | None = None,
        watchlist: dict[str, object] | None = None,
        research_objects: dict[str, object] | list[object] | None = None,
        reports: dict[str, object] | list[object] | None = None,
        snapshots: dict[str, object] | list[object] | None = None,
        snapshot_ids: dict[str, str] | None = None,
        result_id: str | None = None,
        created_at: str | None = None,
    ) -> dict[str, object]:
        from dsp_platform.portfolio_intelligence_facade import (
            evaluate_canonical_portfolio_intelligence,
        )

        return evaluate_canonical_portfolio_intelligence(
            portfolio=portfolio,
            watchlist=watchlist,
            research_objects=research_objects,
            reports=reports,
            snapshots=snapshots,
            snapshot_ids=snapshot_ids,
            result_id=result_id,
            created_at=created_at,
        )

    # -- Institutional Multi-Agent Committee (EPIC-A005) -----------------

    def institutional_committee_schema(self) -> dict[str, object]:
        from dsp_platform.institutional_committee_facade import (
            institutional_committee_schema,
        )

        return institutional_committee_schema()

    def list_committee_agents(self) -> list[dict[str, str]]:
        from dsp_platform.institutional_committee_facade import list_committee_agents

        return list_committee_agents()

    def run_institutional_committee(
        self,
        *,
        subject: str,
        research_object: dict[str, object] | None = None,
        report: dict[str, object] | None = None,
        snapshots: dict[str, object] | list[object] | None = None,
        diffs: dict[str, object] | list[object] | None = None,
        copilot_response: dict[str, object] | None = None,
        portfolio_intelligence: dict[str, object] | None = None,
        monitoring_result: dict[str, object] | None = None,
        workspace: dict[str, object] | None = None,
        report_id: str | None = None,
        created_at: str | None = None,
    ) -> dict[str, object]:
        from dsp_platform.institutional_committee_facade import (
            run_canonical_institutional_committee,
        )

        return run_canonical_institutional_committee(
            subject=subject,
            research_object=research_object,
            report=report,
            snapshots=snapshots,
            diffs=diffs,
            copilot_response=copilot_response,
            portfolio_intelligence=portfolio_intelligence,
            monitoring_result=monitoring_result,
            workspace=workspace,
            report_id=report_id,
            created_at=created_at,
        )

    # -- Institutional Workflow & Approval (EPIC-A007) -------------------

    def institutional_workflow_schema(self) -> dict[str, object]:
        from dsp_platform.institutional_workflow_facade import (
            institutional_workflow_schema,
        )

        return institutional_workflow_schema()

    def list_workflow_templates(self) -> list[dict[str, object]]:
        from dsp_platform.institutional_workflow_facade import (
            list_canonical_workflow_templates,
        )

        return list_canonical_workflow_templates()

    def apply_institutional_workflow(
        self,
        *,
        action: str,
        subject: str | None = None,
        workflow_id: str | None = None,
        template_id: str | None = None,
        artifact_refs: dict[str, object] | None = None,
        reviewers: list[dict[str, object]] | None = None,
        to_stage: str | None = None,
        actor_id: str | None = None,
        author_id: str | None = None,
        body: str | None = None,
        reason: str | None = None,
        note: str | None = None,
        comment_id: str | None = None,
        approval_id: str | None = None,
        event_id: str | None = None,
        reviewer_id: str | None = None,
        role: str | None = None,
        display_name: str | None = None,
        metadata: dict[str, object] | None = None,
        result_id: str | None = None,
        created_at: str | None = None,
    ) -> dict[str, object]:
        from dsp_platform.institutional_workflow_facade import (
            apply_canonical_workflow_action,
        )

        return apply_canonical_workflow_action(
            action=action,
            subject=subject,
            workflow_id=workflow_id,
            template_id=template_id,
            artifact_refs=artifact_refs,
            reviewers=reviewers,
            to_stage=to_stage,
            actor_id=actor_id,
            author_id=author_id,
            body=body,
            reason=reason,
            note=note,
            comment_id=comment_id,
            approval_id=approval_id,
            event_id=event_id,
            reviewer_id=reviewer_id,
            role=role,
            display_name=display_name,
            metadata=metadata,
            result_id=result_id,
            created_at=created_at,
        )

    # -- Investment Policy & Compliance (EPIC-A006) ----------------------

    def investment_policy_schema(self) -> dict[str, object]:
        from dsp_platform.investment_policy_facade import investment_policy_schema

        return investment_policy_schema()

    def default_investment_policy(self) -> dict[str, object]:
        from dsp_platform.investment_policy_facade import (
            default_investment_policy_dict,
        )

        return default_investment_policy_dict()

    def evaluate_investment_policy(
        self,
        *,
        subject: str,
        policy: dict[str, object] | None = None,
        exceptions: list[dict[str, object]] | None = None,
        research_object: dict[str, object] | None = None,
        report: dict[str, object] | None = None,
        snapshots: dict[str, object] | list[object] | None = None,
        diffs: dict[str, object] | list[object] | None = None,
        portfolio_intelligence: dict[str, object] | None = None,
        monitoring_result: dict[str, object] | None = None,
        workspace: dict[str, object] | None = None,
        committee_report: dict[str, object] | None = None,
        result_id: str | None = None,
        created_at: str | None = None,
    ) -> dict[str, object]:
        from dsp_platform.investment_policy_facade import (
            evaluate_canonical_investment_policy,
        )

        return evaluate_canonical_investment_policy(
            subject=subject,
            policy=policy,
            exceptions=exceptions,
            research_object=research_object,
            report=report,
            snapshots=snapshots,
            diffs=diffs,
            portfolio_intelligence=portfolio_intelligence,
            monitoring_result=monitoring_result,
            workspace=workspace,
            committee_report=committee_report,
            result_id=result_id,
            created_at=created_at,
        )

    # -- Persistence support (EPIC-A008) ---------------------------------

    def persistence_schema(self) -> dict[str, object]:
        from dsp_platform.persistence_facade import persistence_schema

        return persistence_schema()

    def persist_entity(
        self,
        *,
        kind: str,
        payload: dict[str, object] | None = None,
        refs: dict[str, object] | None = None,
        provenance: dict[str, object] | None = None,
        entity_id: str | None = None,
        created_at: str | None = None,
        allow_update: bool = True,
    ) -> dict[str, object]:
        from dsp_platform.persistence_facade import persist_canonical_entity

        return persist_canonical_entity(
            kind=kind,
            payload=payload,
            refs=refs,
            provenance=provenance,
            entity_id=entity_id,
            created_at=created_at,
            allow_update=allow_update,
        )

    def get_persisted_entity(
        self, kind: str, entity_id: str
    ) -> dict[str, object] | None:
        from dsp_platform.persistence_facade import get_canonical_persisted_entity

        return get_canonical_persisted_entity(kind, entity_id)

    def persist_workflow_record(
        self,
        workflow: dict[str, object],
        *,
        entity_id: str | None = None,
        created_at: str | None = None,
    ) -> dict[str, object]:
        from dsp_platform.persistence_facade import persist_canonical_workflow_record

        return persist_canonical_workflow_record(
            workflow, entity_id=entity_id, created_at=created_at
        )

    def create_persistence_snapshot(
        self,
        *,
        kind: str,
        source_entity_id: str,
        payload: dict[str, object],
        snapshot_id: str | None = None,
        created_at: str | None = None,
    ) -> dict[str, object]:
        from dsp_platform.persistence_facade import (
            create_canonical_persistence_snapshot,
        )

        return create_canonical_persistence_snapshot(
            kind=kind,
            source_entity_id=source_entity_id,
            payload=payload,
            snapshot_id=snapshot_id,
            created_at=created_at,
        )

    def get_platform_info(self) -> PlatformMetadata:
        """Return immutable platform metadata / capability discovery."""
        return self._metadata()

    def health_check(self) -> PlatformResult:
        """Offline health / readiness probe via frozen health service APIs."""
        self._require_capability("health_check")
        try:
            from dsp_platform.health import PlatformHealthService

            config = self._configuration.to_platform_config()
            service = PlatformHealthService(config=config, platform=self)
            report = service.check()
            ok = report.ready and self._lifecycle.status in {
                PlatformStatus.READY,
                PlatformStatus.DEGRADED,
            }
            limitations: list[str] = []
            if self._lifecycle.status is PlatformStatus.DEGRADED:
                limitations.append("lifecycle=degraded")
            if not report.ready:
                failed = [
                    c.name for c in report.checks if c.status.value == "fail"
                ]
                limitations.append(f"failed_checks={failed}")
            return PlatformResult(
                ok=ok,
                capability="health_check",
                payload=report,
                metadata=self._metadata(),
                limitations=tuple(limitations),
                errors=() if ok else ("platform health check failed",),
            )
        except Exception as exc:
            return self._err_result(
                "health_check",
                PlatformError(f"health_check failed: {exc}"),
            )

    # --- internals ---------------------------------------------------------

    def _require_capability(self, capability: str) -> None:
        if not self._configuration.has_capability(capability):
            msg = f"capability disabled: {capability!r}"
            raise PlatformConfigurationError(msg)
        try:
            self._lifecycle.ensure_operational()
        except PlatformLifecycleError:
            # Legacy DI construction marks READY automatically when an
            # analysis service is present; CREATED-only shells may still
            # answer info/health but not orchestration paths.
            if capability in {"get_platform_info"}:
                return
            if (
                capability == "health_check"
                and self._lifecycle.status
                in {
                    PlatformStatus.CREATED,
                    PlatformStatus.READY,
                    PlatformStatus.DEGRADED,
                    PlatformStatus.INITIALIZING,
                }
            ):
                return
            raise

    def _resolve_service(
        self,
        name: str,
        factory: "type[Any] | Callable[[], Any]",
        *,
        capability: str,
    ) -> Any:
        if self._registry.has(name):
            return self._registry.get(name)
        instance = factory()
        try:
            self._registry.register(
                name,
                instance,
                capability=capability,
                version=_PLATFORM_VERSION,
            )
        except ServiceRegistryError:
            pass
        return instance

    def auth_schema(self) -> dict[str, object]:
        """Institutional Auth & RBAC schema descriptor (EPIC-A009)."""
        from dsp_platform.auth_facade import auth_schema

        return auth_schema()

    def create_auth_user(
        self,
        *,
        username: str,
        email: str,
        password: str,
        display_name: str | None = None,
        roles: list[str] | None = None,
        user_id: str | None = None,
        created_at: str | None = None,
        password_salt: str | None = None,
    ) -> dict[str, object]:
        """Create an institutional user account (passwords hashed)."""
        from dsp_platform.auth_facade import create_auth_user

        return create_auth_user(
            username=username,
            email=email,
            password=password,
            display_name=display_name,
            roles=roles,
            user_id=user_id,
            created_at=created_at,
            password_salt=password_salt,
        )

    def list_auth_users(self) -> list[dict[str, object]]:
        """List institutional users (no password hashes)."""
        from dsp_platform.auth_facade import list_auth_users

        return list_auth_users()

    def get_auth_user(self, user_id: str) -> dict[str, object] | None:
        """Fetch an institutional user by id."""
        from dsp_platform.auth_facade import get_auth_user

        return get_auth_user(user_id)

    def set_auth_user_roles(
        self, user_id: str, roles: list[str]
    ) -> dict[str, object]:
        """Assign roles to an institutional user."""
        from dsp_platform.auth_facade import set_auth_user_roles

        return set_auth_user_roles(user_id, roles)

    def list_auth_roles(self) -> list[dict[str, object]]:
        """List configurable institutional roles."""
        from dsp_platform.auth_facade import list_auth_roles

        return list_auth_roles()

    def upsert_auth_role(
        self,
        role_id: str,
        *,
        name: str | None = None,
        permissions: list[str] | None = None,
    ) -> dict[str, object]:
        """Create or update a configurable role."""
        from dsp_platform.auth_facade import upsert_auth_role

        return upsert_auth_role(role_id, name=name, permissions=permissions)

    def list_auth_permissions(self) -> list[str]:
        """List institutional permissions."""
        from dsp_platform.auth_facade import list_auth_permissions

        return list_auth_permissions()

    def auth_login(self, **kwargs: object) -> dict[str, object]:
        """Institutional login — JWT access + refresh tokens."""
        from dsp_platform.auth_facade import auth_login

        return auth_login(**kwargs)

    def auth_logout(self, **kwargs: object) -> dict[str, object]:
        """Revoke an institutional session."""
        from dsp_platform.auth_facade import auth_logout

        return auth_logout(**kwargs)

    def auth_refresh(self, **kwargs: object) -> dict[str, object]:
        """Refresh institutional access token."""
        from dsp_platform.auth_facade import auth_refresh

        return auth_refresh(**kwargs)

    def auth_current_user(
        self, access_token: str, **kwargs: object
    ) -> dict[str, object]:
        """Resolve current user from access token."""
        from dsp_platform.auth_facade import auth_current_user

        return auth_current_user(access_token, **kwargs)

    def evaluate_auth_permission(
        self, user_id: str, permission: str
    ) -> dict[str, object]:
        """Evaluate whether a user holds a permission."""
        from dsp_platform.auth_facade import evaluate_auth_permission

        return evaluate_auth_permission(user_id, permission)

    def protect_with_permission(
        self, access_token: str, permission: str, **kwargs: object
    ) -> dict[str, object]:
        """Validate token and require permission (optional platform guard)."""
        from dsp_platform.auth_facade import protect_with_permission

        return protect_with_permission(access_token, permission, **kwargs)

    def admin_schema(self) -> dict[str, object]:
        """Enterprise Admin Console schema (EPIC-A010)."""
        from dsp_platform.admin_facade import admin_schema

        return admin_schema()

    def admin_dashboard(self, **kwargs: object) -> dict[str, object]:
        """Read-only admin dashboard aggregate."""
        from dsp_platform.admin_facade import admin_dashboard

        return admin_dashboard(**kwargs)

    def admin_list_users(self) -> list[dict[str, object]]:
        from dsp_platform.admin_facade import admin_list_users

        return admin_list_users()

    def admin_get_user(self, user_id: str) -> dict[str, object] | None:
        from dsp_platform.admin_facade import admin_get_user

        return admin_get_user(user_id)

    def admin_create_user(self, **kwargs: object) -> dict[str, object]:
        from dsp_platform.admin_facade import admin_create_user

        return admin_create_user(**kwargs)

    def admin_set_user_roles(
        self, user_id: str, roles: list[str]
    ) -> dict[str, object]:
        from dsp_platform.admin_facade import admin_set_user_roles

        return admin_set_user_roles(user_id, roles)

    def admin_list_roles(self) -> list[dict[str, object]]:
        from dsp_platform.admin_facade import admin_list_roles

        return admin_list_roles()

    def admin_upsert_role(self, **kwargs: object) -> dict[str, object]:
        from dsp_platform.admin_facade import admin_upsert_role

        return admin_upsert_role(**kwargs)

    def admin_list_permissions(self) -> list[str]:
        from dsp_platform.admin_facade import admin_list_permissions

        return admin_list_permissions()

    def admin_list_sessions(
        self, *, user_id: str | None = None
    ) -> list[dict[str, object]]:
        from dsp_platform.admin_facade import admin_list_sessions

        return admin_list_sessions(user_id=user_id)

    def admin_list_audit_records(self, **kwargs: object) -> list[dict[str, object]]:
        from dsp_platform.admin_facade import admin_list_audit_records

        return admin_list_audit_records(**kwargs)

    def admin_list_workflow_history(self) -> list[dict[str, object]]:
        from dsp_platform.admin_facade import admin_list_workflow_history

        return admin_list_workflow_history()

    def admin_list_research_archive_metadata(
        self,
    ) -> list[dict[str, object]]:
        from dsp_platform.admin_facade import admin_list_research_archive_metadata

        return admin_list_research_archive_metadata()

    def admin_activity_timeline(
        self, *, limit: int = 100
    ) -> list[dict[str, object]]:
        from dsp_platform.admin_facade import admin_activity_timeline

        return admin_activity_timeline(limit=limit)

    def admin_search(
        self, query: str, *, scope: str = "audit"
    ) -> dict[str, object]:
        from dsp_platform.admin_facade import admin_search

        return admin_search(query, scope=scope)

    def admin_export_audit(self, **kwargs: object) -> dict[str, object]:
        from dsp_platform.admin_facade import admin_export_audit

        return admin_export_audit(**kwargs)

    def admin_health_panel(self) -> dict[str, object]:
        from dsp_platform.admin_facade import admin_health_panel

        return admin_health_panel()

    def admin_configuration(self) -> dict[str, object]:
        from dsp_platform.admin_facade import admin_configuration

        return admin_configuration()

    def admin_versions(self) -> dict[str, object]:
        from dsp_platform.admin_facade import admin_versions

        return admin_versions()

    def admin_feature_flags(
        self, flags: dict[str, bool] | None = None
    ) -> dict[str, object]:
        from dsp_platform.admin_facade import admin_feature_flags

        return admin_feature_flags(flags)

    def admin_system_metrics(self) -> dict[str, object]:
        from dsp_platform.admin_facade import admin_system_metrics

        return admin_system_metrics()
    def _metadata(self) -> PlatformMetadata:
        return PlatformMetadata(
            name=self._configuration.platform_name,
            version=_PLATFORM_VERSION,
            status=self._lifecycle.status,
            environment=self._configuration.environment.value,
            capabilities=self._configuration.enabled_capabilities,
            registered_services=tuple(
                d.name for d in self._registry.list_services()
            ),
            generated_at=datetime.now(tz=UTC),
            notes=self._lifecycle.notes,
        )

    def _ok_result(
        self,
        capability: str,
        payload: Any,
        *,
        limitations: tuple[str, ...] = (),
    ) -> PlatformResult:
        return PlatformResult(
            ok=True,
            capability=capability,
            payload=payload,
            metadata=self._metadata(),
            limitations=limitations,
        )

    def _err_result(self, capability: str, exc: PlatformError) -> PlatformResult:
        return PlatformResult(
            ok=False,
            capability=capability,
            payload=None,
            metadata=self._metadata(),
            errors=(str(exc),),
        )
