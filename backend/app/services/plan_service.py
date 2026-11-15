"""plan_service — CRUD for ResearchPlan and ResearchTask ORM rows.

All functions are async and accept an open SQLAlchemy AsyncSession.
They do not open their own sessions — callers are responsible for
transaction management (commit/rollback).
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.plan import ResearchPlan as ResearchPlanORM
from app.models.task import ResearchTask as ResearchTaskORM
from app.schemas.plan import ResearchPlan, ResearchTask

logger = logging.getLogger(__name__)


async def save_plan(
    db: AsyncSession,
    run_id: str,
    plan: ResearchPlan,
) -> ResearchPlanORM:
    """Persist a ResearchPlan and all its tasks to the database.

    If a plan already exists for this run, ``plan_version`` is incremented.
    Returns the newly created ORM instance (not committed — caller commits).
    """
    # Determine next plan_version
    result = await db.execute(
        select(ResearchPlanORM)
        .where(ResearchPlanORM.run_id == run_id)
        .order_by(ResearchPlanORM.plan_version.desc())
    )
    latest = result.scalars().first()
    next_version = (latest.plan_version + 1) if latest else 1

    # Ensure plan_id is unique and valid
    if not plan.plan_id:
        plan.plan_id = str(uuid.uuid4())
    else:
        existing_plan = await db.execute(select(ResearchPlanORM.id).where(ResearchPlanORM.id == plan.plan_id))
        if existing_plan.scalar_one_or_none():
            plan.plan_id = str(uuid.uuid4())

    plan_row = ResearchPlanORM(
        id=plan.plan_id,
        run_id=run_id,
        objectives=json.dumps(plan.objectives),
        refinement_notes=plan.refinement_notes,
        plan_version=next_version,
    )
    db.add(plan_row)
    # Flush to get the plan_row.id available for tasks FK
    await db.flush()

    for order, task in enumerate(plan.tasks):
        if not task.task_id:
            task.task_id = str(uuid.uuid4())
        else:
            existing_task = await db.execute(select(ResearchTaskORM.id).where(ResearchTaskORM.id == task.task_id))
            if existing_task.scalar_one_or_none():
                task.task_id = str(uuid.uuid4())

        task_row = ResearchTaskORM(
            id=task.task_id,
            plan_id=plan.plan_id,
            run_id=run_id,
            task_order=order,
            objective=task.objective,
            search_query=task.search_query,
            expected_evidence_type=task.expected_evidence_type,
            priority=task.priority,
            status="pending",
        )
        db.add(task_row)

    logger.info(
        "plan_service: saved plan %s (v%d) with %d tasks for run %s",
        plan.plan_id,
        next_version,
        len(plan.tasks),
        run_id,
    )
    return plan_row


async def get_latest_plan(
    db: AsyncSession,
    run_id: str,
) -> ResearchPlanORM | None:
    """Return the highest-version plan for a run, or None if no plan exists."""
    result = await db.execute(
        select(ResearchPlanORM)
        .where(ResearchPlanORM.run_id == run_id)
        .order_by(ResearchPlanORM.plan_version.desc())
    )
    return result.scalars().first()


async def get_tasks(
    db: AsyncSession,
    run_id: str,
) -> list[ResearchTaskORM]:
    """Return all tasks for a run ordered by task_order (ascending)."""
    result = await db.execute(
        select(ResearchTaskORM)
        .where(ResearchTaskORM.run_id == run_id)
        .order_by(ResearchTaskORM.task_order)
    )
    return list(result.scalars().all())


async def update_task_status(
    db: AsyncSession,
    task_id: str,
    status: str,
    *,
    findings: str | None = None,
    evidence_count: int | None = None,
    unanswered_questions: list[str] | None = None,
    limitations: str | None = None,
    error_message: str | None = None,
) -> None:
    """Update a ResearchTask's status and optional result fields.

    Fields that are None are left unchanged.
    Caller must commit after calling this function.
    """
    result = await db.execute(
        select(ResearchTaskORM).where(ResearchTaskORM.id == task_id)
    )
    task = result.scalar_one_or_none()
    if task is None:
        logger.warning("update_task_status: task %s not found", task_id)
        return

    task.status = status

    if status == "running" and task.started_at is None:
        task.started_at = datetime.now(timezone.utc)

    if status in ("completed", "partial", "failed", "fatal_error"):
        task.completed_at = datetime.now(timezone.utc)

    if findings is not None:
        task.findings = findings
    if evidence_count is not None:
        task.evidence_count = evidence_count
    if unanswered_questions is not None:
        task.unanswered_questions = json.dumps(unanswered_questions)
    if limitations is not None:
        task.limitations = limitations
    if error_message is not None:
        task.error_message = error_message

    logger.debug("update_task_status: task %s → %s", task_id, status)
