"""add notebook podcast audio job fields

Revision ID: 0009_notebook_podcast_audio_jobs
Revises: 0008_notebook_podcast_scripts
Create Date: 2026-04-02 20:05:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0009_notebook_podcast_audio_jobs"
down_revision = "0008_notebook_podcast_scripts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("notebook_podcast_scripts", sa.Column("audio_job_id", sa.String(length=64), nullable=True))
    op.add_column("notebook_podcast_scripts", sa.Column("audio_error", sa.Text(), nullable=True))
    op.create_index(
        op.f("ix_notebook_podcast_scripts_audio_job_id"),
        "notebook_podcast_scripts",
        ["audio_job_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_notebook_podcast_scripts_audio_job_id"), table_name="notebook_podcast_scripts")
    op.drop_column("notebook_podcast_scripts", "audio_error")
    op.drop_column("notebook_podcast_scripts", "audio_job_id")
