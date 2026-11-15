from __future__ import annotations
import json
import logging
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.run import StartRunRequest, RunResponse, RunListResponse
from app.schemas.report import ReportResponse
from app.schemas.plan import ResearchPlanResponse, ResearchTaskResponse
from app.schemas.agent import AgentActivityResponse, AgentEventResponse
from app.services.run_service import run_service
from app.services.project_service import project_service
from app.services.document_service import document_service
from app.services.research_workflow import run_research_workflow
from app.models.report import ResearchReport
from app.core.content_sanitizer import sanitize_research_question
from app.guardrails.service import guardrails_service

logger = logging.getLogger(__name__)
router = APIRouter()


def _validate_uuid(id_str: str, field_name: str) -> str:
    try:
        uuid.UUID(id_str)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=422, detail=f"Invalid UUID format for {field_name}.")
    return id_str


@router.post("/{project_id}/runs", response_model=RunResponse, status_code=201)
async def start_run(
    project_id: str,
    body: StartRunRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> RunResponse:
    _validate_uuid(project_id, "project_id")

    # Validate project exists
    try:
        project = await project_service.get_project(db, project_id)
    except SQLAlchemyError as exc:
        logger.error("DB error in start_run: %s", exc)
        raise HTTPException(status_code=500, detail="Internal server error")
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found.")

    # Validate document_ids belong to this project
    if body.use_documents and body.document_ids:
        for doc_id in body.document_ids:
            doc = await document_service.get_document(db, doc_id)
            if doc is None or doc.project_id != project_id:
                raise HTTPException(
                    status_code=422,
                    detail=f"Document {doc_id} not found or does not belong to this project."
                )

    # Validate and sanitize research question through Input Guardrails
    validation = guardrails_service.validate_input(body.research_question, mask_pii=True)
    if not validation.is_valid:
        raise HTTPException(
            status_code=422,
            detail=f"Input guardrail violation: {'; '.join(validation.violations)}"
        )
    sanitized_question = validation.sanitized_text
    if not sanitized_question:
        raise HTTPException(
            status_code=422,
            detail="Research question is empty or invalid after sanitization."
        )

    # Create the run record
    try:
        run = await run_service.create_run(
            db=db,
            project_id=project_id,
            research_question=sanitized_question,
            use_web=body.use_web,
            use_documents=body.use_documents,
            document_ids=body.document_ids,
            workflow_mode=body.workflow_mode,
            verification_depth=body.verification_depth,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except SQLAlchemyError as exc:
        logger.error("DB error creating run: %s", exc)
        raise HTTPException(status_code=500, detail="Internal server error")

    # Start the appropriate workflow in the background
    if body.workflow_mode == "multi_agent":
        from app.graph.executor import run_multi_agent_workflow
        background_tasks.add_task(run_multi_agent_workflow, run.id)
    else:
        background_tasks.add_task(run_research_workflow, run.id)

    return RunResponse.model_validate(run)


@router.get("/{project_id}/runs", response_model=RunListResponse)
async def list_runs(
    project_id: str,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> RunListResponse:
    _validate_uuid(project_id, "project_id")
    try:
        project = await project_service.get_project(db, project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found.")
        items, total = await run_service.list_runs(db, project_id, limit, offset)
    except HTTPException:
        raise
    except SQLAlchemyError as exc:
        logger.error("DB error in list_runs: %s", exc)
        raise HTTPException(status_code=500, detail="Internal server error")
    return RunListResponse(
        items=[RunResponse.model_validate(r) for r in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{project_id}/runs/{run_id}", response_model=RunResponse)
async def get_run(
    project_id: str,
    run_id: str,
    db: AsyncSession = Depends(get_db),
) -> RunResponse:
    _validate_uuid(project_id, "project_id")
    _validate_uuid(run_id, "run_id")
    try:
        run = await run_service.get_run(db, run_id)
        if run is None or run.project_id != project_id:
            raise HTTPException(status_code=404, detail="Run not found.")
    except HTTPException:
        raise
    except SQLAlchemyError as exc:
        logger.error("DB error in get_run: %s", exc)
        raise HTTPException(status_code=500, detail="Internal server error")
    return RunResponse.model_validate(run)


@router.get("/{project_id}/runs/{run_id}/report", response_model=ReportResponse)
async def get_report(
    project_id: str,
    run_id: str,
    db: AsyncSession = Depends(get_db),
) -> ReportResponse:
    _validate_uuid(project_id, "project_id")
    _validate_uuid(run_id, "run_id")
    try:
        run = await run_service.get_run(db, run_id)
        if run is None or run.project_id != project_id:
            raise HTTPException(status_code=404, detail="Run not found.")
        if run.status != "completed":
            raise HTTPException(
                status_code=404,
                detail="Report not available. Run has not completed successfully."
            )
        from sqlalchemy import select
        report_result = await db.execute(
            select(ResearchReport).where(ResearchReport.run_id == run_id)
        )
        report = report_result.scalar_one_or_none()
        if report is None:
            raise HTTPException(status_code=404, detail="Report not found.")
    except HTTPException:
        raise
    except SQLAlchemyError as exc:
        logger.error("DB error in get_report: %s", exc)
        raise HTTPException(status_code=500, detail="Internal server error")
    return ReportResponse.model_validate(report)


# ── Phase 3 endpoints ──────────────────────────────────────────────────────────

@router.get("/{project_id}/runs/{run_id}/plan", response_model=ResearchPlanResponse)
async def get_plan(
    project_id: str,
    run_id: str,
    db: AsyncSession = Depends(get_db),
) -> ResearchPlanResponse:
    """Return the latest research plan for a multi-agent run."""
    _validate_uuid(project_id, "project_id")
    _validate_uuid(run_id, "run_id")

    try:
        run = await run_service.get_run(db, run_id)
        if run is None or run.project_id != project_id:
            raise HTTPException(status_code=404, detail="Run not found.")

        from app.services.plan_service import get_latest_plan
        plan = await get_latest_plan(db, run_id)
        if plan is None:
            raise HTTPException(
                status_code=404,
                detail="No research plan found for this run."
            )

        # Load tasks via relationship
        from app.services.plan_service import get_tasks
        tasks = await get_tasks(db, run_id)

        task_responses = []
        for t in tasks:
            unanswered = []
            if t.unanswered_questions:
                try:
                    unanswered = json.loads(t.unanswered_questions)
                except (json.JSONDecodeError, TypeError):
                    unanswered = []
            task_responses.append(ResearchTaskResponse(
                id=t.id,
                objective=t.objective,
                search_query=t.search_query,
                expected_evidence_type=t.expected_evidence_type,
                priority=t.priority,
                status=t.status,
                findings=t.findings,
                evidence_count=t.evidence_count,
                unanswered_questions=unanswered,
                limitations=t.limitations,
                error_message=t.error_message,
                started_at=t.started_at,
                completed_at=t.completed_at,
                created_at=t.created_at,
            ))

        objectives = []
        if plan.objectives:
            try:
                objectives = json.loads(plan.objectives)
            except (json.JSONDecodeError, TypeError):
                objectives = []

        return ResearchPlanResponse(
            id=plan.id,
            run_id=plan.run_id,
            objectives=objectives,
            tasks=task_responses,
            plan_version=plan.plan_version,
            created_at=plan.created_at,
            updated_at=plan.updated_at,
        )

    except HTTPException:
        raise
    except SQLAlchemyError as exc:
        logger.error("DB error in get_plan: %s", exc)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{project_id}/runs/{run_id}/tasks")
async def get_tasks_endpoint(
    project_id: str,
    run_id: str,
    status: str | None = Query(None, description="Filter by task status"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return all research tasks for a run."""
    _validate_uuid(project_id, "project_id")
    _validate_uuid(run_id, "run_id")

    try:
        run = await run_service.get_run(db, run_id)
        if run is None or run.project_id != project_id:
            raise HTTPException(status_code=404, detail="Run not found.")

        from app.services.plan_service import get_tasks
        tasks = await get_tasks(db, run_id)

        if status:
            tasks = [t for t in tasks if t.status == status]

        task_responses = []
        for t in tasks:
            unanswered = []
            if t.unanswered_questions:
                try:
                    unanswered = json.loads(t.unanswered_questions)
                except (json.JSONDecodeError, TypeError):
                    unanswered = []
            task_responses.append(ResearchTaskResponse(
                id=t.id,
                objective=t.objective,
                search_query=t.search_query,
                expected_evidence_type=t.expected_evidence_type,
                priority=t.priority,
                status=t.status,
                findings=t.findings,
                evidence_count=t.evidence_count,
                unanswered_questions=unanswered,
                limitations=t.limitations,
                error_message=t.error_message,
                started_at=t.started_at,
                completed_at=t.completed_at,
                created_at=t.created_at,
            ))

        return {"items": [t.model_dump() for t in task_responses], "total": len(task_responses)}

    except HTTPException:
        raise
    except SQLAlchemyError as exc:
        logger.error("DB error in get_tasks: %s", exc)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{project_id}/runs/{run_id}/activity", response_model=AgentActivityResponse)
async def get_activity(
    project_id: str,
    run_id: str,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> AgentActivityResponse:
    """Return agent execution events for a run (execution timeline)."""
    _validate_uuid(project_id, "project_id")
    _validate_uuid(run_id, "run_id")

    try:
        run = await run_service.get_run(db, run_id)
        if run is None or run.project_id != project_id:
            raise HTTPException(status_code=404, detail="Run not found.")

        from app.services.event_service import get_events, count_events
        events = await get_events(db, run_id, limit=limit, offset=offset)
        total = await count_events(db, run_id)

        return AgentActivityResponse(
            run_id=run_id,
            events=[AgentEventResponse.model_validate(e) for e in events],
            total=total,
        )

    except HTTPException:
        raise
    except SQLAlchemyError as exc:
        logger.error("DB error in get_activity: %s", exc)
        raise HTTPException(status_code=500, detail="Internal server error")
