"""Contact routes — Figma Contact page ("Send message").

``POST /contact`` is public (marketing page) and validated server-side; the
message lands in the durable workspace snapshot store. Administrators read the
inbox through ``GET /admin/contact-messages`` (``configure_platform`` or
``manage_users``).
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from api_platform.api.dependencies import (
    ApiState,
    get_api_state,
    require_admin_access,
)

router = APIRouter(tags=["contact"])


class ContactRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1, max_length=120)
    email: str = Field(..., min_length=3, max_length=254)
    message: str = Field(..., min_length=10, max_length=4000)
    source: str | None = Field(None, max_length=64)


@router.post("/contact", status_code=201)
def submit_contact(
    body: ContactRequest, state: ApiState = Depends(get_api_state)
) -> JSONResponse:
    store = state.platform.investor_workspace().store
    try:
        record = store.add_contact_message(
            name=body.name, email=body.email, message=body.message, source=body.source
        )
    except ValueError as exc:
        return JSONResponse(
            status_code=422,
            content={"ok": False, "error": str(exc), "message": "Unable to send."},
        )
    # Never echo the message body back to the public caller.
    return JSONResponse(
        status_code=201,
        content={
            "ok": True,
            "message_id": record["message_id"],
            "received_at": record["received_at"],
        },
    )


@router.get("/admin/contact-messages")
def list_contact_messages(
    request: Request,
    state: ApiState = Depends(get_api_state),
    limit: int = Query(200, ge=1, le=1000),
) -> dict[str, Any]:
    require_admin_access(request)
    items = state.platform.investor_workspace().store.list_contact_messages(limit=limit)
    return {"ok": True, "items": items, "count": len(items)}
