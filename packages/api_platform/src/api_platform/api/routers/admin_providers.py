"""Admin API routes for Provider & API Management and Task Routing.

Gated by require_admin_access. Never leaks credentials or keys.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from api_platform.api.dependencies import require_admin_access
from llm_adapters import (
    ProviderNotFoundError,
    ValidationFailedError,
    get_runtime_store,
    get_task_routing_manager,
)

router = APIRouter(
    prefix="/admin",
    tags=["admin_providers"],
    dependencies=[Depends(require_admin_access)],
)


class SaveCredentialRequest(BaseModel):
    secret: str = Field(..., min_length=1, description="API key or token to store securely")
    validate_connection: bool = Field(
        default=True,
        alias="validate",
        description="Whether to execute pre-flight connection test before saving",
    )
    selected_model: str | None = Field(default=None, description="Optional model to validate against")

    model_config = {"populate_by_name": True}


class TestConnectionRequest(BaseModel):
    secret: str | None = Field(default=None, description="Candidate secret to test without saving")
    model: str | None = Field(default=None, description="Specific model to test")


class SetStatusRequest(BaseModel):
    is_active: bool = Field(..., description="Enable or disable provider for live routing")


class SetModelRequest(BaseModel):
    model: str = Field(..., min_length=1, description="Model identifier to set as default")


class UpdateRoutingRequest(BaseModel):
    primary_provider: str = Field(..., description="Default primary provider for this task")
    fallback_providers: list[str] = Field(default_factory=list, description="Ordered fallbacks")
    require_independent_corroboration: bool = Field(
        default=False, description="Whether statement extraction requires independent dual models"
    )
    timeout_seconds: float = Field(default=30.0, ge=1.0, le=300.0)
    max_retries: int = Field(default=2, ge=0, le=5)


@router.get("/providers")
async def list_providers(
    category: str | None = Query(default=None, description="Filter by category ('ai' or 'market_data')"),
) -> dict[str, Any]:
    """List all registered providers and their sanitized runtime configuration/health."""
    store = get_runtime_store()
    providers = store.list_providers(category=category)
    return {
        "providers": providers,
        "total": len(providers),
    }


@router.get("/providers/{provider_id}")
async def get_provider(provider_id: str) -> dict[str, Any]:
    """Get single provider configuration and health metadata."""
    store = get_runtime_store()
    rec = store.get_provider(provider_id)
    if rec is None:
        raise HTTPException(status_code=404, detail=f"Provider '{provider_id}' not found")
    return {"provider": rec}


@router.post("/providers/{provider_id}/credential")
async def save_credential(
    provider_id: str,
    payload: SaveCredentialRequest,
    admin_actor: dict[str, Any] = Depends(require_admin_access),
) -> dict[str, Any]:
    """Save or replace provider credential with optional pre-flight validation."""
    store = get_runtime_store()
    actor_id = admin_actor.get("user_id") or "admin"
    try:
        prov = store.replace_credential(
            provider_id=provider_id,
            new_secret=payload.secret,
            author=actor_id,
            validate=payload.validate_connection,
            model=payload.selected_model,
        )
        return {
            "ok": True,
            "provider_id": prov.provider_id,
            "health_status": prov.health_status.value,
            "provider": store.get_provider(provider_id),
        }
    except (ProviderNotFoundError, KeyError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValidationFailedError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to update credential: {exc}") from exc


@router.delete("/providers/{provider_id}/credential")
async def revoke_credential(
    provider_id: str,
    admin_actor: dict[str, Any] = Depends(require_admin_access),
) -> dict[str, Any]:
    """Revoke and securely purge stored credential for a provider."""
    store = get_runtime_store()
    actor_id = admin_actor.get("user_id") or "admin"
    try:
        prov = store.revoke_credential(provider_id=provider_id, author=actor_id)
        return {
            "ok": True,
            "provider_id": prov.provider_id,
            "health_status": prov.health_status.value,
            "provider": store.get_provider(provider_id),
        }
    except (ProviderNotFoundError, KeyError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/providers/{provider_id}/test")
async def run_connection_test(
    provider_id: str,
    payload: TestConnectionRequest | None = None,
) -> dict[str, Any]:
    """Test connection to provider using active or supplied credentials."""
    store = get_runtime_store()
    rec = store.get_provider(provider_id)
    if rec is None:
        raise HTTPException(status_code=404, detail=f"Provider '{provider_id}' not found")

    secret = payload.secret if payload and payload.secret else None
    model = payload.model if payload and payload.model else None

    res = store.test_connection(provider_id, candidate_secret=secret, candidate_model=model)
    return {
        "success": res["ok"],
        "status": res["status"],
        "latency_ms": res["latency_ms"],
        "sanitized_error": res.get("sanitized_error"),
        "recommended_action": res.get("recommended_action"),
        "timestamp": res.get("timestamp"),
    }


@router.post("/providers/{provider_id}/status")
async def update_provider_status(
    provider_id: str,
    payload: SetStatusRequest,
    admin_actor: dict[str, Any] = Depends(require_admin_access),
) -> dict[str, Any]:
    """Enable or disable provider for live execution."""
    store = get_runtime_store()
    actor_id = admin_actor.get("user_id") or "admin"
    try:
        rec = store.set_active_status(provider_id, is_active=payload.is_active, author=actor_id)
        return {"ok": True, "provider": store.get_provider(provider_id)}
    except (ProviderNotFoundError, KeyError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/providers/{provider_id}/model")
async def update_provider_model(
    provider_id: str,
    payload: SetModelRequest,
    admin_actor: dict[str, Any] = Depends(require_admin_access),
) -> dict[str, Any]:
    """Update selected model for a provider."""
    store = get_runtime_store()
    actor_id = admin_actor.get("user_id") or "admin"
    try:
        rec = store.update_model(provider_id, model=payload.model, author=actor_id)
        return {"ok": True, "provider": store.get_provider(provider_id)}
    except (ProviderNotFoundError, KeyError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/providers/{provider_id}/rollback")
async def rollback_provider(
    provider_id: str,
    admin_actor: dict[str, Any] = Depends(require_admin_access),
) -> dict[str, Any]:
    """Roll back to previous configuration version."""
    store = get_runtime_store()
    actor_id = admin_actor.get("user_id") or "admin"
    try:
        rec = store.rollback(provider_id, author=actor_id)
        return {"ok": True, "provider": store.get_provider(provider_id)}
    except (ProviderNotFoundError, KeyError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/providers/{provider_id}/audit")
async def get_provider_audit(provider_id: str) -> dict[str, Any]:
    """Get audit trail for a specific provider."""
    store = get_runtime_store()
    rec = store.get_provider(provider_id)
    if rec is None:
        raise HTTPException(status_code=404, detail=f"Provider '{provider_id}' not found")
    logs = store.get_audit_log(provider_id=provider_id)
    return {"provider_id": provider_id, "audit_log": logs}


@router.get("/routing")
async def get_all_routing_policies() -> dict[str, Any]:
    """Get all task routing and fallback policies."""
    mgr = get_task_routing_manager()
    policies = mgr.list_policies()
    return {"policies": [p.to_dict() for p in policies]}


@router.post("/routing/{task_name}")
async def update_task_routing(
    task_name: str,
    payload: UpdateRoutingRequest,
    admin_actor: dict[str, Any] = Depends(require_admin_access),
) -> dict[str, Any]:
    """Update primary provider, fallbacks, and corroboration settings for a task."""
    mgr = get_task_routing_manager()
    fb_prov = payload.fallback_providers[0] if payload.fallback_providers else None

    if payload.require_independent_corroboration:
        if not fb_prov or fb_prov.lower() == payload.primary_provider.lower():
            raise HTTPException(
                status_code=400,
                detail="Independent corroboration requires at least one distinct fallback provider.",
            )

    try:
        policy = mgr.update_policy(
            task_id=task_name,
            primary_provider=payload.primary_provider,
            fallback_provider=fb_prov,
            require_corroboration=payload.require_independent_corroboration,
            secondary_provider=fb_prov,
            timeout_seconds=payload.timeout_seconds,
            max_retries=payload.max_retries,
        )
        return {
            "ok": True,
            "task": task_name,
            "policy": {
                "task_id": policy.task_id,
                "primary_provider": policy.primary_provider,
                "fallback_providers": payload.fallback_providers,
                "require_independent_corroboration": policy.require_corroboration,
                "timeout_seconds": policy.timeout_seconds,
                "max_retries": policy.max_retries,
            },
        }
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
