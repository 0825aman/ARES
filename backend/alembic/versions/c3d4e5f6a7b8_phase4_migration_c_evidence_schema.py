"""phase4_migration_c_evidence_schema_extension

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-11-11 18:00:00.000000

Phase 4 Migration C — M4.3 Evidence Schema Extension:
  - 7 new columns on evidence_records (all backward compatible)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, Sequence[str], None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Phase 4 Migration C — add 7 columns to evidence_records.

    All new columns are backward compatible:
      - source_id, chunk_id, section_name, extraction_method, extraction_confidence: nullable
      - evidence_type: server_default='other'
      - evidence_relationship: server_default='neutral'
    """
    with op.batch_alter_table('evidence_records', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('source_id', sa.String(length=36), nullable=True)
        )
        batch_op.add_column(
            sa.Column('chunk_id', sa.String(length=36), nullable=True)
        )
        batch_op.add_column(
            sa.Column('evidence_type', sa.String(length=50), nullable=False, server_default='other')
        )
        batch_op.add_column(
            sa.Column('evidence_relationship', sa.String(length=50), nullable=False, server_default='neutral')
        )
        batch_op.add_column(
            sa.Column('section_name', sa.String(length=500), nullable=True)
        )
        batch_op.add_column(
            sa.Column('extraction_method', sa.String(length=50), nullable=True)
        )
        batch_op.add_column(
            sa.Column('extraction_confidence', sa.Float(), nullable=True)
        )
        # Indexes for common filter queries
        batch_op.create_index('ix_evidence_records_source_id', ['source_id'], unique=False)
        batch_op.create_index('ix_evidence_records_evidence_type', ['evidence_type'], unique=False)
        batch_op.create_index('ix_evidence_records_evidence_relationship', ['evidence_relationship'], unique=False)
        # FK constraints — using named constraints for clean downgrade
        batch_op.create_foreign_key(
            'fk_evidence_source_id',
            'sources', ['source_id'], ['id'],
            ondelete='SET NULL',
        )
        batch_op.create_foreign_key(
            'fk_evidence_chunk_id',
            'document_chunks', ['chunk_id'], ['id'],
            ondelete='SET NULL',
        )


def downgrade() -> None:
    """Reverse Phase 4 Migration C.

    Note: SQLite uses batch_alter_table for column drops (table-rebuild strategy).
    All data in the dropped columns will be lost on downgrade.
    """
    with op.batch_alter_table('evidence_records', schema=None) as batch_op:
        batch_op.drop_constraint('fk_evidence_chunk_id', type_='foreignkey')
        batch_op.drop_constraint('fk_evidence_source_id', type_='foreignkey')
        batch_op.drop_index('ix_evidence_records_evidence_relationship')
        batch_op.drop_index('ix_evidence_records_evidence_type')
        batch_op.drop_index('ix_evidence_records_source_id')
        batch_op.drop_column('extraction_confidence')
        batch_op.drop_column('extraction_method')
        batch_op.drop_column('section_name')
        batch_op.drop_column('evidence_relationship')
        batch_op.drop_column('evidence_type')
        batch_op.drop_column('chunk_id')
        batch_op.drop_column('source_id')
