"""Grounded answer builder (EPIC-A001) — extractive, never fabricates."""

from __future__ import annotations

from typing import Any

from dsp_platform.research_copilot.citations import build_citations
from dsp_platform.research_copilot.extract import (
    TOPIC_TO_REPORT_SECTIONS,
    TOPIC_TO_RO_SECTIONS,
    extract_section,
    format_section_facts,
)
from dsp_platform.research_copilot.models import (
    Citation,
    ProcessedQuestion,
    ResearchContextBundle,
    UNAVAILABLE_MESSAGE,
)

__all__ = ["build_grounded_answer"]


def _section_available(section: dict[str, Any] | None) -> bool:
    if section is None:
        return False
    if "available" in section:
        return bool(section.get("available"))
    return True


def build_grounded_answer(
    question: ProcessedQuestion,
    context: ResearchContextBundle,
) -> tuple[str, tuple[Citation, ...], bool]:
    """Return (answer_text, citations, unavailable_flag)."""
    has_any = any(
        (
            context.research_object is not None,
            context.report is not None,
            context.archive_snapshot is not None,
            context.research_diff is not None,
        )
    )
    if not has_any:
        return UNAVAILABLE_MESSAGE, (), True

    blocks: list[str] = []
    cite_specs: list[tuple[str, str, bool]] = []
    any_available = False

    # Prefer report for display sections, then research object, then snapshot payload
    for topic in question.topics:
        if topic == "diff" and context.research_diff is not None:
            diff = dict(context.research_diff)
            summary = diff.get("change_summary") or {}
            blocks.append("research_diff:")
            if isinstance(summary, dict) and summary:
                for key in sorted(summary.keys(), key=str):
                    blocks.append(f"  - {key}: {summary[key]}")
                any_available = True
                cite_specs.append(("research_diff", "change_summary", True))
            else:
                blocks.append(f"  - {UNAVAILABLE_MESSAGE}")
                cite_specs.append(("research_diff", "change_summary", False))
            sections = diff.get("sections") or []
            if isinstance(sections, list):
                changed = [
                    s
                    for s in sections
                    if isinstance(s, dict) and s.get("status") != "unchanged"
                ]
                blocks.append(f"  - changed_sections: {len(changed)}")
                cite_specs.append(("research_diff", "sections", True))
            continue

        report_names = TOPIC_TO_REPORT_SECTIONS.get(topic, ())
        ro_names = TOPIC_TO_RO_SECTIONS.get(topic, ())

        if context.report is not None:
            for name in report_names:
                section = extract_section(context.report, name)
                sec_dict = dict(section) if section else None
                avail = _section_available(sec_dict)
                any_available = any_available or avail
                blocks.append(format_section_facts(f"report.{name}", sec_dict))
                cite_specs.append(("institutional_report", name, avail))

        if context.research_object is not None:
            for name in ro_names:
                section = extract_section(context.research_object, name)
                sec_dict = dict(section) if section else None
                avail = _section_available(sec_dict)
                any_available = any_available or avail
                blocks.append(format_section_facts(f"research_object.{name}", sec_dict))
                cite_specs.append(("research_object", name, avail))

        if context.archive_snapshot is not None:
            snap = dict(context.archive_snapshot)
            payload = snap.get("payload")
            if isinstance(payload, dict):
                # For snapshot, cite the snapshot and surface topic sections from payload
                names = report_names or ro_names or ("metadata",)
                for name in names:
                    section = extract_section(payload, name)
                    if section is None and name in payload and not isinstance(
                        payload.get(name), dict
                    ):
                        # scalar/top-level — report as unavailable section shape
                        blocks.append(
                            format_section_facts(
                                f"archive_snapshot.payload.{name}",
                                {
                                    "available": True,
                                    "payload": {name: payload.get(name)},
                                },
                            )
                        )
                        cite_specs.append(("archive_snapshot", name, True))
                        any_available = True
                        continue
                    sec_dict = dict(section) if section else None
                    avail = _section_available(sec_dict)
                    any_available = any_available or avail
                    blocks.append(
                        format_section_facts(
                            f"archive_snapshot.payload.{name}", sec_dict
                        )
                    )
                    cite_specs.append(("archive_snapshot", name, avail))

    if not blocks:
        return UNAVAILABLE_MESSAGE, (), True

    preface = (
        "Answer grounded in Institutional Research Platform outputs "
        f"(intent={question.intent}). "
        "No new calculations or recommendations were performed."
    )
    answer = preface + "\n\n" + "\n".join(blocks)
    if not any_available:
        answer = UNAVAILABLE_MESSAGE + "\n\n" + answer

    citations = build_citations(context, sections=cite_specs)
    unavailable = not any_available
    return answer, citations, unavailable
