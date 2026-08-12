"""Minimal .pptx export via Office Open XML (stdlib only, EPIC-R003).

Same hand-rolled OOXML approach as ``excel_export.py``/``docx_export.py`` —
no third-party presentation library dependency. One title slide plus one
slide per Institutional Report section; values preserved exactly, no
research reformatting.
"""

from __future__ import annotations

import zipfile
from io import BytesIO
from xml.sax.saxutils import escape

from dsp_platform.institutional_export.mapper import flatten_report
from dsp_platform.institutional_report.models import (
    REPORT_SECTION_ORDER,
    InstitutionalResearchReport,
    UNAVAILABLE_MESSAGE,
)

__all__ = ["export_pptx_bytes"]

_MAX_BULLETS_PER_SLIDE = 14

_CONTENT_TYPES_TEMPLATE = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
    '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
    '<Default Extension="xml" ContentType="application/xml"/>'
    '<Override PartName="/ppt/presentation.xml" '
    'ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>'
    '<Override PartName="/ppt/slideMasters/slideMaster1.xml" '
    'ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml"/>'
    '<Override PartName="/ppt/slideLayouts/slideLayout1.xml" '
    'ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml"/>'
    '<Override PartName="/ppt/theme/theme1.xml" '
    'ContentType="application/vnd.openxmlformats-officedocument.theme+xml"/>'
    "{slide_overrides}"
    "</Types>"
)

_ROOT_RELS = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Id="rId1" '
    'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
    'Target="ppt/presentation.xml"/>'
    "</Relationships>"
)

_THEME_XML = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" name="DSP Institutional">'
    "<a:themeElements>"
    '<a:clrScheme name="DSP">'
    '<a:dk1><a:sysClr val="windowText" lastClr="000000"/></a:dk1>'
    '<a:lt1><a:sysClr val="window" lastClr="FFFFFF"/></a:lt1>'
    '<a:dk2><a:srgbClr val="0B1F3A"/></a:dk2>'
    '<a:lt2><a:srgbClr val="E9EEF5"/></a:lt2>'
    '<a:accent1><a:srgbClr val="1F5C8B"/></a:accent1>'
    '<a:accent2><a:srgbClr val="2E8B57"/></a:accent2>'
    '<a:accent3><a:srgbClr val="B8860B"/></a:accent3>'
    '<a:accent4><a:srgbClr val="8B1A1A"/></a:accent4>'
    '<a:accent5><a:srgbClr val="4B4B4B"/></a:accent5>'
    '<a:accent6><a:srgbClr val="6B4C9A"/></a:accent6>'
    '<a:hlink><a:srgbClr val="1F5C8B"/></a:hlink>'
    '<a:folHlink><a:srgbClr val="6B4C9A"/></a:folHlink>'
    "</a:clrScheme>"
    '<a:fontScheme name="DSP">'
    '<a:majorFont><a:latin typeface="Calibri"/></a:majorFont>'
    '<a:minorFont><a:latin typeface="Calibri"/></a:minorFont>'
    "</a:fontScheme>"
    '<a:fmtScheme name="DSP">'
    "<a:fillStyleLst>"
    '<a:solidFill><a:schemeClr val="phClr"/></a:solidFill>'
    '<a:solidFill><a:schemeClr val="phClr"/></a:solidFill>'
    '<a:solidFill><a:schemeClr val="phClr"/></a:solidFill>'
    "</a:fillStyleLst>"
    "<a:lnStyleLst>"
    '<a:ln><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln>'
    '<a:ln><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln>'
    '<a:ln><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln>'
    "</a:lnStyleLst>"
    "<a:effectStyleLst>"
    "<a:effectStyle><a:effectLst/></a:effectStyle>"
    "<a:effectStyle><a:effectLst/></a:effectStyle>"
    "<a:effectStyle><a:effectLst/></a:effectStyle>"
    "</a:effectStyleLst>"
    "<a:bgFillStyleLst>"
    '<a:solidFill><a:schemeClr val="phClr"/></a:solidFill>'
    '<a:solidFill><a:schemeClr val="phClr"/></a:solidFill>'
    '<a:solidFill><a:schemeClr val="phClr"/></a:solidFill>'
    "</a:bgFillStyleLst>"
    "</a:fmtScheme>"
    "</a:themeElements>"
    "</a:theme>"
)

_SLIDE_LAYOUT_XML = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<p:sldLayout xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
    'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
    'type="title" preserve="1">'
    "<p:cSld><p:spTree>"
    "<p:nvGrpSpPr><p:cNvPr id=\"1\" name=\"\"/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>"
    "<p:grpSpPr/>"
    "</p:spTree></p:cSld>"
    "<p:clrMapOvr><a:overrideClrMapping bg1=\"lt1\" tx1=\"dk1\" bg2=\"lt2\" tx2=\"dk2\" "
    'accent1="accent1" accent2="accent2" accent3="accent3" accent4="accent4" '
    'accent5="accent5" accent6="accent6" hlink="hlink" folHlink="folHlink"/></p:clrMapOvr>'
    "</p:sldLayout>"
)

_SLIDE_LAYOUT_RELS = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Id="rId1" '
    'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" '
    'Target="../slideMasters/slideMaster1.xml"/>'
    "</Relationships>"
)

_SLIDE_MASTER_XML = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<p:sldMaster xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
    'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">'
    "<p:cSld><p:spTree>"
    "<p:nvGrpSpPr><p:cNvPr id=\"1\" name=\"\"/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>"
    "<p:grpSpPr/>"
    "</p:spTree></p:cSld>"
    "<p:clrMap bg1=\"lt1\" tx1=\"dk1\" bg2=\"lt2\" tx2=\"dk2\" accent1=\"accent1\" "
    'accent2="accent2" accent3="accent3" accent4="accent4" accent5="accent5" '
    'accent6="accent6" hlink="hlink" folHlink="folHlink"/>'
    "<p:sldLayoutIdLst>"
    '<p:sldLayoutId id="2147483649" r:id="rId1" '
    'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"/>'
    "</p:sldLayoutIdLst>"
    "</p:sldMaster>"
)

_SLIDE_MASTER_RELS = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Id="rId1" '
    'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" '
    'Target="../slideLayouts/slideLayout1.xml"/>'
    '<Relationship Id="rId2" '
    'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme" '
    'Target="../theme/theme1.xml"/>'
    "</Relationships>"
)


def _text_box(
    shape_id: int, x: int, y: int, cx: int, cy: int, paragraphs: list[str], *, bold: bool = False
) -> str:
    size = "2800" if bold else "1600"
    runs = "".join(
        f'<a:p><a:r><a:rPr lang="en-US" sz="{size}" b="{"1" if bold else "0"}"/>'
        f"<a:t>{escape(text)}</a:t></a:r></a:p>"
        for text in paragraphs
    )
    return (
        f'<p:sp><p:nvSpPr><p:cNvPr id="{shape_id}" name="TextBox {shape_id}"/>'
        "<p:cNvSpPr txBox=\"1\"/><p:nvPr/></p:nvSpPr>"
        "<p:spPr>"
        f'<a:xfrm><a:off x="{x}" y="{y}"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>'
        '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom>'
        "</p:spPr>"
        f"<p:txBody><a:bodyPr wrap=\"square\"/><a:lstStyle/>{runs}</p:txBody>"
        "</p:sp>"
    )


def _slide_xml(title: str, bullets: list[str]) -> str:
    shapes = [_text_box(2, 457200, 274638, 8229600, 800100, [title], bold=True)]
    if bullets:
        shapes.append(_text_box(3, 457200, 1200150, 8229600, 5200650, bullets))
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
        'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">'
        "<p:cSld><p:spTree>"
        "<p:nvGrpSpPr><p:cNvPr id=\"1\" name=\"\"/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>"
        "<p:grpSpPr/>"
        + "".join(shapes)
        + "</p:spTree></p:cSld>"
        "</p:sld>"
    )


_SLIDE_RELS = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Id="rId1" '
    'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" '
    'Target="../slideLayouts/slideLayout1.xml"/>'
    "</Relationships>"
)


def _chunk(items: list[str], size: int) -> list[list[str]]:
    return [items[i : i + size] for i in range(0, len(items), size)] or [[]]


def _build_slides(report: InstitutionalResearchReport) -> list[tuple[str, list[str]]]:
    """Return ``(title, bullets)`` per slide — title slide first."""
    slides: list[tuple[str, list[str]]] = [
        (
            "DSP Institutional Research Report",
            [
                f"Ticker: {report.metadata.ticker or UNAVAILABLE_MESSAGE}",
                f"Report ID: {report.metadata.report_id}",
                f"Research Mode: {report.metadata.research_mode}",
                f"Generated At: {report.metadata.generated_at}",
            ],
        )
    ]

    rows = flatten_report(report)
    by_section: dict[str, list[str]] = {}
    for row in rows:
        prefix = f"{row.section}/{row.rs_id}" if row.rs_id else row.section
        text = f"{row.field}: {row.value}" if row.field != "(section)" else row.value
        by_section.setdefault(prefix, []).append(text)

    seen_sections: set[str] = set()
    for name in REPORT_SECTION_ORDER:
        if name == "metadata":
            continue
        for key in sorted(by_section.keys()):
            if key != name and not key.startswith(f"{name}/"):
                continue
            if key in seen_sections:
                continue
            seen_sections.add(key)
            for chunk in _chunk(by_section[key], _MAX_BULLETS_PER_SLIDE):
                slides.append((key, chunk))
    return slides


def export_pptx_bytes(report: InstitutionalResearchReport) -> bytes:
    """Build a minimal, valid .pptx of the Institutional Report.

    Title slide + one slide per report section (chunked when long) —
    values preserved as-is, no research reformatting.
    """
    slides = _build_slides(report)

    slide_overrides = "".join(
        f'<Override PartName="/ppt/slides/slide{i}.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>'
        for i in range(1, len(slides) + 1)
    )
    content_types = _CONTENT_TYPES_TEMPLATE.format(slide_overrides=slide_overrides)

    # rId1 is reserved for the slide master (see presentation_rels_entries below),
    # so slide relationship ids start at rId2.
    sld_id_entries = "".join(
        f'<p:sldId id="{256 + i}" r:id="rId{i + 2}"/>' for i in range(len(slides))
    )
    presentation_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<p:presentation xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
        'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">'
        '<p:sldMasterIdLst><p:sldMasterId id="2147483648" r:id="rId1"/></p:sldMasterIdLst>'
        f"<p:sldIdLst>{sld_id_entries}</p:sldIdLst>"
        '<p:sldSz cx="9144000" cy="6858000"/>'
        '<p:notesSz cx="6858000" cy="9144000"/>'
        "</p:presentation>"
    )

    presentation_rels_entries = [
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" '
        'Target="slideMasters/slideMaster1.xml"/>'
    ]
    for i in range(1, len(slides) + 1):
        presentation_rels_entries.append(
            f'<Relationship Id="rId{i + 1}" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" '
            f'Target="slides/slide{i}.xml"/>'
        )
    presentation_rels_entries.append(
        f'<Relationship Id="rId{len(slides) + 2}" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme" '
        'Target="theme/theme1.xml"/>'
    )
    presentation_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        + "".join(presentation_rels_entries)
        + "</Relationships>"
    )

    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types)
        zf.writestr("_rels/.rels", _ROOT_RELS)
        zf.writestr("ppt/presentation.xml", presentation_xml)
        zf.writestr("ppt/_rels/presentation.xml.rels", presentation_rels)
        zf.writestr("ppt/slideMasters/slideMaster1.xml", _SLIDE_MASTER_XML)
        zf.writestr("ppt/slideMasters/_rels/slideMaster1.xml.rels", _SLIDE_MASTER_RELS)
        zf.writestr("ppt/slideLayouts/slideLayout1.xml", _SLIDE_LAYOUT_XML)
        zf.writestr("ppt/slideLayouts/_rels/slideLayout1.xml.rels", _SLIDE_LAYOUT_RELS)
        zf.writestr("ppt/theme/theme1.xml", _THEME_XML)
        for i, (title, bullets) in enumerate(slides, start=1):
            zf.writestr(f"ppt/slides/slide{i}.xml", _slide_xml(title, bullets))
            zf.writestr(f"ppt/slides/_rels/slide{i}.xml.rels", _SLIDE_RELS)
    return buffer.getvalue()
