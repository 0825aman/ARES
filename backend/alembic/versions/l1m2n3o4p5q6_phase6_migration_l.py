"""phase6_migration_l_auth_tables

Revision ID: l1m2n3o4p5q6
Revises: k1l2m3n4o5p6
Create Date: 2026-11-14 11:10:00.000000

Phase 6 Migration L — M6.2 Authentication:
  - Create `users` table (admin accounts)
  - Create `sessions` table (HTTP-only session tokens)
  - Create `login_attempts` table (brute-force rate limiting)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'l1m2n3o4p5q6'
down_revision: Union[str, None] = 'k1l2m3n4o5p6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True, nullable=False),
        sa.Column("username", sa.String(50), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(200), nullable=False),
        sa.Column("role", sa.String(20), nullable=False, server_default="admin"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("last_login", sa.DateTime(), nullable=True),
    )
    op.create_index("idx_users_username", "users", ["username"])

    op.create_table(
        "sessions",
        sa.Column("id", sa.String(64), primary_key=True, nullable=False),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("ip_address", sa.String(45), nullable=True),
    )
    op.create_index("idx_sessions_user_id", "sessions", ["user_id"])

    op.create_table(
        "login_attempts",
        sa.Column("id", sa.String(36), primary_key=True, nullable=False),
        sa.Column("username", sa.String(50), nullable=False),
        sa.Column("ip_address", sa.String(45), nullable=False),
        sa.Column("succeeded", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("attempted_at", sa.DateTime(), nullable=False),
    )
    op.create_index("idx_login_attempts_username", "login_attempts", ["username"])
    op.create_index("idx_login_attempts_attempted_at", "login_attempts", ["attempted_at"])


def downgrade() -> None:
    op.drop_table("login_attempts")
    op.drop_table("sessions")
    op.drop_table("users")
