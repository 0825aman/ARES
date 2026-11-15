"""phase4_migration_e_critic_reviews

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-11-11 20:00:00.000000

Phase 4 Migration E — M4.5 Critic / Reviewer Agent:
  - New table: critic_reviews
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e5f6a7b8c9d0'
down_revision: Union[str, Sequence[str], None] = 'd4e5f6a7b8c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Phase 4 Migration E — create critic_reviews table."""
    op.create_table(
        'critic_reviews',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('run_id', sa.String(length=36), nullable=False),
        sa.Column('review_version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('overall_assessment', sa.String(length=50), nullable=False, server_default='adequate'),
        sa.Column('review_status', sa.String(length=50), nullable=False, server_default='needs_attention'),
        sa.Column('recommended_action', sa.String(length=50), nullable=False, server_default='revise_report'),
        sa.Column('unsupported_claims', sa.Text(), nullable=True),
        sa.Column('citation_issues', sa.Text(), nullable=True),
        sa.Column('contradictory_findings', sa.Text(), nullable=True),
        sa.Column('missing_evidence', sa.Text(), nullable=True),
        sa.Column('source_quality_issues', sa.Text(), nullable=True),
        sa.Column('reasoning_issues', sa.Text(), nullable=True),
        sa.Column('review_summary', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ['run_id'], ['research_runs.id'],
            name='fk_critic_reviews_run_id', ondelete='CASCADE'
        ),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('critic_reviews', schema=None) as batch_op:
        batch_op.create_index('ix_critic_reviews_run_id', ['run_id'], unique=False)
        batch_op.create_index('ix_critic_reviews_review_version', ['review_version'], unique=False)


def downgrade() -> None:
    """Reverse Phase 4 Migration E — drop critic_reviews table."""
    with op.batch_alter_table('critic_reviews', schema=None) as batch_op:
        batch_op.drop_index('ix_critic_reviews_review_version')
        batch_op.drop_index('ix_critic_reviews_run_id')
    op.drop_table('critic_reviews')
