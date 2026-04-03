"""add ingestion job date range fields

Revision ID: 0010_ingestion_job_date_range
Revises: 0009_notebook_podcast_audio_jobs
Create Date: 2026-04-03 15:40:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0010_ingestion_job_date_range"
down_revision = "0009_notebook_podcast_audio_jobs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("ingestion_jobs", sa.Column("date_from", sa.String(length=10), nullable=True))
    op.add_column("ingestion_jobs", sa.Column("date_to", sa.String(length=10), nullable=True))


def downgrade() -> None:
    op.drop_column("ingestion_jobs", "date_to")
    op.drop_column("ingestion_jobs", "date_from")
