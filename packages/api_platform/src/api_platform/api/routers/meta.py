"""Version and capabilities metadata routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

import api_platform
from api_platform.api.composition_schemas import (
    CapabilitiesResponse,
    VersionResponse,
)
from api_platform.api.dependencies import ApiState, get_api_state
from dsp_platform import (
    COMPOSITION_PIPELINE_VERSION,
    composition_capability_manifest,
)

router = APIRouter(tags=["meta"])

DOCS_VERSION = "1.3.32"


@router.get("/version", response_model=VersionResponse)
def version(state: ApiState = Depends(get_api_state)) -> VersionResponse:
    info = state.platform.get_platform_info()
    manifest = composition_capability_manifest()
    return VersionResponse(
        api_version=state.api_version,
        api_package_version=api_platform.__version__,
        platform_version=info.version,
        pipeline_version=COMPOSITION_PIPELINE_VERSION,
        docs_version=DOCS_VERSION,
        package_versions=dict(manifest.get("package_versions") or {}),
    )


@router.get("/capabilities", response_model=CapabilitiesResponse)
def capabilities(state: ApiState = Depends(get_api_state)) -> CapabilitiesResponse:
    info = state.platform.get_platform_info()
    manifest = composition_capability_manifest()
    return CapabilitiesResponse(
        analytical_modules=list(manifest.get("analytical_modules") or []),
        supported_reports=list(manifest.get("supported_reports") or []),
        pipeline_stages=list(manifest.get("pipeline_stages") or []),
        pipeline_version=str(manifest.get("pipeline_version") or ""),
        platform_version=info.version,
        api_version=state.api_version,
        package_versions=dict(manifest.get("package_versions") or {}),
        platform_capabilities=list(info.capabilities or []),
    )
