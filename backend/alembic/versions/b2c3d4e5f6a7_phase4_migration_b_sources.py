"""phase4_migration_b_sources

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-11-11 17:00:00.000000

Phase 4 Migration B — M4.2 Multi-Provider Source Collection:
  - New table: sources
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Phase 4 Migration B — create sources table."""
    op.create_table(
        'sources',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('run_id', sa.String(length=36), nullable=False),
        sa.Column('source_type', sa.String(length=50), nullable=False),
        sa.Column('title', sa.String(length=1000), nullable=True),
        sa.Column('url', sa.String(length=2000), nullable=True),
        sa.Column('doi', sa.String(length=200), nullable=True),
        sa.Column('authors', sa.Text(), nullable=True),
        sa.Column('publisher', sa.String(length=500), nullable=True),
        sa.Column('venue', sa.String(length=500), nullable=True),
        sa.Column('publication_date', sa.String(length=50), nullable=True),
        sa.Column('is_peer_reviewed', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('retrieval_provider', sa.String(length=50), nullable=False),
        sa.Column('retrieved_at', sa.DateTime(), nullable=False),
        sa.Column('content_hash', sa.String(length=64), nullable=True),
        sa.Column('is_accessible', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('credibility_notes', sa.Text(), nullable=True),
        sa.Column('metadata_json', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ['run_id'], ['research_runs.id'],
            name='fk_sources_run_id',
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('sources', schema=None) as batch_op:
        batch_op.create_index('ix_sources_run_id', ['run_id'], unique=False)
        batch_op.create_index('ix_sources_content_hash', ['content_hash'], unique=False)
        batch_op.create_index('ix_sources_retrieval_provider', ['retrieval_provider'], unique=False)


def downgrade() -> None:
    """Reverse Phase 4 Migration B — drop sources table."""
    with op.batch_alter_table('sources', schema=None) as batch_op:
        batch_op.drop_index('ix_sources_retrieval_provider')
        batch_op.drop_index('ix_sources_content_hash')
        batch_op.drop_index('ix_sources_run_id')
    op.drop_table('sources')
