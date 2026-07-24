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

_PLATFORM_VERSION = "0.6.0"


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
    """Immutable orchestration result envelope — no business conclusions."""

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
    """Composition helper for ``DSPPlatform`` — registration only."""

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
        """Inject the frozen orchestration façade."""
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
        """Create a platform façade.

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

        ``context`` must be a workflow ``EngineContext`` (with façade port).
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
        """Orchestrate Conversation → Explanation → Reporter via frozen APIs."""
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
        """Export an immutable report envelope — presentation only.

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
