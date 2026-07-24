"""Industry Evidence Bundle tests (C3.5)."""

from __future__ import annotations

import pytest
from core.exceptions import ValidationError

from industry import (
    ApplicabilityLevel,
    EvidenceAvailability,
    EvidenceBundle,
    EvidenceBundleAssemblyContext,
    EvidenceBundleEntry,
    EvidenceBundleMetadata,
    EvidenceBundleStatus,
    EvidenceBundleSummary,
    IndustryError,
    MissingEvidencePolicy,
    seed_example_evidence_bundle_assembler,
    seed_example_evidence_bundle_context,
)
from industry.evidence_applicability import (
    EvidenceApplicabilityRule,
    IndustryEvidenceApplicability,
)
from industry.evidence_applicability_registry import (
    IndustryEvidenceApplicabilityRegistry,
)
from industry.evidence_bundle_assembler import EvidenceBundleAssembler
from industry.evidence_bundle_seeds import example_banking_assembly_context


class TestBundleModels:
    def test_duplicate_entries_rejected(self) -> None:
        meta = EvidenceBundleMetadata(
            bundle_id="dsp.evidence_bundle.x",
            instrument_key="AAA",
            methodology_id="dsp.methodology.commercial_banking",
            methodology_version="1.0.0",
            applicability_id="dsp.evidence_applicability.commercial_banking",
            applicability_version="1.0.0",
            missing_evidence_policy=MissingEvidencePolicy.RECORD_GAP,
        )
        entry = EvidenceBundleEntry(
            evidence_id="dsp.evidence.nim_stability",
            applicability_level=ApplicabilityLevel.REQUIRED,
            is_gap=True,
            limitations=("gap",),
        )
        with pytest.raises(ValidationError, match="duplicate evidence"):
            EvidenceBundle(
                metadata=meta,
                status=EvidenceBundleStatus.INCOMPLETE,
                entries=(entry, entry),
                summary=EvidenceBundleSummary(
                    entry_count=2,
                    required_count=1,
                    required_available_count=0,
                    required_missing_count=1,
                    gap_count=2,
                    observation_count=0,
                ),
            )

    def test_empty_entries_require_empty_status(self) -> None:
        meta = EvidenceBundleMetadata(
            bundle_id="dsp.evidence_bundle.empty",
            instrument_key="AAA",
            methodology_id="dsp.methodology.commercial_banking",
            methodology_version="1.0.0",
            applicability_id="dsp.evidence_applicability.commercial_banking",
            applicability_version="1.0.0",
            missing_evidence_policy=MissingEvidencePolicy.RECORD_GAP,
        )
        with pytest.raises(ValidationError, match="EMPTY status"):
            EvidenceBundle(
                metadata=meta,
                status=EvidenceBundleStatus.COMPLETE,
                entries=(),
                summary=EvidenceBundleSummary(
                    entry_count=0,
                    required_count=0,
                    required_available_count=0,
                    required_missing_count=0,
                    gap_count=0,
                    observation_count=0,
                ),
            )
        empty = EvidenceBundle(
            metadata=meta,
            status=EvidenceBundleStatus.EMPTY,
            entries=(),
            summary=EvidenceBundleSummary(
                entry_count=0,
                required_count=0,
                required_available_count=0,
                required_missing_count=0,
                gap_count=0,
                observation_count=0,
            ),
        )
        assert empty.status is EvidenceBundleStatus.EMPTY
        assert empty.digest


class TestBundleAssembly:
    def test_incomplete_without_placeholder(self) -> None:
        assembler = seed_example_evidence_bundle_assembler()
        bundle = assembler.assemble(example_banking_assembly_context())
        assert bundle.status is EvidenceBundleStatus.INCOMPLETE
        assert bundle.summary.required_missing_count >= 1
        assert bundle.summary.gap_count >= 1
        assert all(e.observation is not None for e in bundle.entries)
        assert "score" not in " ".join(bundle.limitations).lower()
        ref = bundle.reference()
        assert ref.digest == bundle.digest
        assert ref.status is bundle.status

    def test_complete_with_placeholder(self) -> None:
        assembler = seed_example_evidence_bundle_assembler()
        bundle = assembler.assemble(
            example_banking_assembly_context(emit_placeholder=True)
        )
        assert bundle.status is EvidenceBundleStatus.COMPLETE
        assert bundle.summary.required_missing_count == 0
        nim = bundle.entry_for("dsp.evidence.nim_stability")
        assert nim is not None
        assert nim.provider_result is not None
        assert (
            nim.provider_result.availability is EvidenceAvailability.AVAILABLE
        )
        assert nim.is_gap is False

    def test_assemble_many_deterministic(self) -> None:
        assembler = seed_example_evidence_bundle_assembler()
        contexts = (
            example_banking_assembly_context(instrument_key="HDFCBANK"),
            example_banking_assembly_context(instrument_key="ICICIBANK"),
        )
        a = assembler.assemble_many(contexts)
        b = assembler.assemble_many(contexts)
        assert a == b
        assert a[0].metadata.instrument_key == "HDFCBANK"
        assert a[1].metadata.instrument_key == "ICICIBANK"

    def test_bundle_metadata(self) -> None:
        assembler = seed_example_evidence_bundle_assembler()
        meta = assembler.bundle_metadata(example_banking_assembly_context())
        assert meta.methodology_id == "dsp.methodology.commercial_banking"
        assert meta.applicability_id.endswith("commercial_banking")

    def test_missing_methodology_rejected(self) -> None:
        with pytest.raises(ValidationError, match="methodology_id"):
            EvidenceBundleAssemblyContext(
                instrument_key="AAA",
                methodology_id="",
                methodology_version="1.0.0",
            )

    def test_hard_fail_policy(self) -> None:
        (
            _tax,
            _chars,
            methods,
            _metrics,
            evidence,
            _applicability,
            providers,
            interpreters,
        ) = seed_example_evidence_bundle_context()
        hard = IndustryEvidenceApplicability(
            id="dsp.evidence_applicability.commercial_banking_hard",
            methodology_id="dsp.methodology.commercial_banking",
            version="2.0.0",
            methodology_version_pin="1.0.0",
            rules=(
                EvidenceApplicabilityRule(
                    evidence_id="dsp.evidence.nim_stability",
                    level=ApplicabilityLevel.REQUIRED,
                ),
            ),
            missing_evidence_policy=MissingEvidencePolicy.HARD_FAIL,
        )
        app = IndustryEvidenceApplicabilityRegistry(methods, evidence)
        app.register(hard)
        assembler = EvidenceBundleAssembler(
            evidence=evidence,
            applicability=app,
            providers=providers,
            interpreters=interpreters,
        )
        with pytest.raises(IndustryError, match="HARD_FAIL"):
            assembler.assemble(example_banking_assembly_context())

    def test_franchise_partial_or_incomplete(self) -> None:
        assembler = seed_example_evidence_bundle_assembler()
        bundle = assembler.assemble(
            EvidenceBundleAssemblyContext(
                instrument_key="NESTLEIND",
                methodology_id="dsp.methodology.premium_consumer_franchise",
                methodology_version="1.0.0",
            )
        )
        assert bundle.status in {
            EvidenceBundleStatus.INCOMPLETE,
            EvidenceBundleStatus.PARTIAL,
        }
        assert bundle.status is not EvidenceBundleStatus.EMPTY
        assert len(bundle.entries) >= 1

    def test_immutability(self) -> None:
        assembler = seed_example_evidence_bundle_assembler()
        bundle = assembler.assemble(example_banking_assembly_context())
        with pytest.raises(AttributeError):
            bundle.status = EvidenceBundleStatus.COMPLETE  # type: ignore[misc]
        assert bundle.reference().digest == bundle.digest
