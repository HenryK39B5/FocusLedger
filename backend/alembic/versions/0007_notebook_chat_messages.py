"""add notebook chat messages

Revision ID: 0007_notebook_chat_messages
Revises: 0006_notebooks
Create Date: 2026-04-02 22:40:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0007_notebook_chat_messages"
down_revision = "0006_notebooks"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "notebook_chat_messages",
        sa.Column("notebook_id", sa.String(length=32), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("citations", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["notebook_id"], ["notebooks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_notebook_chat_messages_notebook_id"), "notebook_chat_messages", ["notebook_id"], unique=False)
    op.create_index(op.f("ix_notebook_chat_messages_role"), "notebook_chat_messages", ["role"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_notebook_chat_messages_role"), table_name="notebook_chat_messages")
    op.drop_index(op.f("ix_notebook_chat_messages_notebook_id"), table_name="notebook_chat_messages")
    op.drop_table("notebook_chat_messages")
