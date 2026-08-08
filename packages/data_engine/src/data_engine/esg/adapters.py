"""Authenticated ESG score adapters.

Every vendor-specific field name lives in this file. Adapters:

- :class:`NullEsgAdapter` / :class:`InMemoryEsgAdapter` — safe defaults.
- :class:`YahooFinanceEsgAdapter` — Yahoo's
  ``quoteSummary?modules=esgScores`` module (Sustainalytics-sourced).
- :class:`FinancialModelingPrepEsgAdapter` — FMP
  ``esg-environmental-social-governance-data`` endpoint.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import date
from threading import Lock
from typing import Mapping

from contracts.domain.instrument import Instrument
from data_engine.connector_framework.http import JsonHttpClient, UrllibJsonHttpClient
from data_engine.connector_framework.models import (
    ConnectorCompanyIdentity,
    ConnectorField,
    ConnectorProvenance,
    ProviderHealth,
    utc_now,
)
from data_engine.connector_framework.registry import PriorityProviderRegistry
from data_engine.esg.models import AuthenticatedEsgScore
from data_engine.esg.service import EsgProviderPort, EsgQuery
from data_engine.esg.validation import validate_authenticated_esg_score
from data_engine.exceptions import ProviderRequestError

__all__ = [
    "FinancialModelingPrepEsgAdapter",
    "InMemoryEsgAdapter",
    "NullEsgAdapter",
    "YahooFinanceEsgAdapter",
    "build_default_esg_registry_from_env",
    "build_esg_score_from_mapping",
]

_YAHOO_CONTROVERSY_MAP = {1: "low", 2: "moderate", 3: "significant", 4: "high", 5: "severe"}


def build_esg_score_from_mapping(
    *,
    symbol: str,
    as_of: date | None,
    environmental_score: ConnectorField,
    social_score: ConnectorField,
    governance_score: ConnectorField,
    total_score: ConnectorField,
    controversy_level: str | None,
    provenance: ConnectorProvenance,
) -> AuthenticatedEsgScore:
    bundle = AuthenticatedEsgScore(
        identity=ConnectorCompanyIdentity(symbol=symbol.strip().upper()),
        as_of=as_of,
        environmental_score=environmental_score,
        social_score=social_score,
        governance_score=governance_score,
        total_score=total_score,
        controversy_level=controversy_level,
        provenance=provenance,
    )
    validate_authenticated_esg_score(bundle)
    return bundle


@dataclass
class NullEsgAdapter(EsgProviderPort):
    _provider_id: str = "null_esg"

    @property
    def provider_id(self) -> str:
        return self._provider_id

    def get_esg_score(self, query: EsgQuery) -> AuthenticatedEsgScore | None:
        return None

    def health(self) -> ProviderHealth:
        return ProviderHealth(
            provider_id=self.provider_id,
            healthy=True,
            authenticated=False,
            detail="null provider — no esg feed configured",
        )


@dataclass
class InMemoryEsgAdapter(EsgProviderPort):
    api_key: str | None = None
    _provider_id: str = "memory_esg"
    _scores: dict[str, AuthenticatedEsgScore] = field(default_factory=dict)
    _lock: Lock = field(default_factory=Lock, repr=False)

    @property
    def provider_id(self) -> str:
        return self._provider_id

    def put(self, score: AuthenticatedEsgScore) -> None:
        validate_authenticated_esg_score(score)
        with self._lock:
            self._scores[score.identity.symbol.upper()] = score

    def get_esg_score(self, query: EsgQuery) -> AuthenticatedEsgScore | None:
        if not self.api_key:
            raise ProviderRequestError("memory esg adapter requires api_key (authentication)")
        with self._lock:
            return self._scores.get(query.instrument.symbol.strip().upper())

    def health(self) -> ProviderHealth:
        return ProviderHealth(
            provider_id=self.provider_id,
            healthy=True,
            authenticated=bool(self.api_key),
            detail="seeded in-memory authenticated esg" if self.api_key else "missing api_key",
        )


@dataclass
class YahooFinanceEsgAdapter(EsgProviderPort):
    """Yahoo Finance ``esgScores`` quoteSummary module."""

    enabled: bool = False
    base_url: str = "https://query1.finance.yahoo.com/v10/finance/quoteSummary"
    timeout_seconds: float = 10.0
    http_client: JsonHttpClient | None = None
    _provider_id: str = "yahoo_finance_esg"

    @property
    def provider_id(self) -> str:
        return self._provider_id

    def _client(self) -> JsonHttpClient:
        return self.http_client or UrllibJsonHttpClient(timeout_seconds=self.timeout_seconds)

    def get_esg_score(self, query: EsgQuery) -> AuthenticatedEsgScore | None:
        if not self.enabled:
            raise ProviderRequestError("yahoo finance esg adapter is not enabled")
        symbol = query.instrument.symbol.strip().upper()
        payload = self._client().get_json(
            f"{self.base_url}/{symbol}", params={"modules": "esgScores"}
        )
        if not isinstance(payload, Mapping):
            return None
        result_list = (payload.get("quoteSummary") or {}).get("result") if isinstance(
            payload.get("quoteSummary"), Mapping
        ) else None
        if not isinstance(result_list, list) or not result_list:
            return None
        esg = result_list[0].get("esgScores") if isinstance(result_list[0], Mapping) else None
        if not isinstance(esg, Mapping):
            return None

        def _raw(key: str) -> float | None:
            entry = esg.get(key)
            if isinstance(entry, Mapping):
                return entry.get("raw")
            return entry

        env_score = ConnectorField.of(_raw("environmentScore"))
        social_score = ConnectorField.of(_raw("socialScore"))
        gov_score = ConnectorField.of(_raw("governanceScore"))
        total_score = ConnectorField.of(_raw("totalEsg"))
        if not any(f.available for f in (env_score, social_score, gov_score, total_score)):
            return None
        controversy_raw = _raw("highestControversy")
        controversy_level = None
        if controversy_raw is not None:
            try:
                controversy_level = _YAHOO_CONTROVERSY_MAP.get(int(controversy_raw))
            except (TypeError, ValueError):
                controversy_level = None
        provenance = ConnectorProvenance(
            provider_id=self.provider_id,
            provider_name="Yahoo Finance",
            source_type="public_endpoint",
            retrieved_at=utc_now(),
            auth_mode="none",
            metadata={"base_url": self.base_url},
        )
        return build_esg_score_from_mapping(
            symbol=symbol,
            as_of=None,
            environmental_score=env_score,
            social_score=social_score,
            governance_score=gov_score,
            total_score=total_score,
            controversy_level=controversy_level,
            provenance=provenance,
        )

    def health(self) -> ProviderHealth:
        return ProviderHealth(
            provider_id=self.provider_id,
            healthy=self.enabled,
            authenticated=False,
            detail="enabled" if self.enabled else "disabled (set DSP_ESG_YAHOO_ENABLED=1)",
        )


@dataclass
class FinancialModelingPrepEsgAdapter(EsgProviderPort):
    """FMP ``esg-environmental-social-governance-data`` endpoint."""

    api_key: str
    base_url: str = "https://financialmodelingprep.com/api/v4/esg-environmental-social-governance-data"
    timeout_seconds: float = 15.0
    http_client: JsonHttpClient | None = None
    _provider_id: str = "fmp_esg"

    @property
    def provider_id(self) -> str:
        return self._provider_id

    def _client(self) -> JsonHttpClient:
        return self.http_client or UrllibJsonHttpClient(timeout_seconds=self.timeout_seconds)

    def get_esg_score(self, query: EsgQuery) -> AuthenticatedEsgScore | None:
        if not self.api_key.strip():
            raise ProviderRequestError("financial modeling prep esg adapter requires api_key")
        symbol = query.instrument.symbol.strip().upper()
        payload = self._client().get_json(self.base_url, params={"symbol": symbol, "apikey": self.api_key})
        if not isinstance(payload, list) or not payload:
            return None
        latest = payload[0]
        if not isinstance(latest, Mapping):
            return None
        env_score = ConnectorField.of(latest.get("environmentalScore"))
        social_score = ConnectorField.of(latest.get("socialScore"))
        gov_score = ConnectorField.of(latest.get("governanceScore"))
        total_score = ConnectorField.of(latest.get("ESGScore"))
        if not any(f.available for f in (env_score, social_score, gov_score, total_score)):
            return None
        as_of = None
        date_raw = str(latest.get("date") or "").strip()
        if date_raw:
            try:
                as_of = date.fromisoformat(date_raw[:10])
            except ValueError:
                as_of = None
        provenance = ConnectorProvenance(
            provider_id=self.provider_id,
            provider_name="Financial Modeling Prep",
            source_type="licensed_vendor",
            retrieved_at=utc_now(),
            auth_mode="api_key",
            metadata={"base_url": self.base_url},
        )
        return build_esg_score_from_mapping(
            symbol=symbol,
            as_of=as_of,
            environmental_score=env_score,
            social_score=social_score,
            governance_score=gov_score,
            total_score=total_score,
            controversy_level=None,
            provenance=provenance,
        )

    def health(self) -> ProviderHealth:
        ok = bool(self.api_key.strip())
        return ProviderHealth(
            provider_id=self.provider_id, healthy=ok, authenticated=ok,
            detail="configured" if ok else "missing api_key",
        )


def build_default_esg_registry_from_env() -> PriorityProviderRegistry[EsgProviderPort]:
    from data_engine.connector_framework.production_profile import (
        finalize_provider_registry,
        memory_adapter_allowed,
    )

    registry: PriorityProviderRegistry[EsgProviderPort] = PriorityProviderRegistry()

    fmp_key = os.environ.get("DSP_ESG_FMP_API_KEY", "").strip()
    if fmp_key:
        registry.register(FinancialModelingPrepEsgAdapter(api_key=fmp_key), provider_id="fmp_esg", priority=10)

    if os.environ.get("DSP_ESG_YAHOO_ENABLED", "").lower() in {"1", "true", "yes"}:
        registry.register(
            YahooFinanceEsgAdapter(enabled=True), provider_id="yahoo_finance_esg", priority=20
        )

    if memory_adapter_allowed("DSP_ESG_MEMORY", connector="esg"):
        registry.register(
            InMemoryEsgAdapter(api_key="dev-memory-key"), provider_id="memory_esg", priority=90
        )

    return finalize_provider_registry(
        registry,
        connector="esg",
        null_factory=NullEsgAdapter,
        null_provider_id="null_esg",
    )
