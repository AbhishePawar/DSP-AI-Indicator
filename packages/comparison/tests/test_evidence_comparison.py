"""Comparison Evidence Bundle integration tests (C3.7)."""

from __future__ import annotations

import pytest
from industry import (
    EvidenceBundleAssemblyContext,
    seed_example_evidence_bundle_assembler,
)

from comparison import ComparisonError, ComparisonStatus

from .test_comparison import (
    _engine,
    _instrument,
    _with_assurance,
    _with_mos,
    make_pack,
)
from decision_intelligence import AssuranceLevel


def _banking_bundles(
    symbols: tuple[str, ...] = ("HDFCBANK", "ICICIBANK"),
    *,
    emit_placeholder: bool = False,
):
    assembler = seed_example_evidence_bundle_assembler()
    extras = (("emit_placeholder", "true"),) if emit_placeholder else ()
    return tuple(
        assembler.assemble(
            EvidenceBundleAssemblyContext(
                instrument_key=symbol,
                methodology_id="dsp.methodology.commercial_banking",
                methodology_version="1.0.0",
                extras=extras,
            )
        )
        for symbol in symbols
    )


class TestComparisonWithoutBundles:
    def test_legacy_path_records_evidence_gap(self) -> None:
        engine = _engine()
        a = _with_mos(make_pack(_instrument("HDFCBANK")), 0.30)
        b = _with_mos(make_pack(_instrument("ICICIBANK")), 0.20)
        result = engine.compare_packs((a, b))
        assert result.status is ComparisonStatus.COMPLETE
        summary = result.report.evidence_summary
        assert summary is not None
        assert summary.attached is False
        assert summary.availability == "not_supplied"
        assert any(
            lim.code == "industry_evidence_not_supplied"
            for lim in result.report.limitations
        )
        assert result.report.evidence_observations == ()


class TestComparisonWithBundles:
    def test_cites_industry_observations(self) -> None:
        engine = _engine()
        a = _with_mos(make_pack(_instrument("HDFCBANK")), 0.30)
        b = _with_mos(make_pack(_instrument("ICICIBANK")), 0.20)
        a = _with_assurance(a, AssuranceLevel.HIGH)
        b = _with_assurance(b, AssuranceLevel.MODERATE)
        bundles = _banking_bundles()
        result = engine.compare_packs((a, b), evidence_bundles=bundles)
        assert result.status is ComparisonStatus.COMPLETE
        report = result.report
        assert report.evidence_summary is not None
        assert report.evidence_summary.attached is True
        assert report.evidence_summary.bundle_count == 2
        assert report.evidence_summary.bundle_versions == ("1.0.0",)
        assert report.evidence_observations
        assert any(
            o.code == "industry_evidence_observation"
            for o in report.evidence_observations
        )
        assert any(
            lim.code.startswith("industry_evidence_")
            for lim in report.evidence_limitations
        )
        blob = " ".join(o.text.lower() for o in report.evidence_observations)
        for word in ("better", "best", "winner", "score", "rank"):
            assert word not in blob.split()

    def test_complete_placeholder_availability(self) -> None:
        engine = _engine()
        a = make_pack(_instrument("HDFCBANK"))
        b = make_pack(_instrument("ICICIBANK"))
        bundles = _banking_bundles(emit_placeholder=True)
        result = engine.compare_packs((a, b), evidence_bundles=bundles)
        assert result.report.evidence_summary is not None
        assert result.report.evidence_summary.availability == "complete"

    def test_mixed_coverage(self) -> None:
        engine = _engine()
        a = make_pack(_instrument("HDFCBANK"))
        b = make_pack(_instrument("ICICIBANK"))
        only_a = _banking_bundles(("HDFCBANK",))
        result = engine.compare_packs((a, b), evidence_bundles=only_a)
        assert result.report.evidence_summary is not None
        assert result.report.evidence_summary.availability == "partial_coverage"
        assert result.report.evidence_summary.missing_symbols == ("ICICIBANK",)
        assert any(
            lim.code == "industry_evidence_missing_for_peer"
            for lim in result.report.evidence_limitations
        )


class TestEvidenceValidation:
    def test_methodology_mismatch_rejected(self) -> None:
        engine = _engine()
        a = make_pack(_instrument("HDFCBANK"))
        b = make_pack(_instrument("ICICIBANK"))
        assembler = seed_example_evidence_bundle_assembler()
        wrong = assembler.assemble(
            EvidenceBundleAssemblyContext(
                instrument_key="HDFCBANK",
                methodology_id="dsp.methodology.electric_utilities",
                methodology_version="1.0.0",
            )
        )
        ok = _banking_bundles(("ICICIBANK",))[0]
        with pytest.raises(ComparisonError, match="methodology mismatch"):
            engine.compare_packs((a, b), evidence_bundles=(wrong, ok))

    def test_unknown_instrument_rejected(self) -> None:
        engine = _engine()
        a = make_pack(_instrument("HDFCBANK"))
        b = make_pack(_instrument("ICICIBANK"))
        foreign = _banking_bundles(("SBIN",))
        with pytest.raises(ComparisonError, match="not among included"):
            engine.compare_packs((a, b), evidence_bundles=foreign)
