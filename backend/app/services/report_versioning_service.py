"""ReportVersioningService — Phase 5 M5.6.

Archives the current report and bumps the version when a new report is
generated for the same run (revision loop scenario).

Callers: finalize_report_node in app/graph/nodes.py and report_service.py.
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.report import ResearchReport
from app.models.report_version import ReportVersion

logger = logging.getLogger(__name__)


async def get_current_report(
    db: AsyncSession,
    run_id: str,
) -> Optional[ResearchReport]:
    """Return the current (is_current=True) report for a run, or None."""
    result = await db.execute(
        select(ResearchReport).where(
            ResearchReport.run_id == run_id,
            ResearchReport.is_current.is_(True),
        ).order_by(ResearchReport.version_number.desc()).limit(1)
    )
    return result.scalar_one_or_none()


async def list_report_versions(
    db: AsyncSession,
    run_id: str,
) -> list[ResearchReport]:
    """Return all report records for a run, newest first."""
    result = await db.execute(
        select(ResearchReport)
        .where(ResearchReport.run_id == run_id)
        .order_by(ResearchReport.version_number.desc())
    )
    return list(result.scalars().all())


async def archive_current_and_bump(
    db: AsyncSession,
    run_id: str,
) -> int:
    """Archive the current report and return the next version number.

    If no current report exists, returns 1 (first version).
    Does NOT commit — caller commits.
    """
    current = await get_current_report(db, run_id)
    if current is None:
        return 1

    # Snapshot the current report content
    snapshot = {
        "research_question": current.research_question,
        "executive_summary": current.executive_summary,
        "key_findings": current.key_findings,
        "evidence_used": current.evidence_used,
        "observations": current.observations,
        "contradictions": current.contradictions,
        "limitations": current.limitations,
        "sources": current.sources,
        "has_validated_citations": current.has_validated_citations,
        "review_status": current.review_status,
    }

    version_record = ReportVersion(
        id=str(uuid.uuid4()),
        report_id=current.id,
        run_id=run_id,
        version_number=current.version_number,
        archived_at=datetime.now(timezone.utc),
        content_snapshot=json.dumps(snapshot),
    )
    db.add(version_record)

    # Mark old report as not current
    current.is_current = False

    next_version = current.version_number + 1
    logger.info(
        "versioning: archived v%d of report %s for run %s, next version = %d",
        current.version_number, current.id, run_id, next_version,
    )
    return next_version
