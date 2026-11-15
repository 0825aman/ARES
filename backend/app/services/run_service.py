from __future__ import annotations
import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.run import ResearchRun
from app.models.document import UploadedDocument
from app.core.metrics import metrics

logger = logging.getLogger(__name__)

TERMINAL_STATUSES = {"completed", "failed"}


class RunService:
    async def create_run(
        self,
        db: AsyncSession,
        project_id: str,
        research_question: str,
        use_web: bool,
        use_documents: bool,
        document_ids: list[str],
        workflow_mode: str = "sequential",
        verification_depth: str = "basic",
    ) -> ResearchRun:
        """Create a run record. Validates source selection and duplicate-run guard."""
        # Validate source selection
        if not use_web and not use_documents:
            raise ValueError("At least one information source must be selected.")
        if use_documents and not document_ids:
            raise ValueError("Document IDs required when use_documents is True.")

        # Check for active run
        active_result = await db.execute(
            select(ResearchRun).where(
                ResearchRun.project_id == project_id,
                ResearchRun.status == "running",
            )
        )
        if active_result.scalar_one_or_none():
            raise RuntimeError("A research run is already active for this project.")

        run = ResearchRun(
            id=str(uuid.uuid4()),
            project_id=project_id,
            research_question=research_question,
            use_web=use_web,
            use_documents=use_documents,
            workflow_mode=workflow_mode,
            verification_depth=verification_depth,
            status="pending",
            created_at=datetime.now(timezone.utc),
        )
        db.add(run)
        await db.commit()
        await db.refresh(run)

        # Associate documents with this run
        if document_ids:
            docs_result = await db.execute(
                select(UploadedDocument).where(
                    UploadedDocument.id.in_(document_ids),
                    UploadedDocument.project_id == project_id,
                )
            )
            docs = docs_result.scalars().all()
            for doc in docs:
                doc.run_id = run.id
            await db.commit()

        return run

    async def get_run(self, db: AsyncSession, run_id: str) -> ResearchRun | None:
        result = await db.execute(
            select(ResearchRun).where(ResearchRun.id == run_id)
        )
        return result.scalar_one_or_none()

    async def list_runs(
        self, db: AsyncSession, project_id: str, limit: int = 20, offset: int = 0
    ) -> tuple[list[ResearchRun], int]:
        total_result = await db.execute(
            select(func.count()).select_from(ResearchRun).where(ResearchRun.project_id == project_id)
        )
        total = total_result.scalar_one()
        items_result = await db.execute(
            select(ResearchRun)
            .where(ResearchRun.project_id == project_id)
            .order_by(ResearchRun.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(items_result.scalars().all()), total

    async def update_status(
        self,
        db: AsyncSession,
        run: ResearchRun,
        status: str,
        stage: str | None = None,
        error_message: str | None = None,
    ) -> None:
        if run.status in TERMINAL_STATUSES:
            logger.warning("Attempted to update terminal run %s (status=%s)", run.id, run.status)
            return
        run.status = status
        if stage is not None:
            run.current_stage = stage
        if error_message is not None:
            run.error_message = error_message
        if status == "running" and run.started_at is None:
            run.started_at = datetime.now(timezone.utc)
            metrics.increment("runs_started")
        if status in TERMINAL_STATUSES:
            run.completed_at = datetime.now(timezone.utc)
            if status == "completed":
                metrics.increment("runs_completed")
            elif status == "failed":
                metrics.increment("runs_failed")
        await db.commit()

        # Phase 5 M5.1 — publish run_status_changed to SSE subscribers
        from app.services.sse_manager import sse_manager
        from datetime import datetime as _dt

        sse_data: dict = {
            "run_id": run.id,
            "status": run.status,
            "current_stage": run.current_stage,
            "changed_at": _dt.now(timezone.utc).isoformat(),
        }
        if status == "completed":
            await sse_manager.publish(run.id, "run_completed", {
                "run_id": run.id,
                "status": "completed",
                "completed_at": run.completed_at.isoformat() if run.completed_at else None,
            })
        elif status == "failed":
            await sse_manager.publish(run.id, "run_failed", {
                "run_id": run.id,
                "status": "failed",
                "error": run.error_message,
                "failed_at": run.completed_at.isoformat() if run.completed_at else None,
            })
        else:
            await sse_manager.publish(run.id, "run_status_changed", sse_data)


run_service = RunService()
