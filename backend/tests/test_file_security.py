"""test_file_security.py — Tests for file upload security, magic byte validation, and storage paths."""
import pytest
from app.services.document_service import document_service


@pytest.mark.asyncio
async def test_pdf_magic_byte_validation_success(db_session):
    project_id = "test-proj-0001"
    valid_pdf_bytes = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n1 0 obj\n<<\n>>\nendobj\ntrailer\n<<\n>>\n%%EOF"
    doc, err = await document_service.validate_and_store(
        db_session, project_id, "test_doc.pdf", valid_pdf_bytes
    )
    assert err is None
    assert doc is not None
    assert doc.original_filename == "test_doc.pdf"
    # Ensure stored filename is a UUID-based name
    assert doc.stored_filename.endswith(".pdf")
    assert doc.stored_filename != "test_doc.pdf"


@pytest.mark.asyncio
async def test_pdf_magic_byte_validation_failure_on_fake_pdf(db_session):
    project_id = "test-proj-0002"
    # PNG bytes disguised as .pdf
    fake_pdf_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
    doc, err = await document_service.validate_and_store(
        db_session, project_id, "malicious.pdf", fake_pdf_bytes
    )
    assert doc is None
    assert "File content does not match" in err


@pytest.mark.asyncio
async def test_docx_magic_byte_validation_failure_on_fake_docx(db_session):
    project_id = "test-proj-0003"
    fake_docx_bytes = b"NOT_A_ZIP_OR_DOCX_FILE_HEADER"
    doc, err = await document_service.validate_and_store(
        db_session, project_id, "malicious.docx", fake_docx_bytes
    )
    assert doc is None
    assert "File content does not match" in err


@pytest.mark.asyncio
async def test_path_traversal_filename_sanitized(db_session):
    project_id = "test-proj-0004"
    valid_pdf_bytes = b"%PDF-1.4\nvalid minimal pdf content%%EOF"
    traversal_name = "../../../etc/evil.pdf"
    doc, err = await document_service.validate_and_store(
        db_session, project_id, traversal_name, valid_pdf_bytes
    )
    assert err is None
    assert doc is not None
    assert doc.original_filename == "evil.pdf"
    assert ".." not in doc.storage_path
