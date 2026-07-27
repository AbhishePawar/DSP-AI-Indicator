"""Metrics routes — Prometheus-compatible export (EPIC-013 RC1)."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

from api_platform.api.ops import metrics_registry

router = APIRouter(tags=["metrics"])


@router.get("/metrics")
def metrics() -> PlainTextResponse:
    """Prometheus-compatible metrics scrape endpoint."""
    return PlainTextResponse(
        metrics_registry.render_prometheus(),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )
