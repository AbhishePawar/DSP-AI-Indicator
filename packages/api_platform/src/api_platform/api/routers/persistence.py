"""Additive Persistence support routes (EPIC-A008).

Read/write metadata repositories only — does not change existing endpoint behaviour.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from api_platform.api.dependencies import ApiState, get_api_state

router = APIRouter(tags=["persistence"])


class PersistEntityRequest(BaseModel):
    kind: str = Field(..., min_length=1, max_length=64)
    payload: dict[str, Any] | None = None
    refs: dict[str, Any] | None = None
    provenance: dict[str, Any] | None = None
    entity_id: str | None = Field(None, max_length=128)
    created_at: str | None = Field(None, max_length=64)
    allow_update: bool = True


class PersistWorkflowRequest(BaseModel):
    workflow: dict[str, Any]
    entity_id: str | None = Field(None, max_length=128)
    created_at: str | None = Field(None, max_length=64)


class SnapshotRequest(BaseModel):
    kind: str = Field(..., min_length=1, max_length=32)
    source_entity_id: str = Field(..., min_length=1, max_length=128)
    payload: dict[str, Any]
    snapshot_id: str | None = Field(None, max_length=128)
    created_at: str | None = Field(None, max_length=64)


@router.get("/persistence/schema")
def persistence_schema(
    state: ApiState = Depends(get_api_state),
) -> dict[str, Any]:
    return {"ok": True, "schema": state.platform.persistence_schema()}


@router.post("/persistence/entity")
def persist_entity(
    body: PersistEntityRequest,
    state: ApiState = Depends(get_api_state),
) -> JSONResponse:
    try:
        result = state.platform.persist_entity(
            kind=body.kind,
            payload=body.payload,
            refs=body.refs,
            provenance=body.provenance,
            entity_id=body.entity_id,
            created_at=body.created_at,
            allow_update=body.allow_update,
        )
    except ValueError as exc:
        return JSONResponse(
            status_code=400,
            content={"ok": False, "error": str(exc), "message": "Data unavailable."},
        )
    except Exception as exc:  # noqa: BLE001
        return JSONResponse(
            status_code=503,
            content={"ok": False, "error": str(exc), "message": "Data unavailable."},
        )
    return JSONResponse({"ok": True, "result": result, "message": None})


@router.get("/persistence/entity/{kind}/{entity_id}")
def get_entity(
    kind: str,
    entity_id: str,
    state: ApiState = Depends(get_api_state),
) -> JSONResponse:
    result = state.platform.get_persisted_entity(kind, entity_id)
    if result is None:
        return JSONResponse(
            status_code=404,
            content={
                "ok": False,
                "error": "not found",
                "message": "Data unavailable.",
            },
        )
    return JSONResponse({"ok": True, "result": result, "message": None})


@router.post("/persistence/workflow")
def persist_workflow(
    body: PersistWorkflowRequest,
    state: ApiState = Depends(get_api_state),
) -> JSONResponse:
    try:
        result = state.platform.persist_workflow_record(
            body.workflow,
            entity_id=body.entity_id,
            created_at=body.created_at,
        )
    except ValueError as exc:
        return JSONResponse(
            status_code=400,
            content={"ok": False, "error": str(exc), "message": "Data unavailable."},
        )
    return JSONResponse({"ok": True, "result": result, "message": None})


@router.post("/persistence/snapshot")
def create_snapshot(
    body: SnapshotRequest,
    state: ApiState = Depends(get_api_state),
) -> JSONResponse:
    try:
        result = state.platform.create_persistence_snapshot(
            kind=body.kind,
            source_entity_id=body.source_entity_id,
            payload=body.payload,
            snapshot_id=body.snapshot_id,
            created_at=body.created_at,
        )
    except ValueError as exc:
        return JSONResponse(
            status_code=400,
            content={"ok": False, "error": str(exc), "message": "Data unavailable."},
        )
    return JSONResponse({"ok": True, "result": result, "message": None})
