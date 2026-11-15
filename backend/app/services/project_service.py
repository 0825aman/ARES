from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import ResearchProject
from app.schemas.project import (
    ProjectCreateRequest,
    ProjectStatus,
    ProjectSummaryResponse,
    ProjectBriefResponse,
    ProjectUpdateRequest,
)

logger = logging.getLogger(__name__)


class ProjectService:
    async def create_project(
        self, db: AsyncSession, data: ProjectCreateRequest
    ) -> ResearchProject:
        now = datetime.now(timezone.utc)
        project = ResearchProject(
            title=data.title,
            research_question=data.research_question,
            description=data.description,
            category=data.category.value if data.category is not None else None,
            created_at=now,
            updated_at=now,
        )
        db.add(project)
        await db.commit()
        await db.refresh(project)
        return project

    async def get_projects(
        self,
        db: AsyncSession,
        limit: int,
        offset: int,
        status_filter: ProjectStatus | None,
    ) -> tuple[list[ResearchProject], int]:
        base_query = select(ResearchProject)
        count_query = select(func.count()).select_from(ResearchProject)

        if status_filter is not None:
            base_query = base_query.where(ResearchProject.status == status_filter.value)
            count_query = count_query.where(
                ResearchProject.status == status_filter.value
            )

        total_result = await db.execute(count_query)
        total = total_result.scalar_one()

        items_result = await db.execute(
            base_query.order_by(ResearchProject.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        items = list(items_result.scalars().all())
        return items, total

    async def get_project(
        self, db: AsyncSession, project_id: str
    ) -> ResearchProject | None:
        result = await db.execute(
            select(ResearchProject).where(ResearchProject.id == project_id)
        )
        return result.scalar_one_or_none()

    async def update_project(
        self,
        db: AsyncSession,
        project: ResearchProject,
        data: ProjectUpdateRequest,
    ) -> ResearchProject:
        update_data = data.model_dump(exclude_unset=True)
        if update_data:
            for key, value in update_data.items():
                # Store enum values as their string value in the DB
                if hasattr(value, "value"):
                    value = value.value
                setattr(project, key, value)
            project.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(project)
        return project

    async def delete_project(
        self, db: AsyncSession, project: ResearchProject
    ) -> None:
        await db.delete(project)
        await db.commit()

    async def get_summary(self, db: AsyncSession) -> ProjectSummaryResponse:
        # 1. Total count
        total_result = await db.execute(
            select(func.count()).select_from(ResearchProject)
        )
        total = total_result.scalar_one()

        # 2. Count by status (GROUP BY)
        status_result = await db.execute(
            select(ResearchProject.status, func.count()).group_by(ResearchProject.status)
        )
        rows = status_result.all()

        # Start with all statuses at zero, fill from query
        by_status: dict[ProjectStatus, int] = {s: 0 for s in ProjectStatus}
        for row_status, count in rows:
            try:
                key = ProjectStatus(row_status)
                by_status[key] = count
            except ValueError:
                logger.warning("Unknown status value in DB: %s", row_status)

        # 3. Recent projects (up to 5, newest first)
        recent_result = await db.execute(
            select(ResearchProject)
            .order_by(ResearchProject.created_at.desc())
            .limit(5)
        )
        recent_projects_orm = list(recent_result.scalars().all())
        recent_projects = [
            ProjectBriefResponse.model_validate(p) for p in recent_projects_orm
        ]

        return ProjectSummaryResponse(
            total=total,
            by_status=by_status,
            recent_projects=recent_projects,
        )


project_service = ProjectService()
