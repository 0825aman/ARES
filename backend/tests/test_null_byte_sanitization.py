"""Unit tests for null byte (0x00) sanitization across models, services, and DB driver.

PostgreSQL rejects UTF-8 strings containing null bytes (\x00 / 0x00) with:
    invalid byte sequence for encoding "UTF8": 0x00
These tests verify that null bytes are stripped at:
1. SQLAlchemy bind_processor level (database.py)
2. ORM models via @validates (EvidenceRecord, Source, DocumentChunk, ResearchReport)
3. Domain dataclasses (NormalizedEvidence, SearchResult)
4. Evidence normalizer functions (normalize_web_result, normalize_document_chunk)
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy.dialects.postgresql.asyncpg import AsyncpgString, PGDialect_asyncpg
from sqlalchemy.types import String as SqlString, Text as SqlText

from app.core.database import _patch_asyncpg_strings
from app.models.chunk import DocumentChunk
from app.models.evidence import EvidenceRecord
from app.models.report import ResearchReport
from app.models.source import Source
from app.providers.web_search import SearchResult
from app.services.evidence_normalizer import (
    NormalizedEvidence,
    normalize_document_chunk,
    normalize_web_result,
)


def test_asyncpg_bind_processor_strips_null_bytes():
    """Verify dialect bind processors remove 0x00 characters for PostgreSQL."""
    dialect = PGDialect_asyncpg()

    string_proc = SqlString().bind_processor(dialect)
    assert string_proc(None) is None
    assert string_proc("clean string") == "clean string"
    assert string_proc("bad\x00string\x00with\x00nulls") == "badstringwithnulls"

    text_proc = SqlText().bind_processor(dialect)
    assert text_proc(None) is None
    assert text_proc("large\x00text\x00content") == "largetextcontent"

    asyncpg_proc = AsyncpgString().bind_processor(dialect)
    assert asyncpg_proc(None) is None
    assert asyncpg_proc("asyncpg\x00text") == "asyncpgtext"


def test_evidence_record_validates_null_bytes():
    """Verify EvidenceRecord model strips null bytes from string columns on init and update."""
    rec = EvidenceRecord(
        id=str(uuid.uuid4()),
        run_id=str(uuid.uuid4()),
        source_type="web",
        source_label="[S1\x00]",
        content="Research evidence\x00 with embedded\x00 nulls.",
        relevance_score=0.95,
        fetch_status="success",
        url="https://example.com/paper\x00.html",
        page_title="Title\x00 With Nulls",
        section_name="Discussion\x00 Section",
        fetch_error="Error\x00 trace",
    )

    assert rec.content == "Research evidence with embedded nulls."
    assert rec.page_title == "Title With Nulls"
    assert rec.url == "https://example.com/paper.html"
    assert rec.section_name == "Discussion Section"
    assert rec.source_label == "[S1]"
    assert rec.fetch_error == "Error trace"

    # Verify reassignment also cleans text
    rec.content = "Updated\x00 content\x00"
    assert rec.content == "Updated content"


def test_source_model_validates_null_bytes():
    """Verify Source model strips null bytes from metadata and text columns."""
    src = Source(
        id=str(uuid.uuid4()),
        run_id=str(uuid.uuid4()),
        source_type="web",
        title="Source\x00 Title",
        url="https://domain.com/\x00test",
        authors='["Author\x00 One", "Author Two"]',
        publisher="Publisher\x00 Corp",
        venue="Conference\x00 2026",
        retrieval_provider="tavily",
        retrieved_at=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
    )

    assert src.title == "Source Title"
    assert src.url == "https://domain.com/test"
    assert src.authors == '["Author One", "Author Two"]'
    assert src.publisher == "Publisher Corp"
    assert src.venue == "Conference 2026"


def test_document_chunk_validates_null_bytes():
    """Verify DocumentChunk model strips null bytes from text and section_title."""
    chunk = DocumentChunk(
        id=str(uuid.uuid4()),
        document_id=str(uuid.uuid4()),
        chunk_index=0,
        text="Extracted\x00 PDF\x00 text snippet",
        section_title="Introduction\x00 Section",
        created_at=datetime.now(timezone.utc),
    )

    assert chunk.text == "Extracted PDF text snippet"
    assert chunk.section_title == "Introduction Section"


def test_research_report_validates_null_bytes():
    """Verify ResearchReport model strips null bytes from report sections."""
    rep = ResearchReport(
        id=str(uuid.uuid4()),
        run_id=str(uuid.uuid4()),
        research_question="Question\x00?",
        executive_summary="Summary\x00 text",
        key_findings="Findings\x00 list",
        evidence_used="Evidence\x00",
        limitations="Limitations\x00",
        sources="Sources\x00",
        raw_llm_response="Raw\x00 LLM output",
    )

    assert rep.research_question == "Question?"
    assert rep.executive_summary == "Summary text"
    assert rep.key_findings == "Findings list"
    assert rep.raw_llm_response == "Raw LLM output"


def test_normalized_evidence_post_init_strips_null_bytes():
    """Verify NormalizedEvidence dataclass cleans null bytes on initialization."""
    ev = NormalizedEvidence(
        source_type="web",
        content="Content\x00 here",
        source_label="[SRC\x001]",
        url="https://test.com\x00",
        page_title="Title\x00",
        section_name="Sec\x00tion",
    )

    assert ev.content == "Content here"
    assert ev.source_label == "[SRC1]"
    assert ev.url == "https://test.com"
    assert ev.page_title == "Title"
    assert ev.section_name == "Section"


def test_normalize_helpers_strip_null_bytes():
    """Verify normalize_web_result and normalize_document_chunk strip null bytes."""
    web_ev = normalize_web_result(
        url="https://site.org/\x00test",
        title="Web\x00 Title",
        content="Scraped\x00 body text",
    )
    assert web_ev.url == "https://site.org/test"
    assert web_ev.page_title == "Web Title"
    assert web_ev.content == "Scraped body text"

    doc_ev = normalize_document_chunk(
        document_id="doc-123",
        filename="report\x00.pdf",
        chunk_text="Chunk\x00 text from PDF",
        chunk_index=0,
    )
    assert doc_ev.filename == "report.pdf"
    assert doc_ev.content == "Chunk text from PDF"


def test_search_result_post_init_strips_null_bytes():
    """Verify SearchResult dataclass cleans null bytes on creation."""
    sr = SearchResult(
        url="https://search.com/\x00result",
        title="Search\x00 Result Title",
        snippet="Snippet\x00 with nulls",
        content="Raw\x00 page content",
        venue="Venue\x00 Name",
    )
    assert sr.url == "https://search.com/result"
    assert sr.title == "Search Result Title"
    assert sr.snippet == "Snippet with nulls"
    assert sr.content == "Raw page content"
    assert sr.venue == "Venue Name"


if __name__ == "__main__":
    test_asyncpg_bind_processor_strips_null_bytes()
    test_evidence_record_validates_null_bytes()
    test_source_model_validates_null_bytes()
    test_document_chunk_validates_null_bytes()
    test_research_report_validates_null_bytes()
    test_normalized_evidence_post_init_strips_null_bytes()
    test_normalize_helpers_strip_null_bytes()
    test_search_result_post_init_strips_null_bytes()
    print("ALL 8 SANITIZATION TESTS PASSED SUCCESSFULLY!")
