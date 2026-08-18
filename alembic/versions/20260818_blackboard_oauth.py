"""Secure per-connection Blackboard OAuth state.

Revision ID: 20260818_blackboard_oauth
Revises:
Create Date: 2026-08-18
"""

from alembic import op
import sqlalchemy as sa


revision = "20260818_blackboard_oauth"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("lms_connections", sa.Column("base_url", sa.String(), nullable=True))
    op.create_table(
        "lms_oauth_states",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("state_hash", sa.String(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(), nullable=False),
        sa.Column("lms_connection_id", sa.Integer(), nullable=False),
        sa.Column("code_verifier_encrypted", sa.Text(), nullable=False),
        sa.Column("return_path", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("consumed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["lms_connection_id"], ["lms_connections.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("state_hash"),
    )
    op.create_index("ix_lms_oauth_states_id", "lms_oauth_states", ["id"])
    op.create_index("ix_lms_oauth_states_state_hash", "lms_oauth_states", ["state_hash"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_lms_oauth_states_state_hash", table_name="lms_oauth_states")
    op.drop_index("ix_lms_oauth_states_id", table_name="lms_oauth_states")
    op.drop_table("lms_oauth_states")
    op.drop_column("lms_connections", "base_url")
