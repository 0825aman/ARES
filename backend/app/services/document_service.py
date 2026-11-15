import hashlib
import logging
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.services.document_processor import process_document
from app.core.content_sanitizer import sanitize_filename as secure_sanitize_filename

try:
    import magic  # type: ignore[import-untyped]
except Exception:  # pragma: no cover
    magic = None  # type: ignore[assignment]

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.document import UploadedDocument
from app.models.run import ResearchRun

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}
ALLOWED_MIME_TYPES = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".txt": "text/plain",
}


MAGIC_BYTES = {
    ".pdf": b"%PDF",
    ".docx": b"PK\x03\x04",
}


def _sanitize_filename(name: str) -> str:
    """Lowercase, replace non-alphanumeric (except dot) with underscore, max 100 chars."""
    name = name.lower()
    name = re.sub(r"[^\w.]", "_", name)
    return name[:100]


def _compute_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _detect_mime(data: bytes, extension: str) -> tuple[bool, str]:
    """Detect MIME type from file bytes. Returns (is_valid, detected_mime)."""
    try:
        if magic is None:
            raise ImportError("magic not available")
        detected = magic.from_buffer(data, mime=True)
        expected = ALLOWED_MIME_TYPES.get(extension, "")
        # For text/plain, also accept text/x-* variants
        if extension == ".txt":
            return detected.startswith("text/"), detected
        return detected == expected, detected
    except Exception:
        # If magic fails, fall back to extension-based check
        logger.warning("python-magic detection failed, falling back to extension check")
        return extension in ALLOWED_EXTENSIONS, ALLOWED_MIME_TYPES.get(extension, "unknown")


class DocumentService:
    async def validate_and_store(
        self,
        db: AsyncSession,
        project_id: str,
        filename: str,
        file_data: bytes,
    ) -> tuple[UploadedDocument | None, str | None]:
        """
        Validate and store a file. Returns (document, None) on success or (None, error_reason) on rejection.
        run_id is set to None — it will be associated with a run at submission time.
        """
        ext = Path(filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            return None, f"Unsupported file type '{ext}'. Accepted: pdf, docx, txt."

        max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        if len(file_data) > max_bytes:
            return None, f"File exceeds {settings.MAX_UPLOAD_SIZE_MB} MB size limit."

        # Magic byte validation for binary formats
        if ext in MAGIC_BYTES:
            magic_prefix = MAGIC_BYTES[ext]
            if not file_data.startswith(magic_prefix):
                return None, f"File content does not match expected format for '{ext}'."

        is_valid_mime, detected_mime = _detect_mime(file_data[:4096], ext)
        if not is_valid_mime:
            return None, f"File content does not match extension '{ext}' (detected: {detected_mime})."

        clean_filename = secure_sanitize_filename(filename)
        content_hash = _compute_hash(file_data)

        # Check for existing file with same hash for this project
        existing_result = await db.execute(
            select(UploadedDocument)
            .where(UploadedDocument.project_id == project_id)
            .where(UploadedDocument.content_hash == content_hash)
            .limit(1)
        )
        existing = existing_result.scalar_one_or_none()

        if existing:
            # Reuse existing storage path — create a new DB record pointing to same file
            doc_id = str(uuid.uuid4())
            doc = UploadedDocument(
                id=doc_id,
                run_id=None,
                project_id=project_id,
                original_filename=clean_filename,
                stored_filename=existing.stored_filename,
                storage_path=existing.storage_path,
                mime_type=existing.mime_type,
                file_size_bytes=len(file_data),
                content_hash=content_hash,
                extraction_status="pending",
                uploaded_at=datetime.now(timezone.utc),
            )
        else:
            # Write new file to disk using UUID filename
            doc_id = str(uuid.uuid4())
            stored_filename = f"{uuid.uuid4()}{ext}"
            project_dir = Path(settings.UPLOAD_DIR) / project_id
            project_dir.mkdir(parents=True, exist_ok=True)
            storage_path = str(project_dir / stored_filename)

            with open(storage_path, "wb") as f:
                f.write(file_data)

            doc = UploadedDocument(
                id=doc_id,
                run_id=None,
                project_id=project_id,
                original_filename=clean_filename,
                stored_filename=stored_filename,
                storage_path=storage_path,
                mime_type=detected_mime,
                file_size_bytes=len(file_data),
                content_hash=content_hash,
                extraction_status="pending",
                uploaded_at=datetime.now(timezone.utc),
            )

        db.add(doc)
        await db.flush()  # Assigns doc.id before chunking

        # --- Phase 4 M4.1: Extract and persist chunks ---
        chunk_count, has_images, ocr_attempted = await process_document(
            db,
            document_id=doc.id,
            storage_path=doc.storage_path,
            original_filename=doc.original_filename,
        )
        doc.chunk_count = chunk_count
        doc.has_images = has_images
        doc.ocr_attempted = ocr_attempted
        doc.extraction_status = "completed" if (chunk_count > 0 or has_images) else "pending"

        await db.commit()
        await db.refresh(doc)
        return doc, None

    async def list_documents(
        self, db: AsyncSession, project_id: str
    ) -> tuple[list[UploadedDocument], int]:
        result = await db.execute(
            select(UploadedDocument)
            .where(UploadedDocument.project_id == project_id)
            .order_by(UploadedDocument.uploaded_at.desc())
        )
        items = list(result.scalars().all())
        return items, len(items)

    async def get_document(
        self, db: AsyncSession, document_id: str
    ) -> UploadedDocument | None:
        result = await db.execute(
            select(UploadedDocument).where(UploadedDocument.id == document_id)
        )
        return result.scalar_one_or_none()

    async def delete_document(
        self, db: AsyncSession, doc: UploadedDocument
    ) -> None:
        """Delete document record and file from disk."""
        # Delete from disk if file exists and no other document shares it
        storage_path = doc.storage_path
        other = await db.execute(
            select(UploadedDocument)
            .where(UploadedDocument.storage_path == storage_path)
            .where(UploadedDocument.id != doc.id)
            .limit(1)
        )
        if other.scalar_one_or_none() is None:
            try:
                os.remove(storage_path)
            except FileNotFoundError:
                pass

        await db.delete(doc)
        await db.commit()


document_service = DocumentService()
