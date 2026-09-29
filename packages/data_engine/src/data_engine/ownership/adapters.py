"""Authenticated ownership/shareholding adapters.

Every vendor-specific field name lives in this file. Adapters:

- :class:`NullOwnershipAdapter` / :class:`InMemoryOwnershipAdapter` —
  safe defaults.
- :class:`NseOwnershipAdapter` / :class:`BseOwnershipAdapter` — India
  exchange shareholding-pattern disclosures.
- :class:`ScreenerOwnershipAdapter` — Screener.in quarterly
  shareholding pattern (promoters/FII/DII/public/government/others),
  the most commonly used Indian-market source for this data.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import date
from threading import Lock
from typing import Callable, Mapping

from data_engine.connector_framework.http import JsonHttpClient, UrllibJsonHttpClient
from data_engine.connector_framework.models import (
    ConnectorCompanyIdentity,
    ConnectorField,
    ConnectorProvenance,
    ProviderHealth,
    utc_now,
)
from data_engine.connector_framework.registry import PriorityProviderRegistry
from data_engine.exceptions import ProviderRequestError
from data_engine.ownership.models import AuthenticatedOwnership, OwnershipStake
from data_engine.ownership.service import OwnershipProviderPort, OwnershipQuery
from data_engine.ownership.validation import validate_authenticated_ownership

__all__ = [
    "BseOwnershipAdapter",
    "InMemoryOwnershipAdapter",
    "NseOwnershipAdapter",
    "NullOwnershipAdapter",
    "ScreenerOwnershipAdapter",
    "build_default_ownership_registry_from_env",
    "build_ownership_bundle_from_mapping",
]


def build_ownership_bundle_from_mapping(
    *,
    symbol: str,
    as_of: date | None,
    stakes: list[OwnershipStake],
    provenance: ConnectorProvenance,
    promoter_holding_percent: ConnectorField | None = None,
    institutional_holding_percent: ConnectorField | None = None,
    public_holding_percent: ConnectorField | None = None,
) -> AuthenticatedOwnership:
    bundle = AuthenticatedOwnership(
        identity=ConnectorCompanyIdentity(symbol=symbol.strip().upper()),
        as_of=as_of,
        stakes=tuple(stakes),
        promoter_holding_percent=promoter_holding_percent or ConnectorField.missing(),
        institutional_holding_percent=institutional_holding_percent or ConnectorField.missing(),
        public_holding_percent=public_holding_percent or ConnectorField.missing(),
        provenance=provenance,
    )
    validate_authenticated_ownership(bundle)
    return bundle


@dataclass
class NullOwnershipAdapter(OwnershipProviderPort):
    _provider_id: str = "null_ownership"

    @property
    def provider_id(self) -> str:
        return self._provider_id

    def get_ownership(self, query: OwnershipQuery) -> AuthenticatedOwnership | None:
        return None

    def health(self) -> ProviderHealth:
        return ProviderHealth(
            provider_id=self.provider_id,
            healthy=True,
            authenticated=False,
            detail="null provider — no ownership feed configured",
        )


@dataclass
class InMemoryOwnershipAdapter(OwnershipProviderPort):
    api_key: str | None = None
    _provider_id: str = "memory_ownership"
    _bundles: dict[str, AuthenticatedOwnership] = field(default_factory=dict)
    _lock: Lock = field(default_factory=Lock, repr=False)

    @property
    def provider_id(self) -> str:
        return self._provider_id

    def put(self, bundle: AuthenticatedOwnership) -> None:
        validate_authenticated_ownership(bundle)
        with self._lock:
            self._bundles[bundle.identity.symbol.upper()] = bundle

    def get_ownership(self, query: OwnershipQuery) -> AuthenticatedOwnership | None:
        if not self.api_key:
            raise ProviderRequestError("memory ownership adapter requires api_key (authentication)")
        with self._lock:
            return self._bundles.get(query.instrument.symbol.strip().upper())

    def health(self) -> ProviderHealth:
        return ProviderHealth(
            provider_id=self.provider_id,
            healthy=True,
            authenticated=bool(self.api_key),
            detail="seeded in-memory authenticated ownership" if self.api_key else "missing api_key",
        )


_INDIAN_CATEGORY_MAP = (
    ("promoter", "promoter"),
    ("mutual fund", "mutual_fund"),
    ("foreign", "institutional_foreign"),
    ("fii", "institutional_foreign"),
    ("dii", "institutional_domestic"),
    ("institution", "institutional_domestic"),
    ("government", "government"),
    ("public", "retail_public"),
)


def _map_category(category: str) -> str:
    lowered = category.strip().lower()
    for needle, holder_type in _INDIAN_CATEGORY_MAP:
        if needle in lowered:
            return holder_type
    return "other"


@dataclass
class NseOwnershipAdapter(OwnershipProviderPort):
    """NSE (India) shareholding-pattern disclosure feed."""

    enabled: bool = False
    base_url: str = "https://www.nseindia.com/api/corporate-shareholding-pattern"
    timeout_seconds: float = 15.0
    http_client: JsonHttpClient | None = None
    _provider_id: str = "nse_ownership"

    @property
    def provider_id(self) -> str:
        return self._provider_id

    def _client(self) -> JsonHttpClient:
        return self.http_client or UrllibJsonHttpClient(
            timeout_seconds=self.timeout_seconds,
            default_headers={"User-Agent": "Mozilla/5.0 (dsp-data-engine)"},
        )

    def get_ownership(self, query: OwnershipQuery) -> AuthenticatedOwnership | None:
        if not self.enabled:
            raise ProviderRequestError("NSE ownership adapter is not enabled")
        symbol = query.instrument.symbol.strip().upper()
        payload = self._client().get_json(self.base_url, params={"index": "equities", "symbol": symbol})
        if not isinstance(payload, list) or not payload:
            return None
        stakes: list[OwnershipStake] = []
        promoter_pct: float | None = None
        public_pct: float | None = None
        for item in payload:
            if not isinstance(item, Mapping):
                continue
            category = str(item.get("category") or "").strip()
            pct = item.get("percentage")
            shares = item.get("no_of_shares")
            if not category:
                continue
            holder_type = _map_category(category)
            pct_field = ConnectorField.of(pct)
            if holder_type == "promoter" and pct_field.available and pct_field.value is not None:
                promoter_pct = float(pct_field.value)
            if holder_type == "retail_public" and pct_field.available and pct_field.value is not None:
                public_pct = float(pct_field.value)
            stakes.append(
                OwnershipStake(
                    holder_type=holder_type,
                    holder_name=category,
                    percent_held=pct_field,
                    shares_held=ConnectorField.of(shares),
                )
            )
        if not stakes:
            return None
        provenance = ConnectorProvenance(
            provider_id=self.provider_id,
            provider_name="National Stock Exchange of India",
            source_type="exchange_feed",
            retrieved_at=utc_now(),
            auth_mode="none",
            metadata={"base_url": self.base_url},
        )
        return build_ownership_bundle_from_mapping(
            symbol=symbol,
            as_of=None,
            stakes=stakes,
            provenance=provenance,
            promoter_holding_percent=ConnectorField.of(promoter_pct),
            public_holding_percent=ConnectorField.of(public_pct),
        )

    def health(self) -> ProviderHealth:
        return ProviderHealth(
            provider_id=self.provider_id,
            healthy=self.enabled,
            authenticated=False,
            detail="enabled" if self.enabled else "disabled (set DSP_OWNERSHIP_NSE_ENABLED=1)",
        )


@dataclass
class BseOwnershipAdapter(OwnershipProviderPort):
    """BSE (India) shareholding-pattern disclosure feed (numeric scrip code)."""

    enabled: bool = False
    base_url: str = "https://api.bseindia.com/BseIndiaAPI/api/ShareholdingPattern/w"
    timeout_seconds: float = 15.0
    http_client: JsonHttpClient | None = None
    scrip_code_resolver: Callable[[str], str | None] | None = None
    _provider_id: str = "bse_ownership"

    @property
    def provider_id(self) -> str:
        return self._provider_id

    def _client(self) -> JsonHttpClient:
        return self.http_client or UrllibJsonHttpClient(
            timeout_seconds=self.timeout_seconds,
            default_headers={"User-Agent": "Mozilla/5.0 (dsp-data-engine)"},
        )

    def _resolve_scrip_code(self, symbol: str) -> str | None:
        if self.scrip_code_resolver is not None:
            return self.scrip_code_resolver(symbol)
        return symbol if symbol.isdigit() else None

    def get_ownership(self, query: OwnershipQuery) -> AuthenticatedOwnership | None:
        if not self.enabled:
            raise ProviderRequestError("BSE ownership adapter is not enabled")
        symbol = query.instrument.symbol.strip().upper()
        scrip_code = self._resolve_scrip_code(symbol)
        if scrip_code is None:
            return None
        payload = self._client().get_json(self.base_url, params={"scripcode": scrip_code})
        if not isinstance(payload, Mapping):
            return None
        rows = payload.get("Table")
        if not isinstance(rows, list) or not rows:
            return None
        stakes: list[OwnershipStake] = []
        promoter_pct: float | None = None
        public_pct: float | None = None
        for item in rows:
            if not isinstance(item, Mapping):
                continue
            category = str(item.get("CATEGORY") or "").strip()
            pct = item.get("PER_HOLDING")
            shares = item.get("NO_OF_SHARES")
            if not category:
                continue
            holder_type = _map_category(category)
            pct_field = ConnectorField.of(pct)
            if holder_type == "promoter" and pct_field.available and pct_field.value is not None:
                promoter_pct = float(pct_field.value)
            if holder_type == "retail_public" and pct_field.available and pct_field.value is not None:
                public_pct = float(pct_field.value)
            stakes.append(
                OwnershipStake(
                    holder_type=holder_type,
                    holder_name=category,
                    percent_held=pct_field,
                    shares_held=ConnectorField.of(shares),
                )
            )
        if not stakes:
            return None
        provenance = ConnectorProvenance(
            provider_id=self.provider_id,
            provider_name="BSE Limited",
            source_type="exchange_feed",
            retrieved_at=utc_now(),
            auth_mode="none",
            metadata={"base_url": self.base_url, "scrip_code": scrip_code},
        )
        return build_ownership_bundle_from_mapping(
            symbol=symbol,
            as_of=None,
            stakes=stakes,
            provenance=provenance,
            promoter_holding_percent=ConnectorField.of(promoter_pct),
            public_holding_percent=ConnectorField.of(public_pct),
        )

    def health(self) -> ProviderHealth:
        return ProviderHealth(
            provider_id=self.provider_id,
            healthy=self.enabled,
            authenticated=False,
            detail="enabled" if self.enabled else "disabled (set DSP_OWNERSHIP_BSE_ENABLED=1)",
        )


_MONTH_MAP = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}


def _parse_quarter_label(label: str) -> date | None:
    """Parse a "Mon YYYY" quarter-end label (Screener's convention)."""
    parts = label.strip().split()
    if len(parts) != 2:
        return None
    month_key = parts[0][:3].lower()
    month = _MONTH_MAP.get(month_key)
    if month is None or not parts[1].isdigit():
        return None
    return date(int(parts[1]), month, 1)


@dataclass
class ScreenerOwnershipAdapter(OwnershipProviderPort):
    """Screener.in quarterly shareholding pattern.

    Screener publishes promoter/FII/DII/public/government/other
    percentages by quarter — the most widely used Indian-market source
    for this breakdown. Uses the most recent quarterly entry.
    """

    enabled: bool = False
    base_url: str = "https://www.screener.in/api/company"
    timeout_seconds: float = 15.0
    http_client: JsonHttpClient | None = None
    _provider_id: str = "screener_ownership"

    @property
    def provider_id(self) -> str:
        return self._provider_id

    def _client(self) -> JsonHttpClient:
        return self.http_client or UrllibJsonHttpClient(timeout_seconds=self.timeout_seconds)

    def get_ownership(self, query: OwnershipQuery) -> AuthenticatedOwnership | None:
        if not self.enabled:
            raise ProviderRequestError("Screener ownership adapter is not enabled")
        symbol = query.instrument.symbol.strip().upper()
        payload = self._client().get_json(f"{self.base_url}/{symbol}/")
        if not isinstance(payload, Mapping):
            return None
        shareholding = payload.get("shareholding")
        if not isinstance(shareholding, Mapping):
            return None
        quarterly = shareholding.get("quarterly")
        if not isinstance(quarterly, list) or not quarterly:
            return None
        latest = quarterly[-1]
        if not isinstance(latest, Mapping):
            return None

        field_map = {
            "promoters": "promoter",
            "fii": "institutional_foreign",
            "dii": "institutional_domestic",
            "mutual_funds": "mutual_fund",
            "government": "government",
            "public": "retail_public",
            "others": "other",
        }
        stakes: list[OwnershipStake] = []
        promoter_pct: float | None = None
        public_pct: float | None = None
        institutional_total = 0.0
        have_institutional = False
        for key, holder_type in field_map.items():
            if key not in latest:
                continue
            pct_field = ConnectorField.of(latest.get(key))
            if not pct_field.available:
                continue
            stakes.append(
                OwnershipStake(
                    holder_type=holder_type,
                    holder_name=key.replace("_", " ").title(),
                    percent_held=pct_field,
                    shares_held=ConnectorField.missing(),
                )
            )
            value = float(pct_field.value) if pct_field.value is not None else 0.0
            if holder_type == "promoter":
                promoter_pct = value
            elif holder_type == "retail_public":
                public_pct = value
            elif holder_type in {"institutional_domestic", "institutional_foreign", "mutual_fund"}:
                institutional_total += value
                have_institutional = True
        if not stakes:
            return None
        as_of = _parse_quarter_label(str(latest.get("date") or ""))
        provenance = ConnectorProvenance(
            provider_id=self.provider_id,
            provider_name="Screener.in",
            source_type="public_endpoint",
            retrieved_at=utc_now(),
            auth_mode="none",
            metadata={"base_url": self.base_url},
        )
        return build_ownership_bundle_from_mapping(
            symbol=symbol,
            as_of=as_of,
            stakes=stakes,
            provenance=provenance,
            promoter_holding_percent=ConnectorField.of(promoter_pct),
            institutional_holding_percent=ConnectorField.of(
                institutional_total if have_institutional else None
            ),
            public_holding_percent=ConnectorField.of(public_pct),
        )

    def health(self) -> ProviderHealth:
        return ProviderHealth(
            provider_id=self.provider_id,
            healthy=self.enabled,
            authenticated=False,
            detail="enabled" if self.enabled else "disabled (set DSP_OWNERSHIP_SCREENER_ENABLED=1)",
        )


def build_default_ownership_registry_from_env() -> PriorityProviderRegistry[OwnershipProviderPort]:
    from data_engine.connector_framework.production_profile import (
        finalize_provider_registry,
        memory_adapter_allowed,
    )

    registry: PriorityProviderRegistry[OwnershipProviderPort] = PriorityProviderRegistry()

    if os.environ.get("DSP_OWNERSHIP_SCREENER_ENABLED", "").lower() in {"1", "true", "yes"}:
        registry.register(
            ScreenerOwnershipAdapter(enabled=True), provider_id="screener_ownership", priority=10
        )

    if os.environ.get("DSP_OWNERSHIP_NSE_ENABLED", "").lower() in {"1", "true", "yes"}:
        registry.register(
            NseOwnershipAdapter(enabled=True), provider_id="nse_ownership", priority=30
        )

    if os.environ.get("DSP_OWNERSHIP_BSE_ENABLED", "").lower() in {"1", "true", "yes"}:
        registry.register(
            BseOwnershipAdapter(enabled=True), provider_id="bse_ownership", priority=40
        )

    if memory_adapter_allowed("DSP_OWNERSHIP_MEMORY", connector="ownership"):
        registry.register(
            InMemoryOwnershipAdapter(api_key="dev-memory-key"),
            provider_id="memory_ownership",
            priority=90,
        )

    return finalize_provider_registry(
        registry,
        connector="ownership",
        null_factory=NullOwnershipAdapter,
        null_provider_id="null_ownership",
    )
