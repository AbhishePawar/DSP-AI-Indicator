"""Authenticated historical time-series adapters (EPIC-D004).

Retrieval only — never invents bars/points or calculates indicators.
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
from data_engine.exceptions import InvalidProviderDataError, ProviderRequestError
from data_engine.historical_series.models import (
    SERIES_KINDS,
    AuthenticatedHistoricalBundle,
    AuthenticatedOhlcvBar,
    AuthenticatedPoint,
    AuthenticatedSnapshot,
    HistoricalCompanyIdentity,
    HistoricalField,
    HistoricalProvenance,
    utc_now,
)
from data_engine.historical_series.service import (
    HistoricalProviderHealth,
    HistoricalSeriesPort,
    HistoricalSeriesQuery,
)
from data_engine.historical_series.validation import (
    validate_authenticated_historical_bundle,
)

__all__ = [
    "ConfiguredHttpHistoricalAdapter",
    "InMemoryAuthenticatedHistoricalAdapter",
    "NullAuthenticatedHistoricalAdapter",
    "build_default_historical_adapter_from_env",
    "build_historical_bundle_from_mapping",
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


def _sf(payload: Mapping[str, Any], *keys: str) -> HistoricalField:
    for key in keys:
        if key in payload and payload[key] is not None:
            return HistoricalField.of(payload[key])
    return HistoricalField.missing()


def _build_bar(payload: Mapping[str, Any], frequency: str) -> AuthenticatedOhlcvBar:
    bar_date = _parse_date(payload.get("date") or payload.get("bar_date"))
    if bar_date is None:
        raise InvalidProviderDataError("ohlcv bar missing date")
    return AuthenticatedOhlcvBar(
        bar_date=bar_date,
        open=_sf(payload, "open"),
        high=_sf(payload, "high"),
        low=_sf(payload, "low"),
        close=_sf(payload, "close"),
        volume=_sf(payload, "volume"),
        frequency=str(payload.get("frequency") or frequency).strip().lower(),
    )


def _build_point(payload: Mapping[str, Any], series_kind: str) -> AuthenticatedPoint:
    point_date = _parse_date(payload.get("date") or payload.get("point_date"))
    if point_date is None:
        raise InvalidProviderDataError("point missing date")
    return AuthenticatedPoint(
        point_date=point_date,
        value=_sf(payload, "value"),
        series_kind=str(payload.get("series_kind") or series_kind).strip().lower(),
    )


def _build_snapshot(
    payload: Mapping[str, Any], series_kind: str
) -> AuthenticatedSnapshot:
    as_of = _parse_date(payload.get("as_of") or payload.get("date"))
    if as_of is None:
        raise InvalidProviderDataError("snapshot missing as_of")
    fields_raw = payload.get("fields")
    if not isinstance(fields_raw, Mapping) or not fields_raw:
        raise InvalidProviderDataError("snapshot missing fields")
    fields = {
        str(k): HistoricalField.of(v) for k, v in fields_raw.items()
    }
    return AuthenticatedSnapshot(
        as_of=as_of,
        series_kind=str(payload.get("series_kind") or series_kind).strip().lower(),
        fields=fields,
    )


def build_historical_bundle_from_mapping(
    *,
    symbol: str,
    payload: Mapping[str, Any],
    provenance: HistoricalProvenance,
) -> AuthenticatedHistoricalBundle:
    """Deterministic map of vendor-neutral envelope → AuthenticatedHistoricalBundle."""
    series_kind = str(payload.get("series_kind", "")).strip().lower()
    if series_kind not in SERIES_KINDS:
        raise InvalidProviderDataError(f"unknown series_kind: {series_kind!r}")

    identity_raw = payload.get("identity")
    if isinstance(identity_raw, Mapping):
        identity = HistoricalCompanyIdentity(
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
        identity = HistoricalCompanyIdentity(
            symbol=symbol.strip().upper(),
            exchange=str(payload["exchange"]) if payload.get("exchange") else None,
            currency=(
                str(payload["currency"]).strip().upper()
                if payload.get("currency")
                else None
            ),
        )

    frequency = payload.get("frequency")
    frequency_norm = (
        str(frequency).strip().lower() if frequency is not None else None
    )
    start_date = _parse_date(payload.get("start_date"))
    end_date = _parse_date(payload.get("end_date"))

    bars: tuple[AuthenticatedOhlcvBar, ...] = ()
    points: tuple[AuthenticatedPoint, ...] = ()
    snapshots: tuple[AuthenticatedSnapshot, ...] = ()

    if series_kind == "ohlcv":
        bars_raw = payload.get("bars")
        if not isinstance(bars_raw, list) or not bars_raw:
            raise InvalidProviderDataError("ohlcv payload missing bars")
        freq = frequency_norm or "daily"
        built = [
            _build_bar(b, freq) for b in bars_raw if isinstance(b, Mapping)
        ]
        built.sort(key=lambda b: b.bar_date)
        bars = tuple(built)
    elif series_kind in {"market_cap", "volume", "enterprise_value"}:
        points_raw = payload.get("points")
        if not isinstance(points_raw, list) or not points_raw:
            raise InvalidProviderDataError(f"{series_kind} payload missing points")
        built_p = [
            _build_point(p, series_kind)
            for p in points_raw
            if isinstance(p, Mapping)
        ]
        built_p.sort(key=lambda p: p.point_date)
        points = tuple(built_p)
    else:
        snaps_raw = payload.get("snapshots")
        if not isinstance(snaps_raw, list) or not snaps_raw:
            raise InvalidProviderDataError(f"{series_kind} payload missing snapshots")
        built_s = [
            _build_snapshot(s, series_kind)
            for s in snaps_raw
            if isinstance(s, Mapping)
        ]
        built_s.sort(key=lambda s: s.as_of)
        snapshots = tuple(built_s)

    bundle = AuthenticatedHistoricalBundle(
        identity=identity,
        series_kind=series_kind,
        frequency=frequency_norm,
        start_date=start_date,
        end_date=end_date,
        bars=bars,
        points=points,
        snapshots=snapshots,
        provenance=provenance,
        currency=identity.currency,
    )
    validate_authenticated_historical_bundle(bundle)
    return bundle


@dataclass
class NullAuthenticatedHistoricalAdapter(HistoricalSeriesPort):
    """Always unavailable — safe default when no feed is configured."""

    _provider_id: str = "null_historical_series"

    @property
    def provider_id(self) -> str:
        return self._provider_id

    def resolve_company(
        self, instrument: Instrument
    ) -> HistoricalCompanyIdentity | None:
        return None

    def get_series(
        self, query: HistoricalSeriesQuery
    ) -> AuthenticatedHistoricalBundle | None:
        return None

    def health(self) -> HistoricalProviderHealth:
        return HistoricalProviderHealth(
            provider_id=self.provider_id,
            healthy=True,
            authenticated=False,
            detail="null provider — no historical series feed configured",
        )


@dataclass
class InMemoryAuthenticatedHistoricalAdapter(HistoricalSeriesPort):
    """Explicitly seeded authenticated series only — never invents symbols."""

    api_key: str | None = None
    _provider_id: str = "memory_authenticated_historical"
    # key: SYMBOL -> series_kind -> bundle
    _bundles: dict[str, dict[str, AuthenticatedHistoricalBundle]] = field(
        default_factory=dict
    )
    _identities: dict[str, HistoricalCompanyIdentity] = field(default_factory=dict)
    _lock: Lock = field(default_factory=Lock, repr=False)

    @property
    def provider_id(self) -> str:
        return self._provider_id

    def put(self, bundle: AuthenticatedHistoricalBundle) -> None:
        validate_authenticated_historical_bundle(bundle)
        with self._lock:
            key = bundle.identity.symbol.upper()
            self._bundles.setdefault(key, {})[bundle.series_kind] = bundle
            self._identities[key] = bundle.identity

    def resolve_company(
        self, instrument: Instrument
    ) -> HistoricalCompanyIdentity | None:
        if not self.api_key:
            raise ProviderRequestError(
                "memory historical adapter requires api_key (authentication)"
            )
        with self._lock:
            return self._identities.get(instrument.symbol.strip().upper())

    def get_series(
        self, query: HistoricalSeriesQuery
    ) -> AuthenticatedHistoricalBundle | None:
        if not self.api_key:
            raise ProviderRequestError(
                "memory historical adapter requires api_key (authentication)"
            )
        kind = query.series_kind.strip().lower()
        with self._lock:
            by_kind = self._bundles.get(query.instrument.symbol.strip().upper())
            bundle = by_kind.get(kind) if by_kind else None
        if bundle is None:
            return None

        freq = (query.frequency or bundle.frequency or "daily").strip().lower()
        limit = max(1, min(int(query.limit), 5000))

        if kind == "ohlcv":
            bars = [
                b
                for b in bundle.bars
                if (query.frequency is None or b.frequency == freq)
                and (query.start_date is None or b.bar_date >= query.start_date)
                and (query.end_date is None or b.bar_date <= query.end_date)
            ]
            bars.sort(key=lambda b: b.bar_date)
            bars = bars[-limit:] if len(bars) > limit else bars
            if not bars:
                return None
            return AuthenticatedHistoricalBundle(
                identity=bundle.identity,
                series_kind=kind,
                frequency=freq,
                start_date=query.start_date or bars[0].bar_date,
                end_date=query.end_date or bars[-1].bar_date,
                bars=tuple(bars),
                points=(),
                snapshots=(),
                provenance=bundle.provenance,
                currency=bundle.currency,
            )

        if kind in {"market_cap", "volume", "enterprise_value"}:
            points = [
                p
                for p in bundle.points
                if (query.start_date is None or p.point_date >= query.start_date)
                and (query.end_date is None or p.point_date <= query.end_date)
            ]
            points.sort(key=lambda p: p.point_date)
            points = points[-limit:] if len(points) > limit else points
            if not points:
                return None
            return AuthenticatedHistoricalBundle(
                identity=bundle.identity,
                series_kind=kind,
                frequency=None,
                start_date=query.start_date or points[0].point_date,
                end_date=query.end_date or points[-1].point_date,
                bars=(),
                points=tuple(points),
                snapshots=(),
                provenance=bundle.provenance,
                currency=bundle.currency,
            )

        snaps = [
            s
            for s in bundle.snapshots
            if (query.start_date is None or s.as_of >= query.start_date)
            and (query.end_date is None or s.as_of <= query.end_date)
        ]
        snaps.sort(key=lambda s: s.as_of)
        snaps = snaps[-limit:] if len(snaps) > limit else snaps
        if not snaps:
            return None
        return AuthenticatedHistoricalBundle(
            identity=bundle.identity,
            series_kind=kind,
            frequency=None,
            start_date=query.start_date or snaps[0].as_of,
            end_date=query.end_date or snaps[-1].as_of,
            bars=(),
            points=(),
            snapshots=tuple(snaps),
            provenance=bundle.provenance,
            currency=bundle.currency,
        )

    def health(self) -> HistoricalProviderHealth:
        return HistoricalProviderHealth(
            provider_id=self.provider_id,
            healthy=True,
            authenticated=bool(self.api_key),
            detail=(
                "seeded in-memory authenticated historical series"
                if self.api_key
                else "missing api_key"
            ),
        )


@dataclass
class ConfiguredHttpHistoricalAdapter(HistoricalSeriesPort):
    """Authenticated HTTP JSON historical series adapter."""

    base_url: str
    api_key: str
    timeout_seconds: float = 20.0
    _provider_id: str = "configured_http_historical"
    provider_name: str = "Configured HTTP Historical Series"
    header_name: str = "Authorization"
    header_template: str = "Bearer {api_key}"

    @property
    def provider_id(self) -> str:
        return self._provider_id

    def _request(self, path_query: str) -> dict[str, Any] | None:
        if not self.api_key.strip():
            raise ProviderRequestError("historical series api_key required")
        url = f"{self.base_url.rstrip('/')}{path_query}"
        req = urllib.request.Request(
            url,
            headers={
                self.header_name: self.header_template.format(api_key=self.api_key),
                "Accept": "application/json",
                "User-Agent": "dsp-data-engine-historical-series/1.0",
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
                f"historical series HTTP {exc.code}: {exc.reason}"
            ) from exc
        except Exception as exc:  # noqa: BLE001
            raise ProviderRequestError(
                f"historical series request failed: {exc}"
            ) from exc

        if status == 204:
            return None
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ProviderRequestError(
                "historical series response is not JSON"
            ) from exc
        if not isinstance(payload, dict):
            raise ProviderRequestError("historical series JSON must be an object")
        if payload.get("unavailable") is True:
            return None
        return payload

    def resolve_company(
        self, instrument: Instrument
    ) -> HistoricalCompanyIdentity | None:
        symbol = instrument.symbol.strip().upper()
        params = urlencode({"symbol": symbol})
        payload = self._request(f"/resolve?{params}")
        if payload is None:
            return None
        identity_raw = payload.get("identity") if isinstance(payload, dict) else None
        if isinstance(identity_raw, Mapping):
            return HistoricalCompanyIdentity(
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
        return HistoricalCompanyIdentity(
            symbol=symbol, exchange=instrument.exchange
        )

    def get_series(
        self, query: HistoricalSeriesQuery
    ) -> AuthenticatedHistoricalBundle | None:
        symbol = query.instrument.symbol.strip().upper()
        params: dict[str, str] = {
            "symbol": symbol,
            "series_kind": query.series_kind,
            "limit": str(query.limit),
        }
        if query.frequency:
            params["frequency"] = query.frequency
        if query.start_date:
            params["start_date"] = query.start_date.isoformat()
        if query.end_date:
            params["end_date"] = query.end_date.isoformat()
        if query.instrument.exchange:
            params["exchange"] = query.instrument.exchange
        payload = self._request(f"?{urlencode(params)}")
        if payload is None:
            return None
        if "series_kind" not in payload:
            payload = {**payload, "series_kind": query.series_kind}
        provenance = HistoricalProvenance(
            provider_id=self.provider_id,
            provider_name=self.provider_name,
            source_type="licensed_vendor",
            retrieved_at=utc_now(),
            auth_mode="api_key",
            metadata={"base_url": self.base_url},
        )
        return build_historical_bundle_from_mapping(
            symbol=symbol, payload=payload, provenance=provenance
        )

    def health(self) -> HistoricalProviderHealth:
        ok = bool(self.api_key.strip() and self.base_url.strip())
        return HistoricalProviderHealth(
            provider_id=self.provider_id,
            healthy=ok,
            authenticated=bool(self.api_key.strip()),
            detail="configured" if ok else "missing base_url or api_key",
        )


def build_default_historical_adapter_from_env() -> HistoricalSeriesPort:
    """Select historical adapter from environment (no fabricated data)."""
    api_key = os.environ.get("DSP_HISTORICAL_SERIES_API_KEY", "").strip()
    base_url = os.environ.get("DSP_HISTORICAL_SERIES_BASE_URL", "").strip()
    if api_key and base_url:
        return ConfiguredHttpHistoricalAdapter(base_url=base_url, api_key=api_key)
    if os.environ.get("DSP_HISTORICAL_SERIES_MEMORY", "").lower() in {
        "1",
        "true",
        "yes",
    }:
        return InMemoryAuthenticatedHistoricalAdapter(
            api_key=api_key or "dev-memory-key"
        )
    return NullAuthenticatedHistoricalAdapter()
