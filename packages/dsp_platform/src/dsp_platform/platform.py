"""DSP Platform integration entry point (K1.0).

Orchestrates frozen public bounded-context APIs without containing business
logic, financial calculations, persistence, REST, or authentication.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any

from comparison import ComparisonResult, QualitativeComparisonEngine
from contracts import (
    BarFrequency,
    Instrument,
    Recommendation,
    StatementPeriodType,
)
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
        engine: QualitativeComparisonEngine,
        eligibility_options: EligibilityOptions | None = None,
        evidence_bundles: tuple[EvidenceBundle, ...] = (),
    ) -> ComparisonResult:
        """Qualitative comparison of universe DecisionPacks."""
        from comparison import compare_universe_result

        try:
            return compare_universe_result(
                engine,
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
        engine: QualitativeComparisonEngine,
        eligibility_options: EligibilityOptions | None = None,
        evidence_bundles: tuple[EvidenceBundle, ...] = (),
    ) -> PlatformResult:
        """Orchestrate multi-company comparison via frozen comparison APIs."""
        self._require_capability("compare_companies")
        try:
            payload = engine.compare_packs(
                packs,
                eligibility_options=eligibility_options,
                evidence_bundles=evidence_bundles,
            )
            return self._ok_result("compare_companies", payload)
        except Exception as exc:
            return self._err_result(
                "compare_companies",
                PlatformError(f"compare_companies failed: {exc}"),
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
        factory: type[Any],
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
