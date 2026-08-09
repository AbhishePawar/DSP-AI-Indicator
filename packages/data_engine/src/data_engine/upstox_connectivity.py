"""U0 — Upstox Analytics Token connectivity (secure credential path only).

Proves server-side Bearer auth against one read-only Market Data GET.
Does NOT resolve companies, map tickers, load fundamentals, or alter
valuation / Buffett / recommendation pipelines.

Credential (canonical, server-side only):
  DSP_UPSTOX_ANALYTICS_TOKEN

Never log, return, or persist the token value.
Presence of a token does NOT clear G2.
"""

from __future__ import annotations

import os
import time
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from data_engine.connector_framework.http import JsonHttpClient, UrllibJsonHttpClient
from data_engine.connector_framework.production_profile import is_production_environment
from data_engine.exceptions import ProviderRequestError
from data_engine.upstox_investment import (
    UPSTOX_BASE_URL,
    resolve_upstox_analytics_token,
)

__all__ = [
    "UPSTOX_ANALYTICS_TOKEN_ENV",
    "UPSTOX_CONNECTIVITY_ENDPOINT",
    "UPSTOX_CONNECTIVITY_PROBE_INSTRUMENT_KEY",
    "UpstoxConnectivityClient",
    "UpstoxConnectivityResult",
    "UpstoxConnectivityStatus",
    "redact_secret",
    "resolve_u0_upstox_analytics_token",
]

# Canonical env name for U0 / private-beta docs. Existing
# ``resolve_upstox_analytics_token`` also accepts a legacy alias; U0 operators
# should configure this name only (do not invent additional synonyms).
UPSTOX_ANALYTICS_TOKEN_ENV = "DSP_UPSTOX_ANALYTICS_TOKEN"

# Fixed Market Data LTP probe — not a company resolver, not a frontend mapping.
UPSTOX_CONNECTIVITY_PROBE_INSTRUMENT_KEY = "NSE_INDEX|Nifty 50"
UPSTOX_CONNECTIVITY_ENDPOINT = "market-quote/ltp"


def redact_secret(text: str, secret: str | None) -> str:
    """Replace a secret substring if present; never useful for logging the secret."""
    if not secret or not text:
        return text
    if secret in text:
        return text.replace(secret, "***REDACTED***")
    return text


def resolve_u0_upstox_analytics_token(
    environ: Mapping[str, str] | None = None,
) -> str:
    """Resolve the Analytics Token for U0 without exposing the value.

    Prefers the canonical ``DSP_UPSTOX_ANALYTICS_TOKEN``. Reuses the shared
    resolver so a previously documented alias still works, but docs/templates
    only advertise the canonical name.
    """
    env = environ if environ is not None else os.environ
    primary = str(env.get(UPSTOX_ANALYTICS_TOKEN_ENV) or "").strip()
    if primary:
        return primary
    return resolve_upstox_analytics_token(env)


@dataclass(frozen=True, slots=True)
class UpstoxConnectivityStatus:
    """Configuration / health surface — no secrets."""

    provider_id: str
    configured: bool
    healthy: bool
    authenticated: bool
    detail: str


@dataclass(frozen=True, slots=True)
class UpstoxConnectivityResult:
    """Outcome of one read-only connectivity probe — no secrets, no quotes as facts."""

    ok: bool
    provider: str
    endpoint_category: str
    endpoint: str
    http_success: bool
    status_code: int | None
    latency_ms: float | None
    retrieved_at: datetime
    response_shape: dict[str, Any]
    detail: str


@dataclass
class UpstoxConnectivityClient:
    """Smallest server-side Upstox client: Bearer auth + one Market Data probe."""

    access_token: str | None = None
    base_url: str = UPSTOX_BASE_URL
    timeout_seconds: float = 15.0
    http_client: JsonHttpClient | None = None
    max_attempts: int = 2
    provider_id: str = "upstox_connectivity"
    provider_name: str = "Upstox"

    def __post_init__(self) -> None:
        if self.access_token is None:
            object.__setattr__(
                self, "access_token", resolve_u0_upstox_analytics_token()
            )
        token = str(self.access_token or "").strip()
        object.__setattr__(self, "access_token", token)
        attempts = max(1, min(int(self.max_attempts), 3))
        object.__setattr__(self, "max_attempts", attempts)

    def _client(self) -> JsonHttpClient:
        return self.http_client or UrllibJsonHttpClient(
            timeout_seconds=self.timeout_seconds
        )

    def configured(self) -> bool:
        return bool(self.access_token)

    def status(self) -> UpstoxConnectivityStatus:
        if not self.configured():
            return UpstoxConnectivityStatus(
                provider_id=self.provider_id,
                configured=False,
                healthy=False,
                authenticated=False,
                detail="configuration missing: DSP_UPSTOX_ANALYTICS_TOKEN",
            )
        return UpstoxConnectivityStatus(
            provider_id=self.provider_id,
            configured=True,
            healthy=True,
            authenticated=True,
            detail="analytics token configured (value not reported)",
        )

    def authorization_headers(self) -> dict[str, str]:
        if not self.configured():
            raise ProviderRequestError(
                "Upstox connectivity requires DSP_UPSTOX_ANALYTICS_TOKEN"
            )
        # Token is placed only in the Authorization header for the HTTP client —
        # callers must never log this mapping.
        return {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.access_token}",
        }

    def _safe_error(self, exc: BaseException) -> ProviderRequestError:
        raw = redact_secret(str(exc), self.access_token)
        raw = redact_secret(raw, f"Bearer {self.access_token}" if self.access_token else None)
        return ProviderRequestError(redact_secret(raw, self.access_token))

    def probe_market_data(
        self,
        *,
        instrument_key: str = UPSTOX_CONNECTIVITY_PROBE_INSTRUMENT_KEY,
    ) -> UpstoxConnectivityResult:
        """One read-only Market Data LTP GET to prove Bearer authentication.

        Uses a fixed index instrument key (not a company resolver / ticker map).
        """
        retrieved_at = datetime.now(tz=UTC)
        endpoint = UPSTOX_CONNECTIVITY_ENDPOINT
        if not self.configured():
            if is_production_environment():
                detail = (
                    "production fail-closed: Upstox analytics token absent — "
                    "no fixture substitution"
                )
            else:
                detail = "Upstox analytics token absent — provider unavailable"
            return UpstoxConnectivityResult(
                ok=False,
                provider=self.provider_name,
                endpoint_category="market_data",
                endpoint=endpoint,
                http_success=False,
                status_code=None,
                latency_ms=None,
                retrieved_at=retrieved_at,
                response_shape={},
                detail=detail,
            )

        url = f"{self.base_url.rstrip('/')}/{endpoint}"
        if not url.lower().startswith("https://"):
            return UpstoxConnectivityResult(
                ok=False,
                provider=self.provider_name,
                endpoint_category="market_data",
                endpoint=endpoint,
                http_success=False,
                status_code=None,
                latency_ms=None,
                retrieved_at=retrieved_at,
                response_shape={},
                detail="HTTPS required for Upstox connectivity",
            )
        params = {"instrument_key": instrument_key}
        last_error: str | None = None
        started = time.perf_counter()
        for attempt in range(1, self.max_attempts + 1):
            try:
                payload = self._client().get_json(
                    url,
                    params=params,
                    headers=self.authorization_headers(),
                )
                latency_ms = round((time.perf_counter() - started) * 1000.0, 2)
                shape = _response_shape(payload)
                ok = isinstance(payload, Mapping) and str(
                    payload.get("status") or ""
                ).lower() in {"", "success"}
                return UpstoxConnectivityResult(
                    ok=ok,
                    provider=self.provider_name,
                    endpoint_category="market_data",
                    endpoint=endpoint,
                    http_success=True,
                    status_code=200,
                    latency_ms=latency_ms,
                    retrieved_at=retrieved_at,
                    response_shape=shape,
                    detail="authenticated market-data probe succeeded",
                )
            except ProviderRequestError as exc:
                safe = self._safe_error(exc)
                last_error = str(safe)
                # Do not retry auth failures or hard client errors indefinitely.
                msg = str(safe).lower()
                if "429" in msg or "rate limited" in msg:
                    if attempt >= self.max_attempts:
                        break
                    continue
                if "401" in msg or "403" in msg or "authentication failed" in msg:
                    break
                if attempt >= self.max_attempts:
                    break
            except Exception as exc:  # noqa: BLE001 — convert to safe provider error
                safe = self._safe_error(exc)
                last_error = str(safe)
                break

        latency_ms = round((time.perf_counter() - started) * 1000.0, 2)
        status_code = _guess_status(last_error)
        return UpstoxConnectivityResult(
            ok=False,
            provider=self.provider_name,
            endpoint_category="market_data",
            endpoint=endpoint,
            http_success=False,
            status_code=status_code,
            latency_ms=latency_ms,
            retrieved_at=retrieved_at,
            response_shape={},
            detail=last_error or "Upstox connectivity probe failed",
        )


def _guess_status(detail: str | None) -> int | None:
    if not detail:
        return None
    for code in (429, 401, 403, 404, 500, 502, 503):
        if str(code) in detail:
            return code
    return None


def _response_shape(payload: Any) -> dict[str, Any]:
    """Non-sensitive structural summary only (types / key names)."""
    if isinstance(payload, Mapping):
        keys = sorted(str(k) for k in payload.keys())
        data = payload.get("data")
        data_info: dict[str, Any]
        if isinstance(data, Mapping):
            data_info = {
                "type": "object",
                "key_count": len(data),
                "keys_sample": sorted(str(k) for k in list(data.keys())[:5]),
            }
        elif isinstance(data, list):
            data_info = {"type": "array", "length": len(data)}
        else:
            data_info = {"type": type(data).__name__}
        return {
            "type": "object",
            "keys": keys,
            "status": str(payload.get("status")) if "status" in payload else None,
            "data": data_info,
        }
    if isinstance(payload, list):
        return {"type": "array", "length": len(payload)}
    return {"type": type(payload).__name__}
