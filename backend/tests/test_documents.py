"""
tests/test_documents.py — Milestone 2: Document Upload API tests

Test IDs:
  D-01  Upload valid PDF
  D-02  Upload valid DOCX
  D-03  Upload valid TXT
  D-04  Upload invalid extension (.exe) → rejected
  D-05  Upload file exceeding size limit → rejected
  D-06  Upload to non-existent project → 404
  D-07  List documents for project → 200
  D-08  List documents for project with no uploads → empty list
  D-09  Delete a document → 204
  D-10  Delete non-existent document → 404
"""
from __future__ import annotations

import io
import uuid
from unittest.mock import patch, MagicMock

import pytest
import pytest_asyncio
from httpx import AsyncClient

# ---------------------------------------------------------------------------
# Minimal test file content
# ---------------------------------------------------------------------------

# A minimal but structurally valid PDF
MINIMAL_PDF = (
    b"%PDF-1.4\n"
    b"1 0 obj\n<< /Type /Catalog >>\nendobj\n"
    b"xref\n0 1\n0000000000 65535 f\n"
    b"trailer\n<< /Size 1 /Root 1 0 R >>\n"
    b"startxref\n9\n%%EOF"
)

# A minimal plain-text file
MINIMAL_TXT = b"Hello, this is a test document."


def make_docx_bytes(text: str = "Test content") -> bytes:
    """Create a minimal valid DOCX using python-docx."""
    from docx import Document
    doc = Document()
    doc.add_paragraph(text)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Autouse mock for python-magic so minimal test files pass MIME validation
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def mock_magic():
    """
    Mock python-magic so minimal test bytes pass MIME validation.
    Default return value is application/pdf; individual tests override as needed.
    """
    mock_mod = MagicMock()
    mock_mod.from_buffer.return_value = "application/pdf"
    with patch("app.services.document_service.magic", mock_mod):
        yield mock_mod


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def create_project(client: AsyncClient) -> str:
    """Create a project and return its id."""
    resp = await client.post(
        "/api/v1/projects/",
        json={
            "title": "Test Project",
            "research_question": "What is the impact of AI?",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def pdf_upload(filename: str = "test.pdf", data: bytes = MINIMAL_PDF):
    return ("files", (filename, data, "application/pdf"))


def txt_upload(filename: str = "test.txt", data: bytes = MINIMAL_TXT):
    return ("files", (filename, data, "text/plain"))


def docx_upload(filename: str = "test.docx", data: bytes | None = None):
    if data is None:
        data = make_docx_bytes()
    return ("files", (filename, data, "application/vnd.openxmlformats-officedocument.wordprocessingml.document"))


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_d01_upload_valid_pdf(async_client: AsyncClient, mock_magic):
    """D-01: Upload a valid PDF → 201, document in uploaded list."""
    mock_magic.from_buffer.return_value = "application/pdf"
    project_id = await create_project(async_client)

    resp = await async_client.post(
        f"/api/v1/projects/{project_id}/documents",
        files=[pdf_upload()],
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert len(body["uploaded"]) == 1
    assert body["rejected"] == []
    doc = body["uploaded"][0]
    assert doc["original_filename"] == "test.pdf"
    assert doc["mime_type"] == "application/pdf"
    # extraction_status is "completed" if text was extracted, "pending" for image-only PDFs
    assert doc["extraction_status"] in ("pending", "completed")
    assert doc["run_id"] is None
    assert doc["project_id"] == project_id


@pytest.mark.asyncio
async def test_d02_upload_valid_docx(async_client: AsyncClient, mock_magic):
    """D-02: Upload a valid DOCX → 201, document in uploaded list."""
    mock_magic.from_buffer.return_value = (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    project_id = await create_project(async_client)

    resp = await async_client.post(
        f"/api/v1/projects/{project_id}/documents",
        files=[docx_upload()],
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert len(body["uploaded"]) == 1
    assert body["rejected"] == []
    doc = body["uploaded"][0]
    assert doc["original_filename"] == "test.docx"
    # DOCX files with paragraphs produce chunks; status is "completed" after M4.1
    assert doc["extraction_status"] in ("pending", "completed")


@pytest.mark.asyncio
async def test_d03_upload_valid_txt(async_client: AsyncClient, mock_magic):
    """D-03: Upload a valid TXT → 201, document in uploaded list."""
    mock_magic.from_buffer.return_value = "text/plain"
    project_id = await create_project(async_client)

    resp = await async_client.post(
        f"/api/v1/projects/{project_id}/documents",
        files=[txt_upload()],
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert len(body["uploaded"]) == 1
    assert body["rejected"] == []
    assert body["uploaded"][0]["original_filename"] == "test.txt"


@pytest.mark.asyncio
async def test_d04_upload_invalid_extension(async_client: AsyncClient, mock_magic):
    """D-04: Upload .exe file → 422 (all files rejected → no valid files)."""
    project_id = await create_project(async_client)

    resp = await async_client.post(
        f"/api/v1/projects/{project_id}/documents",
        files=[("files", ("malware.exe", b"MZ\x90\x00", "application/octet-stream"))],
    )
    assert resp.status_code == 422, resp.text


@pytest.mark.asyncio
async def test_d05_upload_exceeds_size_limit(async_client: AsyncClient, mock_magic):
    """D-05: Upload file exceeding MAX_UPLOAD_SIZE_MB → rejected."""
    mock_magic.from_buffer.return_value = "application/pdf"
    project_id = await create_project(async_client)

    # Patch the size limit to 0 MB so even a tiny file exceeds it
    with patch("app.services.document_service.settings") as mock_settings:
        mock_settings.MAX_UPLOAD_SIZE_MB = 0
        mock_settings.UPLOAD_DIR = "./uploads"

        resp = await async_client.post(
            f"/api/v1/projects/{project_id}/documents",
            files=[pdf_upload()],
        )

    # All rejected → 422
    assert resp.status_code == 422, resp.text


@pytest.mark.asyncio
async def test_d06_upload_to_nonexistent_project(async_client: AsyncClient, mock_magic):
    """D-06: Upload to non-existent project → 404."""
    fake_id = str(uuid.uuid4())
    resp = await async_client.post(
        f"/api/v1/projects/{fake_id}/documents",
        files=[pdf_upload()],
    )
    assert resp.status_code == 404, resp.text


@pytest.mark.asyncio
async def test_d07_list_documents(async_client: AsyncClient, mock_magic):
    """D-07: List documents for project with uploads → 200 with items."""
    mock_magic.from_buffer.return_value = "application/pdf"
    project_id = await create_project(async_client)

    # Upload two files
    await async_client.post(
        f"/api/v1/projects/{project_id}/documents",
        files=[pdf_upload("a.pdf"), pdf_upload("b.pdf", b"%PDF-1.4\n%%EOF")],
    )

    resp = await async_client.get(f"/api/v1/projects/{project_id}/documents")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "items" in body
    assert "total" in body
    assert body["total"] == 2
    assert len(body["items"]) == 2


@pytest.mark.asyncio
async def test_d08_list_documents_empty(async_client: AsyncClient):
    """D-08: List documents for project with no uploads → empty list."""
    project_id = await create_project(async_client)

    resp = await async_client.get(f"/api/v1/projects/{project_id}/documents")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["items"] == []
    assert body["total"] == 0


@pytest.mark.asyncio
async def test_d09_delete_document(async_client: AsyncClient, mock_magic):
    """D-09: Delete a document → 204."""
    mock_magic.from_buffer.return_value = "application/pdf"
    project_id = await create_project(async_client)

    # Upload a file
    upload_resp = await async_client.post(
        f"/api/v1/projects/{project_id}/documents",
        files=[pdf_upload()],
    )
    assert upload_resp.status_code == 201, upload_resp.text
    doc_id = upload_resp.json()["uploaded"][0]["id"]

    # Delete it
    del_resp = await async_client.delete(
        f"/api/v1/projects/{project_id}/documents/{doc_id}"
    )
    assert del_resp.status_code == 204, del_resp.text

    # Confirm it is gone
    list_resp = await async_client.get(f"/api/v1/projects/{project_id}/documents")
    assert list_resp.json()["total"] == 0


@pytest.mark.asyncio
async def test_d10_delete_nonexistent_document(async_client: AsyncClient):
    """D-10: Delete non-existent document → 404."""
    project_id = await create_project(async_client)
    fake_doc_id = str(uuid.uuid4())

    resp = await async_client.delete(
        f"/api/v1/projects/{project_id}/documents/{fake_doc_id}"
    )
    assert resp.status_code == 404, resp.text
