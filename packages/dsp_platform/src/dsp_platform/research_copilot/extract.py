"""Section extraction helpers (EPIC-A001) — pass-through only."""

from __future__ import annotations

from typing import Any, Mapping

from dsp_platform.research_object.models import UNAVAILABLE_MESSAGE

__all__ = [
    "TOPIC_TO_RO_SECTIONS",
    "TOPIC_TO_REPORT_SECTIONS",
    "extract_section",
    "format_section_facts",
]

TOPIC_TO_RO_SECTIONS: dict[str, tuple[str, ...]] = {
    "market_data": ("market_data",),
    "valuation": ("valuation",),
    "margin_of_safety": ("margin_of_safety",),
    "business_quality": ("business_quality",),
    "risk": ("risk",),
    "scenarios": ("scenarios",),
    "recommendation": ("recommendation",),
    "financial_statements": ("financial_statements",),
    "corporate_actions": ("corporate_actions",),
    "historical": ("historical_series",),
    "explainability": ("explainability",),
    "audit": ("audit", "provenance"),
    "identity": ("identity", "metadata"),
    "overview": ("identity", "recommendation", "margin_of_safety", "market_data"),
    "diff": (),
}

TOPIC_TO_REPORT_SECTIONS: dict[str, tuple[str, ...]] = {
    "market_data": ("market_data", "header"),
    "valuation": ("valuation", "header"),
    "margin_of_safety": ("margin_of_safety", "header"),
    "business_quality": ("business_quality",),
    "risk": ("risk",),
    "scenarios": ("scenarios",),
    "recommendation": ("recommendation", "header", "executive_summary"),
    "financial_statements": ("financial_statements",),
    "corporate_actions": ("corporate_actions",),
    "historical": ("historical_summary",),
    "explainability": ("explainability",),
    "audit": ("audit", "provenance"),
    "identity": ("executive_summary", "metadata"),
    "overview": ("header", "executive_summary", "recommendation"),
    "diff": (),
}


def extract_section(
    document: Mapping[str, Any] | None, section_name: str
) -> Mapping[str, Any] | None:
    if not isinstance(document, Mapping):
        return None
    section = document.get(section_name)
    return section if isinstance(section, Mapping) else None


def format_section_facts(section_name: str, section: Mapping[str, Any] | None) -> str:
    """Render existing section content as text — never invent fields."""
    if section is None:
        return f"{section_name}: {UNAVAILABLE_MESSAGE}"
    available = bool(section.get("available", True))
    if available is False:
        msg = section.get("message") or UNAVAILABLE_MESSAGE
        return f"{section_name}: {msg}"

    payload = section.get("payload")
    lines: list[str] = [f"{section_name}:"]
    if isinstance(payload, Mapping):
        fields = payload.get("fields")
        if isinstance(fields, Mapping) and fields:
            for key in sorted(fields.keys(), key=str):
                val = fields[key]
                if val is None:
                    val = UNAVAILABLE_MESSAGE
                lines.append(f"  - {key}: {val}")
        else:
            for key in sorted(payload.keys(), key=str):
                if key in {"source_payload", "source_status", "source_name"}:
                    continue
                val = payload[key]
                if val is None:
                    val = UNAVAILABLE_MESSAGE
                lines.append(f"  - {key}: {val}")
    else:
        lines.append(f"  - {UNAVAILABLE_MESSAGE}")
    if section.get("retrieved_at"):
        lines.append(f"  - retrieved_at: {section.get('retrieved_at')}")
    return "\n".join(lines)
