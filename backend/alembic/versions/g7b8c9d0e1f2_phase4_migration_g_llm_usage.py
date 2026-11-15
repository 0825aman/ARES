"""phase4_migration_g_llm_usage_tracking

Revision ID: g7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-11-11 22:00:00.000000

Phase 4 Migration G — M4.7 LLM Usage Tracking:
  - New columns on research_runs: llm_call_count, total_tokens_used, estimated_cost_usd
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'g7b8c9d0e1f2'
down_revision: Union[str, Sequence[str], None] = 'f6a7b8c9d0e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Phase 4 Migration G — add LLM usage tracking columns to research_runs."""
    with op.batch_alter_table('research_runs', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('llm_call_count', sa.Integer(), nullable=False, server_default='0')
        )
        batch_op.add_column(
            sa.Column('total_tokens_used', sa.Integer(), nullable=False, server_default='0')
        )
        batch_op.add_column(
            sa.Column('estimated_cost_usd', sa.Float(), nullable=False, server_default='0.0')
        )


def downgrade() -> None:
    """Reverse Phase 4 Migration G."""
    with op.batch_alter_table('research_runs', schema=None) as batch_op:
        batch_op.drop_column('estimated_cost_usd')
        batch_op.drop_column('total_tokens_used')
        batch_op.drop_column('llm_call_count')
