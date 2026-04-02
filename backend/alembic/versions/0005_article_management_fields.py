"""add article management fields

Revision ID: 0005_article_management_fields
Revises: 0004_ingestion_jobs
Create Date: 2026-04-01
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0005_article_management_fields"
down_revision = "0004_ingestion_jobs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "articles",
        sa.Column("is_favorited", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "articles",
        sa.Column("llm_summary_status", sa.String(length=32), nullable=False, server_default=sa.text("'pending'")),
    )
    op.add_column(
        "articles",
        sa.Column("llm_summary_updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "articles",
        sa.Column("llm_summary_error", sa.Text(), nullable=True),
    )
    op.create_index("ix_articles_is_favorited", "articles", ["is_favorited"])
    op.create_index("ix_articles_llm_summary_status", "articles", ["llm_summary_status"])


def downgrade() -> None:
    op.drop_index("ix_articles_llm_summary_status", table_name="articles")
    op.drop_index("ix_articles_is_favorited", table_name="articles")
    op.drop_column("articles", "llm_summary_error")
    op.drop_column("articles", "llm_summary_updated_at")
    op.drop_column("articles", "llm_summary_status")
    op.drop_column("articles", "is_favorited")
