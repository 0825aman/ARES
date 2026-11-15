"""phase6_migration_k_composite_indexes

Revision ID: k1l2m3n4o5p6
Revises: j0e1f2a3b4c5
Create Date: 2026-11-14 10:30:00.000000

Phase 6 Migration K — M6.3 Database Optimization:
  - Add composite index (project_id, status) on research_runs
    for dashboard queries that filter by project AND status together.
  - Add composite index (run_id, created_at) on agent_execution_events
    for activity-feed queries that ORDER BY created_at within a run.
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'k1l2m3n4o5p6'
down_revision: Union[str, None] = 'j0e1f2a3b4c5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "idx_runs_project_status",
        "research_runs",
        ["project_id", "status"],
    )
    op.create_index(
        "idx_events_run_created",
        "agent_execution_events",
        ["run_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("idx_events_run_created", table_name="agent_execution_events")
    op.drop_index("idx_runs_project_status", table_name="research_runs")
