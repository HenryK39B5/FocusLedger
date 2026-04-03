"""add notebook podcast scripts

Revision ID: 0008_notebook_podcast_scripts
Revises: 0007_notebook_chat_messages
Create Date: 2026-04-02 23:25:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0008_notebook_podcast_scripts"
down_revision = "0007_notebook_chat_messages"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "notebook_podcast_scripts",
        sa.Column("notebook_id", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("format", sa.String(length=32), nullable=False),
        sa.Column("target_minutes", sa.Integer(), nullable=False),
        sa.Column("focus_prompt", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("audio_status", sa.String(length=32), nullable=False),
        sa.Column("audio_path", sa.String(length=1024), nullable=True),
        sa.Column("generation_error", sa.Text(), nullable=True),
        sa.Column("cited_article_ids", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("script_markdown", sa.Text(), nullable=False),
        sa.Column("script_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["notebook_id"], ["notebooks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_notebook_podcast_scripts_audio_status"), "notebook_podcast_scripts", ["audio_status"], unique=False)
    op.create_index(op.f("ix_notebook_podcast_scripts_format"), "notebook_podcast_scripts", ["format"], unique=False)
    op.create_index(op.f("ix_notebook_podcast_scripts_notebook_id"), "notebook_podcast_scripts", ["notebook_id"], unique=False)
    op.create_index(op.f("ix_notebook_podcast_scripts_status"), "notebook_podcast_scripts", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_notebook_podcast_scripts_status"), table_name="notebook_podcast_scripts")
    op.drop_index(op.f("ix_notebook_podcast_scripts_notebook_id"), table_name="notebook_podcast_scripts")
    op.drop_index(op.f("ix_notebook_podcast_scripts_format"), table_name="notebook_podcast_scripts")
    op.drop_index(op.f("ix_notebook_podcast_scripts_audio_status"), table_name="notebook_podcast_scripts")
    op.drop_table("notebook_podcast_scripts")
