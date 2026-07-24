"""Evidence Bundle assembler — orchestration only (C3.5).

Assembles Applicability → Provider → Interpreter → EvidenceBundle.
Never calculates, interprets, or compares.
"""

from __future__ import annotations

from industry.enums import (
    ApplicabilityLevel,
    EvidenceAvailability,
    EvidenceBundleStatus,
    EvidenceLifecycle,
    MissingEvidencePolicy,
)
from industry.evidence_applicability import IndustryEvidenceApplicability
from industry.evidence_applicability_registry import (
    IndustryEvidenceApplicabilityRegistry,
)
from industry.evidence_bundle import (
    EvidenceBundle,
    EvidenceBundleAssemblyContext,
    EvidenceBundleEntry,
    EvidenceBundleMetadata,
    EvidenceBundleSummary,
)
from industry.evidence_interpreter import (
    EvidenceInterpretationContext,
    EvidenceObservation,
)
from industry.evidence_interpreter_registry import IndustryEvidenceInterpreterRegistry
from industry.evidence_provider import (
    EvidenceProviderResult,
    EvidenceResolutionContext,
)
from industry.evidence_provider_registry import IndustryEvidenceProviderRegistry
from industry.evidence_registry import IndustryEvidenceRegistry
from industry.exceptions import IndustryError

__all__ = ["EvidenceBundleAssembler"]

_GAP_AVAILABILITIES = frozenset(
    {
        EvidenceAvailability.UNAVAILABLE,
        EvidenceAvailability.INSUFFICIENT_DATA,
        EvidenceAvailability.ERROR,
        EvidenceAvailability.NOT_APPLICABLE,
    }
)


class EvidenceBundleAssembler:
    """Orchestrates registries into immutable EvidenceBundle artifacts."""

    def __init__(
        self,
        evidence: IndustryEvidenceRegistry,
        applicability: IndustryEvidenceApplicabilityRegistry,
        providers: IndustryEvidenceProviderRegistry,
        interpreters: IndustryEvidenceInterpreterRegistry,
    ) -> None:
        self._evidence = evidence
        self._applicability = applicability
        self._providers = providers
        self._interpreters = interpreters

    def bundle_metadata(
        self, context: EvidenceBundleAssemblyContext
    ) -> EvidenceBundleMetadata:
        if not context.methodology_id:
            msg = "missing methodology for bundle assembly"
            raise IndustryError(msg)
        applicability = self._resolve_applicability(context)
        return EvidenceBundleMetadata(
            bundle_id=self._bundle_id(context, applicability),
            instrument_key=context.instrument_key,
            methodology_id=context.methodology_id,
            methodology_version=context.methodology_version,
            applicability_id=applicability.id,
            applicability_version=applicability.version,
            missing_evidence_policy=applicability.missing_evidence_policy,
            as_of=context.as_of,
            notes=("C3.5 EvidenceBundle — assembly only; no calculations.",),
        )

    def assemble(self, context: EvidenceBundleAssemblyContext) -> EvidenceBundle:
        self._validate_registries()
        metadata = self.bundle_metadata(context)
        applicability = self._applicability.lookup(
            metadata.applicability_id, version=metadata.applicability_version
        )
        if (
            applicability.methodology_version_pin is not None
            and applicability.methodology_version_pin != context.methodology_version
        ):
            msg = (
                f"methodology version {context.methodology_version!r} does not "
                f"match applicability pin "
                f"{applicability.methodology_version_pin!r}"
            )
            raise IndustryError(msg)

        entries: list[EvidenceBundleEntry] = []
        limitations: list[str] = []
        required_ids = set(applicability.required_evidence_ids())

        for rule in sorted(applicability.rules, key=lambda r: r.evidence_id):
            if rule.level is ApplicabilityLevel.UNSUPPORTED:
                continue
            if not self._evidence.contains(rule.evidence_id):
                msg = (
                    f"unsupported evidence reference {rule.evidence_id!r} "
                    f"during bundle assembly"
                )
                raise IndustryError(msg)
            entry = self._assemble_entry(
                context=context,
                evidence_id=rule.evidence_id,
                level=rule.level,
            )
            entries.append(entry)
            limitations.extend(entry.limitations)

        status, policy_notes = self._derive_status(
            entries=tuple(entries),
            required_ids=required_ids,
            policy=applicability.missing_evidence_policy,
        )
        limitations.extend(policy_notes)

        if (
            status is EvidenceBundleStatus.INCOMPLETE
            and applicability.missing_evidence_policy
            is MissingEvidencePolicy.HARD_FAIL
        ):
            missing = sorted(
                eid
                for eid in required_ids
                if not self._required_available(tuple(entries), eid)
            )
            msg = (
                f"HARD_FAIL missing required evidence for "
                f"{context.instrument_key}: {missing}"
            )
            raise IndustryError(msg)

        summary = self._summarize(
            entries=tuple(entries),
            required_ids=required_ids,
            limitation_notes=tuple(dict.fromkeys(limitations)),
        )
        return EvidenceBundle(
            metadata=metadata,
            status=status,
            entries=tuple(entries),
            summary=summary,
            limitations=tuple(dict.fromkeys(limitations)),
        )

    def assemble_many(
        self, contexts: tuple[EvidenceBundleAssemblyContext, ...]
    ) -> tuple[EvidenceBundle, ...]:
        return tuple(self.assemble(ctx) for ctx in contexts)

    def _assemble_entry(
        self,
        *,
        context: EvidenceBundleAssemblyContext,
        evidence_id: str,
        level: ApplicabilityLevel,
    ) -> EvidenceBundleEntry:
        provider_id = self._route_provider(evidence_id, context)
        interpreter_id = self._route_interpreter(evidence_id, context)
        limitations: list[str] = []

        provider_result: EvidenceProviderResult | None = None
        if provider_id is None:
            limitations.append(
                f"No provider registered for evidence {evidence_id}."
            )
            is_gap = True
        else:
            resolution_ctx = EvidenceResolutionContext(
                instrument_key=context.instrument_key,
                methodology_id=context.methodology_id,
                methodology_version=context.methodology_version,
                as_of=context.as_of,
                extras=context.extras,
            )
            provider_result = self._providers.resolve(
                provider_id, evidence_id, resolution_ctx
            )
            is_gap = provider_result.availability in _GAP_AVAILABILITIES
            if is_gap:
                limitations.append(
                    f"Provider {provider_id} reported "
                    f"{provider_result.availability.value} for {evidence_id}."
                )

        observation: EvidenceObservation | None = None
        if provider_result is not None and interpreter_id is not None:
            definition = None
            if self._evidence.contains(evidence_id):
                # Prefer active definition when available
                try:
                    definition = self._evidence.lookup_active(evidence_id)
                except IndustryError:
                    definition = None
            interp_ctx = EvidenceInterpretationContext(
                instrument_key=context.instrument_key,
                methodology_id=context.methodology_id,
                methodology_version=context.methodology_version,
                provider_result=provider_result,
                evidence_definition=definition,
                applicability_level=level,
                as_of=context.as_of,
                extras=context.extras,
            )
            observation = self._interpreters.interpret(interpreter_id, interp_ctx)
        elif provider_result is not None and interpreter_id is None:
            limitations.append(
                f"No interpreter registered for evidence {evidence_id}."
            )

        return EvidenceBundleEntry(
            evidence_id=evidence_id,
            applicability_level=level,
            provider_result=provider_result,
            observation=observation,
            provider_id=provider_id,
            interpreter_id=interpreter_id,
            limitations=tuple(limitations),
            is_gap=is_gap,
        )

    def _route_provider(
        self, evidence_id: str, context: EvidenceBundleAssemblyContext
    ) -> str | None:
        explicit = dict(context.provider_by_evidence)
        if evidence_id in explicit:
            pid = explicit[evidence_id]
            if not self._providers.contains(pid):
                msg = f"broken provider reference {pid!r} for {evidence_id!r}"
                raise IndustryError(msg)
            return pid
        resolution_ctx = EvidenceResolutionContext(
            instrument_key=context.instrument_key,
            methodology_id=context.methodology_id,
            methodology_version=context.methodology_version,
            as_of=context.as_of,
            extras=context.extras,
        )
        candidates: list[str] = []
        for meta in self._providers.list_all(status=EvidenceLifecycle.ACTIVE):
            provider = self._providers.get_provider(meta.id)
            if provider.supports(evidence_id, resolution_ctx):
                candidates.append(meta.id)
        if not candidates:
            return None
        return sorted(candidates)[0]

    def _route_interpreter(
        self, evidence_id: str, context: EvidenceBundleAssemblyContext
    ) -> str | None:
        explicit = dict(context.interpreter_by_evidence)
        if evidence_id in explicit:
            iid = explicit[evidence_id]
            if not self._interpreters.contains(iid):
                msg = f"broken interpreter reference {iid!r} for {evidence_id!r}"
                raise IndustryError(msg)
            return iid
        stub_result = EvidenceProviderResult(
            evidence_id=evidence_id,
            provider_id="dsp.provider.routing_probe",
            availability=EvidenceAvailability.INSUFFICIENT_DATA,
        )
        probe = EvidenceInterpretationContext(
            instrument_key=context.instrument_key,
            methodology_id=context.methodology_id,
            methodology_version=context.methodology_version,
            provider_result=stub_result,
            applicability_level=ApplicabilityLevel.UNKNOWN,
            as_of=context.as_of,
            extras=context.extras,
        )
        candidates: list[str] = []
        for meta in self._interpreters.list_all(status=EvidenceLifecycle.ACTIVE):
            interpreter = self._interpreters.get_interpreter(meta.id)
            if interpreter.supports(evidence_id, probe):
                candidates.append(meta.id)
        if not candidates:
            return None
        return sorted(candidates)[0]

    def _resolve_applicability(
        self, context: EvidenceBundleAssemblyContext
    ) -> IndustryEvidenceApplicability:
        return self._applicability.lookup_active_for_methodology(
            context.methodology_id
        )

    def _bundle_id(
        self,
        context: EvidenceBundleAssemblyContext,
        applicability: IndustryEvidenceApplicability,
    ) -> str:
        return (
            f"dsp.evidence_bundle.{context.instrument_key.lower()}."
            f"{context.methodology_id}."
            f"{applicability.version}"
        )

    def _derive_status(
        self,
        *,
        entries: tuple[EvidenceBundleEntry, ...],
        required_ids: set[str],
        policy: MissingEvidencePolicy,
    ) -> tuple[EvidenceBundleStatus, tuple[str, ...]]:
        del policy  # honored via HARD_FAIL in assemble(); status is descriptive
        notes: list[str] = []
        if not entries:
            return EvidenceBundleStatus.EMPTY, (
                "No applicable evidence rules produced bundle entries.",
            )

        required_missing = [
            eid
            for eid in sorted(required_ids)
            if not self._required_available(entries, eid)
        ]
        required_available = len(required_ids) - len(required_missing)
        non_gap = sum(1 for e in entries if not e.is_gap)

        if required_ids and not required_missing:
            if any(e.is_gap for e in entries):
                notes.append(
                    "Required evidence available; non-required gaps remain."
                )
                return EvidenceBundleStatus.PARTIAL, tuple(notes)
            return EvidenceBundleStatus.COMPLETE, tuple(notes)

        if required_missing:
            notes.append(
                "Required evidence missing: " + ", ".join(required_missing) + "."
            )
            if non_gap > 0 or any(not e.is_gap for e in entries if e.evidence_id not in required_ids):
                return EvidenceBundleStatus.PARTIAL, tuple(notes)
            if required_available > 0:
                return EvidenceBundleStatus.PARTIAL, tuple(notes)
            return EvidenceBundleStatus.INCOMPLETE, tuple(notes)

        # No required evidence defined
        if non_gap == len(entries):
            return EvidenceBundleStatus.COMPLETE, tuple(notes)
        if non_gap == 0:
            return EvidenceBundleStatus.INCOMPLETE, tuple(notes)
        return EvidenceBundleStatus.PARTIAL, tuple(notes)

    @staticmethod
    def _required_available(
        entries: tuple[EvidenceBundleEntry, ...], evidence_id: str
    ) -> bool:
        for entry in entries:
            if entry.evidence_id != evidence_id:
                continue
            if entry.provider_result is None:
                return False
            return (
                entry.provider_result.availability is EvidenceAvailability.AVAILABLE
            )
        return False

    def _summarize(
        self,
        *,
        entries: tuple[EvidenceBundleEntry, ...],
        required_ids: set[str],
        limitation_notes: tuple[str, ...],
    ) -> EvidenceBundleSummary:
        required_available = sum(
            1 for eid in required_ids if self._required_available(entries, eid)
        )
        required_missing = len(required_ids) - required_available
        return EvidenceBundleSummary(
            entry_count=len(entries),
            required_count=len(required_ids),
            required_available_count=required_available,
            required_missing_count=required_missing,
            gap_count=sum(1 for e in entries if e.is_gap),
            observation_count=sum(1 for e in entries if e.observation is not None),
            limitation_notes=limitation_notes,
        )

    def _validate_registries(self) -> None:
        self._evidence.validate()
        self._applicability.validate()
        self._providers.validate()
        self._interpreters.validate()
