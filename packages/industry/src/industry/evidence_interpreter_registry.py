"""Industry Evidence Interpreter registry (C3.4)."""

from __future__ import annotations

from industry.enums import EvidenceLifecycle
from industry.evidence_interpreter import (
    EvidenceInterpretationContext,
    EvidenceInterpreter,
    EvidenceObservation,
    IndustryEvidenceInterpreter,
)
from industry.evidence_registry import IndustryEvidenceRegistry
from industry.exceptions import IndustryError
from industry.semver import parse_semver

__all__ = ["IndustryEvidenceInterpreterRegistry"]


class IndustryEvidenceInterpreterRegistry:
    """Registers EvidenceInterpreter meaning contracts.

    Validates interpretation rules against the Evidence definition registry.
    Does not assemble bundles or call providers.
    """

    def __init__(self, evidence: IndustryEvidenceRegistry) -> None:
        self._evidence = evidence
        self._meta_by_key: dict[tuple[str, str], IndustryEvidenceInterpreter] = {}
        self._interpreters: dict[str, EvidenceInterpreter] = {}

    def register(
        self, interpreter: EvidenceInterpreter
    ) -> IndustryEvidenceInterpreter:
        if not isinstance(interpreter, EvidenceInterpreter):
            msg = "interpreter must implement EvidenceInterpreter protocol"
            raise IndustryError(msg)
        meta = interpreter.interpreter_metadata()
        self._validate_meta(meta)
        key = meta.registry_key
        existing = self._meta_by_key.get(key)
        if existing is not None:
            if existing == meta and self._interpreters.get(meta.id) is interpreter:
                return existing
            msg = (
                f"duplicate industry evidence interpreter: {meta.id!r} "
                f"version {meta.version!r}"
            )
            raise IndustryError(msg)
        self._meta_by_key[key] = meta
        self._interpreters[meta.id] = interpreter
        return meta

    def get(
        self, interpreter_id: str, *, version: str
    ) -> IndustryEvidenceInterpreter:
        key = (interpreter_id.strip().lower(), parse_semver(version).raw)
        try:
            return self._meta_by_key[key]
        except KeyError as exc:
            msg = f"unknown industry evidence interpreter: {key!r}"
            raise IndustryError(msg) from exc

    def lookup(
        self, interpreter_id: str, *, version: str
    ) -> IndustryEvidenceInterpreter:
        return self.get(interpreter_id, version=version)

    def lookup_active(self, interpreter_id: str) -> IndustryEvidenceInterpreter:
        iid = interpreter_id.strip().lower()
        active = [
            m
            for m in self._meta_by_key.values()
            if m.id == iid and m.status is EvidenceLifecycle.ACTIVE
        ]
        if not active:
            msg = f"no active industry evidence interpreter for {iid!r}"
            raise IndustryError(msg)
        return max(active, key=lambda m: parse_semver(m.version))

    def get_interpreter(self, interpreter_id: str) -> EvidenceInterpreter:
        iid = interpreter_id.strip().lower()
        try:
            return self._interpreters[iid]
        except KeyError as exc:
            msg = f"unknown industry evidence interpreter instance: {iid!r}"
            raise IndustryError(msg) from exc

    def contains(self, interpreter_id: str, *, version: str | None = None) -> bool:
        iid = interpreter_id.strip().lower()
        if version is not None:
            return (iid, parse_semver(version).raw) in self._meta_by_key
        return any(m.id == iid for m in self._meta_by_key.values())

    def list_all(
        self, *, status: EvidenceLifecycle | None = None
    ) -> tuple[IndustryEvidenceInterpreter, ...]:
        items = list(self._meta_by_key.values())
        if status is not None:
            items = [m for m in items if m.status is status]
        return tuple(
            sorted(items, key=lambda m: (m.id, parse_semver(m.version).as_tuple()))
        )

    def interpret(
        self,
        interpreter_id: str,
        context: EvidenceInterpretationContext,
    ) -> EvidenceObservation:
        if not context.methodology_id:
            msg = "missing methodology for interpretation"
            raise IndustryError(msg)
        interpreter = self.get_interpreter(interpreter_id)
        if not interpreter.supports(context.evidence_id, context):
            msg = (
                f"interpreter {interpreter_id!r} does not support evidence "
                f"{context.evidence_id!r}"
            )
            raise IndustryError(msg)
        return interpreter.interpret(context)

    def validate(self) -> None:
        for key, meta in self._meta_by_key.items():
            if meta.registry_key != key:
                msg = (
                    f"interpreter registry corruption: key {key!r} "
                    f"stores {meta.registry_key!r}"
                )
                raise IndustryError(msg)
            self._validate_meta(meta)
            if meta.id not in self._interpreters:
                msg = (
                    f"interpreter registry corruption: missing instance "
                    f"for {meta.id!r}"
                )
                raise IndustryError(msg)
            live = self._interpreters[meta.id].interpreter_metadata()
            if live.id != meta.id:
                msg = (
                    f"interpreter registry corruption: instance id {live.id!r} "
                    f"does not match registered {meta.id!r}"
                )
                raise IndustryError(msg)

    def _validate_meta(self, meta: IndustryEvidenceInterpreter) -> None:
        for item in meta.interpretations:
            if not self._evidence.contains(item.evidence_id):
                msg = (
                    f"interpreter {meta.id!r} declares unsupported evidence "
                    f"reference {item.evidence_id!r}"
                )
                raise IndustryError(msg)
