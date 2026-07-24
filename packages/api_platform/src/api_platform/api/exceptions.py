"""API Platform exceptions — HTTP mapping only (K1.1)."""

from __future__ import annotations

from dsp_platform import PlatformError

__all__ = [
    "ApiError",
    "ApiNotFoundError",
    "ApiValidationError",
    "PlatformError",
]


class ApiError(Exception):
    """Base API-layer error (no business semantics)."""

    def __init__(self, message: str, *, status_code: int = 500) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class ApiValidationError(ApiError):
    """Request failed API-layer validation before platform delegation."""

    def __init__(self, message: str) -> None:
        super().__init__(message, status_code=422)


class ApiNotFoundError(ApiError):
    """Requested resource is not available in the ephemeral API registry."""

    def __init__(self, message: str) -> None:
        super().__init__(message, status_code=404)
