"""DecisionPack Evidence Bundle reference integration (C3.6)."""

from __future__ import annotations

import pytest
from ai_committee import Decision
from contracts import Instrument
from core.exceptions import ValidationError
from decision_intelligence import (
    DecisionIntelligenceError,
    DecisionIntelligenceService,
    DecisionPack,
    attach_evidence_bundle_ref,
    present_decision_pack,
)
from industry import EvidenceBundleReference, EvidenceBundleStatus

from .conftest import build_pack, make_recommendation, make_report


def _ref(
    instrument: Instrument,
    *,
    status: EvidenceBundleStatus = EvidenceBundleStatus.INCOMPLETE,
    methodology_id: str = "dsp.methodology.commercial_banking",
    methodology_version: str = "1.0.0",
    digest: str = "abcdef0123456789deadbeef",
) -> EvidenceBundleReference:
    return EvidenceBundleReference(
        bundle_id=f"dsp.evidence_bundle.{instrument.symbol.lower()}.demo",
        instrument_key=instrument.symbol,
        methodology_id=methodology_id,
        methodology_version=methodology_version,
        digest=digest,
        status=status,
    )


class TestLegacyDecisionPack:
    def test_pack_without_evidence(self, instrument: Instrument) -> None:
        pack = build_pack(
            instrument,
            decision=Decision.BUY,
            member_decisions=(Decision.BUY, Decision.BUY, Decision.HOLD),
        )
        assert pack.evidence_bundle_ref is None
        summary = pack.evidence_summary()
        assert summary.attached is False
        assert summary.availability == "not_attached"
        assert summary.reference is None
        view = present_decision_pack(pack)
        assert view.evidence.attached is False
        assert view.evidence.availability == "not_attached"


class TestEvidenceAwareDecisionPack:
    def test_build_pack_with_evidence(self, instrument: Instrument) -> None:
        report = make_report(
            instrument,
            decision=Decision.BUY,
            member_decisions=(Decision.BUY, Decision.BUY, Decision.BUY),
        )
        recommendation = make_recommendation(report)
        ref = _ref(instrument, status=EvidenceBundleStatus.COMPLETE)
        pack = DecisionIntelligenceService().build_pack(
            report, recommendation, evidence_bundle_ref=ref
        )
        assert pack.evidence_bundle_ref == ref
        summary = pack.evidence_summary()
        assert summary.attached is True
        assert summary.status is EvidenceBundleStatus.COMPLETE
        assert summary.availability == "complete"
        assert summary.bundle_version == "1.0.0"
        assert summary.reference is not None
        assert "observation" not in summary.__dataclass_fields__
        view = present_decision_pack(pack)
        assert view.evidence.attached is True
        assert view.evidence.reference == summary.reference

    def test_attach_evidence_optional_injection(
        self, instrument: Instrument
    ) -> None:
        pack = build_pack(
            instrument,
            decision=Decision.HOLD,
            member_decisions=(Decision.HOLD, Decision.HOLD, Decision.BUY),
        )
        ref = _ref(instrument)
        attached = attach_evidence_bundle_ref(pack, ref)
        assert attached.evidence_bundle_ref == ref
        assert pack.evidence_bundle_ref is None
        cleared = attach_evidence_bundle_ref(attached, None)
        assert cleared.evidence_bundle_ref is None

    def test_version_mismatch_rejected(self, instrument: Instrument) -> None:
        pack = build_pack(
            instrument,
            decision=Decision.BUY,
            member_decisions=(Decision.BUY,) * 3,
        )
        ref = _ref(instrument, methodology_version="1.0.0")
        with pytest.raises(DecisionIntelligenceError, match="methodology_version"):
            attach_evidence_bundle_ref(
                pack,
                ref,
                expected_methodology_version="2.0.0",
            )

    def test_instrument_mismatch_rejected(self, instrument: Instrument) -> None:
        pack = build_pack(
            instrument,
            decision=Decision.BUY,
            member_decisions=(Decision.BUY,) * 3,
        )
        bad = EvidenceBundleReference(
            bundle_id="dsp.evidence_bundle.msft.demo",
            instrument_key="MSFT",
            methodology_id="dsp.methodology.commercial_banking",
            methodology_version="1.0.0",
            digest="abcdef0123456789deadbeef",
            status=EvidenceBundleStatus.PARTIAL,
        )
        with pytest.raises(ValidationError, match="instrument_key"):
            DecisionPack(
                recommendation=pack.recommendation,
                brief=pack.brief,
                assurance=pack.assurance,
                evidence_bundle_ref=bad,
            )

    def test_invalid_digest_rejected(self, instrument: Instrument) -> None:
        pack = build_pack(
            instrument,
            decision=Decision.BUY,
            member_decisions=(Decision.BUY,) * 3,
        )
        bad = EvidenceBundleReference(
            bundle_id="dsp.evidence_bundle.aapl.demo",
            instrument_key=instrument.symbol,
            methodology_id="dsp.methodology.commercial_banking",
            methodology_version="1.0.0",
            digest="not-a-hex-digest!!",
            status=EvidenceBundleStatus.PARTIAL,
        )
        with pytest.raises(ValidationError, match="digest"):
            DecisionPack(
                recommendation=pack.recommendation,
                brief=pack.brief,
                assurance=pack.assurance,
                evidence_bundle_ref=bad,
            )

    def test_backward_compatible_equality(self, instrument: Instrument) -> None:
        a = build_pack(
            instrument,
            decision=Decision.SELL,
            member_decisions=(Decision.SELL, Decision.SELL, Decision.HOLD),
        )
        b = build_pack(
            instrument,
            decision=Decision.SELL,
            member_decisions=(Decision.SELL, Decision.SELL, Decision.HOLD),
        )
        assert a == b
        assert a.evidence_bundle_ref is None
