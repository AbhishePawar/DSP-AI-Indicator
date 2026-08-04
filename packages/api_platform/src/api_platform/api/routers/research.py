"""Additive Research Object routes (EPIC-R001).

Aggregates existing D005 + analysis payloads only — never re-runs engines.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from api_platform.api.dependencies import ApiState, get_api_state

router = APIRouter(tags=["research"])


class ResearchObjectRequest(BaseModel):
    """Build request — pass through existing outputs; no new calculations."""

    symbol: str = Field(..., min_length=1, max_length=32)
    company: str | None = Field(None, max_length=256)
    exchange: str | None = Field(None, max_length=32)
    correlation_id: str | None = Field(None, max_length=128)
    data_bundle: dict[str, Any] | None = None
    analysis_payload: dict[str, Any] | None = None
    valuation_signals: dict[str, Any] | None = None
    fetch_data_bundle: bool = True


@router.get("/research/object/schema")
def research_object_schema(state: ApiState = Depends(get_api_state)) -> dict[str, Any]:
    """Discover Research Object schema (read-only)."""
    return {
        "ok": True,
        "schema": state.platform.research_object_schema(),
    }


@router.get("/research/report/schema")
def research_report_schema(state: ApiState = Depends(get_api_state)) -> dict[str, Any]:
    """Discover Institutional Research Report schema (read-only)."""
    return {
        "ok": True,
        "schema": state.platform.institutional_report_schema(),
    }


@router.get("/research/export/schema")
def research_export_schema(state: ApiState = Depends(get_api_state)) -> dict[str, Any]:
    """Discover Institutional Export schema (read-only)."""
    return {
        "ok": True,
        "schema": state.platform.institutional_export_schema(),
    }


@router.get("/research/archive/schema")
def research_archive_schema(state: ApiState = Depends(get_api_state)) -> dict[str, Any]:
    """Discover Research Archive schema (read-only)."""
    return {
        "ok": True,
        "schema": state.platform.research_archive_schema(),
    }


@router.get("/research/diff/schema")
def research_diff_schema(state: ApiState = Depends(get_api_state)) -> dict[str, Any]:
    """Discover Research Diff schema (read-only)."""
    return {
        "ok": True,
        "schema": state.platform.research_diff_schema(),
    }


@router.get("/research/copilot/schema")
def research_copilot_schema(state: ApiState = Depends(get_api_state)) -> dict[str, Any]:
    """Discover AI Research Copilot schema (read-only)."""
    return {
        "ok": True,
        "schema": state.platform.research_copilot_schema(),
    }


class ResearchCopilotAskRequest(BaseModel):
    """Ask the Research Copilot using platform artifacts only."""

    question: str = Field(..., min_length=1, max_length=4000)
    research_object: dict[str, Any] | None = None
    report: dict[str, Any] | None = None
    archive_snapshot: dict[str, Any] | None = None
    research_diff: dict[str, Any] | None = None
    snapshot_id: str | None = Field(None, max_length=128)
    conversation_id: str | None = Field(None, max_length=128)
    response_id: str | None = Field(None, max_length=128)
    created_at: str | None = Field(None, max_length=64)


@router.post("/research/copilot/ask")
def research_copilot_ask(
    body: ResearchCopilotAskRequest,
    state: ApiState = Depends(get_api_state),
) -> JSONResponse:
    """Grounded Q&A over R001/R002/R004/R005 — never fabricates or recalculates."""
    try:
        result = state.platform.ask_research_copilot(
            body.question,
            research_object=body.research_object,
            report=body.report,
            archive_snapshot=body.archive_snapshot,
            research_diff=body.research_diff,
            snapshot_id=body.snapshot_id,
            conversation_id=body.conversation_id,
            response_id=body.response_id,
            created_at=body.created_at,
        )
    except KeyError as exc:
        return JSONResponse(
            status_code=404,
            content={"ok": False, "error": str(exc), "message": "Data unavailable."},
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
    return JSONResponse({"ok": True, "response": result, "message": None})


class ResearchDiffRequest(BaseModel):
    """Compare two archived snapshots structurally (EPIC-R005)."""

    left_snapshot_id: str = Field(..., min_length=1, max_length=128)
    right_snapshot_id: str = Field(..., min_length=1, max_length=128)
    diff_id: str | None = Field(None, max_length=128)
    created_at: str | None = Field(None, max_length=64)


@router.post("/research/diff")
def research_diff(
    body: ResearchDiffRequest,
    state: ApiState = Depends(get_api_state),
) -> JSONResponse:
    """Deterministic structural diff of two R004 snapshots — no interpretation."""
    try:
        result = state.platform.diff_research_snapshots(
            body.left_snapshot_id,
            body.right_snapshot_id,
            diff_id=body.diff_id,
            created_at=body.created_at,
        )
    except KeyError as exc:
        return JSONResponse(
            status_code=404,
            content={"ok": False, "error": str(exc), "message": "Data unavailable."},
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
    return JSONResponse({"ok": True, "diff": result, "message": None})


class ArchiveSnapshotRequest(BaseModel):
    """Archive an existing R001 / R002 / R003 payload."""

    kind: str = Field(..., max_length=64)
    payload: dict[str, Any]
    lineage_id: str | None = Field(None, max_length=128)
    parent_snapshot_id: str | None = Field(None, max_length=128)
    snapshot_id: str | None = Field(None, max_length=128)
    archived_at: str | None = Field(None, max_length=64)
    provenance: dict[str, Any] | None = None


class ArchiveCompareRequest(BaseModel):
    left_snapshot_id: str = Field(..., min_length=1, max_length=128)
    right_snapshot_id: str = Field(..., min_length=1, max_length=128)


@router.post("/research/archive/snapshots")
def archive_snapshot(
    body: ArchiveSnapshotRequest,
    state: ApiState = Depends(get_api_state),
) -> JSONResponse:
    """Create an immutable archived snapshot (EPIC-R004)."""
    try:
        snap = state.platform.archive_research_snapshot(
            body.kind,
            body.payload,
            lineage_id=body.lineage_id,
            parent_snapshot_id=body.parent_snapshot_id,
            snapshot_id=body.snapshot_id,
            archived_at=body.archived_at,
            provenance=body.provenance,
        )
    except KeyError as exc:
        return JSONResponse(
            status_code=404,
            content={"ok": False, "error": str(exc), "message": "Data unavailable."},
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
    return JSONResponse({"ok": True, "snapshot": snap, "message": None})


@router.get("/research/archive/snapshots/{snapshot_id}")
def get_archived_snapshot(
    snapshot_id: str,
    state: ApiState = Depends(get_api_state),
) -> JSONResponse:
    """Read-only retrieval of an archived snapshot."""
    try:
        snap = state.platform.get_research_snapshot(snapshot_id)
    except KeyError as exc:
        return JSONResponse(
            status_code=404,
            content={"ok": False, "error": str(exc), "message": "Data unavailable."},
        )
    except Exception as exc:  # noqa: BLE001
        return JSONResponse(
            status_code=503,
            content={"ok": False, "error": str(exc), "message": "Data unavailable."},
        )
    return JSONResponse({"ok": True, "snapshot": snap, "message": None})


@router.get("/research/archive/lineages/{lineage_id}/history")
def archive_version_history(
    lineage_id: str,
    state: ApiState = Depends(get_api_state),
) -> JSONResponse:
    """Return immutable version history for a lineage."""
    history = state.platform.list_research_version_history(lineage_id)
    return JSONResponse(
        {"ok": True, "lineage_id": lineage_id, "history": history, "message": None}
    )


@router.post("/research/archive/compare")
def compare_archived_snapshots(
    body: ArchiveCompareRequest,
    state: ApiState = Depends(get_api_state),
) -> JSONResponse:
    """Compare two snapshots — integrity / version metadata only."""
    try:
        comparison = state.platform.compare_research_snapshots(
            body.left_snapshot_id, body.right_snapshot_id
        )
    except KeyError as exc:
        return JSONResponse(
            status_code=404,
            content={"ok": False, "error": str(exc), "message": "Data unavailable."},
        )
    except Exception as exc:  # noqa: BLE001
        return JSONResponse(
            status_code=503,
            content={"ok": False, "error": str(exc), "message": "Data unavailable."},
        )
    return JSONResponse({"ok": True, "comparison": comparison, "message": None})


class ArchiveRetentionRequest(BaseModel):
    snapshot_id: str = Field(..., min_length=1, max_length=128)


@router.post("/research/archive/retention/evaluate")
def evaluate_archive_retention(
    body: ArchiveRetentionRequest,
    state: ApiState = Depends(get_api_state),
) -> JSONResponse:
    """Advisory retention evaluation — never mutates archived content."""
    try:
        decision = state.platform.evaluate_research_retention(body.snapshot_id)
    except KeyError as exc:
        return JSONResponse(
            status_code=404,
            content={"ok": False, "error": str(exc), "message": "Data unavailable."},
        )
    except Exception as exc:  # noqa: BLE001
        return JSONResponse(
            status_code=503,
            content={"ok": False, "error": str(exc), "message": "Data unavailable."},
        )
    return JSONResponse({"ok": True, "retention": decision, "message": None})


class ResearchReportRequest(BaseModel):
    """Generate report from an existing Research Object only."""

    research_object: dict[str, Any]
    report_id: str | None = Field(None, max_length=128)
    generated_at: str | None = Field(None, max_length=64)


class ResearchExportRequest(BaseModel):
    """Export an existing Institutional Report only."""

    report: dict[str, Any]
    format: str = Field("json", max_length=16)
    export_id: str | None = Field(None, max_length=128)
    exported_at: str | None = Field(None, max_length=64)


@router.post("/research/export")
def export_research_report(
    body: ResearchExportRequest,
    state: ApiState = Depends(get_api_state),
) -> JSONResponse:
    """Export Institutional Report to json/csv/xlsx/pdf (EPIC-R003).

    Additive — Report is the sole source. No calculations or reformatting.
    """
    try:
        artifact = state.platform.export_institutional_report(
            body.report,
            format=body.format,
            export_id=body.export_id,
            exported_at=body.exported_at,
        )
    except ValueError as exc:
        return JSONResponse(
            status_code=400,
            content={
                "ok": False,
                "error": str(exc),
                "message": "Data unavailable.",
            },
        )
    except Exception as exc:  # noqa: BLE001
        return JSONResponse(
            status_code=503,
            content={
                "ok": False,
                "error": str(exc),
                "message": "Data unavailable.",
            },
        )

    return JSONResponse(
        {
            "ok": True,
            "export": artifact,
            "message": None,
        }
    )


@router.post("/research/report")
def generate_research_report(
    body: ResearchReportRequest,
    state: ApiState = Depends(get_api_state),
) -> JSONResponse:
    """Generate Institutional Research Report from Research Object v1.0.0 only.

    Additive — does not alter ``/analyse`` or Research Object builder.
    No calculations, scoring, or valuation.
    """
    try:
        report = state.platform.generate_institutional_report(
            body.research_object,
            report_id=body.report_id,
            generated_at=body.generated_at,
        )
    except ValueError as exc:
        return JSONResponse(
            status_code=400,
            content={
                "ok": False,
                "error": str(exc),
                "message": "Data unavailable.",
            },
        )
    except Exception as exc:  # noqa: BLE001
        return JSONResponse(
            status_code=503,
            content={
                "ok": False,
                "error": str(exc),
                "message": "Data unavailable.",
            },
        )

    meta = body.research_object.get("metadata") if isinstance(
        body.research_object.get("metadata"), dict
    ) else {}
    symbol = meta.get("ticker") if isinstance(meta, dict) else None

    return JSONResponse(
        {
            "ok": True,
            "symbol": symbol,
            "report": report,
            "message": None,
        }
    )


@router.post("/research/object")
def build_research_object(
    body: ResearchObjectRequest,
    state: ApiState = Depends(get_api_state),
) -> JSONResponse:
    """Build canonical immutable Research Object from existing outputs.

    Additive — does not alter ``/analyse``. When ``data_bundle`` is omitted and
    ``fetch_data_bundle`` is True, loads D005 unified bundle. Analysis must be
    supplied by the caller (never re-scored here).
    """
    try:
        research = state.platform.build_research_object(
            body.symbol,
            data_bundle=body.data_bundle,
            analysis_payload=body.analysis_payload,
            valuation_signals=body.valuation_signals,
            company=body.company,
            exchange=body.exchange,
            correlation_id=body.correlation_id,
            fetch_data_bundle=body.fetch_data_bundle,
        )
    except ValueError as exc:
        return JSONResponse(
            status_code=400,
            content={
                "ok": False,
                "error": str(exc),
                "message": "Data unavailable.",
            },
        )
    except Exception as exc:  # noqa: BLE001
        return JSONResponse(
            status_code=503,
            content={
                "ok": False,
                "error": str(exc),
                "message": "Data unavailable.",
            },
        )

    return JSONResponse(
        {
            "ok": True,
            "symbol": body.symbol.strip().upper(),
            "research_object": research,
            "message": None,
        }
    )
