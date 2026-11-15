"""phase5_migration_i_report_versioning

Revision ID: i9d0e1f2a3b4
Revises: h8c9d0e1f2a3
Create Date: 2026-11-14 02:00:00.000000

Phase 5 Migration I — M5.6 Report Versioning:
  - Add `version_number` INTEGER column to `research_reports` (default 1)
  - Add `is_current` BOOLEAN column to `research_reports` (default TRUE)
  - Remove old UNIQUE constraint on `run_id` (SQLite-compatible: recreate table)
  - Add new UNIQUE constraint on (run_id, version_number)
  - Create `report_versions` archive table
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'i9d0e1f2a3b4'
down_revision: Union[str, None] = 'h8c9d0e1f2a3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Add version_number and is_current to research_reports ─────────────────
    # SQLite does not support DROP CONSTRAINT — the unique constraint on run_id
    # was originally defined in the model. Since SQLite ignores inline UNIQUE
    # on a column that also has index=True (they're treated as the same thing),
    # we just add the new columns. The old UNIQUE is effectively replaced by the
    # combination (run_id, version_number) via a new index.
    with op.batch_alter_table("research_reports") as batch_op:
        batch_op.add_column(
            sa.Column(
                "version_number",
                sa.Integer(),
                nullable=False,
                server_default="1",
            )
        )
        batch_op.add_column(
            sa.Column(
                "is_current",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("1"),  # SQLite TRUE = 1
            )
        )
        # Remove old UNIQUE on run_id (named uq_research_reports_run_id)
        # and replace with UNIQUE on (run_id, version_number)
        batch_op.drop_constraint("uq_research_reports_run_id", type_="unique")
        batch_op.create_unique_constraint(
            "uq_research_reports_run_version",
            ["run_id", "version_number"],
        )
        batch_op.create_index(
            "idx_research_reports_run_current",
            ["run_id", "is_current"],
        )

    # ── Create report_versions table ──────────────────────────────────────────
    op.create_table(
        "report_versions",
        sa.Column("id", sa.String(36), primary_key=True, nullable=False),
        sa.Column(
            "report_id",
            sa.String(36),
            sa.ForeignKey("research_reports.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("run_id", sa.String(36), nullable=False, index=True),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("archived_at", sa.DateTime(), nullable=False),
        sa.Column("content_snapshot", sa.Text(), nullable=False),
    )
    op.create_index(
        "idx_report_versions_run_id",
        "report_versions",
        ["run_id"],
    )


def downgrade() -> None:
    op.drop_table("report_versions")
    with op.batch_alter_table("research_reports") as batch_op:
        batch_op.drop_index("idx_research_reports_run_current")
        batch_op.drop_constraint("uq_research_reports_run_version", type_="unique")
        batch_op.create_unique_constraint("uq_research_reports_run_id", ["run_id"])
        batch_op.drop_column("is_current")
        batch_op.drop_column("version_number")
