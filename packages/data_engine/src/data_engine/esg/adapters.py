"""Authenticated ESG score adapters.

Adapters:

- :class:`NullEsgAdapter` / :class:`InMemoryEsgAdapter` — honest absence
  and explicitly seeded scores. No commercial ESG vendor is registered.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from threading import Lock

from data_engine.connector_framework.models import (
    ConnectorCompanyIdentity,
    ConnectorField,
    ConnectorProvenance,
    ProviderHealth,
)
from data_engine.connector_framework.registry import PriorityProviderRegistry
from data_engine.esg.models import AuthenticatedEsgScore
from data_engine.esg.service import EsgProviderPort, EsgQuery
from data_engine.esg.validation import validate_authenticated_esg_score
from data_engine.exceptions import ProviderRequestError

__all__ = [
    "InMemoryEsgAdapter",
    "NullEsgAdapter",
    "build_default_esg_registry_from_env",
    "build_esg_score_from_mapping",
]


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


def build_default_esg_registry_from_env() -> PriorityProviderRegistry[EsgProviderPort]:
    from data_engine.connector_framework.production_profile import (
        finalize_provider_registry,
        memory_adapter_allowed,
    )

    registry: PriorityProviderRegistry[EsgProviderPort] = PriorityProviderRegistry()

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
