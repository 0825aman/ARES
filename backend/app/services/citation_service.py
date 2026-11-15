"""Citation service — Phase 4 M4.6.

Creates Citation records from report source references and formats them
deterministically using structured Source data.

No LLM calls. APA and IEEE formats are computed from fields already present
in the Source or EvidenceRecord — never generated from LLM memory.

This service is workflow-independent: both sequential and multi-agent
workflows call create_citations_for_run().
"""
from __future__ import annotations

import json
import logging
import re
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


# ── APA / IEEE formatting ──────────────────────────────────────────────────────

def _parse_authors(authors_json: str | None) -> list[str]:
    """Parse a JSON-encoded authors list, returning plain strings."""
    if not authors_json:
        return []
    try:
        result = json.loads(authors_json)
        return [str(a) for a in result] if isinstance(result, list) else []
    except (json.JSONDecodeError, TypeError):
        return []


def format_apa(
    title: str | None,
    authors: list[str],
    year: str | None,
    venue: str | None,
    publisher: str | None,
    doi: str | None,
    url: str | None,
) -> str:
    """Format a deterministic APA citation string.

    Degrades gracefully when fields are missing:
    - No authors → "(n.a.)"
    - No year → "(n.d.)"
    - No venue/publisher → omitted
    - DOI takes priority over URL
    """
    # Authors: "Last, F., Last, F., & Last, F."
    if authors:
        if len(authors) == 1:
            author_str = authors[0]
        elif len(authors) == 2:
            author_str = f"{authors[0]} & {authors[1]}"
        else:
            author_str = ", ".join(authors[:-1]) + f", & {authors[-1]}"
    else:
        author_str = "(n.a.)"

    year_str = f"({year})" if year else "(n.d.)"
    title_str = title or "Untitled"

    parts = [f"{author_str} {year_str}. {title_str}."]

    if venue:
        parts.append(f" {venue}.")
    elif publisher:
        parts.append(f" {publisher}.")

    if doi:
        parts.append(f" https://doi.org/{doi}")
    elif url:
        parts.append(f" {url}")

    return "".join(parts)


def format_ieee(
    title: str | None,
    authors: list[str],
    year: str | None,
    venue: str | None,
    publisher: str | None,
    doi: str | None,
    url: str | None,
) -> str:
    """Format a deterministic IEEE citation string.

    IEEE format: [N] Author(s), "Title," Venue/Publisher, Year. doi/url
    Degrades gracefully when fields are missing.
    """
    if authors:
        if len(authors) == 1:
            author_str = authors[0]
        elif len(authors) <= 3:
            author_str = ", ".join(authors)
        else:
            # IEEE allows "et al." for >3 authors
            author_str = f"{authors[0]} et al."
    else:
        author_str = "Unknown Author"

    title_str = f'"{title}"' if title else '"Untitled"'
    year_str = year or "n.d."

    parts = [f"{author_str}, {title_str},"]

    if venue:
        parts.append(f" {venue},")
    elif publisher:
        parts.append(f" {publisher},")

    parts.append(f" {year_str}.")

    if doi:
        parts.append(f" doi:{doi}")
    elif url:
        parts.append(f" [Online]. Available: {url}")

    return "".join(parts)


def format_citations_from_source(source) -> tuple[str, str]:
    """Compute APA and IEEE formatted strings from a Source ORM object.

    Returns (apa_formatted, ieee_formatted).
    """
    authors = _parse_authors(getattr(source, "authors", None))
    title = getattr(source, "title", None)
    year = _extract_year(getattr(source, "publication_date", None))
    venue = getattr(source, "venue", None)
    publisher = getattr(source, "publisher", None)
    doi = getattr(source, "doi", None)
    url = getattr(source, "url", None)

    apa = format_apa(title, authors, year, venue, publisher, doi, url)
    ieee = format_ieee(title, authors, year, venue, publisher, doi, url)
    return apa, ieee


def _extract_year(publication_date: str | None) -> str | None:
    """Extract 4-digit year from a publication_date string like '2024-03-15'."""
    if not publication_date:
        return None
    match = re.search(r"\b(\d{4})\b", publication_date)
    return match.group(1) if match else None


# ── Source key parsing ─────────────────────────────────────────────────────────

def _parse_source_keys_from_report(sources_field: str | None) -> list[str]:
    """Extract [SOURCE N] keys from the report's sources field.

    The sources field can be:
    - A JSON array of strings like ["[SOURCE 1] ...", "[SOURCE 2] ..."]
    - A plain string
    - None

    Returns a list of citation keys like ["[SOURCE 1]", "[SOURCE 2]"].
    """
    if not sources_field:
        return []

    # Try parsing as JSON array
    raw_list: list[str] = []
    try:
        parsed = json.loads(sources_field)
        if isinstance(parsed, list):
            raw_list = [str(item) for item in parsed]
        else:
            raw_list = [str(parsed)]
    except (json.JSONDecodeError, TypeError):
        raw_list = [sources_field]

    # Extract [SOURCE N] patterns
    keys = []
    for item in raw_list:
        match = re.search(r"\[SOURCE\s+\d+\]", item, re.IGNORECASE)
        if match:
            keys.append(match.group(0))
        else:
            # Include the whole item as the key if no pattern found
            # (may be a plain URL or label)
            keys.append(item.strip())

    return [k for k in keys if k]


# ── Main citation creation ─────────────────────────────────────────────────────

async def create_citations_for_run(
    db: AsyncSession,
    run_id: str,
    report_id: str,
) -> list[str]:
    """Create Citation records for all source references in a report.

    Steps:
    1. Load the report and parse its sources field for [SOURCE N] labels
    2. For each source label, find the matching EvidenceRecord by source_label
    3. Optionally look up Source record for APA/IEEE formatting
    4. Create Citation record linking the chain
    5. Return list of Citation IDs created

    Non-fatal: if an individual citation creation fails, it is logged and
    skipped. The list of successfully created IDs is returned regardless.
    """
    from app.models.report import ResearchReport
    from app.models.evidence import EvidenceRecord
    from app.models.citation import Citation
    from app.models.source import Source

    # Load the report
    rpt_result = await db.execute(
        select(ResearchReport).where(ResearchReport.id == report_id)
    )
    report = rpt_result.scalar_one_or_none()
    if report is None:
        logger.warning("create_citations_for_run: report %s not found", report_id)
        return []

    source_keys = _parse_source_keys_from_report(report.sources)
    if not source_keys:
        logger.info(
            "create_citations_for_run: no source keys found in report %s", report_id
        )
        return []

    # Load all evidence records for this run (keyed by source_label)
    ev_result = await db.execute(
        select(EvidenceRecord).where(EvidenceRecord.run_id == run_id)
    )
    evidence_rows = ev_result.scalars().all()
    # Build lookup: source_label → first matching EvidenceRecord
    evidence_by_label: dict[str, EvidenceRecord] = {}
    for ev in evidence_rows:
        label = (ev.source_label or "").strip()
        if label and label not in evidence_by_label:
            evidence_by_label[label] = ev

    created_ids: list[str] = []

    for key in source_keys:
        try:
            # Match citation_key to evidence by source_label
            ev = evidence_by_label.get(key)

            # Also try matching by partial key (e.g. "SOURCE 1" vs "[SOURCE 1]")
            if ev is None:
                stripped_key = re.sub(r"[\[\]]", "", key).strip()
                for label, record in evidence_by_label.items():
                    stripped_label = re.sub(r"[\[\]]", "", label).strip()
                    if stripped_key == stripped_label:
                        ev = record
                        break

            if ev is None:
                logger.info(
                    "create_citations_for_run: no evidence found for key %r in run %s",
                    key, run_id,
                )
                # Still create a citation record with is_verified=False
                cit = Citation(
                    id=str(uuid.uuid4()),
                    run_id=run_id,
                    report_id=report_id,
                    claim_id=None,
                    evidence_id=_find_any_evidence_id(evidence_rows),
                    source_id=None,
                    citation_key=key,
                    url=None,
                    doi=None,
                    apa_formatted=None,
                    ieee_formatted=None,
                    is_verified=False,
                    validation_notes=f"No evidence record found for citation key: {key}",
                    created_at=datetime.now(timezone.utc),
                )
                db.add(cit)
                created_ids.append(cit.id)
                continue

            # Look up Source for APA/IEEE formatting
            source_id = ev.source_id
            source = None
            if source_id:
                src_result = await db.execute(
                    select(Source).where(Source.id == source_id)
                )
                source = src_result.scalar_one_or_none()

            apa, ieee = _format_from_evidence_or_source(ev, source)

            cit = Citation(
                id=str(uuid.uuid4()),
                run_id=run_id,
                report_id=report_id,
                claim_id=None,
                evidence_id=ev.id,
                source_id=source_id,
                citation_key=key,
                url=ev.url or (source.url if source else None),
                doi=source.doi if source else None,
                apa_formatted=apa,
                ieee_formatted=ieee,
                is_verified=False,  # validator sets this to True if all checks pass
                validation_notes=None,
                created_at=datetime.now(timezone.utc),
            )
            db.add(cit)
            created_ids.append(cit.id)

        except Exception as exc:
            logger.warning(
                "create_citations_for_run: failed to create citation for key %r: %s",
                key, exc
            )

    if created_ids:
        await db.flush()  # ensure IDs are available; caller commits
        logger.info(
            "create_citations_for_run: created %d citations for run %s",
            len(created_ids), run_id,
        )

    return created_ids


def _find_any_evidence_id(evidence_rows) -> str:
    """Return the ID of the first evidence record, or a placeholder UUID."""
    if evidence_rows:
        return evidence_rows[0].id
    return str(uuid.uuid4())


def _format_from_evidence_or_source(ev, source) -> tuple[str | None, str | None]:
    """Format APA/IEEE from Source if available, else from EvidenceRecord fields."""
    if source is not None:
        apa, ieee = format_citations_from_source(source)
        return apa, ieee

    # Fallback: use EvidenceRecord fields only
    title = ev.page_title
    url = ev.url
    if title or url:
        apa = format_apa(title, [], None, None, None, None, url)
        ieee = format_ieee(title, [], None, None, None, None, url)
        return apa, ieee

    return None, None
