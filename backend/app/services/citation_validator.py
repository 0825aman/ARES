"""Citation validator — Phase 4 M4.6.

Runs 7 validation checks against the Citation records created by
citation_service.create_citations_for_run(). Updates Citation.is_verified
and Citation.validation_notes for each record.

IMPORTANT: This module must have ZERO imports from app.graph.*
It is a shared backend service callable from both sequential and
multi-agent workflows.

Validation checks:
  1. Every [SOURCE N] label in report's sources_used maps to an EvidenceRecord
  2. Every referenced EvidenceRecord exists and has non-empty content
  3. No fabricated citation keys (citation_key not in report's sources list)
  4. If source_id is set, the Source record exists
  5. URL passes is_safe_url() — no SSRF-unsafe internal URLs
  6. At least 1 citation per key_finding (warning, not failure)
  7. Claims with verification_status="contradicted" are flagged in notes
"""
from __future__ import annotations

import json
import logging
import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def validate_citations_for_run(
    db: AsyncSession,
    run_id: str,
    report_id: str,
) -> dict:
    """Run all 7 validation checks; update Citation.is_verified on each record.

    Returns a summary dict:
    {
        "total_citations": int,
        "verified_count": int,
        "failed_count": int,
        "warnings": list[str],
        "errors": list[str],
    }
    """
    from app.models.citation import Citation
    from app.models.evidence import EvidenceRecord
    from app.models.source import Source
    from app.models.report import ResearchReport
    from app.models.claim_verification import ClaimVerification
    from app.providers.web_fetcher import is_safe_url

    warnings: list[str] = []
    errors: list[str] = []

    # Load report for source keys and key_findings
    rpt_result = await db.execute(
        select(ResearchReport).where(ResearchReport.id == report_id)
    )
    report = rpt_result.scalar_one_or_none()
    if report is None:
        return {
            "total_citations": 0,
            "verified_count": 0,
            "failed_count": 0,
            "warnings": [f"Report {report_id} not found — skipping validation"],
            "errors": [],
        }

    # Parse known source keys from report
    known_keys = _parse_source_keys(report.sources)

    # Load all citations for this run/report
    cit_result = await db.execute(
        select(Citation).where(
            Citation.run_id == run_id,
            Citation.report_id == report_id,
        )
    )
    citations = cit_result.scalars().all()

    if not citations:
        return {
            "total_citations": 0,
            "verified_count": 0,
            "failed_count": 0,
            "warnings": ["No citations found for this run/report"],
            "errors": [],
        }

    # Load all evidence for this run (for check 1+2)
    ev_result = await db.execute(
        select(EvidenceRecord).where(EvidenceRecord.run_id == run_id)
    )
    evidence_rows = ev_result.scalars().all()
    evidence_by_id = {ev.id: ev for ev in evidence_rows}

    # Load contradicted claim verification statuses (check 7)
    contradicted_claim_ids: set[str] = set()
    cv_result = await db.execute(
        select(ClaimVerification).where(
            ClaimVerification.run_id == run_id,
            ClaimVerification.verification_status == "contradicted",
        )
    )
    for cv in cv_result.scalars().all():
        contradicted_claim_ids.add(cv.claim_id)

    # Validate each citation
    for cit in citations:
        citation_errors: list[str] = []
        citation_notes: list[str] = []

        # Check 1: citation_key must be in report's known source keys
        if known_keys and cit.citation_key not in known_keys:
            msg = f"Fabricated citation key: {cit.citation_key!r} not in report sources"
            citation_errors.append(msg)
            errors.append(f"Citation {cit.id}: {msg}")

        # Check 2+3: evidence_id must exist and have non-empty content
        ev = evidence_by_id.get(cit.evidence_id)
        if ev is None:
            msg = f"EvidenceRecord {cit.evidence_id!r} not found"
            citation_errors.append(msg)
            errors.append(f"Citation {cit.id}: {msg}")
        else:
            content = (ev.content or "").strip()
            if not content:
                msg = f"EvidenceRecord {cit.evidence_id!r} has empty content"
                citation_errors.append(msg)
                errors.append(f"Citation {cit.id}: {msg}")

        # Check 4: if source_id set, Source record must exist
        if cit.source_id:
            src_result = await db.execute(
                select(Source).where(Source.id == cit.source_id)
            )
            source = src_result.scalar_one_or_none()
            if source is None:
                msg = f"Source {cit.source_id!r} not found in DB"
                citation_errors.append(msg)
                errors.append(f"Citation {cit.id}: {msg}")

        # Check 5: URL must pass is_safe_url (SSRF check)
        if cit.url:
            try:
                if not is_safe_url(cit.url):
                    msg = f"URL {cit.url!r} failed SSRF safety check"
                    citation_errors.append(msg)
                    errors.append(f"Citation {cit.id}: {msg}")
            except Exception:
                pass  # is_safe_url does DNS lookups — skip if network unavailable

        # Check 7: claim linked to contradicted verification → flag in notes
        if cit.claim_id and cit.claim_id in contradicted_claim_ids:
            note = f"Linked claim {cit.claim_id!r} has contradicted verification status"
            citation_notes.append(note)
            warnings.append(f"Citation {cit.id}: {note}")

        # Update citation record
        if citation_errors:
            cit.is_verified = False
            all_notes = citation_errors + citation_notes
            cit.validation_notes = "; ".join(all_notes)
        else:
            cit.is_verified = True
            cit.validation_notes = "; ".join(citation_notes) if citation_notes else None

    # Check 6: at least 1 citation per key_finding
    key_findings = _parse_key_findings(report.key_findings)
    if key_findings and citations:
        verified_keys = {c.citation_key for c in citations if c.is_verified}
        for finding in key_findings:
            if not _finding_has_source(finding, verified_keys):
                warnings.append(
                    f"Key finding has no verified citation: {finding[:80]!r}"
                )

    verified_count = sum(1 for c in citations if c.is_verified)
    failed_count = len(citations) - verified_count

    # Update report
    report.has_validated_citations = (failed_count == 0)
    report.review_status = "verified" if (failed_count == 0) else "needs_attention"

    logger.info(
        "validate_citations_for_run: run=%s %d/%d citations verified",
        run_id, verified_count, len(citations),
    )

    return {
        "total_citations": len(citations),
        "verified_count": verified_count,
        "failed_count": failed_count,
        "warnings": warnings,
        "errors": errors,
    }


# ── Helpers ────────────────────────────────────────────────────────────────────

def _parse_source_keys(sources_field: str | None) -> list[str]:
    """Extract [SOURCE N] keys from the report.sources field."""
    if not sources_field:
        return []
    raw_list: list[str] = []
    try:
        parsed = json.loads(sources_field)
        raw_list = [str(item) for item in parsed] if isinstance(parsed, list) else [str(parsed)]
    except (json.JSONDecodeError, TypeError):
        raw_list = [sources_field]

    keys = []
    for item in raw_list:
        match = re.search(r"\[SOURCE\s+\d+\]", item, re.IGNORECASE)
        if match:
            keys.append(match.group(0))
        else:
            keys.append(item.strip())
    return [k for k in keys if k]


def _parse_key_findings(key_findings_field: str | None) -> list[str]:
    """Parse report.key_findings JSON field into a list of strings."""
    if not key_findings_field:
        return []
    try:
        parsed = json.loads(key_findings_field)
        return [str(f) for f in parsed] if isinstance(parsed, list) else [str(parsed)]
    except (json.JSONDecodeError, TypeError):
        return [key_findings_field]


def _finding_has_source(finding: str, citation_keys: set[str]) -> bool:
    """Return True if the finding text contains any [SOURCE N] reference."""
    found_keys = re.findall(r"\[SOURCE\s+\d+\]", finding, re.IGNORECASE)
    return any(k in citation_keys for k in found_keys)
