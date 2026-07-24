"""Business Quality explainability framework tests."""

from __future__ import annotations

from business_quality import (
    RESEARCH_DISCLAIMER,
    Confidence,
    build_explainability,
    explainability_from_mapping,
)


class TestExplainability:
    def test_build_and_dict(self) -> None:
        exp = build_explainability(
            title="T",
            description="D",
            evidence=("e1", "e2"),
            reasoning="R",
            confidence=Confidence.HIGH,
            limitations="L",
            references=("ref://1",),
        )
        payload = exp.to_dict()
        assert payload["title"] == "T"
        assert payload["confidence"] == "high"
        assert payload["evidence"] == ["e1", "e2"]
        assert payload["references"] == ["ref://1"]
        assert "research" in RESEARCH_DISCLAIMER.lower() or "Framework" in RESEARCH_DISCLAIMER

    def test_defaults_and_from_mapping(self) -> None:
        exp = build_explainability(
            title="t",
            description="d",
            reasoning="r",
            confidence="low",
        )
        assert exp.evidence == ()
        assert exp.confidence is Confidence.LOW

        roundtrip = explainability_from_mapping(exp.to_dict())
        assert roundtrip.title == "t"
        assert roundtrip.confidence is Confidence.LOW

        empty = explainability_from_mapping({})
        assert empty.title == ""
        assert empty.confidence is Confidence.INSUFFICIENT
