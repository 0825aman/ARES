"""ExportService — Phase 5 M5.6.

Generates downloadable research report files in PDF, DOCX, and Markdown formats.
Manages ExportRecord lifecycle and file storage under EXPORT_DIR.
"""
from __future__ import annotations

import html
import json
import logging
import os
import pathlib
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.export_record import ExportRecord
from app.models.report import ResearchReport
from app.core.metrics import metrics

logger = logging.getLogger(__name__)

VALID_FORMATS = {"pdf", "docx", "markdown"}

MIME_TYPES = {
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "markdown": "text/markdown; charset=utf-8",
}

EXTENSIONS = {
    "pdf": "pdf",
    "docx": "docx",
    "markdown": "md",
}


# ── File path helpers ──────────────────────────────────────────────────────────

def _export_dir(run_id: str) -> pathlib.Path:
    """Return (and create) the per-run export directory."""
    p = pathlib.Path(settings.EXPORT_DIR) / run_id
    p.mkdir(parents=True, exist_ok=True)
    return p


def _export_filename(version_number: int, format: str) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    ext = EXTENSIONS[format]
    return f"v{version_number}_{ts}_report.{ext}"


def _relative_path(run_id: str, filename: str) -> str:
    """Return path relative to EXPORT_DIR."""
    return str(pathlib.Path(run_id) / filename)


# ── Helper functions for citations and hyperlinks ────────────────────────────

def _safe_xml(text: str | None) -> str:
    """Return text with XML-unsafe characters escaped for ReportLab Paragraph."""
    if not text:
        return ""
    return html.escape(str(text), quote=True)


def _safe_url(url: str | None) -> str:
    """Return URL with XML-unsafe characters escaped for href attributes."""
    if not url:
        return ""
    return html.escape(str(url).strip(), quote=True)


def _clean_title(title: str | None, max_len: int = 150) -> str:
    """Clean and truncate raw source titles."""
    if not title:
        return ""
    lines = [line.strip() for line in str(title).splitlines() if line.strip()]
    first_line = lines[0] if lines else str(title).strip()
    if len(first_line) > max_len:
        return first_line[: max_len - 3].rstrip() + "..."
    return first_line


def _parse_sources(sources_raw: Any) -> list:
    """Safely parse sources into a list."""
    if not sources_raw:
        return []
    if isinstance(sources_raw, list):
        return sources_raw
    try:
        data = json.loads(sources_raw)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _build_sources_map(sources_raw: Any, evidence_raw: Any = None) -> dict[int, str]:
    """Build a mapping from source number (int) to URL string."""
    mapping: dict[int, str] = {}

    def process_items(raw_data: Any) -> None:
        items = _parse_sources(raw_data)
        for i, item in enumerate(items, 1):
            if isinstance(item, dict):
                url = item.get("url")
                label = item.get("source_label", "")
                if url and isinstance(url, str) and (url.startswith("http://") or url.startswith("https://")):
                    m = re.search(r"\d+", label)
                    if m:
                        mapping[int(m.group(0))] = url.strip()
                    mapping.setdefault(i, url.strip())
            elif isinstance(item, str) and (item.startswith("http://") or item.startswith("https://")):
                mapping.setdefault(i, item.strip())

    process_items(sources_raw)
    process_items(evidence_raw)
    return mapping


def _format_text_with_citations_pdf(text: str | None, sources_map: dict[int, str]) -> str:
    """Format text for ReportLab Paragraph, escaping XML and linking citations."""
    if not text:
        return ""
    safe_str = _safe_xml(text)

    def sub_src(m: re.Match) -> str:
        num = int(m.group(1))
        url = sources_map.get(num)
        if url:
            safe_u = _safe_url(url)
            return f'<a href="{safe_u}"><font color="#1d4ed8"><u>SOURCE {num}</u></font></a>'
        return m.group(0)

    return re.sub(r"\bSOURCE\s+(\d+)\b", sub_src, safe_str)


def _format_text_with_citations_md(text: str | None, sources_map: dict[int, str]) -> str:
    """Format Markdown text, linking citations."""
    if not text:
        return ""

    def sub_md(m: re.Match) -> str:
        num = int(m.group(1))
        url = sources_map.get(num)
        if url:
            return f"[SOURCE {num}]({url})"
        return m.group(0)

    return re.sub(r"\bSOURCE\s+(\d+)\b", sub_md, str(text))


def _add_docx_hyperlink(
    paragraph: Any,
    url: str,
    text: str,
    color: str = "1D4ED8",
    underline: bool = True,
    font_size_pt: float | None = None,
) -> Any:
    """Add a clickable hyperlink to a python-docx paragraph using standard Word XML."""
    import docx.opc.constants
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn

    part = paragraph.part
    r_id = part.relate_to(
        url,
        docx.opc.constants.RELATIONSHIP_TYPE.HYPERLINK,
        is_external=True,
    )

    hyperlink = OxmlElement("w:hyperlink")
    hyperlink.set(qn("r:id"), r_id)

    new_run = OxmlElement("w:r")
    rPr = OxmlElement("w:rPr")

    if color:
        c = OxmlElement("w:color")
        c.set(qn("w:val"), color)
        rPr.append(c)

    if font_size_pt:
        sz = OxmlElement("w:sz")
        sz.set(qn("w:val"), str(int(font_size_pt * 2)))
        rPr.append(sz)

    if underline:
        u = OxmlElement("w:u")
        u.set(qn("w:val"), "single")
        rPr.append(u)

    new_run.append(rPr)
    text_elem = OxmlElement("w:t")
    text_elem.text = text
    new_run.append(text_elem)
    hyperlink.append(new_run)
    paragraph._p.append(hyperlink)
    return hyperlink


def _add_paragraph_with_citations_docx(
    doc: Any,
    text: str | None,
    sources_map: dict[int, str],
    style: str | None = None,
) -> Any:
    """Add paragraph to docx document, converting citations into clickable hyperlinks."""
    p = doc.add_paragraph(style=style)
    if not text:
        return p
    parts = re.split(r"(\bSOURCE\s+\d+\b)", str(text))
    for part in parts:
        m = re.match(r"\bSOURCE\s+(\d+)\b", part)
        if m:
            num = int(m.group(1))
            if num in sources_map:
                _add_docx_hyperlink(p, sources_map[num], part, color="1D4ED8", underline=True)
                continue
        p.add_run(part)
    return p


# ── PDF generation ─────────────────────────────────────────────────────────────

_UNICODE_FONT_NAME: str | None = None


def _get_unicode_font_name() -> str:
    """Register and cache a TrueType font capable of rendering international Unicode
    (including Hindi/Devanagari, Cyrillic, Greek, Arabic, and extended Latin).
    Falls back gracefully to Helvetica if no TrueType font is found.
    """
    global _UNICODE_FONT_NAME
    if _UNICODE_FONT_NAME:
        return _UNICODE_FONT_NAME

    try:
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont

        base_dir = pathlib.Path(__file__).parent.parent
        candidates = [
            # 1. Bundled universal FreeSerif (covers 8,000+ glyphs including Devanagari/Hindi)
            base_dir / "assets" / "fonts" / "FreeSerif.ttf",
            # 2. Linux system fonts (Debian/Ubuntu/Render)
            pathlib.Path("/usr/share/fonts/truetype/freefont/FreeSerif.ttf"),
            pathlib.Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
            pathlib.Path("/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf"),
            # 3. Windows system fonts (local fallback)
            pathlib.Path("C:/Windows/Fonts/Nirmala.ttf"),
            pathlib.Path("C:/Windows/Fonts/mangal.ttf"),
            pathlib.Path("C:/Windows/Fonts/arial.ttf"),
        ]

        for p in candidates:
            if p.is_file():
                font_path_str = str(p.resolve())
                font_name = "ARES_Unicode_Font"
                try:
                    pdfmetrics.registerFont(TTFont(font_name, font_path_str))
                    # Register family so inline <b>, <i> tags in Paragraphs don't switch to non-Unicode Helvetica
                    pdfmetrics.registerFontFamily(
                        font_name,
                        normal=font_name,
                        bold=font_name,
                        italic=font_name,
                        boldItalic=font_name,
                    )
                    _UNICODE_FONT_NAME = font_name
                    logger.info("export_service: registered Unicode PDF font from %s", font_path_str)
                    return font_name
                except Exception as reg_exc:
                    logger.warning("export_service: failed to register font %s: %s", font_path_str, reg_exc)

    except Exception as exc:
        logger.warning("export_service: error during Unicode font setup: %s", exc)

    _UNICODE_FONT_NAME = "Helvetica"
    return "Helvetica"


def _generate_pdf(report: ResearchReport, file_path: str) -> None:
    """Generate a PDF report using reportlab with multi-lingual Unicode font support."""
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.lib.enums import TA_LEFT

    doc = SimpleDocTemplate(
        file_path,
        pagesize=A4,
        rightMargin=2.5 * cm,
        leftMargin=2.5 * cm,
        topMargin=2.5 * cm,
        bottomMargin=2.5 * cm,
    )

    font_name = _get_unicode_font_name()
    styles = getSampleStyleSheet()

    h1 = ParagraphStyle(
        "CustomH1",
        parent=styles["Heading1"],
        fontName=font_name,
        fontSize=18,
        leading=24,
        spaceAfter=12,
    )
    h2 = ParagraphStyle(
        "CustomH2",
        parent=styles["Heading2"],
        fontName=font_name,
        fontSize=13,
        leading=18,
        spaceBefore=16,
        spaceAfter=6,
    )
    body = ParagraphStyle(
        "CustomBody",
        parent=styles["Normal"],
        fontName=font_name,
        fontSize=10,
        leading=15,
        spaceAfter=8,
        alignment=TA_LEFT,
    )
    source_style = ParagraphStyle(
        "CustomSource",
        parent=styles["Normal"],
        fontName=font_name,
        fontSize=9,
        leading=13.5,
        spaceAfter=6,
        alignment=TA_LEFT,
    )
    footer_style = ParagraphStyle(
        "Footer",
        parent=styles["Normal"],
        fontName=font_name,
        fontSize=8.5,
        leading=12,
        textColor=styles["Normal"].textColor,
    )

    sources_map = _build_sources_map(report.sources, getattr(report, "evidence_used", None))
    story = []

    title = report.research_question[:120]
    story.append(Paragraph(_safe_xml(title), h1))

    conf = getattr(report, "confidence_score", None)
    if conf is not None:
        story.append(Paragraph(f"<i>Confidence Score: {conf:.0%}</i>", body))

    version_number = getattr(report, "version_number", 1)

    # Executive Summary
    story.append(Paragraph("Executive Summary", h2))
    story.append(Paragraph(_format_text_with_citations_pdf(report.executive_summary, sources_map), body))

    # Key Findings
    story.append(Paragraph("Key Findings", h2))
    try:
        findings = json.loads(report.key_findings)
        if isinstance(findings, list):
            for item in findings:
                formatted_item = _format_text_with_citations_pdf(str(item), sources_map)
                story.append(Paragraph(f"• {formatted_item}", body))
        else:
            story.append(Paragraph(_format_text_with_citations_pdf(str(findings), sources_map), body))
    except (json.JSONDecodeError, TypeError):
        story.append(Paragraph(_format_text_with_citations_pdf(report.key_findings, sources_map), body))

    # Observations
    if report.observations:
        story.append(Paragraph("Observations", h2))
        story.append(Paragraph(_format_text_with_citations_pdf(report.observations, sources_map), body))

    # Contradictions
    if report.contradictions:
        story.append(Paragraph("Contradictions", h2))
        story.append(Paragraph(_format_text_with_citations_pdf(report.contradictions, sources_map), body))

    # Limitations
    story.append(Paragraph("Limitations", h2))
    story.append(Paragraph(_format_text_with_citations_pdf(report.limitations, sources_map), body))

    # Sources & References
    story.append(Paragraph("Sources &amp; References", h2))
    try:
        sources = _parse_sources(report.sources)
        if sources:
            for i, s in enumerate(sources, 1):
                if isinstance(s, dict):
                    label = s.get("source_label") or f"[SOURCE {i}]"
                    url = s.get("url")
                    title = _clean_title(s.get("title") or url or "Link")
                    safe_label = _safe_xml(label)
                    safe_title = _safe_xml(title)
                    if url:
                        safe_u = _safe_url(url)
                        markup = (
                            f"<b>{safe_label}</b> "
                            f'<a href="{safe_u}"><font color="#1d4ed8"><u>{safe_title}</u></font></a>'
                            f'<br/>&nbsp;&nbsp;&nbsp;&nbsp;<font color="#64748b" size="8"><a href="{safe_u}"><font color="#64748b">{safe_u}</font></a></font>'
                        )
                    else:
                        filename = s.get("filename")
                        if filename:
                            page_info = []
                            if s.get("page_number") is not None:
                                page_info.append(f"page {s['page_number']}")
                            if s.get("chunk_index") is not None and s.get("page_number") is None:
                                page_info.append(f"section {s['chunk_index'] + 1}")
                            page_str = f" ({', '.join(page_info)})" if page_info else ""
                            markup = f"<b>{safe_label}</b> Document: <i>{_safe_xml(filename)}</i>{page_str}"
                        else:
                            markup = f"<b>{safe_label}</b> {safe_title}"
                else:
                    s_str = str(s).strip()
                    if s_str.startswith("http://") or s_str.startswith("https://"):
                        safe_u = _safe_url(s_str)
                        markup = f'<b>[SOURCE {i}]</b> <a href="{safe_u}"><font color="#1d4ed8"><u>{safe_u}</u></font></a>'
                    else:
                        markup = f"<b>[SOURCE {i}]</b> {_safe_xml(s_str)}"
                story.append(Paragraph(markup, source_style))
        else:
            story.append(Paragraph(_safe_xml(str(report.sources or "")), body))
    except Exception:
        story.append(Paragraph(_safe_xml(str(report.sources or "")), body))

    story.append(Spacer(1, 24))
    story.append(Paragraph(
        f"<i>Generated by ARES (Autonomous Research & Evidence System) · Run ID: {report.run_id} · Version {version_number}</i>",
        footer_style,
    ))

    doc.build(story)


# ── DOCX generation ───────────────────────────────────────────────────────────

def _generate_docx(report: ResearchReport, file_path: str) -> None:
    """Generate a DOCX report using python-docx."""
    from docx import Document

    doc = Document()

    title = report.research_question[:120]
    doc.add_heading(title, level=0)

    conf = getattr(report, "confidence_score", None)
    version_number = getattr(report, "version_number", 1)
    if conf is not None:
        doc.add_paragraph(f"Confidence Score: {conf:.0%}")

    sources_map = _build_sources_map(report.sources, getattr(report, "evidence_used", None))

    # Executive Summary
    doc.add_heading("Executive Summary", level=1)
    _add_paragraph_with_citations_docx(doc, report.executive_summary, sources_map)

    # Key Findings
    doc.add_heading("Key Findings", level=1)
    try:
        findings = json.loads(report.key_findings)
        if isinstance(findings, list):
            for item in findings:
                _add_paragraph_with_citations_docx(doc, str(item), sources_map, style="List Bullet")
        else:
            _add_paragraph_with_citations_docx(doc, str(findings), sources_map)
    except (json.JSONDecodeError, TypeError):
        _add_paragraph_with_citations_docx(doc, report.key_findings, sources_map)

    # Observations
    if report.observations:
        doc.add_heading("Observations", level=1)
        _add_paragraph_with_citations_docx(doc, report.observations, sources_map)

    # Contradictions
    if report.contradictions:
        doc.add_heading("Contradictions", level=1)
        _add_paragraph_with_citations_docx(doc, report.contradictions, sources_map)

    # Limitations
    doc.add_heading("Limitations", level=1)
    _add_paragraph_with_citations_docx(doc, report.limitations, sources_map)

    # Sources & References
    doc.add_heading("Sources & References", level=1)
    try:
        sources = _parse_sources(report.sources)
        if sources:
            for i, s in enumerate(sources, 1):
                p = doc.add_paragraph(style="List Bullet")
                if isinstance(s, dict):
                    label = s.get("source_label") or f"[SOURCE {i}]"
                    url = s.get("url")
                    title = _clean_title(s.get("title") or url or "Link")
                    lbl_run = p.add_run(f"{label} ")
                    lbl_run.bold = True
                    if url:
                        _add_docx_hyperlink(p, url, title, color="1D4ED8", underline=True)
                        p.add_run("\n    ")
                        _add_docx_hyperlink(p, url, url, color="64748B", underline=False, font_size_pt=8.5)
                    else:
                        filename = s.get("filename")
                        if filename:
                            p.add_run(f"Document: {filename}")
                            if s.get("page_number") is not None:
                                p.add_run(f" (page {s['page_number']})")
                        else:
                            p.add_run(title)
                else:
                    s_str = str(s).strip()
                    lbl_run = p.add_run(f"[SOURCE {i}] ")
                    lbl_run.bold = True
                    if s_str.startswith("http://") or s_str.startswith("https://"):
                        _add_docx_hyperlink(p, s_str, s_str, color="1D4ED8", underline=True)
                    else:
                        p.add_run(s_str)
        else:
            doc.add_paragraph(str(report.sources or ""))
    except Exception:
        doc.add_paragraph(str(report.sources or ""))

    # Footer paragraph
    doc.add_paragraph()
    doc.add_paragraph(
        f"Generated by ARES (Autonomous Research & Evidence System) — Run ID: {report.run_id} — Version {version_number}"
    )

    doc.save(file_path)


# ── Markdown generation ───────────────────────────────────────────────────────

def _generate_markdown(report: ResearchReport, file_path: str) -> None:
    """Generate a Markdown report as a plain text file."""
    conf = getattr(report, "confidence_score", None)
    version_number = getattr(report, "version_number", 1)
    generated_at = getattr(report, "generated_at", datetime.now(timezone.utc))
    if hasattr(generated_at, "isoformat"):
        generated_at_str = generated_at.isoformat()
    else:
        generated_at_str = str(generated_at)

    sources_map = _build_sources_map(report.sources, getattr(report, "evidence_used", None))

    lines = [
        f"# {report.research_question}",
        "",
    ]

    if conf is not None:
        lines.append(f"**Confidence Score:** {conf:.0%}  ")
    lines += [
        f"**Run ID:** {report.run_id}  ",
        f"**Generated:** {generated_at_str}  ",
        f"**Version:** {version_number}  ",
        "",
        "---",
        "",
        "## Executive Summary",
        "",
        _format_text_with_citations_md(report.executive_summary, sources_map),
        "",
        "## Key Findings",
        "",
    ]

    try:
        findings = json.loads(report.key_findings)
        if isinstance(findings, list):
            for item in findings:
                lines.append(f"- {_format_text_with_citations_md(str(item), sources_map)}")
        else:
            lines.append(_format_text_with_citations_md(str(findings), sources_map))
    except (json.JSONDecodeError, TypeError):
        lines.append(_format_text_with_citations_md(report.key_findings, sources_map))

    lines.append("")

    if report.observations:
        lines += ["## Observations", "", _format_text_with_citations_md(report.observations, sources_map), ""]

    if report.contradictions:
        lines += ["## Contradictions", "", _format_text_with_citations_md(report.contradictions, sources_map), ""]

    lines += [
        "## Limitations",
        "",
        _format_text_with_citations_md(report.limitations, sources_map),
        "",
        "## Sources",
        "",
    ]

    try:
        sources = _parse_sources(report.sources)
        if sources:
            for i, s in enumerate(sources, 1):
                if isinstance(s, dict):
                    label = s.get("source_label") or f"[SOURCE {i}]"
                    url = s.get("url")
                    title = _clean_title(s.get("title") or url or "Link")
                    if url:
                        lines.append(f"{i}. **{label}** [{title}]({url})  \n   <{url}>")
                    else:
                        filename = s.get("filename")
                        if filename:
                            lines.append(f"{i}. **{label}** Document: *{filename}*")
                        else:
                            lines.append(f"{i}. **{label}** {title}")
                else:
                    s_str = str(s).strip()
                    if s_str.startswith("http://") or s_str.startswith("https://"):
                        lines.append(f"{i}. **[SOURCE {i}]** <{s_str}>")
                    else:
                        lines.append(f"{i}. **[SOURCE {i}]** {s_str}")
        else:
            lines.append(str(report.sources or ""))
    except Exception:
        lines.append(str(report.sources or ""))

    lines += [
        "",
        "---",
        "*Generated by ARES (Autonomous Research & Evidence System)*",
    ]

    with open(file_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


# ── Backward compatibility helpers ────────────────────────────────────────────

def _safe_text(text: str | None) -> str:
    """Return text with XML-unsafe characters escaped for ReportLab Paragraph."""
    return _safe_xml(text)


# ── Service functions ──────────────────────────────────────────────────────────

async def trigger_export(
    db: AsyncSession,
    run_id: str,
    report_id: Optional[str],
    format: str,
) -> ExportRecord:
    """Create an ExportRecord and generate the file synchronously.

    Returns the ExportRecord with status='ready' (or 'failed' if generation fails).
    Does NOT commit — caller commits.
    """
    if format not in VALID_FORMATS:
        raise ValueError(f"Invalid format '{format}'. Must be one of: {', '.join(sorted(VALID_FORMATS))}")

    # Find the report
    if report_id:
        result = await db.execute(
            select(ResearchReport).where(ResearchReport.id == report_id)
        )
    else:
        result = await db.execute(
            select(ResearchReport).where(
                ResearchReport.run_id == run_id,
                ResearchReport.is_current.is_(True),
            ).order_by(ResearchReport.version_number.desc()).limit(1)
        )
    report = result.scalar_one_or_none()

    if report is None:
        raise ValueError(f"No report found for run {run_id}")

    now = datetime.now(timezone.utc)
    version_number = getattr(report, "version_number", 1)

    # Create ExportRecord
    export = ExportRecord(
        id=str(uuid.uuid4()),
        run_id=run_id,
        report_id=report.id,
        format=format,
        status="generating",
        created_at=now,
    )
    db.add(export)
    await db.flush()  # get export.id without committing

    # Generate the file
    export_dir = _export_dir(run_id)
    filename = _export_filename(version_number, format)
    abs_path = str(export_dir / filename)

    try:
        if format == "pdf":
            _generate_pdf(report, abs_path)
        elif format == "docx":
            _generate_docx(report, abs_path)
        else:
            _generate_markdown(report, abs_path)

        file_size = os.path.getsize(abs_path)
        export.status = "ready"
        export.file_path = _relative_path(run_id, filename)
        export.file_size_bytes = file_size
        export.completed_at = datetime.now(timezone.utc)
        metrics.increment("exports_total", labels={"format": format})
        logger.info(
            "export_service: generated %s export for run %s (%d bytes)",
            format, run_id, file_size,
        )
    except Exception as exc:
        logger.error("export_service: generation failed for run %s format %s: %s", run_id, format, exc)
        export.status = "failed"
        export.error_message = str(exc)
        export.completed_at = datetime.now(timezone.utc)
        metrics.increment("exports_failed", labels={"format": format})
        # Clean up partial file
        try:
            if os.path.exists(abs_path):
                os.remove(abs_path)
        except OSError:
            pass

    return export


async def get_export_record(
    db: AsyncSession,
    export_id: str,
    run_id: str,
) -> Optional[ExportRecord]:
    """Return an ExportRecord by id, scoped to run_id."""
    result = await db.execute(
        select(ExportRecord).where(
            ExportRecord.id == export_id,
            ExportRecord.run_id == run_id,
        )
    )
    return result.scalar_one_or_none()


async def list_exports(
    db: AsyncSession,
    run_id: str,
) -> list[ExportRecord]:
    """Return all export records for a run, newest first."""
    result = await db.execute(
        select(ExportRecord)
        .where(ExportRecord.run_id == run_id)
        .order_by(ExportRecord.created_at.desc())
    )
    return list(result.scalars().all())


def get_abs_file_path(export: ExportRecord) -> str:
    """Return the absolute filesystem path for an export record."""
    if not export.file_path:
        raise ValueError(f"ExportRecord {export.id} has no file_path")
    return str(pathlib.Path(settings.EXPORT_DIR) / export.file_path)
