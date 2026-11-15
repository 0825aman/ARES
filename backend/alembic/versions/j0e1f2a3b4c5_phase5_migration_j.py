"""phase5_migration_j_export_records

Revision ID: j0e1f2a3b4c5
Revises: i9d0e1f2a3b4
Create Date: 2026-11-14 02:05:00.000000

Phase 5 Migration J — M5.6 Export Records:
  - Create `export_records` table
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'j0e1f2a3b4c5'
down_revision: Union[str, None] = 'i9d0e1f2a3b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "export_records",
        sa.Column("id", sa.String(36), primary_key=True, nullable=False),
        sa.Column(
            "run_id",
            sa.String(36),
            sa.ForeignKey("research_runs.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "report_id",
            sa.String(36),
            sa.ForeignKey("research_reports.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("format", sa.String(10), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("file_path", sa.Text(), nullable=True),
        sa.Column("file_size_bytes", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
    )
    op.create_index(
        "idx_export_records_run_id",
        "export_records",
        ["run_id"],
    )


def downgrade() -> None:
    op.drop_table("export_records")
