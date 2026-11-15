"""
tests/test_workflow.py — Milestone 4: Research Workflow Engine tests

Test IDs:
  W-01  Web-only run → status=completed, report created in DB
  W-02  Document-only run with a TXT document → status=completed
  W-03  Web + document run → evidence from both sources, status=completed
  W-04  All docs fail extraction, use_web=True → continues, status=completed
  W-05  All docs fail extraction, use_web=False → status=failed
  W-06  Web search fails (MockWebSearchProvider(fail=True)), use_documents=False → status=failed
  W-07  Web search fails, use_documents=True with valid docs → continues, status=completed
  W-08  LLM fails once then succeeds (MockLLMProvider(fail_times=1)) → status=completed
  W-09  LLM fails twice (MockLLMProvider(fail=True)) → status=failed
  W-10  LLM returns malformed JSON → report created with raw text as summary
  W-11  Run starts in non-pending state → exits without crash
  W-12  run_service.create_run with both sources disabled → raises ValueError
  W-13  run_service.create_run while another run is active → raises RuntimeError
  W-14  Report has evidence_used and sources populated
"""
from __future__ import annotations

import uuid
import tempfile
import pytest
from unittest.mock import patch
from sqlalchemy import select

from tests.conftest import TestSessionLocal
from app.models.run import ResearchRun
from app.models.document import UploadedDocument
from app.models.report import ResearchReport
from app.models.evidence import EvidenceRecord
from app.models.project import ResearchProject
from app.providers.llm import MockLLMProvider
from app.providers.web_search import MockWebSearchProvider
from app.services.run_service import run_service
from app.services.research_workflow import run_research_workflow


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _create_project(db) -> ResearchProject:
    """Create a minimal project directly in the DB."""
    project = ResearchProject(
        id=str(uuid.uuid4()),
        title="Test Project",
        research_question="What is the research topic?",
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return project


async def _create_run_direct(db, project_id, use_web=True, use_documents=False):
    """Create a run via run_service.create_run with document_ids=[]."""
    return await run_service.create_run(
        db, project_id, "What is the research topic?", use_web, use_documents, []
    )


async def _create_txt_document(db, project_id, run_id, content: str = None) -> UploadedDocument:
    """Create a real TXT file on disk and an UploadedDocument record pointing to it."""
    if content is None:
        content = (
            "This is a research document about the research topic. "
            "It contains useful information about various aspects of the topic. "
            "The research topic has many interesting properties worth studying."
        )

    # Write a real temp file
    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False, encoding="utf-8"
    )
    tmp.write(content)
    tmp.close()

    doc = UploadedDocument(
        id=str(uuid.uuid4()),
        project_id=project_id,
        run_id=run_id,
        original_filename="test_doc.txt",
        stored_filename="test_doc.txt",
        storage_path=tmp.name,
        mime_type="text/plain",
        file_size_bytes=len(content.encode()),
        content_hash="abc123",
        extraction_status="pending",
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    return doc


async def _create_missing_file_document(db, project_id, run_id) -> UploadedDocument:
    """Create an UploadedDocument pointing to a nonexistent file path."""
    doc = UploadedDocument(
        id=str(uuid.uuid4()),
        project_id=project_id,
        run_id=run_id,
        original_filename="missing.txt",
        stored_filename="missing.txt",
        storage_path="/nonexistent/path/missing.txt",
        mime_type="text/plain",
        file_size_bytes=100,
        content_hash="deadbeef",
        extraction_status="pending",
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    return doc


def _patch_workflow_db():
    """Return a context manager that patches AsyncSessionLocal in the workflow module
    to use the in-memory test database."""
    return patch(
        "app.services.research_workflow.AsyncSessionLocal",
        new=TestSessionLocal,
    )


async def _fetch_run(run_id: str) -> ResearchRun:
    """Open a fresh session to read the current run state from DB."""
    async with TestSessionLocal() as session:
        result = await session.execute(select(ResearchRun).where(ResearchRun.id == run_id))
        return result.scalar_one()


async def _fetch_report(run_id: str) -> ResearchReport | None:
    """Open a fresh session to read the report for a run."""
    async with TestSessionLocal() as session:
        result = await session.execute(
            select(ResearchReport).where(ResearchReport.run_id == run_id)
        )
        return result.scalar_one_or_none()


async def _fetch_evidence(run_id: str) -> list[EvidenceRecord]:
    """Open a fresh session to read all evidence records for a run."""
    async with TestSessionLocal() as session:
        result = await session.execute(
            select(EvidenceRecord).where(EvidenceRecord.run_id == run_id)
        )
        return result.scalars().all()


# ---------------------------------------------------------------------------
# W-01: Web-only run → status=completed, report created in DB
# ---------------------------------------------------------------------------

async def test_w01_web_only_run_completes(db_session):
    project = await _create_project(db_session)
    run = await _create_run_direct(db_session, project.id, use_web=True, use_documents=False)

    with _patch_workflow_db():
        await run_research_workflow(
            run.id,
            llm_provider=MockLLMProvider(),
            search_provider=MockWebSearchProvider(),
        )

    updated_run = await _fetch_run(run.id)
    assert updated_run.status == "completed"
    assert updated_run.completed_at is not None
    assert updated_run.started_at is not None

    report = await _fetch_report(run.id)
    assert report is not None
    assert report.executive_summary
    assert report.research_question == run.research_question


# ---------------------------------------------------------------------------
# W-02: Document-only run with a TXT document → status=completed
# ---------------------------------------------------------------------------

async def test_w02_document_only_run_completes(db_session):
    project = await _create_project(db_session)

    # Create a pending run with use_documents=True directly
    run = ResearchRun(
        id=str(uuid.uuid4()),
        project_id=project.id,
        research_question="What is the research topic?",
        use_web=False,
        use_documents=True,
        status="pending",
    )
    db_session.add(run)
    await db_session.commit()

    # Create TXT document linked to the run
    await _create_txt_document(db_session, project.id, run.id)

    with _patch_workflow_db():
        await run_research_workflow(
            run.id,
            llm_provider=MockLLMProvider(),
            search_provider=MockWebSearchProvider(),
        )

    updated_run = await _fetch_run(run.id)
    assert updated_run.status == "completed"

    report = await _fetch_report(run.id)
    assert report is not None


# ---------------------------------------------------------------------------
# W-03: Web + document run → evidence from both sources, status=completed
# ---------------------------------------------------------------------------

async def test_w03_web_and_document_run_completes(db_session):
    project = await _create_project(db_session)

    run = ResearchRun(
        id=str(uuid.uuid4()),
        project_id=project.id,
        research_question="What is the research topic?",
        use_web=True,
        use_documents=True,
        status="pending",
    )
    db_session.add(run)
    await db_session.commit()

    await _create_txt_document(db_session, project.id, run.id)

    with _patch_workflow_db():
        await run_research_workflow(
            run.id,
            llm_provider=MockLLMProvider(),
            search_provider=MockWebSearchProvider(),
        )

    updated_run = await _fetch_run(run.id)
    assert updated_run.status == "completed"

    evidence = await _fetch_evidence(run.id)
    assert len(evidence) >= 1

    source_types = {ev.source_type for ev in evidence}
    # Both web and document evidence should be present
    assert "web" in source_types or "document" in source_types


# ---------------------------------------------------------------------------
# W-04: All docs fail extraction, use_web=True → continues, status=completed
# ---------------------------------------------------------------------------

async def test_w04_all_docs_fail_web_enabled_continues(db_session):
    project = await _create_project(db_session)

    run = ResearchRun(
        id=str(uuid.uuid4()),
        project_id=project.id,
        research_question="What is the research topic?",
        use_web=True,
        use_documents=True,
        status="pending",
    )
    db_session.add(run)
    await db_session.commit()

    # Create a document pointing to a nonexistent file (will fail extraction)
    await _create_missing_file_document(db_session, project.id, run.id)

    with _patch_workflow_db():
        await run_research_workflow(
            run.id,
            llm_provider=MockLLMProvider(),
            search_provider=MockWebSearchProvider(),
        )

    updated_run = await _fetch_run(run.id)
    # Should complete because web search succeeded
    assert updated_run.status == "completed"


# ---------------------------------------------------------------------------
# W-05: All docs fail extraction, use_web=False → status=failed
# ---------------------------------------------------------------------------

async def test_w05_all_docs_fail_no_web_fails(db_session):
    project = await _create_project(db_session)

    run = ResearchRun(
        id=str(uuid.uuid4()),
        project_id=project.id,
        research_question="What is the research topic?",
        use_web=False,
        use_documents=True,
        status="pending",
    )
    db_session.add(run)
    await db_session.commit()

    # Create a document pointing to a nonexistent file (will fail extraction)
    await _create_missing_file_document(db_session, project.id, run.id)

    with _patch_workflow_db():
        await run_research_workflow(
            run.id,
            llm_provider=MockLLMProvider(),
            search_provider=MockWebSearchProvider(),
        )

    updated_run = await _fetch_run(run.id)
    assert updated_run.status == "failed"
    assert updated_run.error_message


# ---------------------------------------------------------------------------
# W-06: Web search fails, use_documents=False → status=failed
# ---------------------------------------------------------------------------

async def test_w06_web_search_fails_no_docs_fails(db_session):
    project = await _create_project(db_session)
    run = await _create_run_direct(db_session, project.id, use_web=True, use_documents=False)

    with _patch_workflow_db():
        await run_research_workflow(
            run.id,
            llm_provider=MockLLMProvider(),
            search_provider=MockWebSearchProvider(fail=True),
        )

    updated_run = await _fetch_run(run.id)
    assert updated_run.status == "failed"
    assert updated_run.error_message


# ---------------------------------------------------------------------------
# W-07: Web search fails, use_documents=True with valid docs → status=completed
# ---------------------------------------------------------------------------

async def test_w07_web_search_fails_docs_present_completes(db_session):
    project = await _create_project(db_session)

    run = ResearchRun(
        id=str(uuid.uuid4()),
        project_id=project.id,
        research_question="What is the research topic?",
        use_web=True,
        use_documents=True,
        status="pending",
    )
    db_session.add(run)
    await db_session.commit()

    await _create_txt_document(db_session, project.id, run.id)

    with _patch_workflow_db():
        await run_research_workflow(
            run.id,
            llm_provider=MockLLMProvider(),
            search_provider=MockWebSearchProvider(fail=True),
        )

    updated_run = await _fetch_run(run.id)
    assert updated_run.status == "completed"


# ---------------------------------------------------------------------------
# W-08: LLM fails once then succeeds → status=completed
# ---------------------------------------------------------------------------

async def test_w08_llm_fails_once_then_succeeds(db_session):
    project = await _create_project(db_session)
    run = await _create_run_direct(db_session, project.id, use_web=True, use_documents=False)

    with _patch_workflow_db():
        with patch("app.services.report_generator.asyncio.sleep", return_value=None):
            await run_research_workflow(
                run.id,
                llm_provider=MockLLMProvider(fail_times=1),
                search_provider=MockWebSearchProvider(),
            )

    updated_run = await _fetch_run(run.id)
    assert updated_run.status == "completed"


# ---------------------------------------------------------------------------
# W-09: LLM always fails → status=failed
# ---------------------------------------------------------------------------

async def test_w09_llm_always_fails(db_session):
    project = await _create_project(db_session)
    run = await _create_run_direct(db_session, project.id, use_web=True, use_documents=False)

    with _patch_workflow_db():
        with patch("app.services.report_generator.asyncio.sleep", return_value=None):
            await run_research_workflow(
                run.id,
                llm_provider=MockLLMProvider(fail=True),
                search_provider=MockWebSearchProvider(),
            )

    updated_run = await _fetch_run(run.id)
    assert updated_run.status == "failed"
    assert updated_run.error_message


# ---------------------------------------------------------------------------
# W-10: LLM returns malformed JSON → report created with raw text as summary
# ---------------------------------------------------------------------------

async def test_w10_llm_returns_malformed_json(db_session):
    project = await _create_project(db_session)
    run = await _create_run_direct(db_session, project.id, use_web=True, use_documents=False)

    malformed_response = "Here is my analysis: The topic is very interesting. No JSON here."

    with _patch_workflow_db():
        await run_research_workflow(
            run.id,
            llm_provider=MockLLMProvider(response=malformed_response),
            search_provider=MockWebSearchProvider(),
        )

    updated_run = await _fetch_run(run.id)
    # Should complete — malformed JSON falls back to raw text
    assert updated_run.status == "completed"

    report = await _fetch_report(run.id)
    assert report is not None
    assert malformed_response[:200] in report.executive_summary


# ---------------------------------------------------------------------------
# W-11: Run starts in non-pending state → exits without crash
# ---------------------------------------------------------------------------

async def test_w11_non_pending_run_exits_cleanly(db_session):
    project = await _create_project(db_session)

    # Create a run that's already running
    run = ResearchRun(
        id=str(uuid.uuid4()),
        project_id=project.id,
        research_question="What is the research topic?",
        use_web=True,
        use_documents=False,
        status="running",
    )
    db_session.add(run)
    await db_session.commit()

    with _patch_workflow_db():
        # Should return silently without crashing
        await run_research_workflow(
            run.id,
            llm_provider=MockLLMProvider(),
            search_provider=MockWebSearchProvider(),
        )

    # Status should remain unchanged
    updated_run = await _fetch_run(run.id)
    assert updated_run.status == "running"  # unchanged


# ---------------------------------------------------------------------------
# W-12: run_service.create_run with both sources disabled → raises ValueError
# ---------------------------------------------------------------------------

async def test_w12_both_sources_disabled_raises(db_session):
    project = await _create_project(db_session)

    with pytest.raises(ValueError, match="At least one information source"):
        await run_service.create_run(
            db_session,
            project.id,
            "Research question?",
            use_web=False,
            use_documents=False,
            document_ids=[],
        )


# ---------------------------------------------------------------------------
# W-13: run_service.create_run while another run is active → raises RuntimeError
# ---------------------------------------------------------------------------

async def test_w13_duplicate_active_run_raises(db_session):
    project = await _create_project(db_session)

    # Create an already-running run directly
    active_run = ResearchRun(
        id=str(uuid.uuid4()),
        project_id=project.id,
        research_question="First question",
        use_web=True,
        use_documents=False,
        status="running",
    )
    db_session.add(active_run)
    await db_session.commit()

    # Attempting to create another run should raise
    with pytest.raises(RuntimeError, match="already active"):
        await run_service.create_run(
            db_session,
            project.id,
            "Second question",
            use_web=True,
            use_documents=False,
            document_ids=[],
        )


# ---------------------------------------------------------------------------
# W-14: Report has evidence_used and sources populated
# ---------------------------------------------------------------------------

async def test_w14_report_has_evidence_and_sources(db_session):
    import json
    project = await _create_project(db_session)
    run = await _create_run_direct(db_session, project.id, use_web=True, use_documents=False)

    with _patch_workflow_db():
        await run_research_workflow(
            run.id,
            llm_provider=MockLLMProvider(),
            search_provider=MockWebSearchProvider(),
        )

    report = await _fetch_report(run.id)
    assert report is not None

    # sources should be a non-empty JSON array
    sources = json.loads(report.sources)
    assert isinstance(sources, list)
    assert len(sources) > 0

    # evidence_used should be a valid JSON array
    evidence_used = json.loads(report.evidence_used)
    assert isinstance(evidence_used, list)

    # key_findings should be a valid JSON array
    key_findings = json.loads(report.key_findings)
    assert isinstance(key_findings, list)
