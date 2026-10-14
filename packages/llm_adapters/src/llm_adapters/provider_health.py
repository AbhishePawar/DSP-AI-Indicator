"""Centralized Provider Health, Diagnostics, and Error Classification.

Provides structured health states, sanitized error descriptions (zero secret leakage),
and actionable remediation recommendations for administrators.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class ProviderHealthStatus(str, Enum):
    """Normalized provider operational status."""

    NOT_CONFIGURED = "not_configured"
    CONFIGURED_UNTESTED = "configured_untested"
    HEALTHY = "healthy"
    AUTH_FAILURE = "auth_failure"
    EXPIRED_TOKEN = "expired_token"
    PERMISSION_FAILURE = "permission_failure"
    RATE_LIMITED = "rate_limited"
    QUOTA_EXHAUSTED = "quota_exhausted"
    TIMEOUT = "timeout"
    PROVIDER_OUTAGE = "provider_outage"
    CONFIG_ERROR = "config_error"
    NETWORK_ERROR = "network_error"


@dataclass(frozen=True, slots=True)
class ProviderDiagnostics:
    """Sanitized diagnostics for administrator inspection. Never contains secrets."""

    status: ProviderHealthStatus
    sanitized_reason: str
    recommended_action: str
    is_operational: bool
    retryable: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "sanitized_reason": self.sanitized_reason,
            "recommended_action": self.recommended_action,
            "is_operational": self.is_operational,
            "retryable": self.retryable,
        }


def classify_provider_error(
    error: Exception | str | None,
    *,
    status_code: int | None = None,
    provider_id: str = "generic",
) -> ProviderDiagnostics:
    """Classify an upstream provider error into safe diagnostics and action items."""
    msg = str(error or "").strip()
    low = msg.lower()

    # 1. Authentication / Invalid Key
    if (
        status_code in (401, 403)
        or "api key not valid" in low
        or "invalid api key" in low
        or "unauthorized" in low
        or "authentication failed" in low
        or "invalid_api_key" in low
        or "bad credentials" in low
    ):
        if "expired" in low or "token has expired" in low or "jwt expired" in low:
            return ProviderDiagnostics(
                status=ProviderHealthStatus.EXPIRED_TOKEN,
                sanitized_reason="Upstream credential or OAuth token has expired.",
                recommended_action=f"Obtain a fresh access token from {provider_id.upper()} and save it in the Admin Panel.",
                is_operational=False,
                retryable=False,
            )
        if "permission" in low or "forbidden" in low or status_code == 403:
            return ProviderDiagnostics(
                status=ProviderHealthStatus.PERMISSION_FAILURE,
                sanitized_reason="Credential lacks necessary permissions or access tier for the requested operation.",
                recommended_action=f"Verify project scopes, permissions, and billing tier in the {provider_id.upper()} console.",
                is_operational=False,
                retryable=False,
            )
        return ProviderDiagnostics(
            status=ProviderHealthStatus.AUTH_FAILURE,
            sanitized_reason="Upstream authentication failed: invalid API key or credentials.",
            recommended_action=f"Check and replace the API key for {provider_id.upper()} in the Admin Panel.",
            is_operational=False,
            retryable=False,
        )

    # 2. Rate Limits & Quota
    if (
        status_code == 429
        or "rate limit" in low
        or "quota exceeded" in low
        or "insufficient_quota" in low
        or "resource exhausted" in low
    ):
        if "quota" in low or "insufficient_quota" in low or "credit balance" in low:
            return ProviderDiagnostics(
                status=ProviderHealthStatus.QUOTA_EXHAUSTED,
                sanitized_reason="Upstream account balance or quota has been exhausted.",
                recommended_action=f"Add billing credits or increase quota limits in the {provider_id.upper()} account dashboard.",
                is_operational=False,
                retryable=False,
            )
        return ProviderDiagnostics(
            status=ProviderHealthStatus.RATE_LIMITED,
            sanitized_reason="Upstream rate limit reached. Requests are being throttled.",
            recommended_action="Wait for the rate-limit window to reset, or configure a fallback provider in Routing settings.",
            is_operational=True,
            retryable=True,
        )

    # 3. Timeout
    if (
        status_code in (408, 504)
        or "timeout" in low
        or "timed out" in low
        or "deadline exceeded" in low
    ):
        return ProviderDiagnostics(
            status=ProviderHealthStatus.TIMEOUT,
            sanitized_reason="Request to upstream provider timed out.",
            recommended_action="Check provider service status or increase timeout limit in Provider Configuration.",
            is_operational=False,
            retryable=True,
        )

    # 4. Outage / Upstream 5xx
    if (
        status_code in (500, 502, 503)
        or "bad gateway" in low
        or "service unavailable" in low
        or "overloaded" in low
    ):
        return ProviderDiagnostics(
            status=ProviderHealthStatus.PROVIDER_OUTAGE,
            sanitized_reason=f"{provider_id.upper()} service is temporarily unavailable or experiencing downtime.",
            recommended_action="Enable approved fallback provider while upstream provider recovers.",
            is_operational=False,
            retryable=True,
        )

    # 5. Invalid Model / Config
    if (
        status_code == 404
        or "model not found" in low
        or "does not exist" in low
        or "invalid model" in low
        or "unsupported model" in low
    ):
        return ProviderDiagnostics(
            status=ProviderHealthStatus.CONFIG_ERROR,
            sanitized_reason="Requested model name is not recognized or not available to this account.",
            recommended_action=f"Select an approved model for {provider_id.upper()} from the model selection dropdown.",
            is_operational=False,
            retryable=False,
        )

    # 6. Network / DNS error
    if "connect" in low or "name resolution" in low or "getaddrinfo" in low:
        return ProviderDiagnostics(
            status=ProviderHealthStatus.NETWORK_ERROR,
            sanitized_reason="Failed to establish network connection to upstream API host.",
            recommended_action="Verify outbound internet connectivity and firewall rules from the application server.",
            is_operational=False,
            retryable=True,
        )

    # Default fallback
    clean_msg = msg[:120].strip() or "Unknown upstream error."
    return ProviderDiagnostics(
        status=ProviderHealthStatus.CONFIG_ERROR,
        sanitized_reason=f"Provider error: {clean_msg}",
        recommended_action="Inspect provider documentation or verify credentials in Admin Panel.",
        is_operational=False,
        retryable=False,
    )
