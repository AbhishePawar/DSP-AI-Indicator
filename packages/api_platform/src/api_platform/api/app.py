"""FastAPI application factory (K1.1 + EPIC-011A infra bootstrap)."""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from api_platform.api.csrf_middleware import CsrfMiddleware
from api_platform.api.dependencies import (
    ApiState,
    ContextStore,
    ReportStore,
    build_copilot_service,
    build_default_platform,
    build_language_model,
)
from api_platform.api.exceptions import ApiError, PlatformError
from api_platform.api.infra_bootstrap import (
    bootstrap_production_infrastructure,
    public_startup_error,
)
from api_platform.api.mappers import CompositionApiError, composition_error_body
from api_platform.api.middleware import RequestContextMiddleware
from api_platform.api.monitoring import PlatformLifecycleState, mark_lifecycle
from api_platform.api.ops import metrics_registry
from api_platform.api.ops_middleware import (
    MetricsMiddleware,
    RateLimitHookMiddleware,
    SecurityHeadersMiddleware,
)
from api_platform.api.routers import (
    analysis,
    auth,
    beta_programme,
    comparison,
    composition,
    copilot,
    corporate_actions,
    data,
    decision_workspace,
    enterprise,
    enterprise_auth_platform,
    esg,
    filings,
    fundamentals,
    health,
    historical,
    insider_trading,
    institutional_admin,
    institutional_auth,
    institutional_committee,
    institutional_workflow,
    investment_policy,
    market,
    meta,
    metrics,
    news,
    ownership,
    persistence,
    platform,
    portfolio,
    portfolio_analytics,
    portfolio_intelligence,
    reports,
    research,
    research_intelligence,
    research_monitoring,
    transcripts,
    workflow,
)
from api_platform.api.schemas import ApiErrorBody
from dsp_platform import DSPPlatform

API_VERSION = "v1"
API_TITLE = "DSP AI Indicator API Platform"
API_DESCRIPTION = (
    "HTTP surface over ``dsp_platform``. Contains no business logic — "
    "routes validate requests and delegate to DSPPlatform public methods. "
    "EPIC-002 exposes composition via POST /api/v1/analyse."
)


@asynccontextmanager
async def _app_lifespan(application: FastAPI) -> AsyncIterator[None]:
    """Startup / graceful shutdown hooks — no business logic."""
    metrics_registry.inc("dsp_system_restarts_total")
    state = getattr(application.state, "api", None)
    if state is not None and getattr(state, "infrastructure", None) is None:
        try:
            boot = bootstrap_production_infrastructure()
            state.infrastructure = boot.infrastructure
            state.production = boot.production
            state.infra_notes = boot.notes
            application.state.infrastructure = boot.infrastructure
            application.state.production = boot.production
        except Exception as exc:  # noqa: BLE001
            code, message = public_startup_error(exc)
            raise RuntimeError(f"{code}: {message}") from exc
    try:
        yield
    finally:
        pass


def create_app(
    *,
    platform: DSPPlatform | None = None,
    platform_factory: Callable[[], DSPPlatform] | None = None,
    api_version: str = API_VERSION,
    security: Any | None = None,
    enable_security: bool = False,
) -> FastAPI:
    """Create a versioned FastAPI application with OpenAPI / Swagger enabled.

    Args:
        platform: Optional pre-built ``DSPPlatform``.
        platform_factory: Optional factory when ``platform`` is omitted.
        api_version: HTTP API version label.
        security: Optional ``security_platform.SecurityBundle``. When provided,
            ``SecurityMiddleware`` protects non-public routes. DSP Platform
            remains authentication-independent.
        enable_security: When True and ``security`` is None, build a default
            ``SecurityBundle`` (dev/RC convenience for the web app).
    """
    import os

    if security is None and (
        enable_security or os.environ.get("DSP_ENABLE_SECURITY", "").lower() in
        {"1", "true", "yes"}
    ):
        from security_platform import SecurityBundle, SecuritySettings

        jwt_secret = os.environ.get("DSP_JWT_SECRET", "dev-only-change-me")
        is_prod = os.environ.get("DSP_ENVIRONMENT", "").lower() == "production"
        if is_prod and jwt_secret in {
            "dev-only-change-me",
            "dsp-auth-dev-secret",
            "",
        }:
            raise RuntimeError(
                "DSP_JWT_SECRET must be set to a non-default value in production"
            )
        security = SecurityBundle.create(
            SecuritySettings(
                jwt_secret=jwt_secret,
                require_auth=True,
                allow_guest=False,
                allow_passwordless=not is_prod,
            )
        )

    app_version = os.environ.get("DSP_APP_VERSION") or os.environ.get(
        "DSP_SERVICE_VERSION", "1.0.0"
    )
    application = FastAPI(
        title=API_TITLE,
        description=API_DESCRIPTION,
        version=app_version.lstrip("v"),
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=_app_lifespan,
    )

    resolved = platform
    if resolved is None:
        factory = platform_factory or build_default_platform
        resolved = factory()

    # Eager infra bootstrap so TestClient (no lifespan) still sees adapters.
    boot = bootstrap_production_infrastructure()
    application.state.api = ApiState(
        platform=resolved,
        reports=ReportStore(),
        contexts=ContextStore(),
        api_version=api_version,
        copilot_service=build_copilot_service(),
        language_model=build_language_model(),
        infrastructure=boot.infrastructure,
        production=boot.production,
        infra_notes=boot.notes,
    )
    application.state.security = security
    application.state.infrastructure = boot.infrastructure
    application.state.production = boot.production

    # EPIC-016: durable enterprise store when DatabasePort is available.
    # Do not reset an existing singleton (tests inject InMemory services first).
    try:
        from enterprise.service import (
            enterprise_service_configured,
            get_enterprise_service,
        )

        if not enterprise_service_configured():
            db = getattr(boot.infrastructure, "database", None)
            get_enterprise_service(database=db)
    except Exception:  # noqa: BLE001 — enterprise optional at boot
        pass

    # RC1 Milestone 3: durable portfolio store when DatabasePort is available.
    # get_portfolio_service() only honors `database` on the first call, so
    # this is safe to call unconditionally (tests inject InMemory services
    # first via reset_portfolio_store_for_tests, same convention as enterprise).
    try:
        from portfolio_store import get_portfolio_service

        db = getattr(boot.infrastructure, "database", None)
        get_portfolio_service(database=db)
    except Exception:  # noqa: BLE001 — portfolio store optional at boot
        pass

    application.add_middleware(
        CORSMiddleware,
        allow_origins=os.environ.get(
            "DSP_CORS_ORIGINS",
            "http://localhost:3000,http://127.0.0.1:3000",
        ).split(","),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Security middleware runs outermost when configured (added last in Starlette).
    application.add_middleware(
        RequestContextMiddleware, api_version=api_version
    )
    application.add_middleware(SecurityHeadersMiddleware)
    application.add_middleware(MetricsMiddleware)
    application.add_middleware(RateLimitHookMiddleware)
    application.add_middleware(CsrfMiddleware)
    if security is not None:
        from security_platform import SecurityMiddleware

        application.add_middleware(SecurityMiddleware, bundle=security)

    _register_exception_handlers(application)
    _register_routers(application)
    # Eager lifecycle transition (mirrors the eager infra bootstrap above) so
    # TestClient callers that never enter the ASGI lifespan context still see
    # an accurate startup -> ready transition on /health/live and /health/ready.
    mark_lifecycle(PlatformLifecycleState.READY)
    return application


def _register_routers(application: FastAPI) -> None:
    # Versioned mount: /api/v1/... plus root aliases matching the mission routes.
    versioned = [
        health.router,
        metrics.router,
        platform.router,
        meta.router,
        auth.router,
        institutional_auth.router,
        enterprise_auth_platform.router,
        institutional_admin.router,
        beta_programme.public_router,
        beta_programme.admin_router,
        enterprise.router,
        analysis.router,
        composition.router,
        comparison.router,
        workflow.router,
        copilot.router,
        reports.router,
        research_intelligence.router,
        market.router,
        fundamentals.router,
        historical.router,
        corporate_actions.router,
        news.router,
        filings.router,
        ownership.router,
        insider_trading.router,
        esg.router,
        transcripts.router,
        data.router,
        research.router,
        research_monitoring.router,
        decision_workspace.router,
        portfolio.router,
        portfolio_intelligence.router,
        portfolio_analytics.router,
        institutional_committee.router,
        institutional_workflow.router,
        investment_policy.router,
        persistence.router,
    ]
    for router in versioned:
        application.include_router(router)
        application.include_router(router, prefix=f"/api/{API_VERSION}")


def _register_exception_handlers(application: FastAPI) -> None:
    @application.exception_handler(CompositionApiError)
    async def composition_error_handler(
        request: Request, exc: CompositionApiError
    ) -> JSONResponse:
        if exc.correlation_id is None:
            exc.correlation_id = getattr(request.state, "request_id", None)
        body = composition_error_body(exc, api_version=API_VERSION)
        return JSONResponse(
            status_code=exc.status_code, content=body.model_dump(mode="json")
        )

    @application.exception_handler(ApiError)
    async def api_error_handler(
        request: Request, exc: ApiError
    ) -> JSONResponse:
        from datetime import UTC, datetime

        body = ApiErrorBody(
            error=type(exc).__name__,
            detail=exc.message,
            message=exc.message,
            error_code=type(exc).__name__,
            correlation_id=getattr(request.state, "request_id", None),
            timestamp=datetime.now(tz=UTC),
            status_code=exc.status_code,
            api_version=API_VERSION,
        )
        return JSONResponse(status_code=exc.status_code, content=body.model_dump(mode="json"))

    @application.exception_handler(PlatformError)
    async def platform_error_handler(
        request: Request, exc: PlatformError
    ) -> JSONResponse:
        from datetime import UTC, datetime

        body = ApiErrorBody(
            error="PlatformError",
            detail="platform orchestration failure",
            message="platform orchestration failure",
            error_code="PLATFORM_ERROR",
            correlation_id=getattr(request.state, "request_id", None),
            timestamp=datetime.now(tz=UTC),
            status_code=502,
            api_version=API_VERSION,
        )
        return JSONResponse(status_code=502, content=body.model_dump(mode="json"))

    @application.exception_handler(RequestValidationError)
    async def request_validation_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        from datetime import UTC, datetime

        messages = [
            f"{'.'.join(str(p) for p in err.get('loc', ()))}: {err.get('msg')}"
            for err in exc.errors()
        ]
        body = ApiErrorBody(
            error="RequestValidationError",
            detail="request validation failed",
            message="request validation failed",
            error_code="REQUEST_VALIDATION_ERROR",
            validation_errors=messages,
            correlation_id=getattr(request.state, "request_id", None),
            timestamp=datetime.now(tz=UTC),
            status_code=422,
            api_version=API_VERSION,
        )
        return JSONResponse(status_code=422, content=body.model_dump(mode="json"))

    @application.exception_handler(ValidationError)
    async def pydantic_validation_handler(
        request: Request, exc: ValidationError
    ) -> JSONResponse:
        from datetime import UTC, datetime

        body = ApiErrorBody(
            error="ValidationError",
            detail="payload validation failed",
            message="payload validation failed",
            error_code="VALIDATION_ERROR",
            correlation_id=getattr(request.state, "request_id", None),
            timestamp=datetime.now(tz=UTC),
            status_code=422,
            api_version=API_VERSION,
        )
        return JSONResponse(status_code=422, content=body.model_dump(mode="json"))

    @application.exception_handler(Exception)
    async def unhandled_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        from datetime import UTC, datetime

        body = ApiErrorBody(
            error="InternalServerError",
            detail="an unexpected error occurred",
            message="an unexpected error occurred",
            error_code="INTERNAL_ERROR",
            correlation_id=getattr(request.state, "request_id", None),
            timestamp=datetime.now(tz=UTC),
            status_code=500,
            api_version=API_VERSION,
        )
        return JSONResponse(status_code=500, content=body.model_dump(mode="json"))


# Module-level app for ``uvicorn api_platform.api.app:app``
# Set DSP_ENABLE_SECURITY=true for web login (L1.0).
app = create_app()
