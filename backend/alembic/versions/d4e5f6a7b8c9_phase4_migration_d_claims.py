"""phase4_migration_d_claims

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-11-11 19:00:00.000000

Phase 4 Migration D — M4.4 Claim Identification and Verification:
  - New table: claims
  - New table: claim_verifications
  - New column: research_runs.verification_depth
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, Sequence[str], None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Phase 4 Migration D.
    1. Create claims table
    2. Create claim_verifications table
    3. Add verification_depth to research_runs
    """
    # 1. Create claims table
    op.create_table(
        'claims',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('run_id', sa.String(length=36), nullable=False),
        sa.Column('report_id', sa.String(length=36), nullable=True),
        sa.Column('claim_text', sa.Text(), nullable=False),
        sa.Column('claim_type', sa.String(length=50), nullable=False, server_default='factual'),
        sa.Column('originating_section', sa.String(length=200), nullable=False, server_default='key_findings'),
        sa.Column('is_high_impact', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['run_id'], ['research_runs.id'],
                                name='fk_claims_run_id', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['report_id'], ['research_reports.id'],
                                name='fk_claims_report_id', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('claims', schema=None) as batch_op:
        batch_op.create_index('ix_claims_run_id', ['run_id'], unique=False)
        batch_op.create_index('ix_claims_report_id', ['report_id'], unique=False)
        batch_op.create_index('ix_claims_claim_type', ['claim_type'], unique=False)

    # 2. Create claim_verifications table
    op.create_table(
        'claim_verifications',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('claim_id', sa.String(length=36), nullable=False),
        sa.Column('run_id', sa.String(length=36), nullable=False),
        sa.Column('verification_status', sa.String(length=50), nullable=False, server_default='unverified'),
        sa.Column('supporting_evidence_ids', sa.Text(), nullable=True),
        sa.Column('contradicting_evidence_ids', sa.Text(), nullable=True),
        sa.Column('reasoning_summary', sa.Text(), nullable=True),
        sa.Column('evidence_limitations', sa.Text(), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('verified_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['claim_id'], ['claims.id'],
                                name='fk_claim_verifications_claim_id', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['run_id'], ['research_runs.id'],
                                name='fk_claim_verifications_run_id', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('claim_verifications', schema=None) as batch_op:
        batch_op.create_index('ix_claim_verifications_claim_id', ['claim_id'], unique=False)
        batch_op.create_index('ix_claim_verifications_run_id', ['run_id'], unique=False)
        batch_op.create_index('ix_claim_verifications_status', ['verification_status'], unique=False)

    # 3. Add verification_depth to research_runs
    with op.batch_alter_table('research_runs', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('verification_depth', sa.String(length=20), nullable=False, server_default='basic')
        )


def downgrade() -> None:
    """Reverse Phase 4 Migration D."""
    # 3. Remove verification_depth from research_runs
    with op.batch_alter_table('research_runs', schema=None) as batch_op:
        batch_op.drop_column('verification_depth')

    # 2. Drop claim_verifications
    with op.batch_alter_table('claim_verifications', schema=None) as batch_op:
        batch_op.drop_index('ix_claim_verifications_status')
        batch_op.drop_index('ix_claim_verifications_run_id')
        batch_op.drop_index('ix_claim_verifications_claim_id')
    op.drop_table('claim_verifications')

    # 1. Drop claims
    with op.batch_alter_table('claims', schema=None) as batch_op:
        batch_op.drop_index('ix_claims_claim_type')
        batch_op.drop_index('ix_claims_report_id')
        batch_op.drop_index('ix_claims_run_id')
    op.drop_table('claims')
