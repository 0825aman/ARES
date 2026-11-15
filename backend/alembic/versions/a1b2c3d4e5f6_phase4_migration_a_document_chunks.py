"""phase4_migration_a_document_chunks

Revision ID: a1b2c3d4e5f6
Revises: 219aca45d63e
Create Date: 2026-11-11 16:00:00.000000

Phase 4 Migration A — M4.1 Advanced Document Processing:
  - New table: document_chunks
  - New columns on uploaded_documents: chunk_count, has_images, ocr_attempted
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '219aca45d63e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Phase 4 Migration A:
    1. Create document_chunks table
    2. Add chunk_count, has_images, ocr_attempted to uploaded_documents
    """
    # 1. Create document_chunks table
    op.create_table(
        'document_chunks',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('document_id', sa.String(length=36), nullable=False),
        sa.Column('chunk_index', sa.Integer(), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('page_start', sa.Integer(), nullable=True),
        sa.Column('page_end', sa.Integer(), nullable=True),
        sa.Column('section_title', sa.String(length=500), nullable=True),
        sa.Column('heading_level', sa.Integer(), nullable=True),
        sa.Column('extraction_method', sa.String(length=50), nullable=True),
        sa.Column('char_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('has_tables', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ['document_id'], ['uploaded_documents.id'],
            name='fk_chunks_document_id',
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('document_chunks', schema=None) as batch_op:
        batch_op.create_index('ix_document_chunks_document_id', ['document_id'], unique=False)
        batch_op.create_index(
            'ix_document_chunks_document_chunk_idx',
            ['document_id', 'chunk_index'],
            unique=False,
        )

    # 2. Add chunk_count, has_images, ocr_attempted to uploaded_documents
    # server_default ensures existing rows receive the correct default value.
    with op.batch_alter_table('uploaded_documents', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('chunk_count', sa.Integer(), nullable=False, server_default='0')
        )
        batch_op.add_column(
            sa.Column('has_images', sa.Boolean(), nullable=False, server_default='0')
        )
        batch_op.add_column(
            sa.Column('ocr_attempted', sa.Boolean(), nullable=False, server_default='0')
        )


def downgrade() -> None:
    """Reverse Phase 4 Migration A.

    Note on SQLite column drops: SQLite does not support DROP COLUMN natively
    prior to version 3.35.0 (2021-03-12).  Alembic's batch_alter_table uses a
    table-rebuild strategy which recreates the table without the dropped columns,
    preserving all existing data.  This is safe on SQLite.
    """
    # 2. Remove new columns from uploaded_documents
    with op.batch_alter_table('uploaded_documents', schema=None) as batch_op:
        batch_op.drop_column('ocr_attempted')
        batch_op.drop_column('has_images')
        batch_op.drop_column('chunk_count')

    # 1. Drop document_chunks (indexes are dropped automatically with the table in SQLite)
    with op.batch_alter_table('document_chunks', schema=None) as batch_op:
        batch_op.drop_index('ix_document_chunks_document_chunk_idx')
        batch_op.drop_index('ix_document_chunks_document_id')
    op.drop_table('document_chunks')
