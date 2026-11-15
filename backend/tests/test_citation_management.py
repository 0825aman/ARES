"""Tests for M4.6 — Citation Management and Validation.

Test coverage:
  CM-01: APA format correct for source with all fields present
  CM-02: APA format degrades gracefully for source with missing author/date
  CM-03: IEEE format correct for source with all fields
  CM-04: IEEE format degrades for missing author/date
  CM-05: Citation records created for each source reference in report
  CM-06: Citation with no matching evidence has is_verified=False
  CM-07: Validator marks citation is_verified=True when all checks pass
  CM-08: Validator catches fabricated citation key
  CM-09: Validator catches missing evidence content (empty)
  CM-10: Validator catches missing Source record when source_id is set
  CM-11: Validator warns about key finding with no traceable source
  CM-12: Validator flags contradicted claim in citation notes
  CM-13: GET /projects/{id}/runs/{id}/citations returns 200 with citation list
  CM-14: GET returns empty list (200) when no citations exist
  CM-15: citation_validator.py has zero app.graph.* imports (AST check)
  CM-16: Both APA and IEEE fields populated on Citation record after create_citations_for_run
  CM-17: report.has_validated_citations set to True when all citations verified
  CM-18: report.has_validated_citations set to False when citations fail validation
  CM-19: workflow graph compiles with citation_validation_node in topology
  CM-20: _parse_source_keys_from_report handles JSON array, plain string, None
"""
from __future__ import annotations

import ast
import json
import pathlib
import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio


# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------

def _make_source(run_id: str = "run-001"):
    """Create a dict representing Source fields (not ORM)."""
    return {
        "id": str(uuid.uuid4()),
        "run_id": run_id,
        "title": "Renewable Energy and Carbon Emissions",
        "authors": json.dumps(["Smith, J.", "Doe, A."]),
        "publication_date": "2024-03-15",
        "venue": "Nature Energy",
        "publisher": "Nature Publishing Group",
        "doi": "10.1038/s41560-024-001234",
        "url": "https://www.nature.com/articles/s41560-024-001234",
        "is_peer_reviewed": True,
        "source_type": "academic",
        "retrieval_provider": "semantic_scholar",
    }


def _make_source_minimal():
    """Source with missing authors and publication_date."""
    return {
        "id": str(uuid.uuid4()),
        "run_id": "run-002",
        "title": "Climate Change Overview",
        "authors": None,
        "publication_date": None,
        "venue": None,
        "publisher": "Unknown Publisher",
        "doi": None,
        "url": "https://example.com/climate",
        "is_peer_reviewed": False,
        "source_type": "web",
        "retrieval_provider": "tavily",
    }


# ---------------------------------------------------------------------------
# CM-01: APA format — all fields present
# ---------------------------------------------------------------------------

def test_cm01_apa_all_fields():
    """APA format correct for source with all fields."""
    from app.services.citation_service import format_apa

    result = format_apa(
        title="Renewable Energy and Carbon Emissions",
        authors=["Smith, J.", "Doe, A."],
        year="2024",
        venue="Nature Energy",
        publisher=None,
        doi="10.1038/s41560-024-001234",
        url="https://example.com",
    )

    assert "Smith, J." in result
    assert "Doe, A." in result
    assert "2024" in result
    assert "Renewable Energy" in result
    assert "Nature Energy" in result
    assert "10.1038" in result  # DOI takes priority over URL


# ---------------------------------------------------------------------------
# CM-02: APA format — missing author/date
# ---------------------------------------------------------------------------

def test_cm02_apa_missing_fields():
    """APA format degrades gracefully for missing author/date."""
    from app.services.citation_service import format_apa

    result = format_apa(
        title="Climate Change Overview",
        authors=[],
        year=None,
        venue=None,
        publisher="Unknown",
        doi=None,
        url="https://example.com/climate",
    )

    assert "(n.a.)" in result    # missing authors
    assert "(n.d.)" in result    # missing year
    assert "Climate Change" in result
    assert "https://example.com/climate" in result  # URL fallback


# ---------------------------------------------------------------------------
# CM-03: IEEE format — all fields present
# ---------------------------------------------------------------------------

def test_cm03_ieee_all_fields():
    """IEEE format correct for source with all fields."""
    from app.services.citation_service import format_ieee

    result = format_ieee(
        title="Renewable Energy and Carbon Emissions",
        authors=["Smith, J.", "Doe, A."],
        year="2024",
        venue="Nature Energy",
        publisher=None,
        doi="10.1038/s41560-024-001234",
        url="https://example.com",
    )

    assert "Smith, J." in result
    assert '"Renewable Energy' in result  # IEEE puts title in quotes
    assert "Nature Energy" in result
    assert "2024" in result
    assert "10.1038" in result


# ---------------------------------------------------------------------------
# CM-04: IEEE format — missing author/date
# ---------------------------------------------------------------------------

def test_cm04_ieee_missing_fields():
    """IEEE format degrades gracefully for missing author/date."""
    from app.services.citation_service import format_ieee

    result = format_ieee(
        title="Climate Change",
        authors=[],
        year=None,
        venue=None,
        publisher=None,
        doi=None,
        url="https://example.com",
    )

    assert "Unknown Author" in result
    assert "n.d." in result
    assert "https://example.com" in result


# ---------------------------------------------------------------------------
# CM-05: Citation records created for each source reference
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cm05_citations_created_for_source_references(db_session):
    """create_citations_for_run creates one Citation per [SOURCE N] key."""
    from app.models.project import ResearchProject
    from app.models.run import ResearchRun
    from app.models.report import ResearchReport
    from app.models.evidence import EvidenceRecord
    from app.models.citation import Citation
    from app.services.citation_service import create_citations_for_run
    from sqlalchemy import select

    project_id = str(uuid.uuid4())
    run_id = str(uuid.uuid4())
    report_id = str(uuid.uuid4())
    ev1_id = str(uuid.uuid4())
    ev2_id = str(uuid.uuid4())

    project = ResearchProject(
        id=project_id, title="Test", research_question="Q?", status="in_progress"
    )
    run = ResearchRun(
        id=run_id, project_id=project_id, research_question="Q?",
        verification_depth="basic",
    )
    report = ResearchReport(
        id=report_id,
        run_id=run_id,
        research_question="Q?",
        executive_summary="Summary",
        key_findings=json.dumps(["Finding 1 [SOURCE 1]", "Finding 2 [SOURCE 2]"]),
        evidence_used=json.dumps([]),
        limitations="None",
        sources=json.dumps(["[SOURCE 1] Evidence one", "[SOURCE 2] Evidence two"]),
        generated_at=datetime.now(timezone.utc),
    )
    ev1 = EvidenceRecord(
        id=ev1_id, run_id=run_id, source_type="web",
        source_label="[SOURCE 1]", content="Content one",
        fetch_status="success",
    )
    ev2 = EvidenceRecord(
        id=ev2_id, run_id=run_id, source_type="web",
        source_label="[SOURCE 2]", content="Content two",
        fetch_status="success",
    )
    db_session.add_all([project, run, report, ev1, ev2])
    await db_session.commit()

    citation_ids = await create_citations_for_run(
        db=db_session, run_id=run_id, report_id=report_id
    )
    await db_session.commit()

    assert len(citation_ids) == 2

    cit_result = await db_session.execute(
        select(Citation).where(Citation.run_id == run_id)
    )
    cits = cit_result.scalars().all()
    assert len(cits) == 2
    keys = {c.citation_key for c in cits}
    assert "[SOURCE 1]" in keys
    assert "[SOURCE 2]" in keys


# ---------------------------------------------------------------------------
# CM-06: Citation with no matching evidence has is_verified=False
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cm06_citation_no_evidence_not_verified(db_session):
    """Citation created with is_verified=False when no evidence matches."""
    from app.models.project import ResearchProject
    from app.models.run import ResearchRun
    from app.models.report import ResearchReport
    from app.models.citation import Citation
    from app.services.citation_service import create_citations_for_run
    from sqlalchemy import select

    project_id = str(uuid.uuid4())
    run_id = str(uuid.uuid4())
    report_id = str(uuid.uuid4())
    ev_id = str(uuid.uuid4())

    project = ResearchProject(
        id=project_id, title="Test", research_question="Q?", status="in_progress"
    )
    run = ResearchRun(
        id=run_id, project_id=project_id, research_question="Q?", verification_depth="basic"
    )
    # Report references SOURCE 99 but we only have SOURCE 1 in evidence
    report = ResearchReport(
        id=report_id,
        run_id=run_id,
        research_question="Q?",
        executive_summary="Summary",
        key_findings=json.dumps(["Finding [SOURCE 99]"]),
        evidence_used=json.dumps([]),
        limitations="None",
        sources=json.dumps(["[SOURCE 99] Ghost source"]),
        generated_at=datetime.now(timezone.utc),
    )
    # Only SOURCE 1 exists — SOURCE 99 is "fabricated"
    ev = EvidenceRecord = None
    from app.models.evidence import EvidenceRecord
    ev = EvidenceRecord(
        id=ev_id, run_id=run_id, source_type="web",
        source_label="[SOURCE 1]", content="Some content",
        fetch_status="success",
    )
    db_session.add_all([project, run, report, ev])
    await db_session.commit()

    citation_ids = await create_citations_for_run(
        db=db_session, run_id=run_id, report_id=report_id
    )
    await db_session.commit()

    assert len(citation_ids) == 1  # one citation created even without matching evidence

    cit_result = await db_session.execute(
        select(Citation).where(Citation.run_id == run_id)
    )
    cit = cit_result.scalar_one()
    # Must not be verified since no matching evidence was found
    assert cit.is_verified is False
    assert cit.validation_notes is not None


# ---------------------------------------------------------------------------
# CM-07: Validator marks is_verified=True for clean citation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cm07_validator_verifies_clean_citation(db_session):
    """Validator sets is_verified=True when all checks pass."""
    from app.models.project import ResearchProject
    from app.models.run import ResearchRun
    from app.models.report import ResearchReport
    from app.models.evidence import EvidenceRecord
    from app.models.citation import Citation
    from app.services.citation_service import create_citations_for_run
    from app.services.citation_validator import validate_citations_for_run
    from sqlalchemy import select

    project_id = str(uuid.uuid4())
    run_id = str(uuid.uuid4())
    report_id = str(uuid.uuid4())
    ev_id = str(uuid.uuid4())

    project = ResearchProject(
        id=project_id, title="Test", research_question="Q?", status="in_progress"
    )
    run = ResearchRun(
        id=run_id, project_id=project_id, research_question="Q?", verification_depth="basic"
    )
    report = ResearchReport(
        id=report_id,
        run_id=run_id,
        research_question="Q?",
        executive_summary="Summary",
        key_findings=json.dumps(["Finding 1"]),
        evidence_used=json.dumps([]),
        limitations="None",
        sources=json.dumps(["[SOURCE 1] A real source"]),
        generated_at=datetime.now(timezone.utc),
    )
    ev = EvidenceRecord(
        id=ev_id, run_id=run_id, source_type="web",
        source_label="[SOURCE 1]",
        content="This is substantial content from the source with real data.",
        fetch_status="success",
    )
    db_session.add_all([project, run, report, ev])
    await db_session.commit()

    await create_citations_for_run(db=db_session, run_id=run_id, report_id=report_id)
    await db_session.commit()

    summary = await validate_citations_for_run(
        db=db_session, run_id=run_id, report_id=report_id
    )
    await db_session.commit()

    assert summary["total_citations"] == 1
    assert summary["verified_count"] == 1
    assert summary["failed_count"] == 0

    cit_result = await db_session.execute(
        select(Citation).where(Citation.run_id == run_id)
    )
    cit = cit_result.scalar_one()
    assert cit.is_verified is True


# ---------------------------------------------------------------------------
# CM-08: Validator catches fabricated citation key
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cm08_validator_catches_fabricated_key(db_session):
    """Validator marks citation as unverified when citation_key is not in report sources."""
    from app.models.project import ResearchProject
    from app.models.run import ResearchRun
    from app.models.report import ResearchReport
    from app.models.evidence import EvidenceRecord
    from app.models.citation import Citation
    from app.services.citation_validator import validate_citations_for_run
    from sqlalchemy import select

    project_id = str(uuid.uuid4())
    run_id = str(uuid.uuid4())
    report_id = str(uuid.uuid4())
    ev_id = str(uuid.uuid4())

    project = ResearchProject(
        id=project_id, title="Test", research_question="Q?", status="in_progress"
    )
    run = ResearchRun(
        id=run_id, project_id=project_id, research_question="Q?", verification_depth="basic"
    )
    report = ResearchReport(
        id=report_id,
        run_id=run_id,
        research_question="Q?",
        executive_summary="Summary",
        key_findings=json.dumps(["Finding 1"]),
        evidence_used=json.dumps([]),
        limitations="None",
        sources=json.dumps(["[SOURCE 1] Real source"]),  # only SOURCE 1
        generated_at=datetime.now(timezone.utc),
    )
    ev = EvidenceRecord(
        id=ev_id, run_id=run_id, source_type="web",
        source_label="[SOURCE 1]", content="Real content",
        fetch_status="success",
    )
    # Manually create a fabricated citation with a key not in report
    fabricated_cit = Citation(
        id=str(uuid.uuid4()),
        run_id=run_id,
        report_id=report_id,
        evidence_id=ev_id,
        citation_key="[SOURCE 99]",  # FABRICATED — not in report.sources
        is_verified=False,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add_all([project, run, report, ev, fabricated_cit])
    await db_session.commit()

    summary = await validate_citations_for_run(
        db=db_session, run_id=run_id, report_id=report_id
    )
    await db_session.commit()

    assert summary["failed_count"] >= 1
    assert any("fabricated" in e.lower() or "SOURCE 99" in e for e in summary["errors"])

    cit_result = await db_session.execute(
        select(Citation).where(Citation.id == fabricated_cit.id)
    )
    cit = cit_result.scalar_one()
    assert cit.is_verified is False


# ---------------------------------------------------------------------------
# CM-09: Validator catches missing evidence content
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cm09_validator_catches_empty_evidence_content(db_session):
    """Validator marks citation unverified when EvidenceRecord has empty content."""
    from app.models.project import ResearchProject
    from app.models.run import ResearchRun
    from app.models.report import ResearchReport
    from app.models.evidence import EvidenceRecord
    from app.models.citation import Citation
    from app.services.citation_validator import validate_citations_for_run
    from sqlalchemy import select

    project_id = str(uuid.uuid4())
    run_id = str(uuid.uuid4())
    report_id = str(uuid.uuid4())
    ev_id = str(uuid.uuid4())

    project = ResearchProject(
        id=project_id, title="Test", research_question="Q?", status="in_progress"
    )
    run = ResearchRun(
        id=run_id, project_id=project_id, research_question="Q?", verification_depth="basic"
    )
    report = ResearchReport(
        id=report_id, run_id=run_id, research_question="Q?",
        executive_summary="Summary",
        key_findings=json.dumps(["Finding 1"]),
        evidence_used=json.dumps([]),
        limitations="None",
        sources=json.dumps(["[SOURCE 1] Empty source"]),
        generated_at=datetime.now(timezone.utc),
    )
    ev = EvidenceRecord(
        id=ev_id, run_id=run_id, source_type="web",
        source_label="[SOURCE 1]",
        content="",  # EMPTY content
        fetch_status="success",
    )
    cit = Citation(
        id=str(uuid.uuid4()),
        run_id=run_id,
        report_id=report_id,
        evidence_id=ev_id,
        citation_key="[SOURCE 1]",
        is_verified=False,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add_all([project, run, report, ev, cit])
    await db_session.commit()

    summary = await validate_citations_for_run(
        db=db_session, run_id=run_id, report_id=report_id
    )
    await db_session.commit()

    assert summary["failed_count"] >= 1
    assert any("empty content" in e.lower() for e in summary["errors"])


# ---------------------------------------------------------------------------
# CM-10: Validator catches missing Source record when source_id set
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cm10_validator_catches_missing_source(db_session):
    """Validator marks citation unverified when source_id references nonexistent Source."""
    from app.models.project import ResearchProject
    from app.models.run import ResearchRun
    from app.models.report import ResearchReport
    from app.models.evidence import EvidenceRecord
    from app.models.citation import Citation
    from app.services.citation_validator import validate_citations_for_run
    from sqlalchemy import select

    project_id = str(uuid.uuid4())
    run_id = str(uuid.uuid4())
    report_id = str(uuid.uuid4())
    ev_id = str(uuid.uuid4())
    ghost_source_id = str(uuid.uuid4())  # does NOT exist in sources table

    project = ResearchProject(
        id=project_id, title="Test", research_question="Q?", status="in_progress"
    )
    run = ResearchRun(
        id=run_id, project_id=project_id, research_question="Q?", verification_depth="basic"
    )
    report = ResearchReport(
        id=report_id, run_id=run_id, research_question="Q?",
        executive_summary="Summary",
        key_findings=json.dumps(["Finding 1"]),
        evidence_used=json.dumps([]),
        limitations="None",
        sources=json.dumps(["[SOURCE 1] A source"]),
        generated_at=datetime.now(timezone.utc),
    )
    ev = EvidenceRecord(
        id=ev_id, run_id=run_id, source_type="academic",
        source_label="[SOURCE 1]", content="Real content here.",
        fetch_status="success",
    )
    cit = Citation(
        id=str(uuid.uuid4()),
        run_id=run_id,
        report_id=report_id,
        evidence_id=ev_id,
        source_id=ghost_source_id,  # points to nonexistent Source
        citation_key="[SOURCE 1]",
        is_verified=False,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add_all([project, run, report, ev, cit])
    await db_session.commit()

    summary = await validate_citations_for_run(
        db=db_session, run_id=run_id, report_id=report_id
    )
    await db_session.commit()

    assert summary["failed_count"] >= 1
    assert any("not found" in e.lower() for e in summary["errors"])


# ---------------------------------------------------------------------------
# CM-11: Validator warns about key finding with no traceable source
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cm11_validator_warns_finding_without_source(db_session):
    """Validator produces a warning for key_finding with no [SOURCE N] reference."""
    from app.models.project import ResearchProject
    from app.models.run import ResearchRun
    from app.models.report import ResearchReport
    from app.models.evidence import EvidenceRecord
    from app.models.citation import Citation
    from app.services.citation_validator import validate_citations_for_run

    project_id = str(uuid.uuid4())
    run_id = str(uuid.uuid4())
    report_id = str(uuid.uuid4())
    ev_id = str(uuid.uuid4())

    project = ResearchProject(
        id=project_id, title="Test", research_question="Q?", status="in_progress"
    )
    run = ResearchRun(
        id=run_id, project_id=project_id, research_question="Q?", verification_depth="basic"
    )
    report = ResearchReport(
        id=report_id, run_id=run_id, research_question="Q?",
        executive_summary="Summary",
        # key_finding has NO [SOURCE N] reference
        key_findings=json.dumps(["This is an unsourced finding."]),
        evidence_used=json.dumps([]),
        limitations="None",
        sources=json.dumps(["[SOURCE 1] Real source"]),
        generated_at=datetime.now(timezone.utc),
    )
    ev = EvidenceRecord(
        id=ev_id, run_id=run_id, source_type="web",
        source_label="[SOURCE 1]", content="Content.",
        fetch_status="success",
    )
    cit = Citation(
        id=str(uuid.uuid4()),
        run_id=run_id,
        report_id=report_id,
        evidence_id=ev_id,
        citation_key="[SOURCE 1]",
        is_verified=True,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add_all([project, run, report, ev, cit])
    await db_session.commit()

    summary = await validate_citations_for_run(
        db=db_session, run_id=run_id, report_id=report_id
    )

    # Should produce a warning (not a hard error) about unsourced finding
    assert any("no verified citation" in w.lower() or "unsourced" in w.lower()
               for w in summary["warnings"])


# ---------------------------------------------------------------------------
# CM-12: Validator flags contradicted claim
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cm12_validator_flags_contradicted_claim(db_session):
    """Validator adds note to citation when linked claim has contradicted verification."""
    from app.models.project import ResearchProject
    from app.models.run import ResearchRun
    from app.models.report import ResearchReport
    from app.models.evidence import EvidenceRecord
    from app.models.claim import Claim
    from app.models.claim_verification import ClaimVerification
    from app.models.citation import Citation
    from app.services.citation_validator import validate_citations_for_run

    project_id = str(uuid.uuid4())
    run_id = str(uuid.uuid4())
    report_id = str(uuid.uuid4())
    ev_id = str(uuid.uuid4())
    claim_id = str(uuid.uuid4())

    project = ResearchProject(
        id=project_id, title="Test", research_question="Q?", status="in_progress"
    )
    run = ResearchRun(
        id=run_id, project_id=project_id, research_question="Q?", verification_depth="basic"
    )
    report = ResearchReport(
        id=report_id, run_id=run_id, research_question="Q?",
        executive_summary="Summary",
        key_findings=json.dumps(["Finding 1"]),
        evidence_used=json.dumps([]),
        limitations="None",
        sources=json.dumps(["[SOURCE 1] Source"]),
        generated_at=datetime.now(timezone.utc),
    )
    ev = EvidenceRecord(
        id=ev_id, run_id=run_id, source_type="web",
        source_label="[SOURCE 1]", content="Content.",
        fetch_status="success",
    )
    claim = Claim(
        id=claim_id, run_id=run_id, report_id=report_id,
        claim_text="A disputed claim.", claim_type="factual",
        created_at=datetime.now(timezone.utc),
    )
    cv = ClaimVerification(
        id=str(uuid.uuid4()),
        claim_id=claim_id,
        run_id=run_id,
        verification_status="contradicted",
        confidence=0.9,
        verified_at=datetime.now(timezone.utc),
    )
    cit = Citation(
        id=str(uuid.uuid4()),
        run_id=run_id,
        report_id=report_id,
        evidence_id=ev_id,
        claim_id=claim_id,  # linked to contradicted claim
        citation_key="[SOURCE 1]",
        is_verified=False,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add_all([project, run, report, ev, claim, cv, cit])
    await db_session.commit()

    summary = await validate_citations_for_run(
        db=db_session, run_id=run_id, report_id=report_id
    )
    await db_session.commit()

    assert any("contradicted" in w.lower() for w in summary["warnings"])


# ---------------------------------------------------------------------------
# CM-13: GET /projects/{id}/runs/{id}/citations returns 200
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cm13_get_citations_returns_200(async_client, db_session):
    """GET /projects/{id}/runs/{id}/citations returns 200 with citation data."""
    from app.models.project import ResearchProject
    from app.models.run import ResearchRun
    from app.models.report import ResearchReport
    from app.models.evidence import EvidenceRecord
    from app.models.citation import Citation

    project_id = str(uuid.uuid4())
    run_id = str(uuid.uuid4())
    report_id = str(uuid.uuid4())
    ev_id = str(uuid.uuid4())

    project = ResearchProject(
        id=project_id, title="Test", research_question="Q?", status="in_progress"
    )
    run = ResearchRun(
        id=run_id, project_id=project_id, research_question="Q?",
        status="completed", verification_depth="basic",
    )
    report = ResearchReport(
        id=report_id, run_id=run_id, research_question="Q?",
        executive_summary="Summary", key_findings=json.dumps(["F1"]),
        evidence_used=json.dumps([]), limitations="None",
        sources=json.dumps(["[SOURCE 1] Test"]),
        generated_at=datetime.now(timezone.utc),
    )
    ev = EvidenceRecord(
        id=ev_id, run_id=run_id, source_type="web",
        source_label="[SOURCE 1]", content="Real content.",
        fetch_status="success",
    )
    cit = Citation(
        id=str(uuid.uuid4()),
        run_id=run_id,
        report_id=report_id,
        evidence_id=ev_id,
        citation_key="[SOURCE 1]",
        apa_formatted="Smith, J. (2024). Title. Journal.",
        ieee_formatted='Smith, "Title," Journal, 2024.',
        is_verified=True,
        created_at=datetime.now(timezone.utc),
    )

    db_session.add_all([project, run, report, ev, cit])
    await db_session.commit()

    response = await async_client.get(
        f"/api/v1/projects/{project_id}/runs/{run_id}/citations"
    )

    assert response.status_code == 200
    data = response.json()
    assert data["run_id"] == run_id
    assert data["total"] == 1
    assert data["verified_count"] == 1
    assert len(data["citations"]) == 1
    assert data["citations"][0]["citation_key"] == "[SOURCE 1]"
    assert data["citations"][0]["is_verified"] is True


# ---------------------------------------------------------------------------
# CM-14: GET returns empty BibliographyResponse when no citations
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cm14_get_citations_empty(async_client, db_session):
    """GET /projects/{id}/runs/{id}/citations returns 200 with empty list."""
    from app.models.project import ResearchProject
    from app.models.run import ResearchRun

    project_id = str(uuid.uuid4())
    run_id = str(uuid.uuid4())

    project = ResearchProject(
        id=project_id, title="Test", research_question="Q?", status="in_progress"
    )
    run = ResearchRun(
        id=run_id, project_id=project_id, research_question="Q?",
        status="completed", verification_depth="basic",
    )
    db_session.add_all([project, run])
    await db_session.commit()

    response = await async_client.get(
        f"/api/v1/projects/{project_id}/runs/{run_id}/citations"
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["verified_count"] == 0
    assert data["citations"] == []


# ---------------------------------------------------------------------------
# CM-15: citation_validator.py has zero app.graph.* imports (AST check)
# ---------------------------------------------------------------------------

def test_cm15_citation_validator_no_graph_imports():
    """citation_validator.py must not import from app.graph.* at any level."""
    validator_path = (
        pathlib.Path(__file__).parent.parent
        / "app" / "services" / "citation_validator.py"
    )
    assert validator_path.exists(), "app/services/citation_validator.py not found"

    source = validator_path.read_text(encoding="utf-8")
    tree = ast.parse(source)

    graph_imports = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            if isinstance(node, ast.ImportFrom) and node.module:
                if node.module.startswith("app.graph"):
                    graph_imports.append(node.module)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith("app.graph"):
                        graph_imports.append(alias.name)

    assert graph_imports == [], (
        f"citation_validator.py must not import from app.graph.*. Found: {graph_imports}"
    )


# ---------------------------------------------------------------------------
# CM-16: Both APA and IEEE fields populated on Citation after create_citations_for_run
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cm16_apa_ieee_populated_with_source(db_session):
    """APA and IEEE fields are populated when a Source record exists."""
    from app.models.project import ResearchProject
    from app.models.run import ResearchRun
    from app.models.report import ResearchReport
    from app.models.evidence import EvidenceRecord
    from app.models.source import Source
    from app.models.citation import Citation
    from app.services.citation_service import create_citations_for_run
    from sqlalchemy import select

    project_id = str(uuid.uuid4())
    run_id = str(uuid.uuid4())
    report_id = str(uuid.uuid4())
    ev_id = str(uuid.uuid4())
    source_id = str(uuid.uuid4())

    project = ResearchProject(
        id=project_id, title="Test", research_question="Q?", status="in_progress"
    )
    run = ResearchRun(
        id=run_id, project_id=project_id, research_question="Q?", verification_depth="basic"
    )
    report = ResearchReport(
        id=report_id, run_id=run_id, research_question="Q?",
        executive_summary="Summary",
        key_findings=json.dumps(["Finding 1"]),
        evidence_used=json.dumps([]),
        limitations="None",
        sources=json.dumps(["[SOURCE 1] Nature Energy article"]),
        generated_at=datetime.now(timezone.utc),
    )
    source = Source(
        id=source_id,
        run_id=run_id,
        source_type="academic",
        title="Renewable Energy Review",
        authors=json.dumps(["Green, A.", "Brown, B."]),
        publication_date="2023-06-01",
        venue="Nature Energy",
        doi="10.1038/nature12345",
        url="https://nature.com/articles/12345",
        is_peer_reviewed=True,
        retrieval_provider="semantic_scholar",
    )
    ev = EvidenceRecord(
        id=ev_id, run_id=run_id, source_type="academic",
        source_label="[SOURCE 1]",
        source_id=source_id,  # linked to Source
        content="Content about renewable energy.",
        fetch_status="success",
    )
    db_session.add_all([project, run, report, source, ev])
    await db_session.commit()

    citation_ids = await create_citations_for_run(
        db=db_session, run_id=run_id, report_id=report_id
    )
    await db_session.commit()

    assert len(citation_ids) == 1

    cit_result = await db_session.execute(
        select(Citation).where(Citation.id == citation_ids[0])
    )
    cit = cit_result.scalar_one()

    assert cit.apa_formatted is not None
    assert "Green, A." in cit.apa_formatted
    assert "2023" in cit.apa_formatted
    assert cit.ieee_formatted is not None
    assert "Green, A." in cit.ieee_formatted


# ---------------------------------------------------------------------------
# CM-17: has_validated_citations=True after successful validation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cm17_report_validated_citations_true(db_session):
    """report.has_validated_citations=True when all citations pass validation."""
    from app.models.project import ResearchProject
    from app.models.run import ResearchRun
    from app.models.report import ResearchReport
    from app.models.evidence import EvidenceRecord
    from app.services.citation_service import create_citations_for_run
    from app.services.citation_validator import validate_citations_for_run
    from sqlalchemy import select

    project_id = str(uuid.uuid4())
    run_id = str(uuid.uuid4())
    report_id = str(uuid.uuid4())
    ev_id = str(uuid.uuid4())

    project = ResearchProject(
        id=project_id, title="Test", research_question="Q?", status="in_progress"
    )
    run = ResearchRun(
        id=run_id, project_id=project_id, research_question="Q?", verification_depth="basic"
    )
    report = ResearchReport(
        id=report_id, run_id=run_id, research_question="Q?",
        executive_summary="Summary",
        key_findings=json.dumps(["F1"]),
        evidence_used=json.dumps([]),
        limitations="None",
        sources=json.dumps(["[SOURCE 1] Good source"]),
        generated_at=datetime.now(timezone.utc),
    )
    ev = EvidenceRecord(
        id=ev_id, run_id=run_id, source_type="web",
        source_label="[SOURCE 1]", content="Good solid content.",
        fetch_status="success",
    )
    db_session.add_all([project, run, report, ev])
    await db_session.commit()

    await create_citations_for_run(db=db_session, run_id=run_id, report_id=report_id)
    await db_session.commit()
    await validate_citations_for_run(db=db_session, run_id=run_id, report_id=report_id)
    await db_session.commit()

    rpt_result = await db_session.execute(
        select(ResearchReport).where(ResearchReport.id == report_id)
    )
    rpt = rpt_result.scalar_one()
    assert rpt.has_validated_citations is True
    assert rpt.review_status == "verified"


# ---------------------------------------------------------------------------
# CM-18: has_validated_citations=False after failed validation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cm18_report_validated_citations_false_on_failure(db_session):
    """report.has_validated_citations=False when citations fail validation."""
    from app.models.project import ResearchProject
    from app.models.run import ResearchRun
    from app.models.report import ResearchReport
    from app.models.evidence import EvidenceRecord
    from app.models.citation import Citation
    from app.services.citation_validator import validate_citations_for_run
    from sqlalchemy import select

    project_id = str(uuid.uuid4())
    run_id = str(uuid.uuid4())
    report_id = str(uuid.uuid4())
    ev_id = str(uuid.uuid4())

    project = ResearchProject(
        id=project_id, title="Test", research_question="Q?", status="in_progress"
    )
    run = ResearchRun(
        id=run_id, project_id=project_id, research_question="Q?", verification_depth="basic"
    )
    report = ResearchReport(
        id=report_id, run_id=run_id, research_question="Q?",
        executive_summary="Summary",
        key_findings=json.dumps(["F1"]),
        evidence_used=json.dumps([]),
        limitations="None",
        sources=json.dumps(["[SOURCE 1] Real"]),
        generated_at=datetime.now(timezone.utc),
    )
    ev = EvidenceRecord(
        id=ev_id, run_id=run_id, source_type="web",
        source_label="[SOURCE 1]", content="",  # empty content → will fail
        fetch_status="success",
    )
    cit = Citation(
        id=str(uuid.uuid4()),
        run_id=run_id,
        report_id=report_id,
        evidence_id=ev_id,
        citation_key="[SOURCE 1]",
        is_verified=False,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add_all([project, run, report, ev, cit])
    await db_session.commit()

    await validate_citations_for_run(db=db_session, run_id=run_id, report_id=report_id)
    await db_session.commit()

    rpt_result = await db_session.execute(
        select(ResearchReport).where(ResearchReport.id == report_id)
    )
    rpt = rpt_result.scalar_one()
    assert rpt.has_validated_citations is False
    assert rpt.review_status == "needs_attention"


# ---------------------------------------------------------------------------
# CM-19: Graph compiles with citation_validation_node in topology
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cm19_graph_compiles_with_citation_validation_node():
    """The compiled graph includes citation_validation_node."""
    from app.graph.workflow import _build_graph_skeleton
    from langgraph.checkpoint.memory import MemorySaver

    checkpointer = MemorySaver()
    builder = _build_graph_skeleton()
    graph = builder.compile(checkpointer=checkpointer)

    node_names = set(graph.nodes.keys())
    assert "citation_validation_node" in node_names
    # All expected nodes present
    for expected in ["initialize_run", "supervisor_node", "finalize_report",
                     "claim_extraction_node", "critic_node",
                     "citation_validation_node", "fail_workflow"]:
        assert expected in node_names, f"Missing node: {expected}"


# ---------------------------------------------------------------------------
# CM-20: _parse_source_keys handles various formats
# ---------------------------------------------------------------------------

def test_cm20_parse_source_keys_various_formats():
    """_parse_source_keys_from_report handles JSON array, plain string, None."""
    from app.services.citation_service import _parse_source_keys_from_report

    # JSON array
    keys = _parse_source_keys_from_report(
        json.dumps(["[SOURCE 1] Title A", "[SOURCE 2] Title B"])
    )
    assert "[SOURCE 1]" in keys
    assert "[SOURCE 2]" in keys

    # Plain string with [SOURCE N] pattern
    keys2 = _parse_source_keys_from_report("[SOURCE 3] Some title")
    assert "[SOURCE 3]" in keys2

    # None → empty list
    keys3 = _parse_source_keys_from_report(None)
    assert keys3 == []

    # Empty string → empty list
    keys4 = _parse_source_keys_from_report("")
    assert keys4 == []
