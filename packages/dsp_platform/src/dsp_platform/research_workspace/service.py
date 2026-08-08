"""Research Workspace orchestration — CRUD + workflow + Copilot 2.0 reuse."""

from __future__ import annotations

from typing import Any, Mapping

from dsp_platform.research_workspace.store import (
    TEMPLATE_IDS,
    get_research_workspace_store,
)

UNAVAILABLE_MESSAGE = "Data unavailable."
RESEARCH_WORKSPACE_SCHEMA_VERSION = "1.0.0"
RESEARCH_WORKSPACE_SERVICE_VERSION = "0.1.0"


class WorkspaceForbiddenError(PermissionError):
    """P1-07 — cross-tenant / non-owner workspace access."""


def _actor(body: dict[str, Any]) -> str:
    actor = str(body.get("actor_user_id") or "").strip()
    if not actor:
        raise WorkspaceForbiddenError("actor_user_id required")
    # Client-supplied owner fields are never authoritative.
    body.pop("created_by", None)
    body.pop("author_id", None)
    body.pop("actor_id", None)
    body["created_by"] = actor
    body["actor_id"] = actor
    body["author_id"] = actor
    return actor


def _owned_by(row: dict[str, Any] | None, actor: str) -> bool:
    if row is None:
        return False
    owner = str(row.get("created_by") or "").strip()
    return bool(owner and owner == actor)


def _require_note_owner(store: Any, note_id: str, actor: str) -> dict[str, Any]:
    note = store.get_note(note_id)
    if note is None:
        raise ValueError("note not found")
    if not _owned_by(note, actor):
        raise WorkspaceForbiddenError("forbidden")
    return note


def _require_folder_owner(store: Any, folder_id: str, actor: str) -> dict[str, Any]:
    folders = {f["folder_id"]: f for f in store.list_folders()}
    folder = folders.get(folder_id)
    if folder is None:
        raise ValueError("folder not found")
    if folder_id == "folder-root":
        return folder
    if not _owned_by(folder, actor):
        raise WorkspaceForbiddenError("forbidden")
    return folder

_STATUS_TO_WORKFLOW = {
    "draft": "draft",
    "review": "review",
    "approved": "approved",
    "published": "published",
    "archived": "published",
}


def research_workspace_schema() -> dict[str, Any]:
    return {
        "schema_version": RESEARCH_WORKSPACE_SCHEMA_VERSION,
        "service_version": RESEARCH_WORKSPACE_SERVICE_VERSION,
        "templates": list(TEMPLATE_IDS),
        "note_statuses": [
            "draft",
            "review",
            "approved",
            "published",
            "archived",
        ],
        "routes": [
            "/research-workspace",
            "/research-workspace/note",
            "/research-workspace/folder",
            "/research-workspace/bookmark",
            "/research-workspace/template",
            "/research-workspace/comment",
            "/research-workspace/share",
            "/research-workspace/publish",
            "/research-workspace/search",
            "/research-workspace/ai",
        ],
        "rules": [
            "orchestration_only",
            "no_duplicated_calculations",
            "reuse_copilot_v2_for_ai",
            "reuse_workflow_for_publish",
            "workspace_store_separate_from_engine_payloads",
            "missing_is_data_unavailable",
        ],
        "engines_reused": [
            "copilot_v2",
            "institutional_workflow",
            "enterprise_dashboards",
            "portfolio_intelligence",
            "research_engine_artifacts_as_attachments",
            "authentication_platform_user_ids",
        ],
    }


def run_research_workspace(
    action: str,
    *,
    platform: Any = None,
    payload: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Dispatch a Research Workspace action."""
    store = get_research_workspace_store()
    body = dict(payload or {})
    act = (action or "").strip().lower()

    # Schema remains public; every product action requires server actor (P1-07).
    actor: str | None = None
    if act not in {"schema"}:
        actor = _actor(body)

    def _owned_notes() -> list[dict[str, Any]]:
        assert actor is not None
        return [n for n in store.list_notes() if _owned_by(n, actor)]

    def _owned_folders() -> list[dict[str, Any]]:
        assert actor is not None
        return [
            f
            for f in store.list_folders()
            if f.get("folder_id") == "folder-root" or _owned_by(f, actor)
        ]

    def _owned_bookmarks() -> list[dict[str, Any]]:
        assert actor is not None
        return [b for b in store.list_bookmarks() if _owned_by(b, actor)]

    handlers = {
        "dashboard": lambda: _dashboard(store, platform, actor=actor),
        "list_notes": lambda: {"notes": _owned_notes()},
        "get_note": lambda: _require(
            _require_note_owner(store, str(body.get("note_id") or ""), actor or "")
        ),
        "create_note": lambda: {"note": store.create_note(body)},
        "update_note": lambda: (
            _require_note_owner(store, str(body.get("note_id") or ""), actor or ""),
            {"note": store.update_note(str(body.get("note_id") or ""), body)},
        )[1],
        "delete_note": lambda: (
            _require_note_owner(store, str(body.get("note_id") or ""), actor or ""),
            {"deleted": store.delete_note(str(body.get("note_id") or ""))},
        )[1],
        "list_versions": lambda: (
            _require_note_owner(store, str(body.get("note_id") or ""), actor or ""),
            {"versions": store.list_versions(str(body.get("note_id") or ""))},
        )[1],
        "restore_version": lambda: (
            _require_note_owner(store, str(body.get("note_id") or ""), actor or ""),
            {
                "note": store.restore_version(
                    str(body.get("note_id") or ""),
                    int(body.get("version") or 0),
                )
            },
        )[1],
        "create_folder": lambda: {
            "folder": store.create_folder(
                name=str(body.get("name") or "Folder"),
                parent_id=body.get("parent_id"),
                folder_id=body.get("folder_id"),
                created_by=actor,
            )
        },
        "rename_folder": lambda: (
            _require_folder_owner(store, str(body.get("folder_id") or ""), actor or ""),
            {
                "folder": store.rename_folder(
                    str(body.get("folder_id") or ""),
                    str(body.get("name") or ""),
                )
            },
        )[1],
        "move_folder": lambda: (
            _require_folder_owner(store, str(body.get("folder_id") or ""), actor or ""),
            {
                "folder": store.move_folder(
                    str(body.get("folder_id") or ""),
                    body.get("parent_id"),
                )
            },
        )[1],
        "archive_folder": lambda: (
            _require_folder_owner(store, str(body.get("folder_id") or ""), actor or ""),
            {
                "folder": store.archive_folder(
                    str(body.get("folder_id") or ""),
                    bool(body.get("archived", True)),
                )
            },
        )[1],
        "delete_folder": lambda: (
            _require_folder_owner(store, str(body.get("folder_id") or ""), actor or ""),
            {"deleted": store.delete_folder(str(body.get("folder_id") or ""))},
        )[1],
        "list_folders": lambda: {"folders": _owned_folders()},
        "create_bookmark": lambda: {"bookmark": store.create_bookmark(body)},
        "delete_bookmark": lambda: _delete_bookmark_owned(
            store, str(body.get("bookmark_id") or ""), actor or ""
        ),
        "list_bookmarks": lambda: {"bookmarks": _owned_bookmarks()},
        "upsert_tag": lambda: {"tag": store.upsert_tag(body)},
        "delete_tag": lambda: {
            "deleted": store.delete_tag(str(body.get("tag_id") or ""))
        },
        "list_tags": lambda: {"tags": store.list_tags()},
        "add_comment": lambda: (
            _require_note_owner(store, str(body.get("note_id") or ""), actor or ""),
            {"comment": store.add_comment(body)},
        )[1],
        "resolve_comment": lambda: _resolve_comment_owned(store, body, actor or ""),
        "list_comments": lambda: _list_comments_owned(store, body, actor or ""),
        "share": lambda: (
            _require_note_owner(store, str(body.get("note_id") or ""), actor or ""),
            {"share": store.share_note(body)},
        )[1],
        "list_shares": lambda: (
            _require_note_owner(store, str(body.get("note_id") or ""), actor or ""),
            {"shares": store.list_shares(body.get("note_id"))},
        )[1],
        "apply_template": lambda: _apply_template(store, platform, body),
        "publish": lambda: (
            _require_note_owner(store, str(body.get("note_id") or ""), actor or ""),
            _publish(store, platform, body),
        )[1],
        "search": lambda: _search_owned(store, body, actor or ""),
        "ai": lambda: _ai_assist(store, platform, body),
        "diff_versions": lambda: (
            _require_note_owner(store, str(body.get("note_id") or ""), actor or ""),
            _diff_versions(store, body),
        )[1],
    }
    if act not in handlers:
        raise ValueError(f"Unknown research-workspace action: {action!r}")
    try:
        result = handlers[act]()
    except WorkspaceForbiddenError as exc:
        return {
            "ok": False,
            "action": act,
            "message": UNAVAILABLE_MESSAGE,
            "error": str(exc),
            "error_type": "ForbiddenError",
        }
    except ValueError:
        raise
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "action": act,
            "message": UNAVAILABLE_MESSAGE,
            "error": str(exc),
        }
    return {
        "ok": True,
        "action": act,
        "result": result,
        "message": None,
        "provenance": {
            "schema_version": RESEARCH_WORKSPACE_SCHEMA_VERSION,
            "service_version": RESEARCH_WORKSPACE_SERVICE_VERSION,
            "calculations_performed": False,
            "orchestration_only": True,
        },
    }


def _delete_bookmark_owned(store: Any, bookmark_id: str, actor: str) -> dict[str, Any]:
    bookmarks = {b["bookmark_id"]: b for b in store.list_bookmarks()}
    row = bookmarks.get(bookmark_id)
    if row is None:
        return {"deleted": False}
    if not _owned_by(row, actor):
        raise WorkspaceForbiddenError("forbidden")
    return {"deleted": store.delete_bookmark(bookmark_id)}


def _resolve_comment_owned(
    store: Any, body: dict[str, Any], actor: str
) -> dict[str, Any]:
    cid = str(body.get("comment_id") or "")
    comments = {c["comment_id"]: c for c in store.list_comments()}
    comment = comments.get(cid)
    if comment is None:
        raise ValueError("comment not found")
    _require_note_owner(store, str(comment.get("note_id") or ""), actor)
    return {
        "comment": store.resolve_comment(
            cid, bool(body.get("resolved", True))
        )
    }


def _list_comments_owned(
    store: Any, body: dict[str, Any], actor: str
) -> dict[str, Any]:
    note_id = body.get("note_id")
    if note_id:
        _require_note_owner(store, str(note_id), actor)
        return {"comments": store.list_comments(note_id)}
    owned_ids = {n["note_id"] for n in store.list_notes() if _owned_by(n, actor)}
    return {
        "comments": [
            c for c in store.list_comments() if c.get("note_id") in owned_ids
        ]
    }


def _search_owned(store: Any, body: dict[str, Any], actor: str) -> dict[str, Any]:
    raw = store.search(str(body.get("query") or ""))
    return {
        "query": body.get("query"),
        "notes": [n for n in raw.get("notes", []) if _owned_by(n, actor)],
        "folders": [
            f
            for f in raw.get("folders", [])
            if f.get("folder_id") == "folder-root" or _owned_by(f, actor)
        ],
        "bookmarks": [b for b in raw.get("bookmarks", []) if _owned_by(b, actor)],
        "tags": raw.get("tags", []),
        "comments": [
            c
            for c in raw.get("comments", [])
            if _owned_by(store.get_note(str(c.get("note_id") or "")) or {}, actor)
        ],
    }


def _require(row: dict[str, Any] | None) -> dict[str, Any]:
    if row is None:
        raise ValueError("not found")
    return {"note": row}


def _dashboard(
    store: Any, platform: Any, *, actor: str | None = None
) -> dict[str, Any]:
    notes = [
        n
        for n in store.list_notes()
        if actor is None or _owned_by(n, actor)
    ]
    pending = [n for n in notes if n.get("status") in {"draft", "review"}]
    published = [n for n in notes if n.get("status") == "published"]
    bookmarks = [
        b
        for b in store.list_bookmarks()
        if actor is None or _owned_by(b, actor)
    ]
    owned_ids = {n.get("note_id") for n in notes}
    comments = [
        c for c in store.list_comments() if c.get("note_id") in owned_ids
    ]
    open_comments = [c for c in comments if not c.get("resolved")]
    tasks = [
        {
            "note_id": n.get("note_id"),
            "title": n.get("title"),
            "status": n.get("status"),
            "assignee_id": n.get("assignee_id"),
        }
        for n in notes
        if n.get("assignee_id") or n.get("status") == "review"
    ]

    copilot_conversations: list[dict[str, Any]] = []
    if platform is not None:
        try:
            copilot_conversations = list(platform.list_copilot_history())[:10]
        except Exception:  # noqa: BLE001
            copilot_conversations = []

    recent_companies = []
    seen: set[str] = set()
    for note in notes:
        company = str(note.get("company") or "").strip().upper()
        if company and company not in seen:
            seen.add(company)
            recent_companies.append(company)
        if len(recent_companies) >= 10:
            break

    return {
        "recent_notes": notes[:10],
        "pending_reviews": pending[:10],
        "published_reports": published[:10],
        "bookmarks": bookmarks[:20],
        "recent_copilot_conversations": copilot_conversations,
        "recent_companies": recent_companies,
        "tasks": tasks[:20],
        "open_comments": open_comments[:20],
        "folders": store.list_folders(),
        "tags": store.list_tags(),
    }


def _template_body(template_id: str, *, company: str | None, title: str) -> str:
    subject = company or "Subject"
    shells = {
        "investment_memo": f"# Investment Memo — {subject}\n\n## Thesis\n{UNAVAILABLE_MESSAGE}\n\n## Strengths\n{UNAVAILABLE_MESSAGE}\n\n## Weaknesses\n{UNAVAILABLE_MESSAGE}\n\n## Risks\n{UNAVAILABLE_MESSAGE}\n\n## Valuation\n{UNAVAILABLE_MESSAGE}\n\n## AI Committee\n{UNAVAILABLE_MESSAGE}\n",
        "company_report": f"# Company Report — {subject}\n\n## Overview\n{UNAVAILABLE_MESSAGE}\n\n## Business Quality\n{UNAVAILABLE_MESSAGE}\n\n## Valuation\n{UNAVAILABLE_MESSAGE}\n\n## Risks\n{UNAVAILABLE_MESSAGE}\n",
        "quarterly_review": f"# Quarterly Review — {subject}\n\n## Highlights\n{UNAVAILABLE_MESSAGE}\n\n## KPI Changes\n{UNAVAILABLE_MESSAGE}\n\n## Outlook\n{UNAVAILABLE_MESSAGE}\n",
        "management_review": f"# Management Review — {subject}\n\n## Capital Allocation\n{UNAVAILABLE_MESSAGE}\n\n## Execution\n{UNAVAILABLE_MESSAGE}\n",
        "bull_case": f"# Bull Case — {subject}\n\n{UNAVAILABLE_MESSAGE}\n\n_Populate via Copilot / AI Committee — never invent numbers._\n",
        "bear_case": f"# Bear Case — {subject}\n\n{UNAVAILABLE_MESSAGE}\n\n_Populate via Copilot / AI Committee — never invent numbers._\n",
        "base_case": f"# Base Case — {subject}\n\n{UNAVAILABLE_MESSAGE}\n\n_Populate via Copilot / AI Committee — never invent numbers._\n",
        "meeting_notes": f"# Meeting Notes — {title}\n\n## Attendees\n\n## Discussion\n\n## Decisions\n\n## Actions\n",
        "checklist": f"# Research Checklist — {subject}\n\n- [ ] Financial statements authenticated\n- [ ] Valuation reviewed\n- [ ] Risks documented\n- [ ] Committee cases reviewed\n- [ ] MoS verified\n",
    }
    return shells.get(template_id, f"# {title}\n\n{UNAVAILABLE_MESSAGE}\n")


def _apply_template(store: Any, platform: Any, body: dict[str, Any]) -> dict[str, Any]:
    template_id = str(body.get("template_id") or "").strip()
    if template_id not in TEMPLATE_IDS:
        raise ValueError(f"unknown template: {template_id}")
    company = body.get("company")
    title = str(body.get("title") or template_id.replace("_", " ").title())
    content = _template_body(template_id, company=company, title=title)

    # Optionally enrich via Copilot 2.0 when analyse_response / mode provided
    if platform is not None and body.get("enrich_with_ai"):
        mode = {
            "investment_memo": "memo",
            "bull_case": "scenarios",
            "bear_case": "scenarios",
            "base_case": "scenarios",
            "company_report": "company",
        }.get(template_id, "chat")
        try:
            ai = platform.run_copilot_v2(
                message=f"Generate {template_id.replace('_', ' ')} for {company or 'subject'}",
                mode=mode,
                symbol=company,
                analyse_response=body.get("analyse_response"),
                research_object=body.get("research_object"),
                report=body.get("report"),
                committee_result=body.get("committee_result"),
            )
            answer = str(ai.get("answer") or "")
            if answer and answer != UNAVAILABLE_MESSAGE:
                content = answer
        except Exception:  # noqa: BLE001
            pass

    note = store.create_note(
        {
            "title": title,
            "body": content,
            "format": "markdown",
            "folder_id": body.get("folder_id"),
            "company": company,
            "portfolio_id": body.get("portfolio_id"),
            "research_object_id": body.get("research_object_id"),
            "document_refs": body.get("document_refs"),
            "attachments": body.get("attachments"),
            "tag_ids": body.get("tag_ids"),
            "created_by": body.get("created_by"),
            "ai_generated": bool(body.get("enrich_with_ai")),
            "status": "draft",
        }
    )
    return {"template_id": template_id, "note": note}


def _publish(store: Any, platform: Any, body: dict[str, Any]) -> dict[str, Any]:
    note_id = str(body.get("note_id") or "")
    note = store.get_note(note_id)
    if note is None:
        raise ValueError("note not found")
    target_status = str(body.get("status") or "review")
    if target_status not in _STATUS_TO_WORKFLOW:
        raise ValueError("invalid publish status")

    workflow_result = None
    if platform is not None:
        try:
            workflow_id = note.get("workflow_id")
            if not workflow_id:
                created = platform.apply_institutional_workflow(
                    action="create",
                    subject=f"research-note:{note_id}",
                    template_id=body.get("template_id") or "institutional_research_v1",
                    actor_id=body.get("actor_id"),
                    metadata={
                        "note_id": note_id,
                        "title": note.get("title"),
                        "source": "research_workspace",
                    },
                )
                workflow_result = created
                workflow_id = (
                    (created.get("workflow") or {}).get("workflow_id")
                    if isinstance(created, dict)
                    else None
                )
                if not workflow_id and isinstance(created, dict):
                    workflow_id = created.get("workflow_id")
            if workflow_id and target_status in {"review", "approved", "published"}:
                stage = _STATUS_TO_WORKFLOW[target_status]
                if stage != "draft":
                    workflow_result = platform.apply_institutional_workflow(
                        action="transition",
                        workflow_id=str(workflow_id),
                        to_stage=stage,
                        actor_id=body.get("actor_id"),
                        reason=body.get("reason") or "research_workspace_publish",
                    )
            note = store.update_note(
                note_id,
                {
                    "status": target_status,
                    "workflow_id": workflow_id,
                    "actor_id": body.get("actor_id"),
                },
            )
        except Exception as exc:  # noqa: BLE001
            # Still update local status; surface workflow failure honestly
            note = store.update_note(
                note_id,
                {"status": target_status, "actor_id": body.get("actor_id")},
            )
            return {
                "note": note,
                "workflow": None,
                "workflow_message": UNAVAILABLE_MESSAGE,
                "workflow_error": str(exc),
            }
    else:
        note = store.update_note(
            note_id,
            {"status": target_status, "actor_id": body.get("actor_id")},
        )

    return {"note": note, "workflow": workflow_result}


def _ai_assist(store: Any, platform: Any, body: dict[str, Any]) -> dict[str, Any]:
    if platform is None:
        return {"answer": UNAVAILABLE_MESSAGE, "unavailable": True}
    note_id = body.get("note_id")
    note = store.get_note(str(note_id)) if note_id else None
    instruction = str(body.get("instruction") or body.get("message") or "").strip()
    mode = str(body.get("mode") or "chat")
    if not instruction:
        instruction = "Summarize this research note."
    if note:
        instruction = (
            f"{instruction}\n\n---\nNote title: {note.get('title')}\n"
            f"Note body:\n{note.get('body')}\n"
        )
    try:
        result = platform.run_copilot_v2(
            message=instruction,
            mode=mode,
            symbol=body.get("company") or (note or {}).get("company"),
            conversation_id=body.get("conversation_id"),
            analyse_response=body.get("analyse_response"),
            research_object=body.get("research_object"),
            report=body.get("report"),
            portfolio=body.get("portfolio"),
            portfolio_intelligence=body.get("portfolio_intelligence"),
            committee_result=body.get("committee_result"),
            buffett_mode=bool(body.get("buffett_mode")),
        )
    except Exception as exc:  # noqa: BLE001
        return {
            "answer": UNAVAILABLE_MESSAGE,
            "unavailable": True,
            "error": str(exc),
        }

    apply = bool(body.get("apply_to_note")) and note is not None
    updated = None
    if apply:
        answer = str(result.get("answer") or "")
        if answer and answer != UNAVAILABLE_MESSAGE:
            updated = store.update_note(
                str(note_id),
                {
                    "body": answer,
                    "ai_generated": True,
                    "actor_id": body.get("actor_id") or "copilot_v2",
                },
            )
    return {
        "copilot": result,
        "answer": result.get("answer"),
        "unavailable": result.get("unavailable"),
        "note": updated,
        "sources": result.get("sources"),
    }


def _diff_versions(store: Any, body: dict[str, Any]) -> dict[str, Any]:
    note_id = str(body.get("note_id") or "")
    left_v = int(body.get("from_version") or 0)
    right_v = int(body.get("to_version") or 0)
    versions = store.list_versions(note_id)
    if not versions:
        raise ValueError("no versions")

    def pick(v: int) -> dict[str, Any] | None:
        for item in versions:
            if int(item.get("version") or 0) == v:
                return item
        return None

    left = pick(left_v)
    right = pick(right_v)
    if left is None or right is None:
        raise ValueError("version not found")
    left_lines = str(left.get("body") or "").splitlines()
    right_lines = str(right.get("body") or "").splitlines()
    # Simple line diff (no new diff engine — orchestration only)
    max_len = max(len(left_lines), len(right_lines))
    hunks = []
    for i in range(max_len):
        a = left_lines[i] if i < len(left_lines) else None
        b = right_lines[i] if i < len(right_lines) else None
        if a == b:
            continue
        hunks.append({"line": i + 1, "from": a, "to": b})
    return {
        "note_id": note_id,
        "from_version": left_v,
        "to_version": right_v,
        "title_changed": left.get("title") != right.get("title"),
        "hunks": hunks[:200],
        "from_title": left.get("title"),
        "to_title": right.get("title"),
    }
