from __future__ import annotations
import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.run import ResearchRun
from app.schemas.document import (
    DocumentChunkListResponse,
    DocumentChunkResponse,
    DocumentListResponse,
    DocumentResponse,
    DocumentUploadResult,
)
from app.services.chunk_service import get_chunks_for_document
from app.services.document_service import document_service
from app.services.project_service import project_service

logger = logging.getLogger(__name__)
router = APIRouter()


def _validate_uuid(id_str: str, field_name: str) -> str:
    try:
        uuid.UUID(id_str)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=422, detail=f"Invalid UUID format for {field_name}.")
    return id_str


@router.post("/{project_id}/documents", response_model=DocumentUploadResult, status_code=201)
async def upload_documents(
    project_id: str,
    files: Annotated[list[UploadFile], File()],
    db: AsyncSession = Depends(get_db),
) -> DocumentUploadResult:
    _validate_uuid(project_id, "project_id")
    try:
        project = await project_service.get_project(db, project_id)
    except SQLAlchemyError as exc:
        logger.error("DB error in upload_documents: %s", exc)
        raise HTTPException(status_code=500, detail="Internal server error")
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found.")
    if not files:
        raise HTTPException(status_code=422, detail="No files provided.")

    uploaded = []
    rejected = []
    for upload in files[:10]:  # max 10 files
        try:
            data = await upload.read()
            doc, error = await document_service.validate_and_store(
                db, project_id, upload.filename or "unnamed", data
            )
            if doc:
                uploaded.append(DocumentResponse.model_validate(doc))
            else:
                rejected.append({"filename": upload.filename or "unnamed", "reason": error})
        except SQLAlchemyError as exc:
            logger.error("DB error storing file: %s", exc)
            rejected.append({"filename": upload.filename or "unnamed", "reason": "Storage error."})
        except Exception as exc:
            logger.error("Error processing file %s: %s", upload.filename, exc)
            rejected.append({"filename": upload.filename or "unnamed", "reason": "Processing error."})

    if not uploaded and rejected:
        raise HTTPException(status_code=422, detail="No valid files in request.")

    return DocumentUploadResult(uploaded=uploaded, rejected=rejected)


@router.get("/{project_id}/documents", response_model=DocumentListResponse)
async def list_documents(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> DocumentListResponse:
    _validate_uuid(project_id, "project_id")
    try:
        project = await project_service.get_project(db, project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found.")
        items, total = await document_service.list_documents(db, project_id)
    except HTTPException:
        raise
    except SQLAlchemyError as exc:
        logger.error("DB error in list_documents: %s", exc)
        raise HTTPException(status_code=500, detail="Internal server error")
    return DocumentListResponse(
        items=[DocumentResponse.model_validate(d) for d in items],
        total=total,
    )


@router.get("/{project_id}/documents/{document_id}/chunks", response_model=DocumentChunkListResponse)
async def list_document_chunks(
    project_id: str,
    document_id: str,
    offset: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
) -> DocumentChunkListResponse:
    """Return paginated chunks for a specific document."""
    _validate_uuid(project_id, "project_id")
    _validate_uuid(document_id, "document_id")
    try:
        doc = await document_service.get_document(db, document_id)
        if doc is None or doc.project_id != project_id:
            raise HTTPException(status_code=404, detail="Document not found.")
        items, total = await get_chunks_for_document(db, document_id, offset=offset, limit=limit)
    except HTTPException:
        raise
    except SQLAlchemyError as exc:
        logger.error("DB error in list_document_chunks: %s", exc)
        raise HTTPException(status_code=500, detail="Internal server error")
    return DocumentChunkListResponse(
        items=[DocumentChunkResponse.model_validate(c) for c in items],
        total=total,
        document_id=document_id,
    )


@router.delete("/{project_id}/documents/{document_id}", status_code=204)
async def delete_document(
    project_id: str,
    document_id: str,
    db: AsyncSession = Depends(get_db),
):
    _validate_uuid(project_id, "project_id")
    _validate_uuid(document_id, "document_id")
    try:
        doc = await document_service.get_document(db, document_id)
        if doc is None or doc.project_id != project_id:
            raise HTTPException(status_code=404, detail="Document not found.")
        # Block delete if attached to a running run
        if doc.run_id:
            from sqlalchemy import select
            run_result = await db.execute(
                select(ResearchRun).where(
                    ResearchRun.id == doc.run_id,
                    ResearchRun.status == "running"
                )
            )
            if run_result.scalar_one_or_none():
                raise HTTPException(
                    status_code=409,
                    detail="Cannot delete a document attached to a running research run."
                )
        await document_service.delete_document(db, doc)
    except HTTPException:
        raise
    except SQLAlchemyError as exc:
        logger.error("DB error in delete_document: %s", exc)
        raise HTTPException(status_code=500, detail="Internal server error")
