"""Unit tests for public research report schema validation and privacy boundary."""

from __future__ import annotations

import pytest
from api_platform.api.research_report_schema import (
    PublicResearchReportDTO,
    validate_public_research_report,
)


def _valid_report_dict() -> dict:
    return {
        "recommendation": "BUY",
        "valuation": "Fair Value ₹950",
        "analysis": "Solid fundamentals with strong balance sheet and wide moat.",
        "risks": ["Cyclical automotive downturn", "Commodity price inflation"],
        "evidence_citations": [
            "FinancialStatementPort:2024:BalanceSheet",
            "MarketQuotePort:NSE:TATAMOTORS",
        ],
        "confidence": 0.85,
        "limitations": ["Historical statements only; no guidance forecasts."],
        "schema_version": "public_decision_pack_v1",
    }


def test_valid_report_passes_validation():
    valid = _valid_report_dict()
    dto_dict, err = validate_public_research_report(valid)
    assert err is None
    assert dto_dict is not None
    assert dto_dict["recommendation"] == "BUY"
    assert dto_dict["confidence"] == 0.85
    assert len(dto_dict["evidence_citations"]) == 2


def test_missing_required_fields_rejected():
    for req_field in ["recommendation", "analysis", "confidence"]:
        data = _valid_report_dict()
        del data[req_field]
        dto_dict, err = validate_public_research_report(data)
        assert dto_dict is None
        assert "schema validation failed" in err


def test_wrong_field_types_rejected():
    # confidence as string
    data = _valid_report_dict()
    data["confidence"] = "very_confident"
    dto_dict, err = validate_public_research_report(data)
    assert dto_dict is None
    assert "schema validation failed" in err

    # risks as string instead of list
    data = _valid_report_dict()
    data["risks"] = "not_a_list"
    dto_dict, err = validate_public_research_report(data)
    assert dto_dict is None
    assert "schema validation failed" in err

    # evidence_citations containing non-string
    data = _valid_report_dict()
    data["evidence_citations"] = [123, 456]
    dto_dict, err = validate_public_research_report(data)
    assert dto_dict is None
    assert "schema validation failed" in err


def test_invalid_confidence_bounds_rejected():
    # Greater than 1.0
    data = _valid_report_dict()
    data["confidence"] = 1.01
    dto_dict, err = validate_public_research_report(data)
    assert dto_dict is None
    assert "schema validation failed" in err

    # Less than 0.0
    data = _valid_report_dict()
    data["confidence"] = -0.05
    dto_dict, err = validate_public_research_report(data)
    assert dto_dict is None
    assert "schema validation failed" in err

    # NaN / Inf
    data = _valid_report_dict()
    data["confidence"] = float("nan")
    dto_dict, err = validate_public_research_report(data)
    assert dto_dict is None

    data = _valid_report_dict()
    data["confidence"] = float("inf")
    dto_dict, err = validate_public_research_report(data)
    assert dto_dict is None


def test_malformed_evidence_citations_rejected():
    # Empty string citation
    data = _valid_report_dict()
    data["evidence_citations"] = [""]
    dto_dict, err = validate_public_research_report(data)
    assert dto_dict is None
    assert "non-empty string" in err

    # Citation with invalid control characters
    data = _valid_report_dict()
    data["evidence_citations"] = ["valid_source\x00_null_byte"]
    dto_dict, err = validate_public_research_report(data)
    assert dto_dict is None
    assert "control characters" in err


def test_private_fields_and_canaries_rejected():
    # Private field in top-level
    for priv in ["chain_of_thought", "internal_prompt", "raw_ai_response", "api_key", "scratchpad"]:
        data = _valid_report_dict()
        data[priv] = "secret_value"
        dto_dict, err = validate_public_research_report(data)
        assert dto_dict is None
        assert "privacy boundary violation" in err or "extra" in err

    # Secret canary pattern in analysis text
    data = _valid_report_dict()
    data["analysis"] = "Leak: DSP_AI_SECRET_CANARY found"
    dto_dict, err = validate_public_research_report(data)
    assert dto_dict is None
    assert "privacy boundary violation" in err

    # Bearer token pattern in analysis text
    data = _valid_report_dict()
    data["analysis"] = "Leak: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.xyz"
    dto_dict, err = validate_public_research_report(data)
    assert dto_dict is None
    assert "privacy boundary violation" in err


def test_extra_fields_forbidden():
    data = _valid_report_dict()
    data["extra_unapproved_field"] = "unexpected"
    dto_dict, err = validate_public_research_report(data)
    assert dto_dict is None
    assert "schema validation failed" in err


def test_non_dict_input_rejected():
    dto_dict, err = validate_public_research_report(["not", "a", "dict"])
    assert dto_dict is None
    assert "expected dict" in err


def test_schema_version_enforced():
    data = _valid_report_dict()
    data["schema_version"] = "v2_unsupported"
    dto_dict, err = validate_public_research_report(data)
    assert dto_dict is None
    assert "schema validation failed" in err


def test_non_serializable_values_rejected():
    class UnserializableObject:
        pass

    data = _valid_report_dict()
    data["valuation"] = UnserializableObject()
    dto_dict, err = validate_public_research_report(data)
    assert dto_dict is None
    assert err is not None
