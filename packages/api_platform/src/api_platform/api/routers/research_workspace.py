"""RC1 Milestone 8 — thin Research Workspace routes (P1-07 owner isolation)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from api_platform.api.dependencies import (
    ApiState,
    get_api_state,
    require_authenticated_actor,
)

router = APIRouter(tags=["research-workspace"])


class WorkspacePayload(BaseModel):
    model_config = ConfigDict(extra="allow")

    note_id: str | None = Field(None, max_length=128)
    folder_id: str | None = Field(None, max_length=128)
    parent_id: str | None = Field(None, max_length=128)
    bookmark_id: str | None = Field(None, max_length=128)
    tag_id: str | None = Field(None, max_length=128)
    comment_id: str | None = Field(None, max_length=128)
    template_id: str | None = Field(None, max_length=64)
    title: str | None = Field(None, max_length=512)
    name: str | None = Field(None, max_length=256)
    body: str | None = Field(None, max_length=200_000)
    format: str | None = Field(None, max_length=32)
    status: str | None = Field(None, max_length=32)
    company: str | None = Field(None, max_length=32)
    portfolio_id: str | None = Field(None, max_length=128)
    research_object_id: str | None = Field(None, max_length=128)
    query: str | None = Field(None, max_length=512)
    instruction: str | None = Field(None, max_length=8000)
    message: str | None = Field(None, max_length=8000)
    mode: str | None = Field(None, max_length=32)
    version: int | None = None
    from_version: int | None = None
    to_version: int | None = None
    archived: bool | None = None
    resolved: bool | None = None
    enrich_with_ai: bool | None = None
    apply_to_note: bool | None = None
    actor_id: str | None = Field(None, max_length=128)
    author_id: str | None = Field(None, max_length=128)
    created_by: str | None = Field(None, max_length=128)
    assignee_id: str | None = Field(None, max_length=128)
    reason: str | None = Field(None, max_length=1000)
    kind: str | None = Field(None, max_length=64)
    label: str | None = Field(None, max_length=512)
    target_id: str | None = Field(None, max_length=256)
    href: str | None = Field(None, max_length=1024)
    color: str | None = Field(None, max_length=32)
    permission: str | None = Field(None, max_length=64)
    user_ids: list[str] | None = None
    mentions: list[str] | None = None
    document_refs: list[str] | None = None
    tag_ids: list[str] | None = None


def _actor(auth: dict[str, Any]) -> str:
    actor = str(auth.get("user_id") or "").strip()
    if not actor:
        raise HTTPException(status_code=401, detail="authentication required")
    return actor


def _with_actor(
    auth: dict[str, Any], payload: dict[str, Any] | None = None
) -> dict[str, Any]:
    data = dict(payload or {})
    data.pop("actor_user_id", None)
    data.pop("created_by", None)
    data.pop("author_id", None)
    data.pop("actor_id", None)
    data["actor_user_id"] = _actor(auth)
    return data


def _dispatch(
    state: ApiState,
    action: str,
    payload: dict[str, Any] | None = None,
) -> JSONResponse:
    try:
        result = state.platform.run_research_workspace(action, payload=payload)
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
    status = 200
    if result.get("ok") is False:
        err = str(result.get("error_type") or "")
        if err == "ForbiddenError":
            status = 403
        else:
            status = 400
    if action.startswith("delete") and isinstance(result.get("result"), dict):
        if result["result"].get("deleted") is False and status == 200:
            status = 404
    return JSONResponse(status_code=status, content=result)


@router.get("/research-workspace/schema")
def workspace_schema(state: ApiState = Depends(get_api_state)) -> dict[str, Any]:
    return {"ok": True, "schema": state.platform.research_workspace_schema()}


@router.get("/research-workspace")
def workspace_dashboard(
    state: ApiState = Depends(get_api_state),
    auth: dict[str, Any] = Depends(require_authenticated_actor),
) -> JSONResponse:
    return _dispatch(state, "dashboard", _with_actor(auth))


@router.post("/research-workspace/note")
def create_note(
    body: WorkspacePayload,
    state: ApiState = Depends(get_api_state),
    auth: dict[str, Any] = Depends(require_authenticated_actor),
) -> JSONResponse:
    return _dispatch(
        state, "create_note", _with_actor(auth, body.model_dump(exclude_none=True))
    )


@router.get("/research-workspace/note/{note_id}")
def get_note(
    note_id: str,
    state: ApiState = Depends(get_api_state),
    auth: dict[str, Any] = Depends(require_authenticated_actor),
) -> JSONResponse:
    return _dispatch(state, "get_note", _with_actor(auth, {"note_id": note_id}))


@router.put("/research-workspace/note/{note_id}")
def update_note(
    note_id: str,
    body: WorkspacePayload,
    state: ApiState = Depends(get_api_state),
    auth: dict[str, Any] = Depends(require_authenticated_actor),
) -> JSONResponse:
    payload = _with_actor(auth, body.model_dump(exclude_none=True))
    payload["note_id"] = note_id
    return _dispatch(state, "update_note", payload)


@router.delete("/research-workspace/note/{note_id}")
def delete_note(
    note_id: str,
    state: ApiState = Depends(get_api_state),
    auth: dict[str, Any] = Depends(require_authenticated_actor),
) -> JSONResponse:
    return _dispatch(state, "delete_note", _with_actor(auth, {"note_id": note_id}))


@router.get("/research-workspace/note/{note_id}/versions")
def list_versions(
    note_id: str,
    state: ApiState = Depends(get_api_state),
    auth: dict[str, Any] = Depends(require_authenticated_actor),
) -> JSONResponse:
    return _dispatch(
        state, "list_versions", _with_actor(auth, {"note_id": note_id})
    )


@router.post("/research-workspace/note/{note_id}/restore")
def restore_version(
    note_id: str,
    body: WorkspacePayload,
    state: ApiState = Depends(get_api_state),
    auth: dict[str, Any] = Depends(require_authenticated_actor),
) -> JSONResponse:
    return _dispatch(
        state,
        "restore_version",
        _with_actor(auth, {"note_id": note_id, "version": body.version}),
    )


@router.post("/research-workspace/note/{note_id}/diff")
def diff_versions(
    note_id: str,
    body: WorkspacePayload,
    state: ApiState = Depends(get_api_state),
    auth: dict[str, Any] = Depends(require_authenticated_actor),
) -> JSONResponse:
    return _dispatch(
        state,
        "diff_versions",
        _with_actor(
            auth,
            {
                "note_id": note_id,
                "from_version": body.from_version,
                "to_version": body.to_version,
            },
        ),
    )


@router.get("/research-workspace/notes")
def list_notes(
    state: ApiState = Depends(get_api_state),
    auth: dict[str, Any] = Depends(require_authenticated_actor),
) -> JSONResponse:
    return _dispatch(state, "list_notes", _with_actor(auth))


@router.post("/research-workspace/folder")
def create_folder(
    body: WorkspacePayload,
    state: ApiState = Depends(get_api_state),
    auth: dict[str, Any] = Depends(require_authenticated_actor),
) -> JSONResponse:
    return _dispatch(
        state, "create_folder", _with_actor(auth, body.model_dump(exclude_none=True))
    )


@router.put("/research-workspace/folder/{folder_id}")
def update_folder(
    folder_id: str,
    body: WorkspacePayload,
    state: ApiState = Depends(get_api_state),
    auth: dict[str, Any] = Depends(require_authenticated_actor),
) -> JSONResponse:
    payload = _with_actor(auth, body.model_dump(exclude_none=True))
    payload["folder_id"] = folder_id
    if body.name is not None:
        return _dispatch(state, "rename_folder", payload)
    if "parent_id" in payload:
        return _dispatch(state, "move_folder", payload)
    if body.archived is not None:
        return _dispatch(state, "archive_folder", payload)
    return JSONResponse(
        status_code=400,
        content={"ok": False, "error": "no folder mutation", "message": "Data unavailable."},
    )


@router.delete("/research-workspace/folder/{folder_id}")
def delete_folder(
    folder_id: str,
    state: ApiState = Depends(get_api_state),
    auth: dict[str, Any] = Depends(require_authenticated_actor),
) -> JSONResponse:
    return _dispatch(
        state, "delete_folder", _with_actor(auth, {"folder_id": folder_id})
    )


@router.get("/research-workspace/folders")
def list_folders(
    state: ApiState = Depends(get_api_state),
    auth: dict[str, Any] = Depends(require_authenticated_actor),
) -> JSONResponse:
    return _dispatch(state, "list_folders", _with_actor(auth))


@router.post("/research-workspace/bookmark")
def create_bookmark(
    body: WorkspacePayload,
    state: ApiState = Depends(get_api_state),
    auth: dict[str, Any] = Depends(require_authenticated_actor),
) -> JSONResponse:
    return _dispatch(
        state,
        "create_bookmark",
        _with_actor(auth, body.model_dump(exclude_none=True)),
    )


@router.delete("/research-workspace/bookmark/{bookmark_id}")
def delete_bookmark(
    bookmark_id: str,
    state: ApiState = Depends(get_api_state),
    auth: dict[str, Any] = Depends(require_authenticated_actor),
) -> JSONResponse:
    return _dispatch(
        state, "delete_bookmark", _with_actor(auth, {"bookmark_id": bookmark_id})
    )


@router.get("/research-workspace/bookmarks")
def list_bookmarks(
    state: ApiState = Depends(get_api_state),
    auth: dict[str, Any] = Depends(require_authenticated_actor),
) -> JSONResponse:
    return _dispatch(state, "list_bookmarks", _with_actor(auth))


@router.post("/research-workspace/template")
def apply_template(
    body: WorkspacePayload,
    state: ApiState = Depends(get_api_state),
    auth: dict[str, Any] = Depends(require_authenticated_actor),
) -> JSONResponse:
    return _dispatch(
        state,
        "apply_template",
        _with_actor(auth, body.model_dump(exclude_none=True)),
    )


@router.post("/research-workspace/comment")
def add_comment(
    body: WorkspacePayload,
    state: ApiState = Depends(get_api_state),
    auth: dict[str, Any] = Depends(require_authenticated_actor),
) -> JSONResponse:
    return _dispatch(
        state, "add_comment", _with_actor(auth, body.model_dump(exclude_none=True))
    )


@router.post("/research-workspace/comment/{comment_id}/resolve")
def resolve_comment(
    comment_id: str,
    body: WorkspacePayload,
    state: ApiState = Depends(get_api_state),
    auth: dict[str, Any] = Depends(require_authenticated_actor),
) -> JSONResponse:
    return _dispatch(
        state,
        "resolve_comment",
        _with_actor(
            auth,
            {
                "comment_id": comment_id,
                "resolved": body.resolved if body.resolved is not None else True,
            },
        ),
    )


@router.post("/research-workspace/share")
def share_note(
    body: WorkspacePayload,
    state: ApiState = Depends(get_api_state),
    auth: dict[str, Any] = Depends(require_authenticated_actor),
) -> JSONResponse:
    return _dispatch(
        state, "share", _with_actor(auth, body.model_dump(exclude_none=True))
    )


@router.post("/research-workspace/publish")
def publish_note(
    body: WorkspacePayload,
    state: ApiState = Depends(get_api_state),
    auth: dict[str, Any] = Depends(require_authenticated_actor),
) -> JSONResponse:
    return _dispatch(
        state, "publish", _with_actor(auth, body.model_dump(exclude_none=True))
    )


@router.get("/research-workspace/search")
def search_workspace(
    q: str = Query("", max_length=512),
    state: ApiState = Depends(get_api_state),
    auth: dict[str, Any] = Depends(require_authenticated_actor),
) -> JSONResponse:
    return _dispatch(state, "search", _with_actor(auth, {"query": q}))


@router.post("/research-workspace/ai")
def ai_assist(
    body: WorkspacePayload,
    state: ApiState = Depends(get_api_state),
    auth: dict[str, Any] = Depends(require_authenticated_actor),
) -> JSONResponse:
    return _dispatch(
        state, "ai", _with_actor(auth, body.model_dump(exclude_none=True))
    )


@router.post("/research-workspace/tag")
def upsert_tag(
    body: WorkspacePayload,
    state: ApiState = Depends(get_api_state),
    auth: dict[str, Any] = Depends(require_authenticated_actor),
) -> JSONResponse:
    return _dispatch(
        state, "upsert_tag", _with_actor(auth, body.model_dump(exclude_none=True))
    )


@router.delete("/research-workspace/tag/{tag_id}")
def delete_tag(
    tag_id: str,
    state: ApiState = Depends(get_api_state),
    auth: dict[str, Any] = Depends(require_authenticated_actor),
) -> JSONResponse:
    return _dispatch(state, "delete_tag", _with_actor(auth, {"tag_id": tag_id}))
