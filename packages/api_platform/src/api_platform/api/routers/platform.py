"""Platform info routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from api_platform.api.dependencies import ApiState, get_api_state
from api_platform.api.schemas import PlatformInfoResponse

router = APIRouter(tags=["platform"])


@router.get("/platform", response_model=PlatformInfoResponse)
def platform_info(state: ApiState = Depends(get_api_state)) -> PlatformInfoResponse:
    """Return immutable platform metadata / capability discovery."""
    info = state.platform.get_platform_info()
    return PlatformInfoResponse(
        name=info.name,
        version=info.version,
        status=info.status.value,
        environment=info.environment,
        capabilities=list(info.capabilities),
        registered_services=list(info.registered_services),
        generated_at=info.generated_at,
        notes=list(info.notes),
        api_version=state.api_version,
    )
