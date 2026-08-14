"""Authenticated corporate action adapters (EPIC-D003).

Retrieval only — never invents events or adjusts prices.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import date, datetime
from threading import Lock
from typing import Any, Mapping
from urllib.parse import urlencode

from contracts.domain.instrument import Instrument
from data_engine.corporate_actions.models import (
    ACTION_TYPES,
    AuthenticatedCorporateAction,
    AuthenticatedCorporateActions,
    CorporateActionCompanyIdentity,
    CorporateActionField,
    CorporateActionProvenance,
    utc_now,
)
from data_engine.corporate_actions.service import (
    CorporateActionPort,
    CorporateActionProviderHealth,
    CorporateActionQuery,
)
from data_engine.corporate_actions.validation import (
    validate_authenticated_corporate_actions,
)
from data_engine.exceptions import InvalidProviderDataError, ProviderRequestError

__all__ = [
    "ConfiguredHttpCorporateActionAdapter",
    "InMemoryAuthenticatedCorporateActionAdapter",
    "NullAuthenticatedCorporateActionAdapter",
    "build_actions_from_mapping",
    "build_default_corporate_action_adapter_from_env",
    "build_event_from_mapping",
]


def _parse_date(value: Any) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    text = str(value).strip()
    if not text:
        return None
    return date.fromisoformat(text[:10])


def _sf(payload: Mapping[str, Any], *keys: str) -> CorporateActionField:
    for key in keys:
        if key in payload and payload[key] is not None:
            return CorporateActionField.of(payload[key])
    return CorporateActionField.missing()


def _sort_key(event: AuthenticatedCorporateAction) -> tuple:
    """Deterministic newest-first ordering by primary date then action_id."""
    primary = (
        event.effective_date
        or event.ex_date
        or event.record_date
        or event.payment_date
        or event.announcement_date
        or date.min
    )
    return (primary, event.action_id)


def build_event_from_mapping(
    payload: Mapping[str, Any], *, default_symbol: str
) -> AuthenticatedCorporateAction:
    """Deterministic map of vendor-neutral event dict → AuthenticatedCorporateAction."""
    action_type = str(payload.get("action_type", "")).strip().lower()
    if action_type not in ACTION_TYPES:
        raise InvalidProviderDataError(f"unknown action_type: {action_type!r}")
    action_id = str(payload.get("action_id") or "").strip()
    if not action_id:
        # Deterministic synthetic id from type + dates + symbol — still provider data,
        # not invented economics; required for identity when vendor omits id.
        raise InvalidProviderDataError("event missing action_id")

    symbol = str(payload.get("symbol") or default_symbol).strip().upper()
    currency = payload.get("currency")
    currency_norm = None
    if currency is not None and str(currency).strip():
        currency_norm = str(currency).strip().upper()

    meta_raw = payload.get("metadata")
    metadata: dict[str, str] = {}
    if isinstance(meta_raw, Mapping):
        metadata = {str(k): str(v) for k, v in meta_raw.items()}

    return AuthenticatedCorporateAction(
        action_id=action_id,
        action_type=action_type,
        symbol=symbol,
        description=(
            str(payload["description"]) if payload.get("description") else None
        ),
        effective_date=_parse_date(payload.get("effective_date")),
        ex_date=_parse_date(payload.get("ex_date")),
        record_date=_parse_date(payload.get("record_date")),
        payment_date=_parse_date(payload.get("payment_date")),
        announcement_date=_parse_date(payload.get("announcement_date")),
        currency=currency_norm,
        ratio_from=_sf(payload, "ratio_from"),
        ratio_to=_sf(payload, "ratio_to"),
        amount=_sf(payload, "amount", "dividend_amount"),
        shares=_sf(payload, "shares"),
        old_symbol=(
            str(payload["old_symbol"]).strip().upper()
            if payload.get("old_symbol")
            else None
        ),
        new_symbol=(
            str(payload["new_symbol"]).strip().upper()
            if payload.get("new_symbol")
            else None
        ),
        status=str(payload["status"]) if payload.get("status") else None,
        metadata=metadata,
    )


def build_actions_from_mapping(
    *,
    symbol: str,
    payload: Mapping[str, Any],
    provenance: CorporateActionProvenance,
) -> AuthenticatedCorporateActions:
    """Map vendor-neutral envelope → AuthenticatedCorporateActions."""
    identity_raw = payload.get("identity")
    if isinstance(identity_raw, Mapping):
        identity = CorporateActionCompanyIdentity(
            symbol=str(identity_raw.get("symbol") or symbol).strip().upper(),
            exchange=(
                str(identity_raw["exchange"])
                if identity_raw.get("exchange")
                else None
            ),
            company_name=(
                str(identity_raw["company_name"])
                if identity_raw.get("company_name")
                else None
            ),
            isin=str(identity_raw["isin"]) if identity_raw.get("isin") else None,
            provider_company_id=(
                str(identity_raw["provider_company_id"])
                if identity_raw.get("provider_company_id")
                else None
            ),
            currency=(
                str(identity_raw["currency"]).strip().upper()
                if identity_raw.get("currency")
                else None
            ),
        )
    else:
        identity = CorporateActionCompanyIdentity(
            symbol=symbol.strip().upper(),
            exchange=str(payload["exchange"]) if payload.get("exchange") else None,
        )

    events_raw = payload.get("events")
    if not isinstance(events_raw, list) or not events_raw:
        raise InvalidProviderDataError("corporate actions payload missing events")

    events = tuple(
        build_event_from_mapping(e, default_symbol=identity.symbol)
        for e in events_raw
        if isinstance(e, Mapping)
    )
    if not events:
        raise InvalidProviderDataError("corporate actions payload has no valid events")

    bundle = AuthenticatedCorporateActions(
        identity=identity,
        events=events,
        provenance=provenance,
    )
    validate_authenticated_corporate_actions(bundle)
    return bundle


@dataclass
class NullAuthenticatedCorporateActionAdapter(CorporateActionPort):
    """Always unavailable — safe default when no feed is configured."""

    _provider_id: str = "null_corporate_actions"

    @property
    def provider_id(self) -> str:
        return self._provider_id

    def resolve_company(
        self, instrument: Instrument
    ) -> CorporateActionCompanyIdentity | None:
        return None

    def get_actions(
        self, query: CorporateActionQuery
    ) -> AuthenticatedCorporateActions | None:
        return None

    def health(self) -> CorporateActionProviderHealth:
        return CorporateActionProviderHealth(
            provider_id=self.provider_id,
            healthy=True,
            authenticated=False,
            detail="null provider — no corporate actions feed configured",
        )


@dataclass
class InMemoryAuthenticatedCorporateActionAdapter(CorporateActionPort):
    """Explicitly seeded authenticated events only — never invents symbols."""

    api_key: str | None = None
    _provider_id: str = "memory_authenticated_corporate_actions"
    _bundles: dict[str, AuthenticatedCorporateActions] = field(default_factory=dict)
    _identities: dict[str, CorporateActionCompanyIdentity] = field(
        default_factory=dict
    )
    _lock: Lock = field(default_factory=Lock, repr=False)

    @property
    def provider_id(self) -> str:
        return self._provider_id

    def put(self, bundle: AuthenticatedCorporateActions) -> None:
        validate_authenticated_corporate_actions(bundle)
        with self._lock:
            key = bundle.identity.symbol.upper()
            self._bundles[key] = bundle
            self._identities[key] = bundle.identity

    def resolve_company(
        self, instrument: Instrument
    ) -> CorporateActionCompanyIdentity | None:
        if not self.api_key:
            raise ProviderRequestError(
                "memory corporate action adapter requires api_key (authentication)"
            )
        with self._lock:
            return self._identities.get(instrument.symbol.strip().upper())

    def get_actions(
        self, query: CorporateActionQuery
    ) -> AuthenticatedCorporateActions | None:
        if not self.api_key:
            raise ProviderRequestError(
                "memory corporate action adapter requires api_key (authentication)"
            )
        with self._lock:
            bundle = self._bundles.get(query.instrument.symbol.strip().upper())
        if bundle is None:
            return None

        events = list(bundle.events)
        if query.action_type:
            want = query.action_type.strip().lower()
            events = [e for e in events if e.action_type == want]

        def _primary(e: AuthenticatedCorporateAction) -> date | None:
            return (
                e.effective_date
                or e.ex_date
                or e.record_date
                or e.payment_date
                or e.announcement_date
            )

        if query.start_date:
            events = [
                e
                for e in events
                if (_primary(e) is not None and _primary(e) >= query.start_date)  # type: ignore[operator]
            ]
        if query.end_date:
            events = [
                e
                for e in events
                if (_primary(e) is not None and _primary(e) <= query.end_date)  # type: ignore[operator]
            ]

        events.sort(key=_sort_key, reverse=True)
        limit = max(1, min(int(query.limit), 200))
        events = events[:limit]
        if not events:
            return None
        return AuthenticatedCorporateActions(
            identity=bundle.identity,
            events=tuple(events),
            provenance=bundle.provenance,
        )

    def health(self) -> CorporateActionProviderHealth:
        return CorporateActionProviderHealth(
            provider_id=self.provider_id,
            healthy=True,
            authenticated=bool(self.api_key),
            detail=(
                "seeded in-memory authenticated corporate actions"
                if self.api_key
                else "missing api_key"
            ),
        )


@dataclass
class ConfiguredHttpCorporateActionAdapter(CorporateActionPort):
    """Authenticated HTTP JSON corporate actions adapter."""

    base_url: str
    api_key: str
    timeout_seconds: float = 15.0
    _provider_id: str = "configured_http_corporate_actions"
    provider_name: str = "Configured HTTP Corporate Actions"
    header_name: str = "Authorization"
    header_template: str = "Bearer {api_key}"

    @property
    def provider_id(self) -> str:
        return self._provider_id

    def _request(self, path_query: str) -> dict[str, Any] | None:
        if not self.api_key.strip():
            raise ProviderRequestError("corporate actions api_key required")
        url = f"{self.base_url.rstrip('/')}{path_query}"
        req = urllib.request.Request(
            url,
            headers={
                self.header_name: self.header_template.format(api_key=self.api_key),
                "Accept": "application/json",
                "User-Agent": "dsp-data-engine-corporate-actions/1.0",
            },
            method="GET",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
                raw = resp.read().decode("utf-8")
                status = getattr(resp, "status", 200)
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return None
            raise ProviderRequestError(
                f"corporate actions HTTP {exc.code}: {exc.reason}"
            ) from exc
        except Exception as exc:  # noqa: BLE001
            raise ProviderRequestError(
                f"corporate actions request failed: {exc}"
            ) from exc

        if status == 204:
            return None
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ProviderRequestError(
                "corporate actions response is not JSON"
            ) from exc
        if not isinstance(payload, dict):
            raise ProviderRequestError("corporate actions JSON must be an object")
        if payload.get("unavailable") is True:
            return None
        return payload

    def resolve_company(
        self, instrument: Instrument
    ) -> CorporateActionCompanyIdentity | None:
        symbol = instrument.symbol.strip().upper()
        params = urlencode({"symbol": symbol})
        payload = self._request(f"/resolve?{params}")
        if payload is None:
            return None
        identity_raw = payload.get("identity") if isinstance(payload, dict) else None
        if isinstance(identity_raw, Mapping):
            return CorporateActionCompanyIdentity(
                symbol=str(identity_raw.get("symbol") or symbol).strip().upper(),
                exchange=(
                    str(identity_raw["exchange"])
                    if identity_raw.get("exchange")
                    else instrument.exchange
                ),
                company_name=(
                    str(identity_raw["company_name"])
                    if identity_raw.get("company_name")
                    else None
                ),
                isin=str(identity_raw["isin"]) if identity_raw.get("isin") else None,
                provider_company_id=(
                    str(identity_raw["provider_company_id"])
                    if identity_raw.get("provider_company_id")
                    else None
                ),
                currency=(
                    str(identity_raw["currency"]).strip().upper()
                    if identity_raw.get("currency")
                    else None
                ),
            )
        return CorporateActionCompanyIdentity(
            symbol=symbol, exchange=instrument.exchange
        )

    def get_actions(
        self, query: CorporateActionQuery
    ) -> AuthenticatedCorporateActions | None:
        symbol = query.instrument.symbol.strip().upper()
        params: dict[str, str] = {"symbol": symbol, "limit": str(query.limit)}
        if query.action_type:
            params["action_type"] = query.action_type
        if query.start_date:
            params["start_date"] = query.start_date.isoformat()
        if query.end_date:
            params["end_date"] = query.end_date.isoformat()
        if query.instrument.exchange:
            params["exchange"] = query.instrument.exchange
        payload = self._request(f"?{urlencode(params)}")
        if payload is None:
            return None
        provenance = CorporateActionProvenance(
            provider_id=self.provider_id,
            provider_name=self.provider_name,
            source_type="licensed_vendor",
            retrieved_at=utc_now(),
            auth_mode="api_key",
            metadata={"base_url": self.base_url},
        )
        return build_actions_from_mapping(
            symbol=symbol, payload=payload, provenance=provenance
        )

    def health(self) -> CorporateActionProviderHealth:
        ok = bool(self.api_key.strip() and self.base_url.strip())
        return CorporateActionProviderHealth(
            provider_id=self.provider_id,
            healthy=ok,
            authenticated=bool(self.api_key.strip()),
            detail="configured" if ok else "missing base_url or api_key",
        )


def build_default_corporate_action_adapter_from_env() -> CorporateActionPort:
    """Select corporate action adapter from environment (no fabricated data)."""
    api_key = os.environ.get("DSP_CORPORATE_ACTIONS_API_KEY", "").strip()
    base_url = os.environ.get("DSP_CORPORATE_ACTIONS_BASE_URL", "").strip()
    if api_key and base_url:
        return ConfiguredHttpCorporateActionAdapter(
            base_url=base_url, api_key=api_key
        )
    if os.environ.get("DSP_CORPORATE_ACTIONS_MEMORY", "").lower() in {
        "1",
        "true",
        "yes",
    }:
        return InMemoryAuthenticatedCorporateActionAdapter(
            api_key=api_key or "dev-memory-key"
        )
    return NullAuthenticatedCorporateActionAdapter()
