"""phase4_migration_f_citations

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-11-11 21:00:00.000000

Phase 4 Migration F — M4.6 Citation Management:
  - New table: citations
  - New columns: research_reports.has_validated_citations, research_reports.review_status
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f6a7b8c9d0e1'
down_revision: Union[str, Sequence[str], None] = 'e5f6a7b8c9d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Phase 4 Migration F.
    1. Create citations table
    2. Add has_validated_citations to research_reports
    3. Add review_status to research_reports
    """
    # 1. Create citations table
    op.create_table(
        'citations',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('run_id', sa.String(length=36), nullable=False),
        sa.Column('report_id', sa.String(length=36), nullable=False),
        sa.Column('claim_id', sa.String(length=36), nullable=True),
        sa.Column('evidence_id', sa.String(length=36), nullable=False),
        sa.Column('source_id', sa.String(length=36), nullable=True),
        sa.Column('citation_key', sa.String(length=50), nullable=False),
        sa.Column('page_reference', sa.String(length=100), nullable=True),
        sa.Column('section_reference', sa.String(length=200), nullable=True),
        sa.Column('url', sa.String(length=2000), nullable=True),
        sa.Column('doi', sa.String(length=200), nullable=True),
        sa.Column('apa_formatted', sa.Text(), nullable=True),
        sa.Column('ieee_formatted', sa.Text(), nullable=True),
        sa.Column('is_verified', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('validation_notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['run_id'], ['research_runs.id'],
                                name='fk_citations_run_id', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['report_id'], ['research_reports.id'],
                                name='fk_citations_report_id', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['claim_id'], ['claims.id'],
                                name='fk_citations_claim_id', ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['evidence_id'], ['evidence_records.id'],
                                name='fk_citations_evidence_id', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['source_id'], ['sources.id'],
                                name='fk_citations_source_id', ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('citations', schema=None) as batch_op:
        batch_op.create_index('ix_citations_run_id', ['run_id'], unique=False)
        batch_op.create_index('ix_citations_report_id', ['report_id'], unique=False)
        batch_op.create_index('ix_citations_evidence_id', ['evidence_id'], unique=False)
        batch_op.create_index('ix_citations_source_id', ['source_id'], unique=False)
        batch_op.create_index('ix_citations_claim_id', ['claim_id'], unique=False)
        batch_op.create_index('ix_citations_citation_key', ['citation_key'], unique=False)

    # 2. Add has_validated_citations to research_reports
    with op.batch_alter_table('research_reports', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('has_validated_citations', sa.Boolean(), nullable=False, server_default='0')
        )
        # 3. Add review_status to research_reports
        batch_op.add_column(
            sa.Column('review_status', sa.String(length=50), nullable=True)
        )


def downgrade() -> None:
    """Reverse Phase 4 Migration F."""
    # 3. Remove review_status from research_reports
    # 2. Remove has_validated_citations from research_reports
    with op.batch_alter_table('research_reports', schema=None) as batch_op:
        batch_op.drop_column('review_status')
        batch_op.drop_column('has_validated_citations')

    # 1. Drop citations
    with op.batch_alter_table('citations', schema=None) as batch_op:
        batch_op.drop_index('ix_citations_citation_key')
        batch_op.drop_index('ix_citations_claim_id')
        batch_op.drop_index('ix_citations_source_id')
        batch_op.drop_index('ix_citations_evidence_id')
        batch_op.drop_index('ix_citations_report_id')
        batch_op.drop_index('ix_citations_run_id')
    op.drop_table('citations')
