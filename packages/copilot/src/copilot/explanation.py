"""AI Copilot Explanation Engine (J1.2).

Transforms immutable ExplanationInput into structured, evidence-backed
explanations. Optional LanguageModelPort enrichment with deterministic
fallback. Never performs financial analysis, valuation, risk math, workflow
execution, persistence, or upstream report mutation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from copilot.conversation import ExplanationInput
from copilot.enums import (
    ConfidenceLevel,
    ExplanationStatus,
    ExplanationType,
    LanguageModelStatus,
    UserIntentType,
)
from copilot.exceptions import CopilotError
from copilot.models import (
    ContextBundle,
    Explanation,
    LanguageModelRequest,
    LanguageModelResult,
)
from copilot.refs import KnowledgeGraphReference

__all__ = [
    "EvidenceValidator",
    "ExplanationDraft",
    "ExplanationEngine",
    "ExplanationInput",
    "ExplanationResult",
    "LanguageModelPort",
]

_PROVENANCE = ("copilot.explanation", "dsp.copilot.method.explanation.v1")


@runtime_checkable
class LanguageModelPort(Protocol):
    """Provider-neutral LM port — adapters live outside the domain."""

    def invoke(self, request: LanguageModelRequest) -> LanguageModelResult:
        """Return a provider-neutral LanguageModelResult."""


@dataclass(frozen=True, slots=True)
class ExplanationDraft:
    """Intermediate structured explanation before final validation."""

    executive_summary: str
    key_reasons: tuple[str, ...]
    risks: tuple[str, ...]
    supporting_evidence: tuple[str, ...]
    claim_evidence_links: tuple[tuple[str, str], ...]
    citations: tuple[str, ...]
    narrative: str
    explanation_type: ExplanationType
    is_generated_narrative: bool
    limitations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "key_reasons", tuple(self.key_reasons))
        object.__setattr__(self, "risks", tuple(self.risks))
        object.__setattr__(
            self, "supporting_evidence", tuple(self.supporting_evidence)
        )
        object.__setattr__(
            self, "claim_evidence_links", tuple(self.claim_evidence_links)
        )
        object.__setattr__(self, "citations", tuple(self.citations))
        object.__setattr__(
            self, "limitations", tuple(n.strip() for n in self.limitations if n.strip())
        )


@dataclass(frozen=True, slots=True)
class ExplanationResult:
    """Explanation engine output — structured sections + domain Explanation."""

    explanation: Explanation
    draft: ExplanationDraft
    status: ExplanationStatus
    executive_summary: str
    key_reasons: tuple[str, ...]
    risks: tuple[str, ...]
    supporting_evidence: tuple[str, ...]
    confidence: ConfidenceLevel
    citations: tuple[str, ...]
    provenance: tuple[str, ...]
    warnings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "key_reasons", tuple(self.key_reasons))
        object.__setattr__(self, "risks", tuple(self.risks))
        object.__setattr__(
            self, "supporting_evidence", tuple(self.supporting_evidence)
        )
        object.__setattr__(self, "citations", tuple(self.citations))
        object.__setattr__(self, "provenance", tuple(self.provenance))
        object.__setattr__(self, "warnings", tuple(self.warnings))


class EvidenceValidator:
    """Validates cite-backed evidence for explanation drafts."""

    def validate_bundle(self, bundle: ContextBundle) -> None:
        """Reject broken / missing Knowledge Graph and citation structure."""
        if bundle is None:
            msg = "missing ContextBundle"
            raise CopilotError(msg)
        if bundle.knowledge_graph_ref is None:
            msg = "broken KnowledgeGraph references: KnowledgeGraphReference required"
            raise CopilotError(msg)
        self._validate_kg_ref(bundle.knowledge_graph_ref)
        if not bundle.provenance:
            msg = "missing provenance: ContextBundle requires provenance"
            raise CopilotError(msg)
        digests = list(bundle.digest_ids)
        if len(digests) != len(set(digests)):
            msg = "duplicate citations: ContextBundle digest_ids not unique"
            raise CopilotError(msg)
        if (
            bundle.knowledge_graph_ref.digest
            and bundle.digest_ids
            and bundle.knowledge_graph_ref.digest not in digests
        ):
            msg = (
                "broken KnowledgeGraph references: KG digest missing from "
                "ContextBundle.digest_ids"
            )
            raise CopilotError(msg)

    def validate_draft(
        self,
        draft: ExplanationDraft,
        *,
        allowed_digests: frozenset[str],
        require_evidence: bool,
    ) -> tuple[str, ...]:
        """Return warnings; raise on hard invariant violations."""
        warnings: list[str] = []
        if not draft.narrative.strip():
            msg = "empty explanation: narrative is required"
            raise CopilotError(msg)
        if not draft.executive_summary.strip():
            msg = "empty explanation: executive_summary is required"
            raise CopilotError(msg)

        citations = draft.citations
        if len(citations) != len(set(citations)):
            msg = "duplicate citations in ExplanationDraft"
            raise CopilotError(msg)

        for digest in citations:
            if digest not in allowed_digests:
                msg = f"unsupported claims: citation {digest!r} not in ContextBundle"
                raise CopilotError(msg)

        for claim, digest in draft.claim_evidence_links:
            if not claim.strip():
                msg = "unsupported claims: empty claim text"
                raise CopilotError(msg)
            if digest not in allowed_digests:
                msg = (
                    f"unsupported claims: claim {claim!r} cites unknown digest "
                    f"{digest!r}"
                )
                raise CopilotError(msg)

        if require_evidence and not draft.citations and not draft.supporting_evidence:
            msg = "missing evidence: factual explanation requires citations"
            raise CopilotError(msg)

        if require_evidence and not draft.claim_evidence_links:
            warnings.append(
                "claim → evidence links absent; relying on citation list only."
            )
        if not draft.supporting_evidence and require_evidence:
            warnings.append("supporting evidence section empty.")
        return tuple(warnings)

    def _validate_kg_ref(self, ref: KnowledgeGraphReference) -> None:
        for field in ("id", "report_id", "version", "digest", "status", "generated_at"):
            value = getattr(ref, field, None)
            if not value or not str(value).strip():
                msg = f"broken KnowledgeGraph references: missing {field}"
                raise CopilotError(msg)
        if len(ref.digest.strip()) < 8:
            msg = "broken KnowledgeGraph references: digest invalid"
            raise CopilotError(msg)


class ExplanationEngine:
    """Canonical evidence-backed explanation builder.

    Deterministic template assembly with optional LanguageModelPort enrichment.
    """

    def __init__(
        self,
        *,
        language_model: LanguageModelPort | None = None,
        validator: EvidenceValidator | None = None,
    ) -> None:
        self._lm = language_model
        self._validator = validator or EvidenceValidator()

    def validate_inputs(self, explanation_input: ExplanationInput) -> None:
        """Reject invalid explanation inputs."""
        if explanation_input is None:
            msg = "ExplanationInput is required"
            raise CopilotError(msg)
        if not explanation_input.copilot_id:
            msg = "missing copilot_id"
            raise CopilotError(msg)
        if not explanation_input.session_id:
            msg = "missing session_id"
            raise CopilotError(msg)
        if explanation_input.intent is None:
            msg = "missing UserIntent"
            raise CopilotError(msg)
        if not explanation_input.provenance:
            msg = "missing provenance: ExplanationInput requires provenance"
            raise CopilotError(msg)
        self._validator.validate_bundle(explanation_input.context_bundle)

    def explain(self, explanation_input: ExplanationInput) -> ExplanationResult:
        """Build structured ExplanationResult from ExplanationInput."""
        self.validate_inputs(explanation_input)
        warnings: list[str] = []
        intent_type = explanation_input.intent.intent_type
        bundle = explanation_input.context_bundle
        allowed = frozenset(bundle.digest_ids)

        if intent_type is UserIntentType.OUT_OF_SCOPE:
            draft = self._refusal_draft(explanation_input)
            return self._finalize(
                explanation_input=explanation_input,
                draft=draft,
                status=ExplanationStatus.REFUSED,
                confidence=ConfidenceLevel.NONE,
                warnings=warnings,
                require_evidence=False,
            )

        if intent_type in (UserIntentType.CLARIFY, UserIntentType.UNKNOWN):
            draft = self._clarify_draft(explanation_input)
            return self._finalize(
                explanation_input=explanation_input,
                draft=draft,
                status=ExplanationStatus.CLARIFY,
                confidence=ConfidenceLevel.NONE,
                warnings=warnings,
                require_evidence=False,
            )

        if not allowed:
            msg = "missing evidence: ContextBundle has no digest_ids"
            raise CopilotError(msg)

        draft = self._template_draft(explanation_input)
        used_fallback = True
        if self._lm is not None:
            lm_result, lm_warnings = self._try_language_model(explanation_input)
            warnings.extend(lm_warnings)
            if lm_result is not None and lm_result.status in (
                LanguageModelStatus.COMPLETE,
                LanguageModelStatus.PARTIAL,
            ):
                draft = self._merge_lm_draft(
                    base=draft,
                    lm_result=lm_result,
                    allowed_digests=allowed,
                )
                used_fallback = False

        if used_fallback:
            warnings.append(
                "deterministic fallback used — LanguageModelPort unavailable "
                "or non-complete."
            )

        confidence = self._confidence(len(allowed))
        status = (
            ExplanationStatus.PARTIAL if warnings else ExplanationStatus.COMPLETE
        )
        return self._finalize(
            explanation_input=explanation_input,
            draft=draft,
            status=status,
            confidence=confidence,
            warnings=warnings,
            require_evidence=True,
        )

    def explain_many(
        self, inputs: tuple[ExplanationInput, ...]
    ) -> tuple[ExplanationResult, ...]:
        """Explain many inputs; reject duplicate explanation identities."""
        seen: set[str] = set()
        results: list[ExplanationResult] = []
        for item in inputs:
            result = self.explain(item)
            key = result.explanation.explanation_id
            if key in seen:
                msg = f"duplicate explanation ids: {key!r}"
                raise CopilotError(msg)
            seen.add(key)
            results.append(result)
        return tuple(results)

    def _finalize(
        self,
        *,
        explanation_input: ExplanationInput,
        draft: ExplanationDraft,
        status: ExplanationStatus,
        confidence: ConfidenceLevel,
        warnings: list[str],
        require_evidence: bool,
    ) -> ExplanationResult:
        allowed = frozenset(explanation_input.context_bundle.digest_ids)
        extra = self._validator.validate_draft(
            draft,
            allowed_digests=allowed,
            require_evidence=require_evidence,
        )
        warnings = [*warnings, *extra]
        if status is ExplanationStatus.COMPLETE and warnings:
            status = ExplanationStatus.PARTIAL

        explanation = Explanation(
            explanation_id=(
                f"dsp.copilot.explanation.{explanation_input.session_id}."
                f"{explanation_input.intent.intent_id}"
            ),
            explanation_type=draft.explanation_type,
            narrative=draft.narrative,
            provenance=_PROVENANCE,
            evidence_refs=draft.citations,
            is_generated_narrative=draft.is_generated_narrative,
            limitations=draft.limitations,
        )
        return ExplanationResult(
            explanation=explanation,
            draft=draft,
            status=status,
            executive_summary=draft.executive_summary,
            key_reasons=draft.key_reasons,
            risks=draft.risks,
            supporting_evidence=draft.supporting_evidence,
            confidence=confidence,
            citations=draft.citations,
            provenance=_PROVENANCE,
            warnings=tuple(dict.fromkeys(warnings)),
        )

    def _template_draft(self, explanation_input: ExplanationInput) -> ExplanationDraft:
        bundle = explanation_input.context_bundle
        intent = explanation_input.intent
        citations = tuple(bundle.digest_ids)
        kg = bundle.knowledge_graph_ref
        reasons = (
            f"Intent routed as {intent.intent_type.value} (cite-only).",
            f"Knowledge Graph citation {kg.report_id} anchors navigation.",
        )
        evidence_lines = tuple(
            f"Cited digest {digest}" for digest in citations
        )
        risks = (
            "Explanation is citation-backed only; no recalculated analysis.",
            "Upstream report payloads are not embedded.",
        )
        claim_links = tuple(
            (f"Platform citation {digest} is in scope for this explanation.", digest)
            for digest in citations
        )
        summary = (
            f"Evidence-backed summary for intent {intent.intent_type.value} "
            f"using {len(citations)} citation(s)."
        )
        narrative = (
            f"{summary} Key reasons: {'; '.join(reasons)} "
            f"Supporting evidence digests: {', '.join(citations)}."
        )
        return ExplanationDraft(
            executive_summary=summary,
            key_reasons=reasons,
            risks=risks,
            supporting_evidence=evidence_lines,
            claim_evidence_links=claim_links,
            citations=citations,
            narrative=narrative,
            explanation_type=ExplanationType.EVIDENCE_SUMMARY,
            is_generated_narrative=False,
            limitations=(
                "Template explanation — deterministic fallback / cite-only.",
                *explanation_input.notes,
            ),
        )

    def _refusal_draft(self, explanation_input: ExplanationInput) -> ExplanationDraft:
        summary = (
            "Request is out of scope for AI Copilot (trading / OMS / order "
            "instructions are not supported)."
        )
        return ExplanationDraft(
            executive_summary=summary,
            key_reasons=("Intent classified as out_of_scope.",),
            risks=("No financial action was generated.",),
            supporting_evidence=(),
            claim_evidence_links=(),
            citations=(),
            narrative=summary,
            explanation_type=ExplanationType.REFUSAL,
            is_generated_narrative=False,
            limitations=("Refusal — no invented facts or orders.",),
        )

    def _clarify_draft(self, explanation_input: ExplanationInput) -> ExplanationDraft:
        summary = (
            "Clarification required before an evidence-backed explanation "
            "can be produced."
        )
        return ExplanationDraft(
            executive_summary=summary,
            key_reasons=("Intent is clarify/unknown; additional user detail needed.",),
            risks=("Proceeding without clarification risks unsupported claims.",),
            supporting_evidence=(),
            claim_evidence_links=(),
            citations=(),
            narrative=summary,
            explanation_type=ExplanationType.CLARIFICATION,
            is_generated_narrative=False,
            limitations=("Clarification — no factual invention.",),
        )

    def _try_language_model(
        self, explanation_input: ExplanationInput
    ) -> tuple[LanguageModelResult | None, list[str]]:
        assert self._lm is not None
        warnings: list[str] = []
        digests = explanation_input.context_bundle.digest_ids
        request = LanguageModelRequest(
            request_id=(
                f"dsp.copilot.lm.req.{explanation_input.session_id}."
                f"{explanation_input.intent.intent_id}"
            ),
            intent_class=explanation_input.intent.intent_type,
            prompt_parts=(
                "Produce cite-only explanation sections.",
                f"Intent: {explanation_input.intent.intent_type.value}",
                f"Digests: {', '.join(digests)}",
            ),
            context_digest_ids=digests,
            provenance=_PROVENANCE,
            constraints=("cite-only", "no-financial-calculation"),
        )
        try:
            result = self._lm.invoke(request)
        except Exception as exc:  # noqa: BLE001 — adapters may raise freely
            warnings.append(f"LanguageModelPort failed: {exc!s}")
            return None, warnings
        if result.status in (
            LanguageModelStatus.PROVIDER_UNAVAILABLE,
            LanguageModelStatus.TIMEOUT,
            LanguageModelStatus.FAILED,
            LanguageModelStatus.UNKNOWN,
            LanguageModelStatus.INVALID_REQUEST,
            LanguageModelStatus.REFUSAL,
        ):
            warnings.append(
                f"LanguageModelPort status {result.status.value}; using fallback."
            )
            return None, warnings
        # Citations from LM must be subset of context digests.
        allowed = frozenset(digests)
        for digest in result.cited_digest_ids:
            if digest not in allowed:
                warnings.append(
                    f"LM cited unknown digest {digest!r}; discarding LM result."
                )
                return None, warnings
        return result, warnings

    def _merge_lm_draft(
        self,
        *,
        base: ExplanationDraft,
        lm_result: LanguageModelResult,
        allowed_digests: frozenset[str],
    ) -> ExplanationDraft:
        narrative = lm_result.narrative_text or base.narrative
        sections = lm_result.structured_sections or ()
        summary = sections[0] if sections else base.executive_summary
        reasons = sections[1:] if len(sections) > 1 else base.key_reasons
        citations = tuple(lm_result.cited_digest_ids) or base.citations
        citations = tuple(c for c in citations if c in allowed_digests) or base.citations
        claim_links = tuple(
            (f"LM-supported citation {digest}.", digest) for digest in citations
        )
        evidence = tuple(f"Cited digest {d}" for d in citations)
        return ExplanationDraft(
            executive_summary=summary,
            key_reasons=tuple(reasons) if reasons else base.key_reasons,
            risks=base.risks,
            supporting_evidence=evidence or base.supporting_evidence,
            claim_evidence_links=claim_links or base.claim_evidence_links,
            citations=citations,
            narrative=narrative,
            explanation_type=ExplanationType.HYBRID,
            is_generated_narrative=True,
            limitations=(
                *base.limitations,
                *lm_result.limitations,
                "Narrative includes LanguageModelPort output; evidence remains cite-only.",
            ),
        )

    def _confidence(self, citation_count: int) -> ConfidenceLevel:
        if citation_count >= 4:
            return ConfidenceLevel.HIGH
        if citation_count >= 2:
            return ConfidenceLevel.MEDIUM
        if citation_count == 1:
            return ConfidenceLevel.LOW
        return ConfidenceLevel.NONE
