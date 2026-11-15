"""phase5_migration_h_sse_sequence_and_approval_requests

Revision ID: h8c9d0e1f2a3
Revises: g7b8c9d0e1f2
Create Date: 2026-11-12 18:00:00.000000

Phase 5 Migration H — M5.1 Backend SSE Infrastructure:
  - Add `sequence` INTEGER column to `agent_execution_events`
  - Back-fill sequence values ordered by created_at within each run_id
  - Create `approval_requests` table
  - Add indexes on approval_requests(run_id) and approval_requests(run_id, status)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'h8c9d0e1f2a3'
down_revision: Union[str, Sequence[str], None] = 'g7b8c9d0e1f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Phase 5 Migration H — event sequencing and approval requests."""

    # ── 1. Add sequence column to agent_execution_events ──────────────────────
    with op.batch_alter_table('agent_execution_events', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('sequence', sa.Integer(), nullable=True)
        )

    # Back-fill: assign per-run sequence numbers ordered by (created_at, id)
    # Uses a correlated sub-query compatible with SQLite.
    op.execute(
        """
        UPDATE agent_execution_events
        SET sequence = (
            SELECT COUNT(*)
            FROM agent_execution_events b
            WHERE b.run_id = agent_execution_events.run_id
              AND (
                  b.created_at < agent_execution_events.created_at
                  OR (
                      b.created_at = agent_execution_events.created_at
                      AND b.id <= agent_execution_events.id
                  )
              )
        )
        WHERE sequence IS NULL
        """
    )

    # Unique index on (run_id, sequence) for fast replay queries
    op.create_index(
        'idx_agent_events_run_sequence',
        'agent_execution_events',
        ['run_id', 'sequence'],
        unique=True,
    )

    # ── 2. Create approval_requests table ─────────────────────────────────────
    op.create_table(
        'approval_requests',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column(
            'run_id',
            sa.String(36),
            sa.ForeignKey('research_runs.id', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column('checkpoint_name', sa.String(100), nullable=False),
        sa.Column('node_name', sa.String(100), nullable=False),
        sa.Column('context_snapshot', sa.Text(), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('decision', sa.String(30), nullable=True),
        sa.Column('decision_notes', sa.Text(), nullable=True),
        sa.Column(
            'created_at',
            sa.DateTime(),
            nullable=False,
            server_default=sa.text('CURRENT_TIMESTAMP'),
        ),
        sa.Column('decided_at', sa.DateTime(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
    )

    op.create_index(
        'idx_approval_requests_run_id',
        'approval_requests',
        ['run_id'],
        unique=False,
    )
    op.create_index(
        'idx_approval_requests_run_status',
        'approval_requests',
        ['run_id', 'status'],
        unique=False,
    )


def downgrade() -> None:
    """Reverse Phase 5 Migration H."""
    op.drop_index('idx_approval_requests_run_status', table_name='approval_requests')
    op.drop_index('idx_approval_requests_run_id', table_name='approval_requests')
    op.drop_table('approval_requests')

    op.drop_index('idx_agent_events_run_sequence', table_name='agent_execution_events')

    with op.batch_alter_table('agent_execution_events', schema=None) as batch_op:
        batch_op.drop_column('sequence')
