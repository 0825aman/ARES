"""
tests/test_evidence_extraction.py — Phase 4 M4.3: Evidence Schema Extension

Test IDs:
  EE-01  EvidenceRecord has all 7 new Phase 4 columns with correct defaults
  EE-02  EvidenceExtractor maps web evidence to source_id when URL matches Source
  EE-03  EvidenceExtractor maps document evidence to chunk_id by (doc_id, chunk_index)
  EE-04  EvidenceExtractor sets section_name from DocumentChunk.section_title
  EE-05  evidence_type defaults to "other" on LLM classification failure
  EE-06  evidence_relationship defaults to "neutral" on LLM classification failure
  EE-07  LLM classification returns valid enum values only
  EE-08  _safe_classification handles malformed JSON gracefully
  EE-09  _safe_classification pads short response to expected count
  EE-10  build_source_map builds correct URL → source_id mapping
  EE-11  build_chunk_map builds correct (doc_id, chunk_index) → chunk_id mapping
  EE-12  GET /runs/{run_id}/evidence → 200 with items list
  EE-13  GET /runs/{run_id}/evidence → filterable by evidence_type
  EE-14  GET /runs/{run_id}/evidence → filterable by evidence_relationship
  EE-15  GET /runs/{run_id}/evidence → 404 for non-existent run
  EE-16  EvidenceResponse includes all Phase 4 fields
  EE-17  NormalizedEvidence dataclass has new Phase 4 fields with correct defaults
  EE-18  Existing Phase 2/3 EvidenceRecord rows backward-compatible (defaults apply)
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chunk import DocumentChunk
from app.models.evidence import EvidenceRecord
from app.models.project import ResearchProject
from app.models.run import ResearchRun
from app.models.source import Source
from app.services.evidence_extractor import (
    _safe_classification,
    build_chunk_map,
    build_source_map,
    enrich_evidence_records,
)
from app.services.evidence_normalizer import NormalizedEvidence


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_project(project_id: str | None = None) -> ResearchProject:
    return ResearchProject(
        id=project_id or str(uuid.uuid4()),
        title="Test Project",
        research_question="What is evidence?",
    )


def _make_run(project_id: str, run_id: str | None = None) -> ResearchRun:
    return ResearchRun(
        id=run_id or str(uuid.uuid4()),
        project_id=project_id,
        research_question="What is evidence?",
    )


def _make_source(run_id: str, url: str, source_id: str | None = None) -> Source:
    return Source(
        id=source_id or str(uuid.uuid4()),
        run_id=run_id,
        source_type="web",
        url=url,
        retrieval_provider="tavily",
        is_peer_reviewed=False,
        is_accessible=True,
        retrieved_at=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
    )


def _make_chunk(
    doc_id: str,
    chunk_index: int = 0,
    section_title: str | None = None,
    chunk_id: str | None = None,
) -> DocumentChunk:
    text = "test chunk content"
    return DocumentChunk(
        id=chunk_id or str(uuid.uuid4()),
        document_id=doc_id,
        chunk_index=chunk_index,
        text=text,
        char_count=len(text),
        has_tables=False,
        created_at=datetime.now(timezone.utc),
        section_title=section_title,
    )


def _make_evidence_record(run_id: str, url: str | None = None,
                           document_id: str | None = None,
                           chunk_index: int | None = None) -> EvidenceRecord:
    return EvidenceRecord(
        id=str(uuid.uuid4()),
        run_id=run_id,
        source_type="web" if url else "document",
        source_label="[SOURCE 1]",
        content="This contains statistical data showing 80% improvement.",
        relevance_score=0.8,
        url=url,
        document_id=document_id,
        chunk_index=chunk_index,
    )


async def _create_project_and_run(client: AsyncClient) -> tuple[str, str]:
    proj = await client.post(
        "/api/v1/projects/",
        json={"title": "EE Test", "research_question": "Evidence?"},
    )
    assert proj.status_code == 201
    project_id = proj.json()["id"]
    run = await client.post(
        f"/api/v1/projects/{project_id}/runs",
        json={"research_question": "Evidence?", "workflow_mode": "sequential"},
    )
    assert run.status_code == 201
    return project_id, run.json()["id"]


# ---------------------------------------------------------------------------
# Unit tests — _safe_classification
# ---------------------------------------------------------------------------

def test_ee08_safe_classification_malformed_json():
    """EE-08: _safe_classification returns defaults on invalid JSON."""
    result = _safe_classification("not json at all", 3)
    assert len(result) == 3
    for item in result:
        assert item["evidence_type"] == "other"
        assert item["evidence_relationship"] == "neutral"


def test_ee08b_safe_classification_invalid_enum():
    """_safe_classification replaces invalid enum values with defaults."""
    raw = '[{"evidence_type": "magic", "evidence_relationship": "yes"}]'
    result = _safe_classification(raw, 1)
    assert result[0]["evidence_type"] == "other"
    assert result[0]["evidence_relationship"] == "neutral"


def test_ee09_safe_classification_pads_short_response():
    """EE-09: _safe_classification pads to expected count when LLM returns fewer items."""
    raw = '[{"evidence_type": "statistical", "evidence_relationship": "supports"}]'
    result = _safe_classification(raw, 3)
    assert len(result) == 3
    assert result[0]["evidence_type"] == "statistical"
    assert result[1]["evidence_type"] == "other"  # padded
    assert result[2]["evidence_type"] == "other"  # padded


def test_ee07_safe_classification_valid_enums():
    """EE-07: _safe_classification preserves valid enum values."""
    raw = json.dumps([
        {"evidence_type": "statistical", "evidence_relationship": "supports"},
        {"evidence_type": "expert_opinion", "evidence_relationship": "contradicts"},
        {"evidence_type": "observational", "evidence_relationship": "neutral"},
    ])
    result = _safe_classification(raw, 3)
    assert result[0] == {"evidence_type": "statistical", "evidence_relationship": "supports"}
    assert result[1] == {"evidence_type": "expert_opinion", "evidence_relationship": "contradicts"}
    assert result[2] == {"evidence_type": "observational", "evidence_relationship": "neutral"}


# ---------------------------------------------------------------------------
# Unit tests — build_source_map / build_chunk_map
# ---------------------------------------------------------------------------

def test_ee10_build_source_map():
    """EE-10: build_source_map returns correct URL → source_id mapping."""
    run_id = str(uuid.uuid4())
    sources = [
        _make_source(run_id, "https://example.com/paper1", source_id="s-001"),
        _make_source(run_id, "https://example.com/paper2", source_id="s-002"),
    ]
    mapping = build_source_map(None, sources)
    assert mapping["https://example.com/paper1"] == "s-001"
    assert mapping["https://example.com/paper2"] == "s-002"


def test_ee10b_build_source_map_normalises_url():
    """build_source_map normalises to lowercase and strips trailing slash."""
    run_id = str(uuid.uuid4())
    sources = [_make_source(run_id, "https://Example.com/Paper/", source_id="s-001")]
    mapping = build_source_map(None, sources)
    assert "https://example.com/paper" in mapping


def test_ee11_build_chunk_map():
    """EE-11: build_chunk_map returns correct (doc_id, chunk_index) → chunk_id mapping."""
    doc_id = str(uuid.uuid4())
    chunks = [
        _make_chunk(doc_id, chunk_index=0, chunk_id="c-001"),
        _make_chunk(doc_id, chunk_index=1, chunk_id="c-002"),
    ]
    mapping = build_chunk_map(chunks)
    assert mapping[(doc_id, 0)] == "c-001"
    assert mapping[(doc_id, 1)] == "c-002"


# ---------------------------------------------------------------------------
# Unit tests — NormalizedEvidence dataclass
# ---------------------------------------------------------------------------

def test_ee17_normalized_evidence_new_fields():
    """EE-17: NormalizedEvidence has Phase 4 fields with correct defaults."""
    ev = NormalizedEvidence(source_type="web", content="test")
    assert ev.source_id is None
    assert ev.chunk_id is None
    assert ev.evidence_type == "other"
    assert ev.evidence_relationship == "neutral"
    assert ev.section_name is None
    assert ev.extraction_method is None
    assert ev.extraction_confidence is None


# ---------------------------------------------------------------------------
# Integration tests — enrich_evidence_records
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_ee01_evidence_record_has_new_columns(db_session: AsyncSession):
    """EE-01: EvidenceRecord has all 7 new Phase 4 columns with correct defaults."""
    project = _make_project()
    db_session.add(project)
    run = _make_run(project.id)
    db_session.add(run)
    await db_session.flush()

    rec = _make_evidence_record(run.id, url="https://example.com")
    db_session.add(rec)
    await db_session.flush()

    # Verify defaults
    assert rec.evidence_type == "other"
    assert rec.evidence_relationship == "neutral"
    assert rec.source_id is None
    assert rec.chunk_id is None
    assert rec.section_name is None
    assert rec.extraction_method is None
    assert rec.extraction_confidence is None


@pytest.mark.asyncio
async def test_ee02_enricher_maps_source_id(db_session: AsyncSession):
    """EE-02: enrich_evidence_records maps source_id by URL match."""
    project = _make_project()
    db_session.add(project)
    run = _make_run(project.id)
    db_session.add(run)
    await db_session.flush()

    source = _make_source(run.id, "https://example.com/paper", source_id=str(uuid.uuid4()))
    db_session.add(source)
    await db_session.flush()

    rec = _make_evidence_record(run.id, url="https://example.com/paper")
    db_session.add(rec)
    await db_session.flush()

    # Mock LLM to return valid classification
    mock_llm = MagicMock()
    mock_llm.complete = AsyncMock(return_value='[{"evidence_type": "statistical", "evidence_relationship": "supports"}]')

    source_map = build_source_map(None, [source])
    await enrich_evidence_records(
        db=db_session,
        run_id=run.id,
        research_question="What is evidence?",
        evidence_ids=[rec.id],
        source_map=source_map,
        chunk_map={},
        llm_provider=mock_llm,
    )

    await db_session.refresh(rec)
    assert rec.source_id == source.id


@pytest.mark.asyncio
async def test_ee03_enricher_maps_chunk_id(db_session: AsyncSession):
    """EE-03: enrich_evidence_records maps chunk_id by (document_id, chunk_index)."""
    from app.models.document import UploadedDocument

    project = _make_project()
    db_session.add(project)
    run = _make_run(project.id)
    db_session.add(run)
    await db_session.flush()

    doc = UploadedDocument(
        id=str(uuid.uuid4()),
        project_id=project.id,
        original_filename="test.txt",
        stored_filename="test.txt",
        storage_path="/tmp/test.txt",
        mime_type="text/plain",
        file_size_bytes=100,
        content_hash="abc123",
    )
    db_session.add(doc)

    chunk = _make_chunk(doc.id, chunk_index=0, chunk_id=str(uuid.uuid4()))
    db_session.add(chunk)
    await db_session.flush()

    rec = _make_evidence_record(run.id, document_id=doc.id, chunk_index=0)
    db_session.add(rec)
    await db_session.flush()

    mock_llm = MagicMock()
    mock_llm.complete = AsyncMock(return_value='[{"evidence_type": "other", "evidence_relationship": "neutral"}]')

    chunk_map = build_chunk_map([chunk])
    await enrich_evidence_records(
        db=db_session,
        run_id=run.id,
        research_question="Q?",
        evidence_ids=[rec.id],
        source_map={},
        chunk_map=chunk_map,
        llm_provider=mock_llm,
    )

    await db_session.refresh(rec)
    assert rec.chunk_id == chunk.id


@pytest.mark.asyncio
async def test_ee04_enricher_sets_section_name(db_session: AsyncSession):
    """EE-04: enrich_evidence_records sets section_name from DocumentChunk.section_title."""
    from app.models.document import UploadedDocument

    project = _make_project()
    db_session.add(project)
    run = _make_run(project.id)
    db_session.add(run)
    await db_session.flush()

    doc = UploadedDocument(
        id=str(uuid.uuid4()),
        project_id=project.id,
        original_filename="report.docx",
        stored_filename="report.docx",
        storage_path="/tmp/report.docx",
        mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        file_size_bytes=200,
        content_hash="def456",
    )
    db_session.add(doc)

    chunk = _make_chunk(doc.id, chunk_index=2, section_title="Methods Section", chunk_id=str(uuid.uuid4()))
    db_session.add(chunk)
    await db_session.flush()

    rec = _make_evidence_record(run.id, document_id=doc.id, chunk_index=2)
    db_session.add(rec)
    await db_session.flush()

    mock_llm = MagicMock()
    mock_llm.complete = AsyncMock(return_value='[{"evidence_type": "observational", "evidence_relationship": "supports"}]')

    chunk_map = build_chunk_map([chunk])
    await enrich_evidence_records(
        db=db_session,
        run_id=run.id,
        research_question="Q?",
        evidence_ids=[rec.id],
        source_map={},
        chunk_map=chunk_map,
        llm_provider=mock_llm,
    )

    await db_session.refresh(rec)
    assert rec.section_name == "Methods Section"


@pytest.mark.asyncio
async def test_ee05_enricher_defaults_on_llm_failure(db_session: AsyncSession):
    """EE-05/EE-06: enrich_evidence_records defaults to 'other'/'neutral' on LLM failure."""
    project = _make_project()
    db_session.add(project)
    run = _make_run(project.id)
    db_session.add(run)
    await db_session.flush()

    rec = _make_evidence_record(run.id, url="https://example.com")
    db_session.add(rec)
    await db_session.flush()

    mock_llm = MagicMock()
    mock_llm.complete = AsyncMock(side_effect=RuntimeError("LLM failure"))

    await enrich_evidence_records(
        db=db_session,
        run_id=run.id,
        research_question="Q?",
        evidence_ids=[rec.id],
        source_map={},
        chunk_map={},
        llm_provider=mock_llm,
    )

    await db_session.refresh(rec)
    assert rec.evidence_type == "other"
    assert rec.evidence_relationship == "neutral"


@pytest.mark.asyncio
async def test_ee18_backward_compatible_defaults(db_session: AsyncSession):
    """EE-18: Phase 2/3 evidence records have correct default values for new columns."""
    project = _make_project()
    db_session.add(project)
    run = _make_run(project.id)
    db_session.add(run)
    await db_session.flush()

    # Simulate a pre-Phase-4 EvidenceRecord (no new fields explicitly set)
    rec = EvidenceRecord(
        id=str(uuid.uuid4()),
        run_id=run.id,
        source_type="web",
        source_label="[SOURCE 1]",
        content="old evidence",
        relevance_score=0.5,
        url="https://example.com/old",
    )
    db_session.add(rec)
    await db_session.commit()
    await db_session.refresh(rec)

    assert rec.evidence_type == "other"
    assert rec.evidence_relationship == "neutral"
    assert rec.source_id is None
    assert rec.chunk_id is None


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_ee12_get_evidence_200(async_client: AsyncClient):
    """EE-12: GET /runs/{run_id}/evidence → 200."""
    project_id, run_id = await _create_project_and_run(async_client)
    resp = await async_client.get(f"/api/v1/projects/{project_id}/runs/{run_id}/evidence")
    assert resp.status_code == 200
    body = resp.json()
    assert "items" in body
    assert "total" in body
    assert body["run_id"] == run_id


@pytest.mark.asyncio
async def test_ee13_get_evidence_filter_type(async_client: AsyncClient):
    """EE-13: GET evidence with evidence_type filter → 200."""
    project_id, run_id = await _create_project_and_run(async_client)
    resp = await async_client.get(
        f"/api/v1/projects/{project_id}/runs/{run_id}/evidence",
        params={"evidence_type": "statistical"},
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_ee14_get_evidence_filter_relationship(async_client: AsyncClient):
    """EE-14: GET evidence with evidence_relationship filter → 200."""
    project_id, run_id = await _create_project_and_run(async_client)
    resp = await async_client.get(
        f"/api/v1/projects/{project_id}/runs/{run_id}/evidence",
        params={"evidence_relationship": "supports"},
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_ee15_get_evidence_nonexistent_run(async_client: AsyncClient):
    """EE-15: GET evidence for non-existent run → 404."""
    project_id, _ = await _create_project_and_run(async_client)
    fake_run_id = str(uuid.uuid4())
    resp = await async_client.get(f"/api/v1/projects/{project_id}/runs/{fake_run_id}/evidence")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_ee16_evidence_response_has_phase4_fields(db_session: AsyncSession):
    """EE-16: EvidenceResponse includes all Phase 4 M4.3 fields."""
    from app.schemas.evidence import EvidenceResponse

    rec = EvidenceRecord(
        id=str(uuid.uuid4()),
        run_id=str(uuid.uuid4()),
        source_type="web",
        source_label="[S1]",
        content="content",
        relevance_score=0.9,
        fetch_status="success",
        evidence_type="statistical",
        evidence_relationship="supports",
        section_name="Results",
        extraction_method="llm_classification",
        extraction_confidence=0.8,
    )
    resp = EvidenceResponse.model_validate(rec)
    assert resp.evidence_type == "statistical"
    assert resp.evidence_relationship == "supports"
    assert resp.section_name == "Results"
    assert resp.extraction_method == "llm_classification"
    assert resp.extraction_confidence == 0.8
