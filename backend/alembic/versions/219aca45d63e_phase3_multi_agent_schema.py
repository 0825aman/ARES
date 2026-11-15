"""phase3_multi_agent_schema

Revision ID: 219aca45d63e
Revises: 835db006d5e4
Create Date: 2026-11-11 15:40:45.247700

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '219aca45d63e'
down_revision: Union[str, Sequence[str], None] = '835db006d5e4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Phase 3 schema additions:
    - New tables: agent_execution_events, research_plans, research_tasks
    - New columns: evidence_records.task_id, research_runs.workflow_mode
    """
    # 1. Create agent_execution_events
    op.create_table(
        'agent_execution_events',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('run_id', sa.String(length=36), nullable=False),
        sa.Column('agent_name', sa.String(length=50), nullable=False),
        sa.Column('event_type', sa.String(length=50), nullable=False),
        sa.Column('summary', sa.Text(), nullable=False),
        sa.Column('input_ref', sa.String(length=200), nullable=True),
        sa.Column('output_ref', sa.String(length=200), nullable=True),
        sa.Column('iteration', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['run_id'], ['research_runs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('agent_execution_events', schema=None) as batch_op:
        batch_op.create_index('ix_agent_execution_events_created_at', ['created_at'], unique=False)
        batch_op.create_index('ix_agent_execution_events_run_id', ['run_id'], unique=False)

    # 2. Create research_plans
    op.create_table(
        'research_plans',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('run_id', sa.String(length=36), nullable=False),
        sa.Column('objectives', sa.Text(), nullable=False),
        sa.Column('refinement_notes', sa.Text(), nullable=True),
        sa.Column('plan_version', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['run_id'], ['research_runs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('run_id', 'plan_version', name='uq_research_plans_run_version'),
    )
    with op.batch_alter_table('research_plans', schema=None) as batch_op:
        batch_op.create_index('ix_research_plans_run_id', ['run_id'], unique=False)

    # 3. Create research_tasks
    op.create_table(
        'research_tasks',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('plan_id', sa.String(length=36), nullable=False),
        sa.Column('run_id', sa.String(length=36), nullable=False),
        sa.Column('task_order', sa.Integer(), nullable=False),
        sa.Column('objective', sa.Text(), nullable=False),
        sa.Column('search_query', sa.Text(), nullable=False),
        sa.Column('expected_evidence_type', sa.String(length=100), nullable=True),
        sa.Column('priority', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('findings', sa.Text(), nullable=True),
        sa.Column('evidence_count', sa.Integer(), nullable=False),
        sa.Column('unanswered_questions', sa.Text(), nullable=True),
        sa.Column('limitations', sa.Text(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['plan_id'], ['research_plans.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['run_id'], ['research_runs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('research_tasks', schema=None) as batch_op:
        batch_op.create_index('ix_research_tasks_plan_id', ['plan_id'], unique=False)
        batch_op.create_index('ix_research_tasks_run_id', ['run_id'], unique=False)
        batch_op.create_index('ix_research_tasks_status', ['status'], unique=False)

    # 4. Add task_id column to evidence_records (nullable FK to research_tasks)
    with op.batch_alter_table('evidence_records', schema=None) as batch_op:
        batch_op.add_column(sa.Column('task_id', sa.String(length=36), nullable=True))
        batch_op.create_index('ix_evidence_records_task_id', ['task_id'], unique=False)
        batch_op.create_foreign_key(
            'fk_evidence_records_task_id',
            'research_tasks', ['task_id'], ['id'],
            ondelete='SET NULL',
        )

    # 5. Add workflow_mode column to research_runs (defaults to 'sequential')
    with op.batch_alter_table('research_runs', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('workflow_mode', sa.String(length=20), nullable=False, server_default='sequential')
        )
        batch_op.create_index('ix_research_runs_workflow_mode', ['workflow_mode'], unique=False)


def downgrade() -> None:
    """Reverse Phase 3 schema additions."""
    # 5. Remove workflow_mode from research_runs
    with op.batch_alter_table('research_runs', schema=None) as batch_op:
        batch_op.drop_index('ix_research_runs_workflow_mode')
        batch_op.drop_column('workflow_mode')

    # 4. Remove task_id from evidence_records
    with op.batch_alter_table('evidence_records', schema=None) as batch_op:
        batch_op.drop_constraint('fk_evidence_records_task_id', type_='foreignkey')
        batch_op.drop_index('ix_evidence_records_task_id')
        batch_op.drop_column('task_id')

    # 3. Drop research_tasks
    with op.batch_alter_table('research_tasks', schema=None) as batch_op:
        batch_op.drop_index('ix_research_tasks_status')
        batch_op.drop_index('ix_research_tasks_run_id')
        batch_op.drop_index('ix_research_tasks_plan_id')
    op.drop_table('research_tasks')

    # 2. Drop research_plans
    with op.batch_alter_table('research_plans', schema=None) as batch_op:
        batch_op.drop_index('ix_research_plans_run_id')
    op.drop_table('research_plans')

    # 1. Drop agent_execution_events
    with op.batch_alter_table('agent_execution_events', schema=None) as batch_op:
        batch_op.drop_index('ix_agent_execution_events_run_id')
        batch_op.drop_index('ix_agent_execution_events_created_at')
    op.drop_table('agent_execution_events')
