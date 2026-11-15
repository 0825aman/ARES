"""Export and Report Versioning API — Phase 5 M5.6.

Endpoints (all under /projects/{project_id}/runs/{run_id}/):
  POST export                        — trigger a new export
  GET  exports                       — list all exports for a run
  GET  export/{export_id}/download   — download an export file
  GET  reports                       — list all report versions for a run
"""
from __future__ import annotations

import logging
import os
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Path, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.export_service import (
    MIME_TYPES,
    get_abs_file_path,
    get_export_record,
    list_exports,
    trigger_export,
)
from app.services.report_versioning_service import list_report_versions

logger = logging.getLogger(__name__)

router = APIRouter()


# ── Schemas ────────────────────────────────────────────────────────────────────

class ExportRequest(BaseModel):
    format: str = Field(..., description="pdf | docx | markdown")
    report_id: Optional[str] = Field(
        None,
        description="Specific report version to export. Defaults to the current version.",
    )


class ExportRecordResponse(BaseModel):
    id: str
    run_id: str
    report_id: str
    format: str
    status: str
    file_size_bytes: Optional[int]
    error_message: Optional[str]
    created_at: str
    completed_at: Optional[str]
    download_url: Optional[str]


class ExportListResponse(BaseModel):
    items: list[ExportRecordResponse]
    total: int


class ReportVersionResponse(BaseModel):
    id: str
    run_id: str
    version_number: int
    is_current: bool
    research_question: str
    executive_summary: str
    key_findings: str          # raw JSON text
    observations: Optional[str]
    contradictions: Optional[str]
    limitations: str
    sources: str               # raw JSON text
    has_validated_citations: bool
    review_status: Optional[str]
    generated_at: str


class ReportVersionListResponse(BaseModel):
    items: list[ReportVersionResponse]
    total: int


# ── Helpers ────────────────────────────────────────────────────────────────────

def _download_url(project_id: str, run_id: str, export_id: str) -> str:
    return f"/api/v1/projects/{project_id}/runs/{run_id}/export/{export_id}/download"


def _serialize_export(export, project_id: str) -> ExportRecordResponse:
    return ExportRecordResponse(
        id=export.id,
        run_id=export.run_id,
        report_id=export.report_id,
        format=export.format,
        status=export.status,
        file_size_bytes=export.file_size_bytes,
        error_message=export.error_message,
        created_at=export.created_at.isoformat(),
        completed_at=export.completed_at.isoformat() if export.completed_at else None,
        download_url=(
            _download_url(project_id, export.run_id, export.id)
            if export.status == "ready"
            else None
        ),
    )


def _serialize_report_version(report) -> ReportVersionResponse:
    return ReportVersionResponse(
        id=report.id,
        run_id=report.run_id,
        version_number=getattr(report, "version_number", 1),
        is_current=getattr(report, "is_current", True),
        research_question=report.research_question,
        executive_summary=report.executive_summary,
        key_findings=report.key_findings,
        observations=report.observations,
        contradictions=report.contradictions,
        limitations=report.limitations,
        sources=report.sources,
        has_validated_citations=report.has_validated_citations,
        review_status=report.review_status,
        generated_at=report.generated_at.isoformat(),
    )


# ── Routes ─────────────────────────────────────────────────────────────────────

@router.post(
    "/{project_id}/runs/{run_id}/export",
    response_model=ExportRecordResponse,
    summary="Trigger a new report export",
    tags=["exports"],
)
async def create_export(
    body: ExportRequest,
    project_id: str = Path(...),
    run_id: str = Path(...),
    db: AsyncSession = Depends(get_db),
) -> ExportRecordResponse:
    """Generate a downloadable report file synchronously.

    Returns immediately with the export record (status=ready on success).
    """
    try:
        export = await trigger_export(
            db,
            run_id=run_id,
            report_id=body.report_id,
            format=body.format,
        )
        await db.commit()
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )
    except Exception as exc:
        logger.error("create_export: unexpected error for run %s: %s", run_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Export generation failed.",
        )

    if export.status == "failed":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=export.error_message or "Export generation failed.",
        )

    return _serialize_export(export, project_id)


@router.get(
    "/{project_id}/runs/{run_id}/exports",
    response_model=ExportListResponse,
    summary="List all exports for a run",
    tags=["exports"],
)
async def list_run_exports(
    project_id: str = Path(...),
    run_id: str = Path(...),
    db: AsyncSession = Depends(get_db),
) -> ExportListResponse:
    """Return all export records for the run, newest first."""
    exports = await list_exports(db, run_id=run_id)
    return ExportListResponse(
        items=[_serialize_export(e, project_id) for e in exports],
        total=len(exports),
    )


@router.get(
    "/{project_id}/runs/{run_id}/export/{export_id}/download",
    summary="Download an export file",
    tags=["exports"],
)
async def download_export(
    project_id: str = Path(...),
    run_id: str = Path(...),
    export_id: str = Path(...),
    db: AsyncSession = Depends(get_db),
):
    """Return the binary export file for download."""
    export = await get_export_record(db, export_id=export_id, run_id=run_id)
    if export is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Export {export_id} not found for run {run_id}",
        )

    if export.status != "ready":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Export is not ready (status={export.status})",
        )

    abs_path = get_abs_file_path(export)
    if not os.path.exists(abs_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Export file not found on disk.",
        )

    mime = MIME_TYPES.get(export.format, "application/octet-stream")
    ext = {"pdf": "pdf", "docx": "docx", "markdown": "md"}.get(export.format, "bin")
    filename = f"research_report.{ext}"

    return FileResponse(
        path=abs_path,
        media_type=mime,
        filename=filename,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "/{project_id}/runs/{run_id}/reports",
    response_model=ReportVersionListResponse,
    summary="List all report versions for a run",
    tags=["exports"],
)
async def list_run_reports(
    project_id: str = Path(...),
    run_id: str = Path(...),
    db: AsyncSession = Depends(get_db),
) -> ReportVersionListResponse:
    """Return all report versions for the run, newest first."""
    reports = await list_report_versions(db, run_id=run_id)
    return ReportVersionListResponse(
        items=[_serialize_report_version(r) for r in reports],
        total=len(reports),
    )
