"""Business Quality validation framework tests."""

from __future__ import annotations

import pytest

from business_quality import (
    BusinessQualityValidationError,
    Confidence,
    EvidenceLevel,
    empty_validation,
    merge_validation_results,
    validate_confidence,
    validate_evidence_level,
    validate_required_inputs,
)


class TestValidation:
    def test_required_ok(self) -> None:
        result = validate_required_inputs(
            {"a": 1, "b": "ok"},
            ("a", "b"),
            raise_on_missing=False,
        )
        assert result.ok
        assert result.missing_inputs == ()
        assert result.to_dict()["ok"] is True

    def test_missing_and_invalid(self) -> None:
        with pytest.raises(BusinessQualityValidationError, match="Missing"):
            validate_required_inputs({"a": None}, ("a", "b"))

        soft = validate_required_inputs(
            None,
            ("x",),
            raise_on_missing=False,
        )
        assert not soft.ok
        assert soft.missing_inputs == ("x",)

        bad = validate_required_inputs(
            {"a": float("nan"), "b": "  "},
            ("a", "b"),
            raise_on_missing=False,
        )
        assert not bad.ok
        assert "a" in bad.invalid_inputs
        assert "b" in bad.invalid_inputs

        with pytest.raises(BusinessQualityValidationError, match="Invalid"):
            validate_required_inputs(
                {"a": float("inf")},
                ("a",),
            )

    def test_confidence_and_evidence(self) -> None:
        assert validate_confidence(Confidence.HIGH) is Confidence.HIGH
        assert validate_confidence("medium") is Confidence.MEDIUM
        with pytest.raises(BusinessQualityValidationError, match="required"):
            validate_confidence(None)
        with pytest.raises(BusinessQualityValidationError, match="Invalid confidence"):
            validate_confidence("nope")
        with pytest.raises(BusinessQualityValidationError, match="Insufficient"):
            validate_confidence(
                Confidence.INSUFFICIENT, allow_insufficient=False
            )

        assert validate_evidence_level(EvidenceLevel.ADEQUATE) is EvidenceLevel.ADEQUATE
        assert validate_evidence_level("limited") is EvidenceLevel.LIMITED
        with pytest.raises(BusinessQualityValidationError, match="required"):
            validate_evidence_level(None)
        with pytest.raises(BusinessQualityValidationError, match="Invalid evidence"):
            validate_evidence_level("bogus")
        with pytest.raises(BusinessQualityValidationError, match="none"):
            validate_evidence_level(EvidenceLevel.NONE, allow_none=False)

    def test_merge_and_empty(self) -> None:
        assert empty_validation().ok
        assert empty_validation(ok=False).ok is False
        assert merge_validation_results([]).ok
        a = validate_required_inputs({"a": 1}, ("a",), raise_on_missing=False)
        b = validate_required_inputs({"b": None}, ("b",), raise_on_missing=False)
        merged = merge_validation_results([a, b])
        assert not merged.ok
        assert "b" in merged.missing_inputs
