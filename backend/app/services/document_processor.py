"""Document processor service — Phase 4 M4.1.

Replaces the inline text extraction logic scattered across:
  - app/services/research_workflow.py (_extract_documents)
  - app/agents/tools.py (get_document_chunks)

This service is called on document upload to produce permanent
DocumentChunk records. The chunks outlive individual research runs.

Extraction strategies by file type:
  PDF   — pypdf page-by-page; detects image-only pages by char density
  DOCX  — python-docx paragraph-level; preserves Heading styles as section_title
  TXT   — plain UTF-8; no heading detection

OCR strategy:
  If a PDF has fewer than OCR_CHAR_THRESHOLD chars per page on average,
  it is flagged as has_images=True on the UploadedDocument.
  Actual LLM-based OCR is only attempted when OCR_ENABLED=True AND the
  configured LLM is vision-capable.
  The current IBM watsonx Llama 3.3 70B model is text-only — OCR will
  never execute in Phase 4. The branch is implemented for future use.

Chunk sizes match Phase 2/3: 8000 chars with 400-char overlap.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from io import BytesIO
from typing import NamedTuple

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# Chars-per-page threshold below which a PDF is flagged as image-heavy
_OCR_CHAR_THRESHOLD = 50

# Chunk parameters — match Phase 2/3 chunk_text() defaults
_CHUNK_SIZE = 8000
_CHUNK_OVERLAP = 400


# ---------------------------------------------------------------------------
# Internal data structures
# ---------------------------------------------------------------------------

class _RawChunk(NamedTuple):
    chunk_index: int
    text: str
    page_start: int | None
    page_end: int | None
    section_title: str | None
    heading_level: int | None
    extraction_method: str


class _ExtractionResult(NamedTuple):
    chunks: list[_RawChunk]
    has_images: bool
    ocr_attempted: bool


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _split_with_pages(
    pages_text: list[str],
    extraction_method: str,
    chunk_size: int = _CHUNK_SIZE,
    overlap: int = _CHUNK_OVERLAP,
) -> list[_RawChunk]:
    """Chunk page-aware text.  Tracks which 1-based source pages each chunk spans.

    Strategy: walk pages sequentially, accumulating a buffer.  When the buffer
    exceeds chunk_size, emit a chunk and retain the last ``overlap`` chars.
    page_start / page_end reflect the first and last source page contributing
    to each chunk.
    """
    raw: list[_RawChunk] = []
    buffer = ""
    buf_page_start = 1
    buf_page_end = 1
    chunk_index = 0

    for page_num, page_text in enumerate(pages_text, start=1):
        stripped = page_text.strip()
        if not stripped:
            continue
        if not buffer:
            buf_page_start = page_num
        buffer += ("\n\n" if buffer else "") + stripped
        buf_page_end = page_num

        while len(buffer) >= chunk_size:
            raw.append(_RawChunk(
                chunk_index=chunk_index,
                text=buffer[:chunk_size],
                page_start=buf_page_start,
                page_end=buf_page_end,
                section_title=None,
                heading_level=None,
                extraction_method=extraction_method,
            ))
            chunk_index += 1
            # Overlap: keep the last `overlap` chars
            buffer = buffer[chunk_size - overlap:]
            # After carry-over we don't know the exact page — keep buf_page_end
            buf_page_start = buf_page_end

    # Flush remaining buffer
    if buffer.strip():
        raw.append(_RawChunk(
            chunk_index=chunk_index,
            text=buffer,
            page_start=buf_page_start,
            page_end=buf_page_end,
            section_title=None,
            heading_level=None,
            extraction_method=extraction_method,
        ))

    return raw


def _split_plain(text: str, extraction_method: str) -> list[_RawChunk]:
    """Simple overlap chunking — used for TXT files."""
    raw: list[_RawChunk] = []
    start = 0
    idx = 0
    while start < len(text):
        end = start + _CHUNK_SIZE
        raw.append(_RawChunk(
            chunk_index=idx,
            text=text[start:end],
            page_start=None,
            page_end=None,
            section_title=None,
            heading_level=None,
            extraction_method=extraction_method,
        ))
        idx += 1
        start = end - _CHUNK_OVERLAP
        if start >= len(text):
            break
    return raw


def _extract_pdf(file_data: bytes) -> _ExtractionResult:
    """Extract text from a PDF file page-by-page.

    Returns has_images=True if the average text length per page is below
    the OCR_CHAR_THRESHOLD (suggesting scanned/image pages).
    """
    from pypdf import PdfReader
    from pypdf.errors import FileNotDecryptedError

    try:
        reader = PdfReader(BytesIO(file_data))
    except FileNotDecryptedError:
        # Caller catches this and sets extraction_status="failed"
        raise

    pages_text: list[str] = []
    total_chars = 0
    for page in reader.pages:
        text = (page.extract_text() or "").replace("\x00", "")
        pages_text.append(text)
        total_chars += len(text.strip())

    num_pages = len(reader.pages)
    avg_chars = total_chars / num_pages if num_pages > 0 else 0
    has_images = avg_chars < _OCR_CHAR_THRESHOLD

    if not any(t.strip() for t in pages_text):
        # Image-only PDF — no text extractable
        return _ExtractionResult(chunks=[], has_images=True, ocr_attempted=False)

    chunks = _split_with_pages(pages_text, "pypdf")
    return _ExtractionResult(chunks=chunks, has_images=has_images, ocr_attempted=False)


def _extract_docx(file_data: bytes) -> _ExtractionResult:
    """Extract text from a DOCX file.

    Heading-style paragraphs set section_title and heading_level on subsequent
    non-heading content chunks.  This is a best-effort heuristic — DOCX heading
    levels are 1–9 in python-docx (Heading 1 → Heading 9).
    """
    from docx import Document as DocxDocument

    docx_doc = DocxDocument(BytesIO(file_data))

    # Build a list of (text, heading_level | None, section_title | None)
    # Walk paragraphs and group into chunks with section metadata.
    current_section_title: str | None = None
    current_heading_level: int | None = None
    buffer = ""
    chunk_index = 0
    raw: list[_RawChunk] = []

    def _flush(buf: str, sec: str | None, level: int | None, idx: int) -> list[_RawChunk]:
        result = []
        start = 0
        while start < len(buf):
            end = start + _CHUNK_SIZE
            result.append(_RawChunk(
                chunk_index=idx + len(result),
                text=buf[start:end],
                page_start=None,
                page_end=None,
                section_title=sec,
                heading_level=level,
                extraction_method="python-docx",
            ))
            start = end - _CHUNK_OVERLAP
            if start >= len(buf):
                break
        return result

    for para in docx_doc.paragraphs:
        style_name = (para.style.name or "").replace("\x00", "") if para.style else ""
        text = para.text.replace("\x00", "").strip()
        if not text:
            continue

        # Detect heading paragraphs
        heading_level: int | None = None
        if style_name.startswith("Heading "):
            try:
                heading_level = int(style_name.split("Heading ")[1].strip())
            except (ValueError, IndexError):
                heading_level = None

        if heading_level is not None:
            # Flush any accumulated buffer before this heading
            if buffer.strip():
                raw.extend(_flush(buffer, current_section_title, current_heading_level, chunk_index))
                chunk_index = len(raw)
                buffer = ""
            # Update current section context
            current_section_title = text
            current_heading_level = heading_level
        else:
            buffer += ("\n" if buffer else "") + text

    # Flush remaining buffer
    if buffer.strip():
        raw.extend(_flush(buffer, current_section_title, current_heading_level, chunk_index))

    # Re-number chunk_index sequentially after any heading flushes
    renumbered = [
        _RawChunk(
            chunk_index=i,
            text=c.text,
            page_start=c.page_start,
            page_end=c.page_end,
            section_title=c.section_title,
            heading_level=c.heading_level,
            extraction_method=c.extraction_method,
        )
        for i, c in enumerate(raw)
    ]
    return _ExtractionResult(chunks=renumbered, has_images=False, ocr_attempted=False)


def _extract_txt(file_data: bytes) -> _ExtractionResult:
    """Extract text from a plain UTF-8 text file."""
    text = file_data.decode("utf-8", errors="replace").replace("\x00", "")
    if not text.strip():
        return _ExtractionResult(chunks=[], has_images=False, ocr_attempted=False)
    chunks = _split_plain(text, "plain-text")
    return _ExtractionResult(chunks=chunks, has_images=False, ocr_attempted=False)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def process_document(
    db: AsyncSession,
    document_id: str,
    storage_path: str,
    original_filename: str,
) -> tuple[int, bool, bool]:
    """Extract text from a stored document and persist DocumentChunk records.

    Returns (chunk_count, has_images, ocr_attempted).

    On extraction failure the function returns (0, False, False) and logs a
    warning.  The caller (document_service) is responsible for updating
    extraction_status on the UploadedDocument.

    This function is intentionally synchronous-extraction + async-persistence:
    the I/O-bound file read and CPU-bound extraction happen synchronously
    (acceptable for document sizes up to ~20 MB), while DB operations are async.
    """
    from app.models.chunk import DocumentChunk

    ext = original_filename.rsplit(".", 1)[-1].lower() if "." in original_filename else ""

    # --- Read file ---
    try:
        with open(storage_path, "rb") as fh:
            file_data = fh.read()
    except OSError as exc:
        logger.warning("process_document: cannot read %s: %s", storage_path, exc)
        return 0, False, False

    # --- Extract ---
    result: _ExtractionResult
    try:
        if ext == "pdf":
            result = _extract_pdf(file_data)
        elif ext == "docx":
            result = _extract_docx(file_data)
        elif ext == "txt":
            result = _extract_txt(file_data)
        else:
            logger.warning(
                "process_document: unsupported extension '%s' for document %s", ext, document_id
            )
            return 0, False, False
    except Exception as exc:
        logger.warning("process_document: extraction failed for %s: %s", document_id, exc)
        return 0, False, False

    if not result.chunks:
        logger.info(
            "process_document: no text extracted from %s (has_images=%s)",
            document_id, result.has_images,
        )
        return 0, result.has_images, result.ocr_attempted

    # --- Persist chunks ---
    now = datetime.now(timezone.utc)
    chunk_objects = [
        DocumentChunk(
            id=str(uuid.uuid4()),
            document_id=document_id,
            chunk_index=c.chunk_index,
            text=c.text,
            page_start=c.page_start,
            page_end=c.page_end,
            section_title=c.section_title,
            heading_level=c.heading_level,
            extraction_method=c.extraction_method,
            char_count=len(c.text),
            has_tables=False,
            created_at=now,
        )
        for c in result.chunks
    ]

    db.add_all(chunk_objects)
    # Note: commit is handled by the caller (document_service) after also
    # updating chunk_count / has_images on the UploadedDocument.

    return len(chunk_objects), result.has_images, result.ocr_attempted
