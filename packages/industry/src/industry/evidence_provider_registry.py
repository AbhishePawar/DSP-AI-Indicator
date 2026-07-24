"""Industry Evidence Provider registry (C3.3)."""

from __future__ import annotations

from industry.enums import EvidenceLifecycle
from industry.evidence_provider import (
    EvidenceProvider,
    EvidenceProviderResult,
    EvidenceResolutionContext,
    IndustryEvidenceProvider,
)
from industry.evidence_registry import IndustryEvidenceRegistry
from industry.exceptions import IndustryError
from industry.semver import parse_semver

__all__ = ["IndustryEvidenceProviderRegistry"]


class IndustryEvidenceProviderRegistry:
    """Registers EvidenceProvider execution contracts.

    Validates capabilities against the Evidence definition registry.
    Does not interpret or assemble bundles.
    """

    def __init__(self, evidence: IndustryEvidenceRegistry) -> None:
        self._evidence = evidence
        self._meta_by_key: dict[tuple[str, str], IndustryEvidenceProvider] = {}
        self._providers: dict[str, EvidenceProvider] = {}

    def register(self, provider: EvidenceProvider) -> IndustryEvidenceProvider:
        if not isinstance(provider, EvidenceProvider):
            msg = "provider must implement EvidenceProvider protocol"
            raise IndustryError(msg)
        meta = provider.provider_metadata()
        self._validate_meta(meta)
        key = meta.registry_key
        existing = self._meta_by_key.get(key)
        if existing is not None:
            if existing == meta and self._providers.get(meta.id) is provider:
                return existing
            msg = (
                f"duplicate industry evidence provider: {meta.id!r} "
                f"version {meta.version!r}"
            )
            raise IndustryError(msg)
        if meta.id in self._providers and self._meta_by_key:
            # Same id different version is allowed; active lookup picks max
            pass
        # Reject duplicate capability ownership across ACTIVE providers for same evidence?
        # Mission: reject duplicate capabilities — interpret as same provider can't
        # double-declare; cross-provider overlap is allowed (routing later).
        self._meta_by_key[key] = meta
        # Keep latest registered instance per id for resolve routing by id
        self._providers[meta.id] = provider
        return meta

    def get(self, provider_id: str, *, version: str) -> IndustryEvidenceProvider:
        key = (provider_id.strip().lower(), parse_semver(version).raw)
        try:
            return self._meta_by_key[key]
        except KeyError as exc:
            msg = f"unknown industry evidence provider: {key!r}"
            raise IndustryError(msg) from exc

    def lookup(self, provider_id: str, *, version: str) -> IndustryEvidenceProvider:
        return self.get(provider_id, version=version)

    def lookup_active(self, provider_id: str) -> IndustryEvidenceProvider:
        pid = provider_id.strip().lower()
        active = [
            m
            for m in self._meta_by_key.values()
            if m.id == pid and m.status is EvidenceLifecycle.ACTIVE
        ]
        if not active:
            msg = f"no active industry evidence provider for {pid!r}"
            raise IndustryError(msg)
        return max(active, key=lambda m: parse_semver(m.version))

    def get_provider(self, provider_id: str) -> EvidenceProvider:
        pid = provider_id.strip().lower()
        try:
            return self._providers[pid]
        except KeyError as exc:
            msg = f"unknown industry evidence provider instance: {pid!r}"
            raise IndustryError(msg) from exc

    def contains(self, provider_id: str, *, version: str | None = None) -> bool:
        pid = provider_id.strip().lower()
        if version is not None:
            return (pid, parse_semver(version).raw) in self._meta_by_key
        return any(m.id == pid for m in self._meta_by_key.values())

    def list_all(
        self, *, status: EvidenceLifecycle | None = None
    ) -> tuple[IndustryEvidenceProvider, ...]:
        items = list(self._meta_by_key.values())
        if status is not None:
            items = [m for m in items if m.status is status]
        return tuple(
            sorted(items, key=lambda m: (m.id, parse_semver(m.version).as_tuple()))
        )

    def resolve(
        self,
        provider_id: str,
        evidence_id: str,
        context: EvidenceResolutionContext,
    ) -> EvidenceProviderResult:
        provider = self.get_provider(provider_id)
        return provider.resolve(evidence_id, context)

    def validate(self) -> None:
        for key, meta in self._meta_by_key.items():
            if meta.registry_key != key:
                msg = (
                    f"provider registry corruption: key {key!r} "
                    f"stores {meta.registry_key!r}"
                )
                raise IndustryError(msg)
            self._validate_meta(meta)
            if meta.id not in self._providers:
                msg = f"provider registry corruption: missing instance for {meta.id!r}"
                raise IndustryError(msg)
            live = self._providers[meta.id].provider_metadata()
            if live.id != meta.id:
                msg = (
                    f"provider registry corruption: instance id {live.id!r} "
                    f"does not match registered {meta.id!r}"
                )
                raise IndustryError(msg)

    def _validate_meta(self, meta: IndustryEvidenceProvider) -> None:
        for cap in meta.capabilities:
            if not self._evidence.contains(cap.evidence_id):
                msg = (
                    f"provider {meta.id!r} declares unsupported evidence "
                    f"reference {cap.evidence_id!r}"
                )
                raise IndustryError(msg)
